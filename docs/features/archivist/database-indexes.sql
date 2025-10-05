-- Database Indexes for Archivist Visibility Layer
-- Run these in Supabase SQL Editor

-- Index for entity lookups by source_event_id (critical for archivist-log API)
CREATE INDEX IF NOT EXISTS idx_entity_source_event_id ON entity(source_event_id);

-- Index for edge lookups by entity IDs
CREATE INDEX IF NOT EXISTS idx_edge_from_to ON edge(from_id, to_id);

-- Index for chunk lookups by entity ID
CREATE INDEX IF NOT EXISTS idx_chunk_entity_id ON chunk(entity_id);

-- Index for signal lookups by entity ID
CREATE INDEX IF NOT EXISTS idx_signal_entity_id ON signal(entity_id);

-- Index for raw_events by status and created_at (for fetching recent processed events)
CREATE INDEX IF NOT EXISTS idx_raw_events_status_created_at ON raw_events(status, created_at DESC);
