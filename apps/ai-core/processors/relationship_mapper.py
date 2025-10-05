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
        existing_entities: List[Dict] = []
    ) -> List[Dict]:
        """Detect relationships between entities using GPT-4

        Args:
            text: The source text containing the entities
            entities: List of extracted entities with 'title' and 'type' fields
            existing_entities: Optional list of existing entities from the graph

        Returns:
            List of relationship dictionaries with:
                - from_entity: Source entity title
                - to_entity: Destination entity title
                - relationship_type: Type of edge (belongs_to, modifies, etc.)
                - metadata: Additional context
        """
        if not entities or len(entities) < 2:
            logger.debug("Not enough entities to detect relationships")
            return []

        try:
            # Build entity list for LLM
            entity_list = [f"{e['title']} ({e['type']})" for e in entities]

            prompt = f"""Given this text and list of entities, identify relationships between them.

Text: {text}

Entities:
{chr(10).join(entity_list)}

For each relationship, specify:
- from_entity: The source entity title (must match exactly from the list above)
- to_entity: The destination entity title (must match exactly from the list above)
- relationship_type: One of [belongs_to, modifies, mentions, informs, blocks, contradicts, relates_to]
- metadata: Any relevant context as a JSON object

Relationship type meanings:
- belongs_to: Hierarchical ownership (e.g., Feature belongs_to Project)
- modifies: Changes or updates (e.g., Meeting modifies Feature via rename)
- mentions: Simple reference (e.g., Note mentions Person)
- informs: Knowledge transfer (e.g., Research informs Decision)
- blocks: Dependencies (e.g., Task blocks another Task)
- contradicts: Tensions (e.g., Decision contradicts previous Strategy)
- relates_to: General connection (e.g., Spoke relates_to Hub)

Return ONLY a JSON object with a "relationships" array:
{{
  "relationships": [
    {{
      "from_entity": "entity name",
      "to_entity": "entity name",
      "relationship_type": "belongs_to",
      "metadata": {{"context": "additional info"}}
    }}
  ]
}}

If no relationships exist, return {{"relationships": []}}"""

            response = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2048,
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

            logger.info(f"Detected {len(relationships)} relationships via LLM")
            return relationships

        except Exception as e:
            logger.error(f"Error detecting relationships with LLM: {str(e)}")
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
        db
    ) -> bool:
        """Create an edge in the database from a detected relationship

        Args:
            relationship: Relationship dict with from_entity, to_entity, relationship_type
            entity_map: Mapping of entity titles to entity IDs
            db: Database service instance

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
                'metadata': relationship.get('metadata', {})
            }

            db.create_edge(edge_data)
            logger.info(f"Created edge: {from_title} --{rel_type}--> {to_title}")
            return True

        except Exception as e:
            logger.error(f"Error creating edge: {str(e)}")
            return False
