"""
Relationship Engine - Discovers and creates relationships (edges) between entities

This engine operates independently of the Archivist to enable:
- Cross-event analysis (finds connections across the entire graph)
- Iterative refinement (can be re-run to improve edge quality)
- Flexible detection strategies (not limited to predefined relationship types)

Based on neuroscientific principles:
- Hebbian Learning (LTP): "Neurons that fire together, wire together"
- Systems Consolidation: Offline processing strengthens connections
- Synaptic Homeostasis: Weak connections are pruned
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from services.database import DatabaseService
from anthropic import Anthropic
from config import settings
import logging
import re
import json

logger = logging.getLogger(__name__)


class RelationshipEngine:
    """
    Discovers and creates relationships (edges) between entities in the graph.

    Operates independently of the Archivist to enable cross-event analysis,
    iterative refinement, and flexible detection strategies.
    """

    def __init__(self):
        self.db = DatabaseService()
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Strategy weights (can be tuned)
        self.strategy_weights = {
            'semantic_llm': 1.0,
            'pattern_based': 1.0,
            'embedding_similarity': 0.8,
            'temporal': 0.7,
            'graph_topology': 0.6
        }

        # Thresholds
        self.min_confidence = 0.5  # Don't create edges below this
        self.max_edges_per_run = 10000  # Safety limit

        logger.info("RelationshipEngine initialized")

    # ==================== PUBLIC API ====================

    def run_incremental(self, event_id: str) -> Dict:
        """
        Incremental Mode: Analyze entities from a single event.

        Called after Archivist processes an event. Finds relationships
        between newly created entities and existing entities.

        Args:
            event_id: The event that was just processed

        Returns:
            {
                'edges_created': int,
                'edges_updated': int,
                'strategies_used': [str],
                'processing_time': float
            }
        """
        import time
        start_time = time.time()

        logger.info(f"Running incremental mode for event {event_id}")

        # Get entities created by this event
        entities = self.db.get_entities_by_event(event_id)

        if len(entities) < 2:
            logger.info(f"Event {event_id} has <2 entities, skipping incremental analysis")
            return {
                'edges_created': 0,
                'edges_updated': 0,
                'strategies_used': [],
                'processing_time': 0
            }

        # Get text context for this event
        event = self.db.get_event_by_id(event_id)
        context_text = event.payload.get('content', '') if event else None

        # Also get recent entities for cross-event connections
        existing_entities = self.db.get_recent_entities(limit=50)
        all_entities_objs = entities + existing_entities

        # Convert to dicts for strategy methods
        all_entities = [
            {
                'id': e.id,
                'title': e.title,
                'type': e.type,
                'summary': e.summary if hasattr(e, 'summary') else None,
                'metadata': e.metadata if hasattr(e, 'metadata') else {}
            }
            for e in all_entities_objs
        ]

        # Run CHEAP strategies only (fast, synchronous)
        strategies = [
            ('pattern_based', self.strategy_pattern_based(all_entities)),
            ('semantic_llm', self.strategy_semantic_llm(all_entities, context_text))
        ]

        edges_created = 0
        edges_updated = 0

        for strategy_name, relationships in strategies:
            filtered = self._filter_by_confidence(relationships)

            for rel in filtered:
                # Add metadata about source strategy
                rel['metadata'] = rel.get('metadata', {})
                rel['metadata']['source_strategy'] = strategy_name
                rel['metadata']['source_event_id'] = event_id

                # Create or reinforce edge
                was_updated = self.create_or_update_edge(rel)
                if was_updated:
                    edges_updated += 1
                else:
                    edges_created += 1

        elapsed = time.time() - start_time

        result = {
            'edges_created': edges_created,
            'edges_updated': edges_updated,
            'strategies_used': [s[0] for s in strategies],
            'processing_time': elapsed
        }

        logger.info(f"Incremental mode complete: {result}")
        return result

    def run_nightly(self, full_scan: bool = False) -> Dict:
        """
        Nightly Mode: Deep graph analysis during idle time.

        Runs expensive strategies (embeddings, graph topology) to find
        distant connections across the entire graph.

        Args:
            full_scan: If True, re-analyze all entities. If False, only
                      analyze entities created/updated since last run.

        Returns:
            {
                'edges_created': int,
                'edges_updated': int,
                'edges_pruned': int,
                'entities_analyzed': int,
                'processing_time': float
            }
        """
        import time
        start_time = time.time()

        logger.info(f"Starting nightly mode (full_scan={full_scan})")

        # Determine scope
        if full_scan:
            entities = self.db.get_all_entities()
        else:
            # Only entities created/updated in last 24 hours
            entities = self.db.get_entities_created_since(
                datetime.now() - timedelta(days=1)
            )

        entity_dicts = [
            {
                'id': e.id,
                'title': e.title,
                'type': e.type,
                'summary': e.summary if hasattr(e, 'summary') else None,
                'metadata': e.metadata if hasattr(e, 'metadata') else {}
            }
            for e in entities
        ]

        logger.info(f"Analyzing {len(entity_dicts)} entities")

        # Run ALL strategies (including expensive ones)
        strategies = [
            ('pattern_based', self.strategy_pattern_based(entity_dicts)),
            ('semantic_llm', self.strategy_semantic_llm(entity_dicts)),
            ('embedding_similarity', self.strategy_embedding_similarity(entity_dicts)),
            ('temporal', self.strategy_temporal(entity_dicts)),
            ('graph_topology', self.strategy_graph_topology([e['id'] for e in entity_dicts]))
        ]

        edges_created = 0
        edges_updated = 0

        for strategy_name, relationships in strategies:
            filtered = self._filter_by_confidence(relationships)

            for rel in filtered:
                rel['metadata'] = rel.get('metadata', {})
                rel['metadata']['source_strategy'] = strategy_name

                was_updated = self.create_or_update_edge(rel)
                if was_updated:
                    edges_updated += 1
                else:
                    edges_created += 1

        # Phase 2: Pruning (NREM sleep analog)
        logger.info("Applying global decay and pruning weak edges")

        edges_decayed = self.apply_global_decay(decay_factor=0.99)
        edges_pruned = self.prune_weak_edges(threshold=0.1)

        elapsed = time.time() - start_time

        result = {
            'edges_created': edges_created,
            'edges_updated': edges_updated,
            'edges_pruned': edges_pruned,
            'entities_analyzed': len(entities),
            'processing_time': elapsed
        }

        logger.info(f"Nightly mode complete: {result}")
        return result

    def run_on_demand(self, entity_ids: Optional[List[str]] = None) -> Dict:
        """
        On-Demand Mode: User-triggered analysis.

        Allows manual graph refinement or testing new strategies.

        Args:
            entity_ids: If provided, only analyze these entities.
                       If None, analyze entire graph.

        Returns: Same as run_nightly()
        """
        if entity_ids:
            entities = [self.db.get_entity_by_id(eid) for eid in entity_ids]
            entities = [e for e in entities if e]  # Filter out None
            logger.info(f"On-demand mode: analyzing {len(entities)} specified entities")
        else:
            entities = self.db.get_all_entities()
            logger.info(f"On-demand mode: analyzing entire graph ({len(entities)} entities)")

        # Run with same logic as nightly mode
        return self.run_nightly(full_scan=True)

    # ==================== DETECTION STRATEGIES ====================

    def strategy_semantic_llm(
        self,
        entities: List[Dict],
        context_text: Optional[str] = None
    ) -> List[Dict]:
        """
        Strategy 1: Semantic Co-Occurrence (LLM-Based)

        Uses Claude to analyze entities and their context to find
        meaningful relationships. NOT prescriptive - allows Claude
        to infer relationship types from the semantic content.

        Args:
            entities: List of entity dicts with id, title, type, summary
            context_text: Optional text context where entities appear

        Returns:
            List of relationship dicts
        """
        if len(entities) < 2:
            return []

        # Limit to avoid huge prompts (process in batches if needed)
        if len(entities) > 20:
            logger.warning(f"Truncating entity list from {len(entities)} to 20 for LLM analysis")
            entities = entities[:20]

        # Build entity list with short IDs for the prompt
        entity_list = []
        id_map = {}  # Maps short IDs back to full UUIDs
        for i, e in enumerate(entities):
            short_id = f"e{i}"
            id_map[short_id] = e['id']
            entity_str = f"  {short_id}: {e['title']} (type: {e['type']})"
            entity_list.append(entity_str)

        entity_list_str = "\n".join(entity_list)

        prompt = f"""You are analyzing entities in a personal knowledge graph to find meaningful connections.

