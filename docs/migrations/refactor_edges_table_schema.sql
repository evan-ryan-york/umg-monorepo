-- Migration: Refactor edges table with structured columns for agent queries
-- Date: 2025-10-12
-- Description: Adds temporal, confidence, and description columns to edges table
--              for efficient querying by Mentor and other agents

-- Step 1: Add new columns to edges table
ALTER TABLE edge ADD COLUMN IF NOT EXISTS start_date DATE;
ALTER TABLE edge ADD COLUMN IF NOT EXISTS end_date DATE;
ALTER TABLE edge ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 1.0;
ALTER TABLE edge ADD COLUMN IF NOT EXISTS importance FLOAT;
ALTER TABLE edge ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE edge ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Step 2: Migrate existing JSONB metadata to structured columns (if applicable)
-- This attempts to extract temporal data from existing metadata
-- Note: Only migrates properly formatted dates (YYYY-MM-DD), skips invalid formats
UPDATE edge
SET
  confidence = CASE
    WHEN metadata->>'confidence' IS NOT NULL
    THEN (metadata->>'confidence')::FLOAT
    ELSE 1.0
  END,
  importance = CASE
    WHEN metadata->>'importance' IS NOT NULL
    THEN (metadata->>'importance')::FLOAT
    ELSE NULL
  END,
  description = metadata->>'description'
WHERE metadata IS NOT NULL;

-- Migrate start_date only if it's in valid YYYY-MM-DD format
UPDATE edge
SET start_date = (metadata->>'start_date')::DATE
WHERE metadata->>'start_date' IS NOT NULL
  AND metadata->>'start_date' ~ '^\d{4}-\d{2}-\d{2}$';

-- Migrate end_date only if it's in valid YYYY-MM-DD format
UPDATE edge
SET end_date = (metadata->>'end_date')::DATE
WHERE metadata->>'end_date' IS NOT NULL
  AND metadata->>'end_date' ~ '^\d{4}-\d{2}-\d{2}$';

-- Step 3: Create indexes optimized for agent query patterns

-- Index for "What did Ryan do in 2015?" temporal queries
CREATE INDEX IF NOT EXISTS idx_edges_temporal
ON edge(start_date, end_date)
WHERE start_date IS NOT NULL;

-- Index for "What is Ryan currently doing?" (active relationships)
CREATE INDEX IF NOT EXISTS idx_edges_active
ON edge(from_id, kind)
WHERE end_date IS NULL;

-- Index for relationship type + entity lookups
CREATE INDEX IF NOT EXISTS idx_edges_from_type
ON edge(from_id, kind);

CREATE INDEX IF NOT EXISTS idx_edges_to_type
ON edge(to_id, kind);

-- Index for confidence-based filtering
CREATE INDEX IF NOT EXISTS idx_edges_confidence
ON edge(confidence);

-- Index for importance-based filtering
CREATE INDEX IF NOT EXISTS idx_edges_importance
ON edge(importance)
WHERE importance IS NOT NULL;

-- Index for temporal range queries (start_date DESC for timeline views)
CREATE INDEX IF NOT EXISTS idx_edges_timeline
ON edge(from_id, start_date DESC);

-- Step 4: Add comments for documentation
COMMENT ON COLUMN edge.start_date IS 'When this relationship began (e.g., employment start date, project launch)';
COMMENT ON COLUMN edge.end_date IS 'When this relationship ended (NULL means ongoing/current)';
COMMENT ON COLUMN edge.confidence IS 'How confident the system is about this relationship (0.0 to 1.0)';
COMMENT ON COLUMN edge.importance IS 'How important this relationship is (0.0 to 1.0)';
COMMENT ON COLUMN edge.description IS 'Rich description of the relationship (e.g., "Principal", "Co-founder")';

-- Step 5: Create a view for "current" relationships (useful for agents)
CREATE OR REPLACE VIEW edge_current AS
SELECT * FROM edge
WHERE end_date IS NULL OR end_date >= CURRENT_DATE;

COMMENT ON VIEW edge_current IS 'Active/current relationships (end_date is NULL or in the future)';

-- Migration complete!
--
-- New relationship types to support:
-- - worked_at (uses start_date, end_date, description for role)
-- - attended (uses start_date, end_date, description for degree/program)
-- - founded (uses start_date, usually no end_date)
-- - led (uses start_date, end_date, description for leadership role)
-- - participated_in (uses start_date, end_date)
-- - lived_in (uses start_date, end_date)
-- - learned_from (knowledge transfer, person → source)
-- - achieved (milestone reached, uses start_date for when)
--
-- Existing types remain supported:
-- - belongs_to, modifies, mentions, informs, blocks, contradicts, relates_to, values, owns
