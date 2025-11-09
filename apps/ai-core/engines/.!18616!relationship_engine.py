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
        # Note: embedding_similarity and graph_topology are commented out for now
        # until those strategies are fully implemented
        strategies = [
            ('pattern_based', self.strategy_pattern_based(entity_dicts)),
            ('semantic_llm', self.strategy_semantic_llm(entity_dicts)),
            # ('embedding_similarity', self.strategy_embedding_similarity(entity_dicts)),
            # ('temporal', self.strategy_temporal(entity_dicts)),
            # ('graph_topology', self.strategy_graph_topology([e['id'] for e in entity_dicts]))
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
