"""
UndoService: Smart deletion logic that respects cross-event entity references

This service implements three-tier deletion logic:
1. Event-only deletion: Remove event but preserve referenced entities
2. Reference removal: Decrement mention counts for shared entities
3. Entity deletion: Only delete entities with no other references
"""

from services.database import DatabaseService
from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class UndoService:
    """Handles smart undo logic for event deletion"""

    def __init__(self):
        self.db = DatabaseService()

    def delete_event_and_related_data(self, event_id: str) -> Dict:
        """
        Delete an event and intelligently handle related entities

        Args:
            event_id: UUID of the event to delete

        Returns:
            Dictionary with deletion statistics and details
        """
        logger.info(f"Starting smart deletion for event {event_id}")

        try:
            # Step 1: Get all entities created by this event
            entities = self.db.get_entities_by_source_event(event_id)
            entity_ids = [e.id for e in entities]

            logger.info(f"Found {len(entity_ids)} entities created by event {event_id}")

            # Step 2: Get all edges created by this event
            edges_response = self.db.client.table('edge').select('*').eq('source_event_id', event_id).execute()
            event_edges = edges_response.data or []

            logger.info(f"Found {len(event_edges)} edges created by event {event_id}")

            # Step 3: Analyze which entities can be safely deleted
            deletion_analysis = self._analyze_entities_for_deletion(entity_ids, event_id)

            # Step 4: Execute deletions in proper order
            deletion_result = self._execute_deletion(
                event_id,
                deletion_analysis['safe_to_delete'],
                deletion_analysis['decrement_mentions'],
                event_edges
            )

            logger.info(f"✅ Successfully deleted event {event_id}")
            logger.info(f"   Entities deleted: {deletion_result['entities_deleted']}")
            logger.info(f"   Entities preserved: {deletion_result['entities_preserved']}")
            logger.info(f"   Edges deleted: {deletion_result['edges_deleted']}")

            return {
                'success': True,
                'event_id': event_id,
                **deletion_result,
                'analysis': deletion_analysis
            }

        except Exception as e:
            logger.error(f"Error during smart deletion of event {event_id}: {e}", exc_info=True)
            return {
                'success': False,
                'event_id': event_id,
                'error': str(e)
            }

    def _analyze_entities_for_deletion(self, entity_ids: List[str], event_id: str) -> Dict:
        """
        Analyze which entities can be safely deleted vs. which are referenced by other events

        Args:
            entity_ids: List of entity IDs created by this event
            event_id: The event being deleted

        Returns:
            Dictionary with 'safe_to_delete' and 'decrement_mentions' lists
        """
        safe_to_delete: List[str] = []
        decrement_mentions: List[Dict] = []

        for entity_id in entity_ids:
            entity = self.db.get_entity_by_id(entity_id)
            if not entity:
                logger.warning(f"Entity {entity_id} not found, skipping")
                continue

            # Get referenced_by_event_ids from metadata
            referenced_by = entity.metadata.get('referenced_by_event_ids', [event_id])
            mention_count = entity.metadata.get('mention_count', 1)

            # Ensure the source event is in the referenced_by list
            if event_id not in referenced_by:
                referenced_by.append(event_id)

            logger.debug(f"Entity {entity_id[:8]}... referenced by {len(referenced_by)} events")
            logger.debug(f"  Mention count: {mention_count}, Referenced by: {referenced_by[:3]}...")

            # Tier 1: Event-only deletion
            # If other events reference this entity, preserve it but remove current event reference
            if len(referenced_by) > 1:
                remaining_events = [eid for eid in referenced_by if eid != event_id]
                decrement_mentions.append({
                    'entity_id': entity_id,
                    'entity_title': entity.title,
                    'entity_type': entity.type,
                    'remaining_events': remaining_events,
                    'new_mention_count': max(0, mention_count - 1)
                })
                logger.debug(f"  → Preserving entity (referenced by {len(remaining_events)} other events)")

            # Tier 3: Full deletion
            # Only this event references this entity → safe to delete
            else:
                safe_to_delete.append(entity_id)
                logger.debug(f"  → Safe to delete (only referenced by this event)")

        return {
            'safe_to_delete': safe_to_delete,
            'decrement_mentions': decrement_mentions
        }

    def _execute_deletion(
        self,
        event_id: str,
        safe_to_delete: List[str],
        decrement_mentions: List[Dict],
        event_edges: List[Dict]
    ) -> Dict:
        """
        Execute the deletion plan in the correct order

        Deletion order (respecting foreign key constraints):
        1. Delete embeddings (references chunks)
        2. Delete chunks (references entities)
        3. Delete signals (references entities)
        4. Delete edges (references entities)
        5. Delete entities (only those safe to delete)
        6. Update entities (decrement mention counts)
        7. Delete raw event

        Args:
            event_id: Event to delete
            safe_to_delete: Entity IDs that can be fully deleted
            decrement_mentions: Entities to update (preserve but decrement mentions)
            event_edges: Edges created by this event

        Returns:
            Deletion statistics
        """
        stats = {
            'entities_deleted': 0,
            'entities_preserved': len(decrement_mentions),
            'entities_demoted': 0,
            'edges_deleted': 0,
            'chunks_deleted': 0,
            'embeddings_deleted': 0,
            'signals_deleted': 0
        }

        # Step 1: Update entities that should be preserved (decrement mentions)
        for item in decrement_mentions:
            entity_id = item['entity_id']
            entity = self.db.get_entity_by_id(entity_id)

            if entity:
                updated_metadata = {
                    **entity.metadata,
                    'referenced_by_event_ids': item['remaining_events'],
                    'mention_count': item['new_mention_count']
                }

                self.db.update_entity_metadata(entity_id, updated_metadata)
                logger.debug(f"Updated entity {entity_id[:8]}... mention_count: {item['new_mention_count']}")

                # Check if entity should be demoted (mention count < 2)
                if item['new_mention_count'] < 2:
                    self._demote_entity(entity_id, item['entity_title'])
                    stats['entities_demoted'] += 1
                    logger.info(f"Entity {item['entity_title']} demoted (mention_count < 2)")

        # Step 2: Delete data for entities that are safe to delete
        if safe_to_delete:
            # 2a. Delete embeddings (references chunks)
            chunks_response = self.db.client.table('chunk').select('id').in_('entity_id', safe_to_delete).execute()
            chunk_ids = [c['id'] for c in chunks_response.data or []]

            if chunk_ids:
                embeddings_result = self.db.client.table('embedding').delete().in_('chunk_id', chunk_ids).execute()
                stats['embeddings_deleted'] = len(embeddings_result.data or [])

            # 2b. Delete chunks (references entities)
            chunks_result = self.db.client.table('chunk').delete().in_('entity_id', safe_to_delete).execute()
            stats['chunks_deleted'] = len(chunks_result.data or [])

            # 2c. Delete signals (references entities)
            signals_result = self.db.client.table('signal').delete().in_('entity_id', safe_to_delete).execute()
            stats['signals_deleted'] = len(signals_result.data or [])

            # 2d. Delete edges involving these entities (both from and to)
            # NOTE: Edges created by THIS event are handled separately below
            from_edges_result = self.db.client.table('edge').delete().in_('from_id', safe_to_delete).execute()
            to_edges_result = self.db.client.table('edge').delete().in_('to_id', safe_to_delete).execute()

            # 2e. Delete entities
            entities_result = self.db.client.table('entity').delete().in_('id', safe_to_delete).execute()
            stats['entities_deleted'] = len(entities_result.data or [])

        # Step 3: Delete edges created by this event (even if they involve preserved entities)
        # This is important: edges created by Event 1 should be removed when Event 1 is deleted
        edge_ids = [e['id'] for e in event_edges]
        if edge_ids:
            edges_result = self.db.client.table('edge').delete().in_('id', edge_ids).execute()
            stats['edges_deleted'] = len(edges_result.data or [])

        # Step 4: Finally, delete the raw event
        self.db.client.table('raw_events').delete().eq('id', event_id).execute()

        return stats

    def _demote_entity(self, entity_id: str, entity_title: str):
        """
        Demote an entity when its mention count drops below 2

        Demotion strategy:
        1. Mark entity as 'metadata-only' in metadata
        2. Preserve the entity but flag it as not promoted
        3. Future: Could convert to mention tracker entry only

        Args:
            entity_id: Entity to demote
            entity_title: Title of the entity (for logging)
        """
        entity = self.db.get_entity_by_id(entity_id)
        if not entity:
            logger.warning(f"Cannot demote entity {entity_id} - not found")
            return

        # Mark as metadata-only (not fully promoted)
        updated_metadata = {
            **entity.metadata,
            'is_promoted': False,
            'is_metadata_only': True,
            'demotion_reason': 'mention_count_below_threshold'
        }

        self.db.update_entity_metadata(entity_id, updated_metadata)

        # Lower signal scores to reflect demotion
        signal = self.db.get_signal_by_entity_id(entity_id)
        if signal:
            self.db.update_signal(entity_id, {
                'importance': max(0.1, signal.get('importance', 0.5) - 0.2),
                'novelty': max(0.1, signal.get('novelty', 0.5) - 0.1)
            })
            logger.debug(f"Lowered signal scores for demoted entity {entity_id[:8]}...")

        logger.info(f"Demoted entity '{entity_title}' to metadata-only status")

    def preview_deletion(self, event_id: str) -> Dict:
        """
        Preview what would be deleted without actually deleting

        Args:
            event_id: Event to analyze

        Returns:
            Analysis of what would be deleted
        """
        entities = self.db.get_entities_by_source_event(event_id)
        entity_ids = [e.id for e in entities]

        edges_response = self.db.client.table('edge').select('*').eq('source_event_id', event_id).execute()
        event_edges = edges_response.data or []

        analysis = self._analyze_entities_for_deletion(entity_ids, event_id)

        return {
            'event_id': event_id,
            'total_entities': len(entity_ids),
            'entities_to_delete': len(analysis['safe_to_delete']),
            'entities_to_preserve': len(analysis['decrement_mentions']),
            'edges_to_delete': len(event_edges),
            'safe_to_delete': analysis['safe_to_delete'],
            'decrement_mentions': analysis['decrement_mentions']
        }
