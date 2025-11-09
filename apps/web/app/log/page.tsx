import { LogList } from '@/components/LogList';
import { ResetButton } from '@/components/ResetButton';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { ArchivistLogEntry } from '@repo/db';
import { createClient } from '@supabase/supabase-js';
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
      .select('id, payload, source, status, created_at')
      .eq('status', 'processed')
      .order('created_at', { ascending: false })
      .limit(10);

    if (eventsError) {
      error = 'Failed to fetch raw events';
    } else if (rawEvents && rawEvents.length > 0) {
      // For each event, gather all related data in parallel
      logs = await Promise.all(
        rawEvents.map(async (event) => {
          // Fetch entities created by this event
          const { data: entities } = await supabase
            .from('entity')
            .select('id, title, type, summary')
            .eq('source_event_id', event.id);

          const createdEntities: Array<{
            id: string;
            title: string;
            type: string;
            summary: string;
          }> = [];

          if (entities) {
            for (const e of entities) {
              createdEntities.push({
                id: String(e.id),
                title: String(e.title || ''),
                type: String(e.type),
                summary: String(e.summary || ''),
              });
            }
          }

          const entityIds = createdEntities.map((e) => e.id);

          // Fetch edges, signals, and chunks in parallel
          const [edgesResult, signalsResult, chunksResult] = await Promise.all([
            supabase.from('edge').select('id, kind, from_id, to_id').eq('source_event_id', event.id),
            entityIds.length > 0
              ? supabase.from('signal').select('entity_id, importance, recency, novelty').in('entity_id', entityIds)
              : Promise.resolve({ data: null }),
            entityIds.length > 0
              ? supabase.from('chunk').select('id').in('entity_id', entityIds)
              : Promise.resolve({ data: null }),
          ]);

          // Process edges
          const createdEdges: Array<{
            id: string;
            fromEntity: { id: string; title: string; type: string };
            toEntity: { id: string; title: string; type: string };
            kind: string;
          }> = [];

          if (edgesResult.data && edgesResult.data.length > 0) {
            // Batch fetch all entities needed for edges
            const edgeEntityIds = new Set<string>();
            edgesResult.data.forEach(edge => {
              edgeEntityIds.add(edge.from_id);
              edgeEntityIds.add(edge.to_id);
            });

            const { data: edgeEntities } = await supabase
              .from('entity')
              .select('id, title, type')
              .in('id', Array.from(edgeEntityIds));

            // Create a lookup map
            const entityMap = new Map<string, { id: string; title: string; type: string }>();
            if (edgeEntities) {
              edgeEntities.forEach(ent => {
                entityMap.set(ent.id, {
                  id: String(ent.id),
                  title: String(ent.title || 'Unknown'),
                  type: String(ent.type || 'unknown'),
                });
              });
            }

            // Build edges using the lookup map
            edgesResult.data.forEach(edge => {
              const fromEntity = entityMap.get(edge.from_id) || {
                id: String(edge.from_id),
                title: 'Unknown',
                type: 'unknown',
              };

              const toEntity = entityMap.get(edge.to_id) || {
                id: String(edge.to_id),
                title: 'Unknown',
                type: 'unknown',
              };

              createdEdges.push({
                id: String(edge.id),
                fromEntity,
                toEntity,
                kind: String(edge.kind),
              });
            });
          }

          // Process signals
          const signals: Array<{
            entity_id: string;
            importance: number;
            recency: number;
            novelty: number;
          }> = [];

          if (signalsResult.data) {
            for (const s of signalsResult.data) {
              signals.push({
                entity_id: String(s.entity_id),
                importance: Number(s.importance),
                recency: Number(s.recency),
                novelty: Number(s.novelty),
              });
            }
          }

          // Process chunks and embeddings
          let chunkCount = 0;
          let embeddingCount = 0;

          if (chunksResult.data) {
            chunkCount = chunksResult.data.length;

            const chunkIds = chunksResult.data.map((c) => String(c.id));
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

          // Construct clean log entry - explicitly typed to ensure no references leak
          const logEntry: ArchivistLogEntry = {
            rawEvent: {
              id: String(event.id),
              payload: {
                type: String(event.payload?.type || 'text'),
                content: String(event.payload?.content || ''),
              },
              source: String(event.source),
              status: String(event.status),
              created_at: String(event.created_at),
            },
            createdEntities,
            createdEdges,
            summary: {
              chunkCount: Number(chunkCount),
              embeddingCount: Number(embeddingCount),
              signalCount: signals.length,
            },
            signals,
          };

          return logEntry;
        })
      );
    }
  } catch {
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
              <strong className="font-semibold">Relationships:</strong> How entities connect. For example, a meeting note might &ldquo;relate to&rdquo; a project.
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
