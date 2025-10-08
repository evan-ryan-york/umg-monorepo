-- Add source_event_id column to edge table
-- This tracks which event created each relationship

ALTER TABLE edge
ADD COLUMN source_event_id UUID REFERENCES raw_events(id);

-- Create index for querying edges by source event
CREATE INDEX idx_edge_source_event_id ON edge(source_event_id);

-- Add comment
COMMENT ON COLUMN edge.source_event_id IS 'The raw event that created this relationship';
