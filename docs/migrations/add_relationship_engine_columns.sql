-- Migration: Add Relationship Engine Columns to Edge Table
-- Date: 2025-11-08
-- Purpose: Add weight and last_reinforced_at columns to support Hebbian learning
--          and edge reinforcement in the Relationship Engine

-- Add weight column (synaptic strength)
-- Default 1.0 for new edges, increases with reinforcement
ALTER TABLE edge ADD COLUMN IF NOT EXISTS weight FLOAT DEFAULT 1.0;

-- Add last_reinforced_at column (timestamp tracking)
-- Used to track when edge was last strengthened
ALTER TABLE edge ADD COLUMN IF NOT EXISTS last_reinforced_at TIMESTAMPTZ DEFAULT NOW();

-- Add indexes for performance
-- Weight index: for queries like "find strongest edges" or "edges above threshold"
CREATE INDEX IF NOT EXISTS idx_edge_weight ON edge(weight);

-- Last reinforced index: for queries like "recently reinforced edges" or pruning old edges
CREATE INDEX IF NOT EXISTS idx_edge_last_reinforced ON edge(last_reinforced_at);

-- Composite index: for queries like "strong edges from entity X"
CREATE INDEX IF NOT EXISTS idx_edge_from_weight ON edge(from_id, weight DESC);

-- Comments for documentation
COMMENT ON COLUMN edge.weight IS 'Synaptic strength - increases with reinforcement (LTP), decreases with decay. Default 1.0, no upper limit.';
COMMENT ON COLUMN edge.last_reinforced_at IS 'Timestamp when this edge was last strengthened via detection or reinforcement. Used for pruning decisions.';

-- Backfill existing edges with default values
-- This ensures all existing edges have the new columns populated
UPDATE edge
SET
    weight = COALESCE(weight, 1.0),
    last_reinforced_at = COALESCE(last_reinforced_at, created_at)
WHERE weight IS NULL OR last_reinforced_at IS NULL;

-- Verify migration
-- These queries should return counts > 0 if migration succeeded
DO $$
DECLARE
    weight_count INTEGER;
    reinforced_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO weight_count FROM edge WHERE weight IS NOT NULL;
    SELECT COUNT(*) INTO reinforced_count FROM edge WHERE last_reinforced_at IS NOT NULL;

    RAISE NOTICE 'Migration verification:';
    RAISE NOTICE '  Edges with weight: %', weight_count;
    RAISE NOTICE '  Edges with last_reinforced_at: %', reinforced_count;

    IF weight_count = 0 OR reinforced_count = 0 THEN
        RAISE WARNING 'Migration may have failed - some edges missing new columns!';
    ELSE
        RAISE NOTICE '✅ Migration successful!';
    END IF;
END $$;
