-- Migration: Add reference tracking to entity table for proper undo logic
-- Date: 2025-10-11
-- Purpose: Track which events reference each entity and maintain accurate mention counts

-- Add mention_count column to track total mentions across events
ALTER TABLE entity ADD COLUMN IF NOT EXISTS mention_count INTEGER DEFAULT 1;

-- Add referenced_by_event_ids column to track which events reference this entity
ALTER TABLE entity ADD COLUMN IF NOT EXISTS referenced_by_event_ids JSONB DEFAULT '[]'::jsonb;

-- Add index for efficient filtering by mention_count
CREATE INDEX IF NOT EXISTS idx_entity_mention_count ON entity(mention_count);

-- Add index for JSONB operations on referenced_by_event_ids
CREATE INDEX IF NOT EXISTS idx_entity_referenced_by_event_ids ON entity USING gin(referenced_by_event_ids);

-- Add comments for documentation
COMMENT ON COLUMN entity.mention_count IS 'Total number of events that mention/reference this entity';
COMMENT ON COLUMN entity.referenced_by_event_ids IS 'Array of event IDs that reference this entity (for smart undo logic)';
