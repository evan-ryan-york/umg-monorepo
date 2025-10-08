-- Migration: Create dismissed_patterns table
-- Purpose: Store patterns that users have dismissed to avoid similar insights in future
-- Created: 2025-10-07

-- Table to store patterns user has dismissed
CREATE TABLE IF NOT EXISTS dismissed_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_type TEXT NOT NULL,           -- 'Delta Watch', 'Connection', 'Prompt'
    driver_entity_types TEXT[],           -- ['feature', 'project', 'person']
    pattern_signature JSONB,              -- Flexible pattern data
    dismissed_count INTEGER DEFAULT 1,    -- How many times this pattern dismissed
    first_dismissed_at TIMESTAMPTZ DEFAULT NOW(),
    last_dismissed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying patterns by type
CREATE INDEX IF NOT EXISTS idx_dismissed_patterns_type
ON dismissed_patterns(insight_type);

-- Index for querying by timestamp (most recent dismissals)
CREATE INDEX IF NOT EXISTS idx_dismissed_patterns_last_dismissed
ON dismissed_patterns(last_dismissed_at DESC);

-- Index for counting pattern frequency
CREATE INDEX IF NOT EXISTS idx_dismissed_patterns_count
ON dismissed_patterns(dismissed_count DESC);

-- Add comment for documentation
COMMENT ON TABLE dismissed_patterns IS 'Stores insight patterns that users have dismissed to avoid generating similar insights in the future';
COMMENT ON COLUMN dismissed_patterns.insight_type IS 'Type of insight: Delta Watch, Connection, or Prompt';
COMMENT ON COLUMN dismissed_patterns.driver_entity_types IS 'Array of entity types that triggered the dismissed insight';
COMMENT ON COLUMN dismissed_patterns.pattern_signature IS 'JSONB object containing pattern details for matching future insights';
COMMENT ON COLUMN dismissed_patterns.dismissed_count IS 'Number of times this pattern has been dismissed (incremented on similar dismissals)';
