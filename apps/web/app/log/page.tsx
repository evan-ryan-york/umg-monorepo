import { LogList } from '@/components/LogList';
import { ResetButton } from '@/components/ResetButton';
import { NavBar } from '@/components/NavBar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { ArchivistLogEntry } from '@repo/db';
import { createClient } from '@supabase/supabase-js';
import type { RawEvent } from '@repo/db';
import { Info } from 'lucide-react';

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

          // Fetch edges created by this event (not all edges involving these entities)
          let createdEdges: ArchivistLogEntry['createdEdges'] = [];
          const { data: edges } = await supabase
            .from('edge')
            .select('id, kind, from_id, to_id')
            .eq('source_event_id', event.id);

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
    <div className="min-h-screen bg-background">
      <main className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Activity Log</h1>
            <p className="text-muted-foreground mt-1">
              See how the Archivist transforms your thoughts into structured knowledge
            </p>
          </div>
          <ResetButton />
        </div>

        {/* Explanation Panel */}
        <Card className="mb-6 border-primary/20 bg-primary/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Info className="h-4 w-4" />
              How to Read This Log
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <strong className="font-semibold">Raw Event:</strong> The original text you submitted through Quick Capture.
            </div>
            <div>
              <strong className="font-semibold">Entities:</strong> Important concepts the AI extracted (people, projects, features, decisions). Hub entities (🚀 projects, 🎯 decisions) are central nodes that other notes connect to.
            </div>
            <div>
              <strong className="font-semibold">Relationships:</strong> How entities connect. For example, a meeting note might "relate to" a project.
            </div>
            <div>
              <strong className="font-semibold">Signals:</strong> Scoring metrics that help surface relevant memories:
              <ul className="ml-6 mt-2 space-y-1 text-xs text-muted-foreground">
                <li>
                  <strong>Importance (0-1):</strong> How central this entity is. Hub entities get higher scores.
                </li>
                <li>
                  <strong>Recency (0-1):</strong> How recently created. Newer items score higher, older items decay.
                </li>
                <li>
                  <strong>Novelty (0-1):</strong> How new or unique. Entities with fewer connections are more novel.
                </li>
              </ul>
            </div>
            <div className="text-xs text-muted-foreground pt-2 border-t">
              <strong>Chunks:</strong> Text split for efficient retrieval. <strong>Embeddings:</strong> Vector representations (currently placeholder values).
            </div>
          </CardContent>
        </Card>

        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : (
          <LogList initialLogs={logs} />
        )}
      </main>
    </div>
  );
}
