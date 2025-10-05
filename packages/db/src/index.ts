import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Payload types for raw_events
export interface RawEventPayload {
  type: 'text' | 'voice' | 'webhook';
  content: string;
  metadata?: Record<string, any>;
}

// Database types based on our schema
export interface RawEvent {
  id: string;
  payload: RawEventPayload;
  source: string;
  status: string;
  created_at: string;
}

// Insert type for creating new raw events
export interface RawEventInsert {
  payload: RawEventPayload;
  source: string;
  status?: string;
}

export interface Entity {
  id: string;
  source_event_id?: string;
  type: string;
  title?: string;
  summary?: string;
  metadata?: Record<string, any>;
  uri?: string;
  created_at: string;
  updated_at: string;
}

export interface Edge {
  id: string;
  from_id: string;
  to_id: string;
  kind: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface Chunk {
  id: string;
  entity_id: string;
  text: string;
  token_count?: number;
  hash?: string;
}

export interface Embedding {
  chunk_id: string;
  vec: number[];
  model: string;
}

export interface Signal {
  entity_id: string;
  importance: number;
  recency: number;
  novelty: number;
  last_surfaced_at?: string;
}

export interface Insight {
  id: string;
  title: string;
  body: string;
  drivers?: Record<string, any>;
  status: string;
  created_at: string;
}

// Archivist Log API types
export interface ArchivistLogEntry {
  rawEvent: {
    id: string;
    payload: {
      type: string;
      content: string;
      metadata?: Record<string, any>;
    };
    source: string;
    status: string;
    created_at: string;
  };
  createdEntities: Array<{
    id: string;
    title: string;
    type: string;
    summary: string;
  }>;
  createdEdges: Array<{
    id: string;
    fromEntity: {
      id: string;
      title: string;
      type: string;
    };
    toEntity: {
      id: string;
      title: string;
      type: string;
    };
    kind: string;
  }>;
  summary: {
    chunkCount: number;
    embeddingCount: number;
    signalCount: number;
  };
  signals: Array<{
    entity_id: string;
    importance: number;
    recency: number;
    novelty: number;
  }>;
}

// Export auth helpers
export * from './auth';
