from services.database import DatabaseService
from utils.text_cleaner import TextCleaner
from services.chunker import Chunker
from processors.entity_extractor import EntityExtractor
from processors.mention_tracker import MentionTracker
from processors.relationship_mapper import RelationshipMapper  # TODO: Only used for alias detection, will be deprecated
from services.embeddings import EmbeddingsService
from services.entity_resolver import EntityResolver
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
        self.relationship_mapper = RelationshipMapper()  # TODO: Only for alias detection, will be deprecated
        self.embeddings_service = EmbeddingsService()
        self.entity_resolver = EntityResolver()
        self.signal_scorer = SignalScorer()

        logger.info("Archivist initialized with all processors")

    def clear_cache(self) -> None:
        """Clear all in-memory caches (called after database reset)"""
        logger.info("Clearing Archivist in-memory cache")
        self.mention_tracker = MentionTracker()  # Reinitialize with empty cache
        logger.info("Cache cleared successfully")

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
        6. Trigger relationship engine (asynchronous edge creation)
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
            logger.info(f"🔍 [DEBUG] Extracted entities: {[{'title': e.get('title'), 'type': e.get('type'), 'is_primary': e.get('is_primary_subject')} for e in extracted_entities]}")

            # Step 3.5: Entity Resolution (NEW - Phase 1)
            # Resolve pronouns and references to existing entities
            user_entity_id = event.payload.user_entity_id
            reference_map = self.entity_resolver.resolve_references(
                cleaned_text,
                user_entity_id
            )

            # Fetch recent entities for cross-event relationship detection
            existing_entities = self.db.get_recent_entities(limit=20)
            logger.info(f"Fetched {len(existing_entities)} recent entities for resolution")
            logger.info(f"Resolved {len(reference_map)} references: {reference_map}")

            # Step 4: Mention Tracking & Entity Promotion
            entity_ids = []
            hub_entity_id = None
            entity_map = {}  # Map of entity titles to IDs
            user_person_entity_id = None  # Track if we create a person entity for the user

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

                # Check if should promote (pass entity_type for better promotion logic)
                if self.mention_tracker.should_promote(entity_title, is_primary, entity_type):
                    # Check if already exists (mention tracker first, then database)
                    existing_id = self.mention_tracker.get_existing_entity_id(entity_title)

                    if not existing_id:
                        # Check database for existing entity
                        logger.info(f"🔍 [DEBUG] Checking database for entity '{entity_title}' (type: {entity_type})")
                        existing_entity = self.db.get_entity_by_title(entity_title, entity_type)
                        if existing_entity:
                            existing_id = existing_entity.id
                            logger.info(f"✅ [DEBUG] Found existing entity in database: {existing_id[:8]}...")
                            # Update mention tracker so we don't query again
                            self.mention_tracker.mark_promoted(entity_title, existing_id)

                    if existing_id:
                        entity_ids.append(existing_id)
                        entity_map[entity_title] = existing_id
                        logger.info(f"✅ [DEBUG] Using existing entity '{entity_title}': {existing_id[:8]}...")

                        # Update reference tracking for existing entity
                        existing_entity = self.db.get_entity_by_id(existing_id)
                        if existing_entity:
                            referenced_by = existing_entity.metadata.get('referenced_by_event_ids', [])
                            if event_id not in referenced_by:
                                referenced_by.append(event_id)

                            mention_count = existing_entity.metadata.get('mention_count', 0) + 1

                            self.db.update_entity_metadata(existing_id, {
                                **existing_entity.metadata,
                                'referenced_by_event_ids': referenced_by,
                                'mention_count': mention_count
                            })
                            logger.info(f"Updated entity {existing_id[:8]}... mention_count: {mention_count}, events: {len(referenced_by)}")
                    else:
                        # Determine if this should be a hub entity
                        is_hub = entity_type in ['project', 'feature', 'decision']

                        # Initialize reference tracking metadata
                        entity_metadata = entity_data.get('metadata', {})
                        entity_metadata['referenced_by_event_ids'] = [event_id]
                        entity_metadata['mention_count'] = 1

                        entity_payload = {
                            'source_event_id': event_id,
                            'type': entity_type,
                            'title': entity_title,
                            'summary': entity_data.get('summary', ''),
                            'metadata': entity_metadata,
                        }

                        try:
                            if is_hub:
                                entity_id = self.db.create_hub_entity(entity_payload)
                                hub_entity_id = entity_id
                                logger.info(f"Created hub entity '{entity_title}': {entity_id}")
                            else:
                                entity_id = self.db.create_entity(entity_payload)
                                logger.info(f"Created entity '{entity_title}': {entity_id}")

                            # If this is a person entity and is primary subject, it might be the user introducing themselves
                            logger.info(f"🔍 [DEBUG] Checking for self-introduction: type={entity_type}, is_primary={is_primary}, user_entity_id={user_entity_id}")
                            if entity_type == 'person' and is_primary:
                                # THIS is the user introducing themselves!
                                user_person_entity_id = entity_id
                                logger.info(f"✅ [DEBUG] Detected self-introduction: '{entity_title}' is the user (entity_id: {entity_id[:8]}...)")

                            self.mention_tracker.mark_promoted(entity_title, entity_id)
                            entity_ids.append(entity_id)
                            entity_map[entity_title] = entity_id
                        except Exception as e:
                            logger.error(f"Failed to create entity '{entity_title}': {e}")
                            # Don't add to entity_ids if creation failed
                else:
                    logger.debug(f"Entity '{entity_title}' not promoted yet (mention count too low)")

            # Step 4.5: Link user entity to person entity if this is a self-introduction
            logger.info(f"\n🔍 [DEBUG] Step 4.5 - Self-introduction detection")
            logger.info(f"🔍 [DEBUG] user_person_entity_id: {user_person_entity_id}")
            logger.info(f"🔍 [DEBUG] user_entity_id from payload: {user_entity_id}")

            if user_person_entity_id:
                logger.info(f"✅ [DEBUG] Detected person entity creation: {user_person_entity_id[:8]}...")
                try:
                    if not user_entity_id:
                        # This is the FIRST event - user introduced themselves
                        # Use the person entity as the user entity directly
                        logger.info(f"✅ [DEBUG] FIRST EVENT: Using person entity {user_person_entity_id[:8]}... as user entity")
                        user_entity_id = user_person_entity_id

                        # Update person entity metadata to mark it as the user
                        person_entity = self.db.get_entity_by_id(user_person_entity_id)
                        if person_entity:
                            logger.info(f"✅ [DEBUG] Marking person entity as user (is_user_entity: true)")
                            self.db.update_entity_metadata(user_person_entity_id, {
                                **person_entity.metadata,
                                'user_id': 'default_user',
                                'is_user_entity': True
                            })
                            logger.info(f"✅ [DEBUG] Updated metadata for {user_person_entity_id[:8]}...")
                        else:
                            logger.error(f"❌ [DEBUG] Could not fetch person entity {user_person_entity_id[:8]}...")


                    elif user_person_entity_id != user_entity_id:
                        # User entity exists but they created a new person entity
                        # Merge the generic user entity with the real person entity
                        user_entity = self.db.get_entity_by_id(user_entity_id)

                        if user_entity and user_entity.metadata.get('is_system_user'):
                            # This is the auto-created generic user entity
                            # Update reference_map to point to the real person entity instead
                            logger.info(f"Merging user entity {user_entity_id[:8]} with person entity {user_person_entity_id[:8]}")

                            # Update reference_map so "I" points to the real person entity
                            for ref_key in list(reference_map.keys()):
                                if reference_map[ref_key] == user_entity_id:
                                    reference_map[ref_key] = user_person_entity_id
                                    logger.info(f"Updated reference '{ref_key}' to point to {user_person_entity_id[:8]}")

                            # Mark the generic user entity for future cleanup (add to metadata)
                            # In production, you might want to actually merge/delete the generic entity
                            self.db.update_entity_metadata(user_entity_id, {
                                **user_entity.metadata,
                                'merged_into': user_person_entity_id,
                                'is_deprecated': True
                            })

                            # Update person entity to mark as user
                            person_entity = self.db.get_entity_by_id(user_person_entity_id)
                            if person_entity:
                                self.db.update_entity_metadata(user_person_entity_id, {
                                    **person_entity.metadata,
                                    'user_id': 'default_user',
                                    'is_user_entity': True
                                })

                except Exception as e:
                    logger.error(f"Error linking user entity to person entity: {e}")

            # Step 5: Create spoke entity if hub exists
            # Skip spoke creation for core identity documents (where multiple core_identity entities were extracted)
            core_identity_count = sum(1 for e in extracted_entities if e.get('type') == 'core_identity')
            should_create_spoke = (
                hub_entity_id and
                event.source in ['quick_capture', 'voice_debrief', 'webhook_granola'] and
                core_identity_count < 2  # Don't create spoke for core identity documents (they have many core_identity entities)
            )

            if should_create_spoke:
                # Determine spoke type based on content
                spoke_type = 'meeting_note' if 'meeting' in cleaned_text.lower() else 'reflection'

                spoke_payload = {
                    'source_event_id': event_id,
                    'type': spoke_type,
                    'title': f"{spoke_type.replace('_', ' ').title()}: {cleaned_text[:50]}...",
                    'summary': cleaned_text[:200],
                    'metadata': {'is_spoke': True, 'hub_id': hub_entity_id}
                }

                spoke_id = self.db.create_spoke_entity(hub_entity_id, spoke_payload, source_event_id=event_id)
                entity_ids.append(spoke_id)
                logger.info(f"Created spoke entity {spoke_id} linked to hub {hub_entity_id}")
            elif hub_entity_id and core_identity_count >= 2:
                logger.info(f"Skipping spoke creation - this appears to be a core identity document ({core_identity_count} core_identity entities)")

            # Step 6: Trigger Incremental Relationship Detection
            # Now that entities are created, trigger the RelationshipEngine to find connections
            if entity_ids:
                try:
                    from engines.relationship_engine import RelationshipEngine
                    engine = RelationshipEngine()
                    rel_result = engine.run_incremental(event_id)
                    logger.info(f"Relationship engine created {rel_result.get('edges_created', 0)} edges, updated {rel_result.get('edges_updated', 0)} edges")
                except Exception as e:
                    logger.error(f"Relationship engine failed: {e}")
                    # Don't fail the entire event if relationship detection fails

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
                chunks_created = 0
                for i, chunk in enumerate(chunks):
                    # Associate with first entity (only create chunks if entities exist)
                    if not entity_ids:
                        logger.warning("Skipping chunk - no entities extracted")
                        continue

                    primary_entity_id = entity_ids[0]
                    logger.info(f"🔍 [DEBUG] Creating chunk for entity {primary_entity_id[:8]}...")

                    try:
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
                        chunks_created += 1
                    except Exception as e:
                        logger.error(f"❌ [DEBUG] Failed to create chunk for entity {primary_entity_id[:8]}...: {e}")
                        # Continue with next chunk instead of failing the entire event

                logger.info(f"Stored {chunks_created}/{len(chunks)} chunks and embeddings")

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