ENTITIES:
{entity_list_str}

{f"CONTEXT TEXT:\\n{context_text[:1000]}\\n" if context_text else ""}

Your task: Find ALL meaningful relationships between these entities.

CRITICAL RULES:
1. Look for ANY connection type that makes semantic sense
2. Do NOT limit yourself to predefined relationship types
3. If two entities are clearly related, connect them - even if the relationship type is novel
4. Infer relationship_type from the context (e.g., "role_at", "worked_at", "inspired_by", "contradicts")
5. Be creative but grounded in the evidence

For each relationship, provide:
- from_entity_id: The source entity ID (use the short form like "e0", "e1")
- to_entity_id: The target entity ID (use the short form)
- relationship_type: A concise, meaningful type name (snake_case)
- confidence: 0.0 to 1.0 (how certain are you?)
- importance: 0.0 to 1.0 (how significant is this connection?)
- description: Rich context (1-2 sentences)
- start_date: YYYY-MM-DD or null
- end_date: YYYY-MM-DD or null

EXAMPLES:

Input:
  e0: Executive Director at Youth Empowerment Through Arts and Humanities (type: role)
  e1: Youth Empowerment Through Arts and Humanities (type: organization)

Output:
{{
  "relationships": [
    {{
      "from_entity_id": "e0",
      "to_entity_id": "e1",
      "relationship_type": "role_at",
      "confidence": 0.95,
      "importance": 0.85,
      "description": "Leadership position at the organization",
      "start_date": null,
      "end_date": null
    }}
  ]
}}

