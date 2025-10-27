-- UMG Initial Database Schema
-- This creates all the core tables for the UMG system
-- Run this in your Supabase SQL Editor after creating a new project

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. RAW EVENTS TABLE
-- Stores all incoming data before processing
CREATE TABLE IF NOT EXISTS raw_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payload JSONB NOT NULL,
  source TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending_processing',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_events_status ON raw_events(status);
CREATE INDEX IF NOT EXISTS idx_raw_events_created_at ON raw_events(created_at);

COMMENT ON TABLE raw_events IS 'Universal inbox for all incoming data (text, voice transcripts, webhooks)';
COMMENT ON COLUMN raw_events.status IS 'pending_processing, processed, or error';


-- 2. ENTITY TABLE
-- Core knowledge graph nodes
CREATE TABLE IF NOT EXISTS entity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  type TEXT NOT NULL,
  summary TEXT,
  metadata JSONB DEFAULT '{}',
  source_event_id UUID REFERENCES raw_events(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entity_type ON entity(type);
CREATE INDEX IF NOT EXISTS idx_entity_title ON entity(title);
CREATE INDEX IF NOT EXISTS idx_entity_created_at ON entity(created_at);
CREATE INDEX IF NOT EXISTS idx_entity_type_created_at ON entity(type, created_at);
CREATE INDEX IF NOT EXISTS idx_entity_source_event ON entity(source_event_id);

COMMENT ON TABLE entity IS 'Knowledge graph nodes: people, projects, concepts, tasks, goals, etc.';
COMMENT ON COLUMN entity.type IS 'Entity type: person, organization, project, product, task, goal, core_identity, etc.';
COMMENT ON COLUMN entity.metadata IS 'Flexible JSON storage for aliases, tags, and other entity-specific data';


-- 3. EDGE TABLE
-- Relationships between entities
CREATE TABLE IF NOT EXISTS edge (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_id UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  to_id UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  start_date DATE,
  end_date DATE,
  confidence FLOAT DEFAULT 1.0,
  importance FLOAT,
  description TEXT,
  metadata JSONB DEFAULT '{}',
  source_event_id UUID REFERENCES raw_events(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_edge_from ON edge(from_id);
CREATE INDEX IF NOT EXISTS idx_edge_to ON edge(to_id);
CREATE INDEX IF NOT EXISTS idx_edge_kind ON edge(kind);
CREATE INDEX IF NOT EXISTS idx_edges_temporal ON edge(start_date, end_date) WHERE start_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_edges_active ON edge(from_id, kind) WHERE end_date IS NULL;
CREATE INDEX IF NOT EXISTS idx_edges_from_type ON edge(from_id, kind);
CREATE INDEX IF NOT EXISTS idx_edges_to_type ON edge(to_id, kind);
CREATE INDEX IF NOT EXISTS idx_edges_timeline ON edge(from_id, start_date DESC);

COMMENT ON TABLE edge IS 'Typed relationships between entities with temporal support';
COMMENT ON COLUMN edge.kind IS 'Relationship type: worked_at, founded, belongs_to, mentions, modifies, etc.';
COMMENT ON COLUMN edge.start_date IS 'When this relationship began (e.g., employment start date)';
COMMENT ON COLUMN edge.end_date IS 'When this relationship ended (NULL means ongoing/current)';
COMMENT ON COLUMN edge.description IS 'Rich description of the relationship (e.g., "CTO", "Co-founder")';


-- 4. CHUNK TABLE
-- Text chunks for processing and embedding
CREATE TABLE IF NOT EXISTS chunk (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  content_hash TEXT UNIQUE NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunk_entity_id ON chunk(entity_id);
CREATE INDEX IF NOT EXISTS idx_chunk_content_hash ON chunk(content_hash);

COMMENT ON TABLE chunk IS 'Text chunks from entities for embedding and retrieval';
COMMENT ON COLUMN chunk.content_hash IS 'SHA-256 hash of content to prevent duplicates';


-- 5. EMBEDDING TABLE
-- Vector embeddings for semantic search
CREATE TABLE IF NOT EXISTS embedding (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chunk_id UUID NOT NULL REFERENCES chunk(id) ON DELETE CASCADE,
  vector VECTOR(1536),
  model TEXT NOT NULL DEFAULT 'text-embedding-ada-002',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embedding_chunk_id ON embedding(chunk_id);
-- Vector similarity search index (using cosine distance)
CREATE INDEX IF NOT EXISTS idx_embedding_vector ON embedding USING ivfflat (vector vector_cosine_ops);

COMMENT ON TABLE embedding IS 'Vector embeddings for semantic search (1536 dimensions for OpenAI ada-002)';


-- 6. SIGNAL TABLE
-- Importance, recency, and novelty scores for entities
CREATE TABLE IF NOT EXISTS signal (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID UNIQUE NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  importance FLOAT NOT NULL DEFAULT 0.5,
  recency FLOAT NOT NULL DEFAULT 1.0,
  novelty FLOAT NOT NULL DEFAULT 0.5,
  last_mentioned_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_entity_id ON signal(entity_id);
CREATE INDEX IF NOT EXISTS idx_signal_importance ON signal(importance);
CREATE INDEX IF NOT EXISTS idx_signal_recency ON signal(recency);
CREATE INDEX IF NOT EXISTS idx_signal_importance_recency ON signal(importance, recency);

COMMENT ON TABLE signal IS 'Priority scores for entities to surface important/recent/novel information';
COMMENT ON COLUMN signal.importance IS 'How important this entity is (0.0 to 1.0)';
COMMENT ON COLUMN signal.recency IS 'How recently this entity was mentioned (0.0 to 1.0)';
COMMENT ON COLUMN signal.novelty IS 'How novel/surprising this entity is (0.0 to 1.0)';


-- 7. INSIGHT TABLE
-- AI-generated insights for the user
CREATE TABLE IF NOT EXISTS insight (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  priority FLOAT NOT NULL DEFAULT 0.5,
  status TEXT NOT NULL DEFAULT 'pending',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insight_status ON insight(status);
CREATE INDEX IF NOT EXISTS idx_insight_created_at ON insight(created_at);
CREATE INDEX IF NOT EXISTS idx_insight_status_created ON insight(status, created_at);
CREATE INDEX IF NOT EXISTS idx_insight_priority ON insight(priority);

COMMENT ON TABLE insight IS 'AI-generated insights, suggestions, and feedback';
COMMENT ON COLUMN insight.status IS 'pending, acknowledged, dismissed';
COMMENT ON COLUMN insight.type IS 'Insight type: goal_drift, contradiction, opportunity, etc.';


-- 8. DISMISSED_PATTERNS TABLE
-- Track dismissed insight patterns to avoid repeating them
CREATE TABLE IF NOT EXISTS dismissed_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_type TEXT NOT NULL,
  entity_ids UUID[] NOT NULL,
  reason TEXT,
  dismiss_count INTEGER DEFAULT 1,
  last_dismissed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dismissed_patterns_type ON dismissed_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_dismissed_patterns_last_dismissed ON dismissed_patterns(last_dismissed_at);

COMMENT ON TABLE dismissed_patterns IS 'Tracks insight patterns the user has dismissed to avoid repetition';
COMMENT ON COLUMN dismissed_patterns.entity_ids IS 'Array of entity IDs involved in this pattern';


-- Create a view for current/active relationships (useful for agents)
CREATE OR REPLACE VIEW edge_current AS
SELECT * FROM edge
WHERE end_date IS NULL OR end_date >= CURRENT_DATE;

COMMENT ON VIEW edge_current IS 'Active/current relationships (end_date is NULL or in the future)';


-- Schema setup complete!
-- Next steps:
-- 1. Run additional migrations in order (see docs/migrations/README.md)
-- 2. Configure Row Level Security (RLS) if needed for multi-user support
-- 3. Set up any additional triggers or functions
