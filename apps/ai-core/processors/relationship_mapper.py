from typing import List, Dict
from anthropic import Anthropic
from config import settings
import re
import logging
import json

logger = logging.getLogger(__name__)


class RelationshipMapper:
    """Detects relationships between entities and creates edges"""

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def detect_relationships(
        self,
        text: str,
        entities: List[Dict],
        existing_entities: List[Dict] = [],
        reference_map: Dict[str, str] = {}
    ) -> List[Dict]:
        """Detect relationships between entities using Claude

        Args:
            text: The source text containing the entities
            entities: List of extracted entities with 'title' and 'type' fields
            existing_entities: Optional list of existing entities from the graph
            reference_map: Mapping of references (pronouns) to entity IDs

        Returns:
            List of relationship dictionaries with:
                - from_entity: Source entity title
                - to_entity: Destination entity title
                - relationship_type: Type of edge (belongs_to, modifies, etc.)
                - metadata: Additional context
        """
        # Combine new and existing entities for full context
        all_entities = entities + existing_entities

        # Need at least 2 entities total OR have reference_map (pronoun references)
        if len(all_entities) < 2 and not reference_map:
            logger.debug("Not enough entities to detect relationships")
            return []

        try:
            # Build entity list for LLM with reference hints
            entity_list = []
            for e in all_entities:
                entity_str = f"{e['title']} ({e['type']})"

                # Add reference hints if this entity is referenced by pronouns
                entity_id = e.get('id', e.get('entity_id'))
                matching_refs = [
                    ref for ref, ref_entity_id in reference_map.items()
                    if ref_entity_id == entity_id
                ]
                if matching_refs:
                    entity_str += f" [also referred to as: {', '.join(matching_refs)}]"

                entity_list.append(entity_str)

            prompt = f"""Given this text and list of entities, identify relationships. Focus on:

1. Work history: person → organization (worked_at, founded, attended)
2. Major achievements: person → milestone (achieved) - ONLY top accomplishments
3. Skills: person → skill (manages) - **CRITICAL: Create manages edge for EVERY skill entity**
4. Key locations: organization → location (relates_to)
5. Core identity: person → core_identity (values)
6. Goals: person → goal (owns)

CRITICAL FOR SKILLS: If a skill entity exists, create a "manages" relationship from person to that skill.
DO NOT skip any skills. Connect ALL of them.

Text: {text}

Entities (new + existing from knowledge graph):
{chr(10).join(entity_list)}

IMPORTANT: Pay attention to pronouns like "I", "me", "my" which may refer to existing entities. These are shown in [also referred to as: ...] hints.

For each relationship, specify:
- from_entity: Source entity title (must match exactly from list above)
- to_entity: Destination entity title (must match exactly from list above)
- relationship_type: One of the supported types below
- start_date: When relationship began (YYYY-MM-DD format, or null if unknown)
- end_date: When relationship ended (YYYY-MM-DD format, or null if ongoing/unknown)
- description: Brief context (e.g., "Principal", "Co-founder", "Renamed from X to Y")
- confidence: How confident you are (0.0 to 1.0)
- importance: How important this relationship is (0.0 to 1.0, or null)

SUPPORTED RELATIONSHIP TYPES:

**Work & Career:**
- worked_at: Employment (person → organization). Extract role in description. Use start_date/end_date.
- attended: Education (person → organization). Extract degree in description. Use start_date/end_date.
- founded: Created organization (person → organization). Use start_date, usually no end_date.
- led: Leadership role (person → organization/project/team). Extract role in description. Use start_date/end_date.
- participated_in: Project/initiative participation (person → project). Use start_date/end_date.

**Location & Temporal:**
- lived_in: Residency (person → location). Use start_date/end_date.

**Knowledge & Learning:**
- learned_from: Knowledge source (person → source). Use start_date if applicable.
- achieved: Milestone reached (person → milestone). Use start_date for when achieved.

**Hierarchical & Structural:**
- belongs_to: Hierarchical ownership (e.g., product belongs_to project)
- modifies: Changes/updates (e.g., meeting modifies product via rename)
- mentions: Simple reference (e.g., note mentions person)
- informs: Knowledge transfer (e.g., research informs decision)

**Dependencies & Conflicts:**
- blocks: Dependencies (e.g., task blocks another task)
- contradicts: Tensions (e.g., decision contradicts previous strategy)

**General & Identity:**
- relates_to: General connection (e.g., spoke relates_to hub)
- values: Identity relationship (person values core_identity)
- owns: Ownership/responsibility (person owns goal/project)
- manages: Management (person manages team/project)
- contributes_to: Contribution (person contributes_to project)

TEMPORAL EXTRACTION GUIDELINES:
- "Jan 2024 - Current" → start_date: "2024-01-01", end_date: null
- "2015-2016" → start_date: "2015-01-01", end_date: "2016-12-31"
- "May 2018 - Dec 2023" → start_date: "2018-05-01", end_date: "2023-12-31"
- "Aug 2017 - May 2018" → start_date: "2017-08-01", end_date: "2018-05-31"
- If no dates mentioned → start_date: null, end_date: null

Return ONLY a JSON object:
{{
  "relationships": [
    {{
      "from_entity": "entity name",
      "to_entity": "entity name",
      "relationship_type": "worked_at",
      "start_date": "2024-01-01",
      "end_date": null,
      "description": "Chief Technology Officer",
      "confidence": 0.95,
      "importance": 0.85
    }}
  ]
}}

EXAMPLES:

Input: "Ryan York was CTO at Willow Education from Jan 2024 to Current"
Output:
{{
  "relationships": [
    {{
      "from_entity": "Ryan York",
      "to_entity": "Willow Education",
      "relationship_type": "worked_at",
      "start_date": "2024-01-01",
      "end_date": null,
      "description": "Chief Technology Officer",
      "confidence": 0.95,
      "importance": 0.9
    }}
  ]
}}

Input: "Co-founded The Gathering Place from May 2018 to Dec 2023"
Output:
{{
  "relationships": [
    {{
      "from_entity": "Ryan York",
      "to_entity": "The Gathering Place",
      "relationship_type": "founded",
      "start_date": "2018-05-01",
      "end_date": "2023-12-31",
      "description": "Co-Founder",
      "confidence": 0.95,
      "importance": 0.95
    }},
    {{
      "from_entity": "Ryan York",
      "to_entity": "The Gathering Place",
      "relationship_type": "worked_at",
      "start_date": "2018-05-01",
      "end_date": "2023-12-31",
      "description": "Co-CEO",
      "confidence": 0.95,
      "importance": 0.9
    }}
  ]
}}

If no relationships exist, return {{"relationships": []}}"""

            response = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=8192,  # Increased to handle large resumes with many relationships
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            # Handle truncated JSON by closing any incomplete structures
            if not content.rstrip().endswith('}'):
                logger.warning("Response appears truncated, attempting to close JSON structure")
                # Find the last complete relationship by finding the last complete }
                last_complete = content.rfind('},')
                if last_complete > 0:
                    # Truncate to last complete relationship and close the JSON
                    content = content[:last_complete + 1] + '\n  ]\n}'
                    logger.info(f"Salvaged truncated response, will process partial relationships")

            result = json.loads(content)
            relationships = result.get('relationships', [])

            logger.info(f"Detected {len(relationships)} relationships via LLM")
            return relationships

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Full raw Claude response that failed to parse:")
            logger.error(content)  # Log the FULL response
            return []
        except Exception as e:
            logger.error(f"Error detecting relationships with LLM: {str(e)}", exc_info=True)
            return []

    def detect_explicit_relationships(self, text: str) -> List[Dict]:
        """Detect explicit relationships from keywords and patterns

        Args:
            text: The source text to analyze

        Returns:
            List of relationship hints with type, signal, and confidence
        """
        relationships = []
        text_lower = text.lower()

        # Pattern: Rename/modification signals
        if any(keyword in text_lower for keyword in ["renamed", "now called", "changing the name"]):
            relationships.append({
                'type': 'modifies',
                'signal': 'rename',
                'confidence': 0.9
            })

        # Pattern: Hierarchical ownership
        if any(keyword in text_lower for keyword in ["belongs to", "part of", "within"]):
            relationships.append({
                'type': 'belongs_to',
                'signal': 'explicit_mention',
                'confidence': 0.95
            })

        # Pattern: Blocking/dependency
        if any(keyword in text_lower for keyword in ["blocked by", "waiting for", "depends on"]):
            relationships.append({
                'type': 'blocks',
                'signal': 'dependency',
                'confidence': 0.9
            })

        # Pattern: Information flow
        if any(keyword in text_lower for keyword in ["learned from", "based on", "informed by"]):
            relationships.append({
                'type': 'informs',
                'signal': 'knowledge_transfer',
                'confidence': 0.85
            })

        # Pattern: Contradiction/conflict
        if any(keyword in text_lower for keyword in ["contradicts", "conflicts with", "opposed to"]):
            relationships.append({
                'type': 'contradicts',
                'signal': 'tension',
                'confidence': 0.9
            })

        if relationships:
            logger.info(f"Detected {len(relationships)} explicit relationship signals")

        return relationships

    def detect_alias_and_update(
        self,
        text: str,
        entities: List[Dict],
        db
    ) -> List[Dict]:
        """Detect entity renames/aliases and update entity metadata

        Args:
            text: The source text containing potential rename information
            entities: List of extracted entities
            db: Database service instance

        Returns:
            List of alias update records
        """
        alias_updates = []

        # Regex patterns for detecting renames
        # Captures: "renamed from X to Y", "now called Y instead of X", etc.
        rename_patterns = [
            r'renamed?\s+(?:from\s+)?["\']?([^"\']+?)["\']?\s+to\s+["\']?([^"\']+?)["\']?(?:\s|$|\.)',
            r'now\s+called\s+["\']?([^"\']+?)["\']?\s+instead\s+of\s+["\']?([^"\']+?)["\']?(?:\s|$|\.)',
            r'changing\s+["\']?([^"\']+?)["\']?\s+to\s+["\']?([^"\']+?)["\']?(?:\s|$|\.)',
            r'(?:was|used to be)\s+["\']?([^"\']+?)["\']?[,\s]+now\s+["\']?([^"\']+?)["\']?(?:\s|$|\.)'
        ]

        for pattern in rename_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                old_name = match.group(1).strip()
                new_name = match.group(2).strip()

                logger.debug(f"Found potential rename: '{old_name}' -> '{new_name}'")

                # Find matching entity in the current entity list
                for entity in entities:
                    entity_title = entity.get('title', '')

                    # Check if this entity matches the new name
                    if new_name.lower() in entity_title.lower() or entity_title.lower() in new_name.lower():
                        # Get entity_id if it exists (entity might be newly created)
                        entity_id = entity.get('entity_id')

                        if entity_id:
                            try:
                                # Get current metadata
                                current_metadata = db.get_entity_metadata(entity_id)
                                aliases = current_metadata.get('aliases', [])

                                # Add old name to aliases if not already present
                                if old_name not in aliases:
                                    aliases.append(old_name)
                                    logger.info(f"Adding alias '{old_name}' to entity '{entity_title}'")

                                # Update entity metadata
                                db.update_entity_metadata(entity_id, {
                                    **current_metadata,
                                    'aliases': aliases,
                                    'previous_names': aliases  # Duplicate for clarity
                                })

                                alias_updates.append({
                                    'entity_id': entity_id,
                                    'old_name': old_name,
                                    'new_name': new_name,
                                    'type': 'rename'
                                })
                            except Exception as e:
                                logger.error(f"Error updating entity metadata: {str(e)}")
                        else:
                            logger.debug(f"Entity '{entity_title}' not yet created, cannot update aliases")

        if alias_updates:
            logger.info(f"Updated {len(alias_updates)} entity aliases")

        return alias_updates

    def create_edge_from_relationship(
        self,
        relationship: Dict,
        entity_map: Dict[str, str],
        db,
        source_event_id: str = None
    ) -> bool:
        """Create an edge in the database from a detected relationship

        Args:
            relationship: Relationship dict with from_entity, to_entity, relationship_type,
                         start_date, end_date, description, confidence, importance
            entity_map: Mapping of entity titles to entity IDs
            db: Database service instance
            source_event_id: Optional ID of the event that created this relationship

        Returns:
            True if edge created successfully, False otherwise
        """
        from_title = relationship.get('from_entity')
        to_title = relationship.get('to_entity')
        rel_type = relationship.get('relationship_type')

        if not all([from_title, to_title, rel_type]):
            logger.warning(f"Incomplete relationship data: {relationship}")
            return False

        # Get entity IDs from map
        from_id = entity_map.get(from_title)
        to_id = entity_map.get(to_title)

        if not from_id or not to_id:
            logger.warning(f"Could not find entity IDs for: {from_title} -> {to_title}")
            return False

        try:
            edge_data = {
                'from_id': from_id,
                'to_id': to_id,
                'kind': rel_type,
                'confidence': relationship.get('confidence', 1.0),
                'metadata': relationship.get('metadata', {})
            }

            # Add structured columns from relationship
            if 'start_date' in relationship and relationship['start_date']:
                edge_data['start_date'] = relationship['start_date']

            if 'end_date' in relationship and relationship['end_date']:
                edge_data['end_date'] = relationship['end_date']

            if 'description' in relationship and relationship['description']:
                edge_data['description'] = relationship['description']

            if 'importance' in relationship and relationship['importance'] is not None:
                edge_data['importance'] = relationship['importance']

            # Add source_event_id if provided
            if source_event_id:
                edge_data['source_event_id'] = source_event_id

            db.create_edge(edge_data)

            # Build detailed log message with temporal data
            log_parts = [f"Created edge: {from_title} --{rel_type}--> {to_title}"]

            if relationship.get('description'):
                log_parts.append(f"description='{relationship.get('description')}'")

            if relationship.get('start_date'):
                log_parts.append(f"start={relationship.get('start_date')}")

            if relationship.get('end_date'):
                log_parts.append(f"end={relationship.get('end_date')}")
            elif 'start_date' in relationship and relationship.get('start_date'):
                log_parts.append(f"end=ongoing")

            if relationship.get('importance'):
                log_parts.append(f"importance={relationship.get('importance')}")

            logger.info(" | ".join(log_parts))
            return True

        except Exception as e:
            logger.error(f"Error creating edge: {str(e)}")
            return False
