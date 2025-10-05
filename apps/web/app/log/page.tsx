import { LogList } from '@/components/LogList';
import type { ArchivistLogEntry } from '@repo/db';
import { createClient } from '@supabase/supabase-js';
import type { RawEvent } from '@repo/db';

export const dynamic = 'force-dynamic';

export default async function ArchivistLogPage(): Promise<React.ReactElement> {
  let logs: ArchivistLogEntry[] = [];
  let error: string | null = null;

  try {
    // Create Supabase client with service role key for server-side access
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );

    // Fetch 10 most recent processed events
    const { data: rawEvents, error: eventsError } = await supabase
      .from('raw_events')
      .select('*')
      .eq('status', 'processed')
      .order('created_at', { ascending: false })
      .limit(10);

    if (eventsError) {
      console.error('Error fetching raw events:', eventsError);
      error = 'Failed to fetch raw events';
    } else if (rawEvents) {
      // For each event, gather all related data
      logs = await Promise.all(
        rawEvents.map(async (event: RawEvent) => {
          // Fetch entities created by this event
          const { data: entities } = await supabase
            .from('entity')
            .select('id, title, type, summary')
            .eq('source_event_id', event.id);

          const createdEntities = entities || [];
          const entityIds = createdEntities.map((e) => e.id);

          // Fetch edges involving these entities
          let createdEdges: ArchivistLogEntry['createdEdges'] = [];
          if (entityIds.length > 0) {
            const { data: edges } = await supabase
              .from('edge')
              .select('id, kind, from_id, to_id')
              .or(`from_id.in.(${entityIds.join(',')}),to_id.in.(${entityIds.join(',')})`);

            if (edges) {
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
            const { data: signalData } = await supabase
              .from('signal')
              .select('entity_id, importance, recency, novelty')
              .in('entity_id', entityIds);

            signals = signalData || [];
          }

          // Count chunks and embeddings
          let chunkCount = 0;
          let embeddingCount = 0;

          if (entityIds.length > 0) {
            const { data: chunks } = await supabase
              .from('chunk')
              .select('id')
              .in('entity_id', entityIds);

            if (chunks) {
              chunkCount = chunks.length;

              const chunkIds = chunks.map((c) => c.id);
              if (chunkIds.length > 0) {
                const { data: embeddings } = await supabase
                  .from('embedding')
                  .select('chunk_id')
                  .in('chunk_id', chunkIds);

                if (embeddings) {
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
    }
  } catch (e) {
    console.error('Error fetching logs:', e);
    error = 'Error while fetching logs';
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-6">Archivist Activity Log</h1>
      {error ? (
        <div className="text-red-600 bg-red-50 border border-red-200 rounded p-4">
          {error}
        </div>
      ) : (
        <LogList logs={logs} />
      )}
    </div>
  );
}
