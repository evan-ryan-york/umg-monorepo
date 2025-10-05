from services.database import DatabaseService
from utils.text_cleaner import TextCleaner
from services.chunker import Chunker
from processors.entity_extractor import EntityExtractor
from processors.mention_tracker import MentionTracker
from processors.relationship_mapper import RelationshipMapper
from services.embeddings import EmbeddingsService
from processors.signal_scorer import SignalScorer
from typing import List, Dict
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)


class Archivist:
    """Main orchestrator for the Archivist agent - transforms raw events into structured memory graph"""

    def __init__(self):
        """Initialize all services and processors"""
        self.db = DatabaseService()
        self.text_cleaner = TextCleaner()
        self.chunker = Chunker()
        self.entity_extractor = EntityExtractor()
        self.mention_tracker = MentionTracker()
        self.relationship_mapper = RelationshipMapper()
        self.embeddings_service = EmbeddingsService()
        self.signal_scorer = SignalScorer()

        logger.info("Archivist initialized with all processors")

    def process_event(self, event_id: str) -> Dict:
        """Process a single raw event through the full pipeline

        Args:
            event_id: UUID of the raw_event to process

        Returns:
            Dictionary with processing results and statistics

        Pipeline Steps:
        1. Fetch event
        2. Parse & clean text
        3. Extract entities
        4. Track mentions & promote entities
        5. Create hub-and-spoke structures
        6. Detect relationships
        7. Detect aliases/renames
        8. Chunk text
        9. Generate embeddings
        10. Assign signals
        11. Update event status
        """
        try:
            logger.info(f"Starting processing for event {event_id}")
            start_time = time.time()

            # Step 1: Fetch event
            event = self.db.get_event_by_id(event_id)
            if not event:
                raise ValueError(f"Event {event_id} not found")

            logger.info(f"Fetched event {event_id} from {event.source}")

            # Step 2: Parse & Clean
            raw_text = event.payload.content
            cleaned_text = self.text_cleaner.clean(raw_text)

            logger.info(f"Cleaned text: {len(raw_text)} → {len(cleaned_text)} chars")

            # Step 3: Entity Extraction
            extracted_entities = self.entity_extractor.extract_entities(cleaned_text)
            logger.info(f"Extracted {len(extracted_entities)} entities")

            # Step 4: Mention Tracking & Entity Promotion
            entity_ids = []
            hub_entity_id = None
            entity_map = {}  # Map of entity titles to IDs

            for entity_data in extracted_entities:
                entity_title = entity_data.get('title', '')
                entity_type = entity_data.get('type', 'reference_document')
                is_primary = entity_data.get('is_primary_subject', False)

                # Record mention
                self.mention_tracker.record_mention(
                    entity_title,
                    entity_type,
                    event_id,
                    is_primary
                )

                # Check if should promote
                if self.mention_tracker.should_promote(entity_title, is_primary):
                    # Check if already exists
                    existing_id = self.mention_tracker.get_existing_entity_id(entity_title)

                    if existing_id:
                        entity_ids.append(existing_id)
                        entity_map[entity_title] = existing_id
                        logger.debug(f"Entity '{entity_title}' already exists: {existing_id}")
                    else:
                        # Determine if this should be a hub entity
                        is_hub = entity_type in ['project', 'feature', 'decision']

                        entity_payload = {
                            'source_event_id': event_id,
                            'type': entity_type,
                            'title': entity_title,
                            'summary': entity_data.get('summary', ''),
                            'metadata': entity_data.get('metadata', {}),
                        }

                        if is_hub:
                            entity_id = self.db.create_hub_entity(entity_payload)
                            hub_entity_id = entity_id
                            logger.info(f"Created hub entity '{entity_title}': {entity_id}")
                        else:
                            entity_id = self.db.create_entity(entity_payload)
                            logger.info(f"Created entity '{entity_title}': {entity_id}")

                        self.mention_tracker.mark_promoted(entity_title, entity_id)
                        entity_ids.append(entity_id)
                        entity_map[entity_title] = entity_id
                else:
                    logger.debug(f"Entity '{entity_title}' not promoted yet (mention count too low)")

            # Step 5: Create spoke entity if hub exists
            if hub_entity_id and event.source in ['quick_capture', 'voice_debrief', 'webhook_granola']:
                # Determine spoke type based on content
                spoke_type = 'meeting_note' if 'meeting' in cleaned_text.lower() else 'reflection'

                spoke_payload = {
                    'source_event_id': event_id,
                    'type': spoke_type,
                    'title': f"{spoke_type.replace('_', ' ').title()}: {cleaned_text[:50]}...",
                    'summary': cleaned_text[:200],
                    'metadata': {'is_spoke': True, 'hub_id': hub_entity_id}
                }

                spoke_id = self.db.create_spoke_entity(hub_entity_id, spoke_payload)
                entity_ids.append(spoke_id)
                logger.info(f"Created spoke entity {spoke_id} linked to hub {hub_entity_id}")

            # Step 6: Relationship Mapping
            relationships = self.relationship_mapper.detect_relationships(
                cleaned_text,
                extracted_entities
            )

            edges_created = 0
            for rel in relationships:
                success = self.relationship_mapper.create_edge_from_relationship(
                    rel,
                    entity_map,
                    self.db
                )
                if success:
                    edges_created += 1

            logger.info(f"Created {edges_created} edges from {len(relationships)} detected relationships")

            # Step 7: Alias Detection & Update
            # Prepare entities with IDs for alias detection
            entities_with_ids = []
            for entity_data in extracted_entities:
                title = entity_data.get('title', '')
                if title in entity_map:
                    entities_with_ids.append({
                        **entity_data,
                        'entity_id': entity_map[title]
                    })

            alias_updates = self.relationship_mapper.detect_alias_and_update(
                cleaned_text,
                entities_with_ids,
                self.db
            )

            if alias_updates:
                logger.info(f"Updated {len(alias_updates)} entity aliases")

            # Step 8: Chunking
            chunks = self.chunker.chunk_text(cleaned_text)
            logger.info(f"Created {len(chunks)} chunks")

            # Step 9: Embedding Generation
            if chunks:
                chunk_texts = [c['text'] for c in chunks]
                embeddings = self.embeddings_service.generate_embeddings_batch(chunk_texts)

                # Step 9b: Store Chunks & Embeddings
                for i, chunk in enumerate(chunks):
                    # Associate with first entity (only create chunks if entities exist)
                    if not entity_ids:
                        logger.warning("Skipping chunk - no entities extracted")
                        continue

                    primary_entity_id = entity_ids[0]

                    chunk_payload = {
                        'entity_id': primary_entity_id,
                        'text': chunk['text'],
                        'token_count': chunk['token_count'],
                        'hash': chunk['hash']
                    }

                    chunk_id = self.db.create_chunk(chunk_payload)

                    embedding_payload = {
                        'chunk_id': chunk_id,
                        'vec': embeddings[i],
                        'model': 'text-embedding-3-small'
                    }

                    self.db.create_embedding(embedding_payload)

                logger.info(f"Stored {len(chunks)} chunks and embeddings")

            # Step 10: Signal Assignment
            for entity_id in entity_ids:
                entity = self.db.get_entity_by_id(entity_id)

                if not entity:
                    logger.warning(f"Could not fetch entity {entity_id} for signal scoring")
                    continue

                # Get edge count for novelty calculation
                edge_count = self.db.get_edge_count_for_entity(entity_id)

                # Calculate all signals
                signals = self.signal_scorer.calculate_all_signals(
                    entity_type=entity.type,
                    created_at=entity.created_at,
                    updated_at=entity.updated_at,
                    edge_count=edge_count,
                    metadata=entity.metadata
                )

                signal_payload = {
                    'entity_id': entity_id,
                    'importance': signals['importance'],
                    'recency': signals['recency'],
                    'novelty': signals['novelty'],
                    'last_surfaced_at': None
                }

                self.db.create_signal(signal_payload)
                logger.debug(f"Created signals for entity {entity_id}: I={signals['importance']:.2f}, R={signals['recency']:.2f}, N={signals['novelty']:.2f}")

            logger.info(f"Assigned signals to {len(entity_ids)} entities")

            # Step 11: Update Event Status
            self.db.update_event_status(event_id, 'processed')

            # Calculate processing time
            elapsed_time = time.time() - start_time

            logger.info(f"Successfully processed event {event_id} in {elapsed_time:.2f}s")

            return {
                'event_id': event_id,
                'status': 'success',
                'entities_created': len(entity_ids),
                'edges_created': edges_created,
                'chunks_created': len(chunks),
                'aliases_updated': len(alias_updates),
                'processing_time_seconds': elapsed_time
            }

        except Exception as e:
            logger.error(f"Error processing event {event_id}: {str(e)}", exc_info=True)
            self.db.update_event_status(event_id, 'error')

            return {
                'event_id': event_id,
                'status': 'error',
                'error': str(e)
            }

    def process_pending_events(self, batch_size: int = 10) -> Dict:
        """Process all pending events in batches

        Args:
            batch_size: Maximum number of events to process in this batch

        Returns:
            Dictionary with batch processing results
        """
        logger.info(f"Fetching up to {batch_size} pending events")

        events = self.db.get_pending_events(limit=batch_size)
        total_events = len(events)

        if total_events == 0:
            logger.info("No pending events to process")
            return {
                'status': 'success',
                'events_processed': 0,
                'events_succeeded': 0,
                'events_failed': 0
            }

        logger.info(f"Processing batch of {total_events} events")

        results = []
        succeeded = 0
        failed = 0

        for event in events:
            result = self.process_event(event.id)
            results.append(result)

            if result['status'] == 'success':
                succeeded += 1
            else:
                failed += 1

        logger.info(f"Batch complete: {succeeded} succeeded, {failed} failed")

        return {
            'status': 'success',
            'events_processed': total_events,
            'events_succeeded': succeeded,
            'events_failed': failed,
            'results': results
        }

    def run_continuous(self, interval_seconds: int = 60, max_iterations: int = None):
        """Run Archivist in continuous mode (background worker)

        Args:
            interval_seconds: How often to check for new events (default 60s)
            max_iterations: Optional limit on iterations (for testing)

        Note:
            This runs indefinitely unless max_iterations is set.
            Use Ctrl+C to stop, or run in a separate thread/process.
        """
        logger.info(f"Starting Archivist in continuous mode (checking every {interval_seconds}s)")

        iteration = 0

        try:
            while True:
                if max_iterations and iteration >= max_iterations:
                    logger.info(f"Reached max_iterations ({max_iterations}), stopping")
                    break

                iteration += 1
                logger.debug(f"Continuous mode iteration {iteration}")

                try:
                    result = self.process_pending_events()
                    if result['events_processed'] > 0:
                        logger.info(f"Iteration {iteration}: Processed {result['events_processed']} events")
                except Exception as e:
                    logger.error(f"Error in continuous processing iteration {iteration}: {str(e)}", exc_info=True)

                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("Continuous mode stopped by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"Fatal error in continuous mode: {str(e)}", exc_info=True)
            raise
