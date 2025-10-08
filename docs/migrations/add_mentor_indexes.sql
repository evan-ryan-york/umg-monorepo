-- Migration: Add indexes for Mentor agent queries
-- Purpose: Optimize query performance for insight generation and feedback processing
-- Created: 2025-10-07

-- Index for fetching open insights (used by Daily Digest UI)
CREATE INDEX IF NOT EXISTS idx_insight_status
ON insight(status);

-- Index for fetching recent insights (ordered by creation time)
CREATE INDEX IF NOT EXISTS idx_insight_created_at
ON insight(created_at DESC);

-- Composite index for insight queries (status + created_at)
CREATE INDEX IF NOT EXISTS idx_insight_status_created
ON insight(status, created_at DESC);

-- Index for entity lookups with high importance/recency (Mentor queries)
CREATE INDEX IF NOT EXISTS idx_signal_importance_recency
ON signal(importance DESC, recency DESC);

-- Index for high recency entities (active work detection)
CREATE INDEX IF NOT EXISTS idx_signal_recency
ON signal(recency DESC) WHERE recency >= 0.8;

-- Index for core identity entities (user's values/goals)
CREATE INDEX IF NOT EXISTS idx_entity_type_core_identity
ON entity(type) WHERE type = 'core_identity';

-- Index for entity created_at (recent work queries)
CREATE INDEX IF NOT EXISTS idx_entity_created_at
ON entity(created_at DESC);

-- Composite index for entity type + created_at (type-specific recent queries)
CREATE INDEX IF NOT EXISTS idx_entity_type_created_at
ON entity(type, created_at DESC);

-- Add comments for documentation
COMMENT ON INDEX idx_insight_status IS 'Optimizes queries for insights by status (open/acknowledged/dismissed)';
COMMENT ON INDEX idx_insight_created_at IS 'Optimizes queries for recent insights';
COMMENT ON INDEX idx_signal_importance_recency IS 'Optimizes Mentor queries for high-priority entities';
COMMENT ON INDEX idx_entity_type_core_identity IS 'Optimizes queries for user goals and values';
