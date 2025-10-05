import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import type { ArchivistLogEntry, RawEvent } from '@repo/db';

export async function GET() {
  try {
    // Create Supabase client
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );

    // Step 1: Fetch 10 most recent processed events
    const { data: rawEvents, error: eventsError } = await supabase
      .from('raw_events')
      .select('*')
      .eq('status', 'processed')
      .order('created_at', { ascending: false })
      .limit(10);

    if (eventsError) {
      console.error('Error fetching raw events:', eventsError);
      return NextResponse.json(
        { error: 'Failed to fetch raw events' },
        { status: 500 }
      );
    }

    if (!rawEvents || rawEvents.length === 0) {
      return NextResponse.json([]);
    }

    // Step 2: For each event, gather all related data
    const logEntries: ArchivistLogEntry[] = await Promise.all(
      rawEvents.map(async (event: RawEvent) => {
        // Fetch entities created by this event
        const { data: entities, error: entitiesError } = await supabase
          .from('entity')
          .select('id, title, type, summary')
          .eq('source_event_id', event.id);

        if (entitiesError) {
          console.error('Error fetching entities:', entitiesError);
        }

        const createdEntities = entities || [];
        const entityIds = createdEntities.map((e) => e.id);

        // Fetch edges involving these entities
        let createdEdges: ArchivistLogEntry['createdEdges'] = [];
        if (entityIds.length > 0) {
          const { data: edges, error: edgesError } = await supabase
            .from('edge')
            .select(`
              id,
              kind,
              from_id,
              to_id
            `)
            .or(`from_id.in.(${entityIds.join(',')}),to_id.in.(${entityIds.join(',')})`);

          if (edgesError) {
            console.error('Error fetching edges:', edgesError);
          } else if (edges) {
            // For each edge, fetch the entity titles
            createdEdges = await Promise.all(
              edges.map(async (edge) => {
                const { data: fromEntity } = await supabase
                  .from('entity')
                  .select('id, title, type')
                  .eq('id', edge.from_id)
                  .single();

                const { data: toEntity } = await supabase
                  .from('entity')
                  .select('id, title, type')
                  .eq('id', edge.to_id)
                  .single();

                return {
                  id: edge.id,
                  fromEntity: fromEntity || { id: edge.from_id, title: 'Unknown', type: 'unknown' },
                  toEntity: toEntity || { id: edge.to_id, title: 'Unknown', type: 'unknown' },
                  kind: edge.kind,
                };
              })
            );
          }
        }

        // Fetch signals for these entities
        let signals: ArchivistLogEntry['signals'] = [];
        if (entityIds.length > 0) {
          const { data: signalData, error: signalsError } = await supabase
            .from('signal')
            .select('entity_id, importance, recency, novelty')
            .in('entity_id', entityIds);

          if (signalsError) {
            console.error('Error fetching signals:', signalsError);
          } else {
            signals = signalData || [];
          }
        }

        // Count chunks and embeddings
        let chunkCount = 0;
        let embeddingCount = 0;

        if (entityIds.length > 0) {
          const { data: chunks, error: chunksError } = await supabase
            .from('chunk')
            .select('id')
            .in('entity_id', entityIds);

          if (chunksError) {
            console.error('Error fetching chunks:', chunksError);
          } else if (chunks) {
            chunkCount = chunks.length;

            // Count embeddings for these chunks
            const chunkIds = chunks.map((c) => c.id);
            if (chunkIds.length > 0) {
              const { data: embeddings, error: embeddingsError } = await supabase
                .from('embedding')
                .select('chunk_id')
                .in('chunk_id', chunkIds);

              if (embeddingsError) {
                console.error('Error fetching embeddings:', embeddingsError);
              } else if (embeddings) {
                embeddingCount = embeddings.length;
              }
            }
          }
        }

        return {
          rawEvent: {
            id: event.id,
            payload: event.payload,
            source: event.source,
            status: event.status,
            created_at: event.created_at,
          },
          createdEntities: createdEntities.map((e) => ({
            id: e.id,
            title: e.title || '',
            type: e.type,
            summary: e.summary || '',
          })),
          createdEdges,
          summary: {
            chunkCount,
            embeddingCount,
            signalCount: signals.length,
          },
          signals,
        };
      })
    );

    return NextResponse.json(logEntries);
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