Return ONLY valid JSON with a "relationships" array. If no relationships exist, return {{"relationships": []}}.
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=8192,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            result = json.loads(content)
            relationships = result.get('relationships', [])

            # Map short IDs back to full UUIDs
            for rel in relationships:
                from_short = rel.get('from_entity_id')
                to_short = rel.get('to_entity_id')

                if from_short in id_map and to_short in id_map:
                    rel['from_id'] = id_map[from_short]
                    rel['to_id'] = id_map[to_short]
                    rel['kind'] = rel.pop('relationship_type')
                    # Remove the short IDs
                    del rel['from_entity_id']
                    del rel['to_entity_id']

            # Filter out relationships with missing IDs
            relationships = [r for r in relationships if 'from_id' in r and 'to_id' in r]

            logger.info(f"LLM strategy found {len(relationships)} relationships")
            return relationships

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in LLM strategy: {e}")
            logger.error(f"Raw response: {content[:500] if 'content' in locals() else 'N/A'}")
            return []
        except Exception as e:
            logger.error(f"Error in LLM strategy: {e}", exc_info=True)
            return []

    def strategy_pattern_based(self, entities: List[Dict]) -> List[Dict]:
        """
        Strategy 2: Pattern-Based Inference

        Fast, deterministic pattern matching. No LLM required.

        Patterns:
        - "Title at Organization"  role --role_at--> organization

        Args:
            entities: List of entity dicts

        Returns: List of relationship dicts
        """
        relationships = []

        # Pattern 1: Extract organization from role titles
        # Example: "CTO at Willow Education"  role_at relationship
        role_entities = [e for e in entities if e['type'] == 'role']
        org_entities = [e for e in entities if e['type'] == 'organization']

        for role in role_entities:
            role_title = role['title']

            # Try to extract organization name from role title
            # Patterns: "Title at Org", "Title, Org"
            patterns = [
                r'at\s+(.+?)(?:\s*\(|$)',  # "CTO at Willow Education"
                r',\s*(.+?)(?:\s*\(|$)',   # "CTO, Willow Education"
            ]

            for pattern in patterns:
                match = re.search(pattern, role_title, re.IGNORECASE)
                if match:
                    org_name_in_title = match.group(1).strip()

                    # Find matching organization entity
                    for org in org_entities:
                        org_title = org['title']

                        # Check for match (case-insensitive, partial)
                        if (org_name_in_title.lower() in org_title.lower() or
                            org_title.lower() in org_name_in_title.lower()):

                            relationships.append({
                                'from_id': role['id'],
                                'to_id': org['id'],
                                'kind': 'role_at',
                                'confidence': 0.95,
                                'importance': 0.85,
                                'description': f'Role at {org_title}',
                                'start_date': None,
                                'end_date': None,
                                'metadata': {
                                    'pattern_match': 'role_at_organization'
                                }
                            })

                            logger.debug(f"Pattern match: {role_title} -> {org_title}")
                            break  # Only create one edge per role
                    break  # Stop after first pattern match

        logger.info(f"Pattern-based strategy found {len(relationships)} relationships")
        return relationships

    def strategy_embedding_similarity(
        self,
        entities: List[Dict],
        similarity_threshold: float = 0.75
    ) -> List[Dict]:
        """
        Strategy 3: Embedding Similarity - Finds semantically similar entities

        Args:
            entities: List of entity dicts
            similarity_threshold: Minimum cosine similarity to create edge

        Returns: List of relationship dicts
        """
        if len(entities) < 2:
            logger.debug("Less than 2 entities, skipping embedding similarity")
            return []

        try:
            import numpy as np
        except ImportError:
            logger.error("NumPy not available, skipping embedding similarity")
            return []

        relationships = []

        try:
            # Generate text representations for each entity
            entity_texts = []
            for e in entities:
                title = e.get('title', '')
                summary = e.get('summary', '')
                text = f"{title}. {summary}" if summary else title
                entity_texts.append(text)

            # Generate embeddings using the embeddings service
            from services.embeddings import EmbeddingsService
            embeddings_service = EmbeddingsService()
            embeddings = embeddings_service.generate_embeddings_batch(entity_texts)

            # Calculate pairwise cosine similarity
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    # Calculate cosine similarity
                    vec1 = np.array(embeddings[i])
                    vec2 = np.array(embeddings[j])

                    similarity = float(
                        np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    )

                    if similarity >= similarity_threshold:
                        entity_a = entities[i]
                        entity_b = entities[j]

                        # Don't create edges between entities of the same type if they're very similar
                        # (likely duplicates that should be merged instead)
                        if entity_a.get('type') == entity_b.get('type') and similarity > 0.95:
                            logger.debug(
                                f"Skipping very similar same-type entities (likely duplicates): "
                                f"{entity_a.get('title')} <-> {entity_b.get('title')} (sim={similarity:.2f})"
                            )
                            continue

                        relationships.append({
                            'from_id': entity_a['id'],
                            'to_id': entity_b['id'],
                            'kind': 'semantically_related',
                            'confidence': similarity,
                            'importance': 0.6,  # Medium importance for inferred connections
                            'description': f'Semantically similar (score: {similarity:.2f})',
                            'start_date': None,
                            'end_date': None,
                            'metadata': {
                                'embedding_similarity': similarity
                            }
                        })

            logger.info(f"Embedding similarity strategy found {len(relationships)} connections")
            return relationships

        except Exception as e:
            logger.error(f"Embedding similarity strategy failed: {e}")
            return []

    def strategy_temporal(self, entities: List[Dict]) -> List[Dict]:
        """
        Strategy 4: Temporal Analysis - Finds temporal overlaps and sequences

        Args:
            entities: List of entity dicts with temporal data

        Returns: List of relationship dicts
        """
        from datetime import datetime

        relationships = []

        # Filter entities with temporal metadata
        temporal_entities = []
        for e in entities:
            metadata = e.get('metadata', {})
            start_date = metadata.get('start_date')
            end_date = metadata.get('end_date')

            if start_date or end_date:
                temporal_entities.append({
                    **e,
                    '_start_date': start_date,
                    '_end_date': end_date
                })

        if len(temporal_entities) < 2:
            logger.debug(f"Only {len(temporal_entities)} entities with temporal data, skipping temporal strategy")
            return []

        # Parse dates
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%Y-%m', '%Y']:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
                return None
            except:
                return None

        # Check for temporal overlaps
        for i in range(len(temporal_entities)):
            for j in range(i + 1, len(temporal_entities)):
                entity_a = temporal_entities[i]
                entity_b = temporal_entities[j]

                start_a = parse_date(entity_a.get('_start_date'))
                end_a = parse_date(entity_a.get('_end_date'))
                start_b = parse_date(entity_b.get('_start_date'))
                end_b = parse_date(entity_b.get('_end_date'))

                # Skip if we can't parse dates
                if not (start_a or end_a) or not (start_b or end_b):
                    continue

                # Use a very late date if end_date is None (ongoing)
                if not end_a:
                    end_a = datetime(2099, 12, 31)
                if not end_b:
                    end_b = datetime(2099, 12, 31)

                # Use earliest possible date if start_date is None
                if not start_a:
                    start_a = datetime(1900, 1, 1)
                if not start_b:
                    start_b = datetime(1900, 1, 1)

                # Check for overlap: (StartA <= EndB) and (EndA >= StartB)
                if start_a <= end_b and end_a >= start_b:
                    # Calculate overlap period
                    overlap_start = max(start_a, start_b)
                    overlap_end = min(end_a, end_b)

                    # Format overlap period for description
                    if overlap_end.year == 2099:
                        period_desc = f"from {overlap_start.strftime('%Y-%m-%d')} onwards"
                    else:
                        period_desc = f"{overlap_start.strftime('%Y-%m-%d')} to {overlap_end.strftime('%Y-%m-%d')}"

                    # Calculate confidence based on overlap duration
                    overlap_days = (overlap_end - overlap_start).days
                    if overlap_days > 365:
                        confidence = 0.8
                    elif overlap_days > 90:
                        confidence = 0.7
                    else:
                        confidence = 0.6

                    relationships.append({
                        'from_id': entity_a['id'],
                        'to_id': entity_b['id'],
                        'kind': 'temporal_overlap',
                        'confidence': confidence,
                        'importance': 0.5,
                        'description': f'Co-occurred during {period_desc}',
                        'start_date': overlap_start.strftime('%Y-%m-%d'),
                        'end_date': overlap_end.strftime('%Y-%m-%d') if overlap_end.year < 2099 else None,
                        'metadata': {
                            'overlap_days': overlap_days
                        }
                    })

        logger.info(f"Temporal strategy found {len(relationships)} connections")
        return relationships

    def strategy_graph_topology(self, entity_ids: List[str]) -> List[Dict]:
        """
        Strategy 5: Graph Topology - Finds transitive connections

        Args:
            entity_ids: Entities to analyze for topology patterns

        Returns: List of relationship dicts
        """
        if len(entity_ids) < 3:
            logger.debug("Less than 3 entities, skipping graph topology")
            return []

        relationships = []
        checked_pairs = set()  # Track pairs we've already checked

        try:
            for entity_id in entity_ids:
                # Get all outgoing edges from this entity
                first_order_edges = self.db.get_outgoing_edges(entity_id)

                if not first_order_edges:
                    continue

                for first_edge in first_order_edges:
                    # For each connected entity, get its outgoing edges
                    intermediate_id = first_edge.to_id
                    second_order_edges = self.db.get_outgoing_edges(intermediate_id)

                    if not second_order_edges:
                        continue

                    for second_edge in second_order_edges:
                        target_id = second_edge.to_id

                        # Don't create self-loops
                        if target_id == entity_id:
                            continue

                        # Don't create duplicate inferred edges
                        pair_key = (entity_id, target_id)
                        if pair_key in checked_pairs:
                            continue
                        checked_pairs.add(pair_key)

                        # Check if direct edge already exists
                        existing_edge = self.db.get_edge_by_from_to_kind(
                            entity_id,
                            target_id,
                            'inferred_connection'
                        )

                        if existing_edge:
                            continue

                        # Also check if any edge exists between these entities
                        # (don't infer if there's already an explicit connection)
                        try:
                            all_edges = self.db.get_outgoing_edges(entity_id)
                            has_direct = any(e.to_id == target_id for e in all_edges)
                            if has_direct:
                                continue
                        except:
                            pass

                        # Create inferred connection
                        relationships.append({
                            'from_id': entity_id,
                            'to_id': target_id,
                            'kind': 'inferred_connection',
                            'confidence': 0.5,  # Lower confidence for inferred
                            'importance': 0.4,
                            'description': f'Inferred via {intermediate_id[:8]}...',
                            'start_date': None,
                            'end_date': None,
                            'metadata': {
                                'intermediate_entity_id': intermediate_id,
                                'first_edge_kind': first_edge.kind,
                                'second_edge_kind': second_edge.kind
                            }
                        })

            logger.info(f"Graph topology strategy found {len(relationships)} transitive connections")
            return relationships

        except Exception as e:
            logger.error(f"Graph topology strategy failed: {e}")
            return []

    # ==================== EDGE MANAGEMENT ====================

    def create_or_update_edge(self, relationship: Dict) -> bool:
        """
        Create a new edge or reinforce an existing one (Hebbian learning).

        Args:
            relationship: Dict with from_id, to_id, kind, confidence, etc.

        Returns:
            True if edge was updated (reinforced), False if newly created
        """
        from_id = relationship['from_id']
        to_id = relationship['to_id']
        kind = relationship['kind']

        # Check if edge already exists
        existing_edge = self.db.get_edge_by_from_to_kind(from_id, to_id, kind)

        if existing_edge:
            # Edge exists - REINFORCE it (LTP)
            new_weight = (existing_edge.weight if hasattr(existing_edge, 'weight') else 1.0) + 1.0

            # Update metadata
            metadata = existing_edge.metadata or {}
            metadata['reinforcement_count'] = metadata.get('reinforcement_count', 0) + 1

            # Track which events contributed
            if 'detected_in_events' not in metadata:
                metadata['detected_in_events'] = []

            event_id = relationship.get('metadata', {}).get('source_event_id')
            if event_id and event_id not in metadata['detected_in_events']:
                metadata['detected_in_events'].append(event_id)

            # Update edge
            self.db.update_edge(existing_edge.id, {
                'weight': new_weight,
                'last_reinforced_at': datetime.now().isoformat(),
                'metadata': metadata,
                'confidence': max(
                    existing_edge.confidence,
                    relationship.get('confidence', 0.5)
                )
            })

            logger.info(f"Reinforced edge {existing_edge.id[:8]}... (weight: {existing_edge.weight if hasattr(existing_edge, 'weight') else 1.0}  {new_weight})")
            return True  # Updated

        else:
            # New edge - CREATE it
            edge_data = {
                'from_id': from_id,
                'to_id': to_id,
                'kind': kind,
                'confidence': relationship.get('confidence', 1.0),
                'importance': relationship.get('importance'),
                'description': relationship.get('description'),
                'start_date': relationship.get('start_date'),
                'end_date': relationship.get('end_date'),
                'weight': 1.0,  # Initial weight
                'last_reinforced_at': datetime.now().isoformat(),
                'metadata': relationship.get('metadata', {})
            }

            # Initialize metadata
            edge_data['metadata']['reinforcement_count'] = 0
            edge_data['metadata']['detected_in_events'] = []

            event_id = relationship.get('metadata', {}).get('source_event_id')
            if event_id:
                edge_data['metadata']['detected_in_events'].append(event_id)
                edge_data['source_event_id'] = event_id

            edge_id = self.db.create_edge(edge_data)
            logger.info(f"Created edge {edge_id[:8]}... ({kind}): {from_id[:8]}...  {to_id[:8]}...")
            return False  # Created

    def prune_weak_edges(self, threshold: float = 0.1) -> int:
        """
        Remove edges below weight threshold (synaptic homeostasis).

        Args:
            threshold: Minimum weight to keep

        Returns:
            Number of edges deleted
        """
        deleted_count = self.db.delete_edges_below_weight(threshold)
        logger.info(f"Pruned {deleted_count} edges below weight {threshold}")
        return deleted_count

    def apply_global_decay(self, decay_factor: float = 0.99) -> int:
        """
        Apply global weight decay to all edges ("use-it-or-lose-it").

        Args:
            decay_factor: Multiply all weights by this (< 1.0)

        Returns:
            Number of edges updated
        """
        # Get all edges
        edges = self.db.get_all_edges()

        updated_count = 0

        for edge in edges:
            current_weight = edge.weight if hasattr(edge, 'weight') else 1.0
            new_weight = current_weight * decay_factor

            self.db.update_edge(edge.id, {
                'weight': new_weight,
                'updated_at': datetime.now().isoformat()
            })

            updated_count += 1

        logger.info(f"Applied global decay ({decay_factor}) to {updated_count} edges")
        return updated_count

    # ==================== UTILITIES ====================

    def _check_duplicate_edge(self, from_id: str, to_id: str, kind: str) -> Optional[str]:
        """Check if edge already exists. Returns edge_id if found."""
        edge = self.db.get_edge_by_from_to_kind(from_id, to_id, kind)
        return edge.id if edge else None

    def _calculate_salience(self, relationship: Dict, context: Dict) -> float:
        """Calculate salience score for LTP threshold check."""
        confidence = relationship.get('confidence', 0.5)
        importance = relationship.get('importance', 0.5)
        return confidence * importance

    def _filter_by_confidence(self, relationships: List[Dict]) -> List[Dict]:
        """Filter out low-confidence relationships."""
        filtered = [r for r in relationships if r.get('confidence', 0) >= self.min_confidence]
        if len(filtered) < len(relationships):
            logger.debug(f"Filtered {len(relationships) - len(filtered)} low-confidence relationships")
        return filtered
