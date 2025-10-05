import type { ArchivistLogEntry } from '@repo/db';

interface LogItemProps {
  log: ArchivistLogEntry;
}

export function LogItem({ log }: LogItemProps): React.ReactElement {
  const { rawEvent, createdEntities, createdEdges, summary, signals } = log;

  return (
    <div className="border rounded-lg p-6 bg-white shadow-sm">
      {/* Raw Event Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold mb-2">📦 RAW EVENT</h3>
        <div className="text-sm text-gray-600 space-y-1">
          <p>ID: {rawEvent.id.slice(0, 8)}...</p>
          <p>🗓️ {new Date(rawEvent.created_at).toLocaleString()}</p>
          <p>✍️ Source: {rawEvent.source}</p>
          <p>
            Status:{' '}
            <span
              className={
                rawEvent.status === 'processed'
                  ? 'text-green-600 font-medium'
                  : 'text-yellow-600 font-medium'
              }
            >
              {rawEvent.status}
            </span>
          </p>
        </div>
        <blockquote className="mt-3 border-l-4 border-gray-300 pl-4 italic text-gray-700 bg-gray-50 py-2 rounded-r">
          {rawEvent.payload.content}
        </blockquote>
      </div>

      {/* Archivist Actions */}
      <div className="border-t pt-4">
        <h4 className="font-semibold mb-3 text-lg">🧠 ARCHIVIST&apos;S ACTIONS</h4>

        {/* Entities */}
        {createdEntities.length > 0 && (
          <div className="mb-4">
            <p className="font-medium mb-2">
              ✨ Entities Created ({createdEntities.length}):
            </p>
            <ul className="ml-4 space-y-2">
              {createdEntities.map((entity) => {
                const entitySignal = signals.find((s) => s.entity_id === entity.id);
                return (
                  <li key={entity.id} className="text-sm">
                    <div className="flex items-start gap-2">
                      <span>{getEntityEmoji(entity.type)}</span>
                      <div className="flex-1">
                        <span className="font-medium">{entity.type}</span>: &quot;
                        {entity.title}&quot;
                        {entity.summary && (
                          <div className="text-gray-600 text-xs mt-1">
                            {entity.summary}
                          </div>
                        )}
                        {entitySignal && (
                          <div className="text-xs text-gray-500 mt-1">
                            → Signals: I={entitySignal.importance.toFixed(2)}, R=
                            {entitySignal.recency.toFixed(2)}, N=
                            {entitySignal.novelty.toFixed(2)}
                          </div>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Edges */}
        {createdEdges.length > 0 && (
          <div className="mb-4">
            <p className="font-medium mb-2">
              🔗 Relationships Mapped ({createdEdges.length}):
            </p>
            <ul className="ml-4 space-y-1">
              {createdEdges.map((edge) => {
                // Detect hub-spoke relationships
                const isHubSpoke =
                  edge.kind === 'relates_to' &&
                  (edge.fromEntity.type === 'meeting_note' ||
                    edge.fromEntity.type === 'reflection' ||
                    edge.toEntity.type === 'project' ||
                    edge.toEntity.type === 'feature' ||
                    edge.toEntity.type === 'decision');

                return (
                  <li key={edge.id} className="text-sm text-gray-700">
                    &quot;{edge.fromEntity.title}&quot;{' '}
                    <span className="text-blue-600 font-mono text-xs">
                      --[{edge.kind}]--&gt;
                    </span>{' '}
                    &quot;{edge.toEntity.title}&quot;
                    {isHubSpoke && (
                      <span className="text-xs text-blue-600 ml-2 font-medium">
                        (SPOKE→HUB)
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Summary */}
        <div className="mb-3 bg-gray-50 p-3 rounded border border-gray-200">
          <p className="font-medium mb-2">📊 Data Processed:</p>
          <ul className="ml-4 space-y-1 text-sm text-gray-700">
            <li>• Text split into {summary.chunkCount} chunks</li>
            <li>
              • {summary.embeddingCount} vector embeddings generated (1536 dimensions)
            </li>
            <li>• {summary.signalCount} signals assigned to new entities</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function getEntityEmoji(type: string): string {
  const emojiMap: Record<string, string> = {
    // Work-related
    feature: '🚀',
    project: '📂',
    task: '✅',
    // Relationship
    person: '👤',
    company: '🏢',
    // Thought entities
    meeting_note: '📝',
    reflection: '💭',
    decision: '🎯',
    // Knowledge
    core_identity: '⭐',
    reference_document: '📄',
  };
  return emojiMap[type] || '📌';
}
