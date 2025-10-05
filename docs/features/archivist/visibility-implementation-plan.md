# Implementation Plan: Archivist Visibility Layer

## Overview
The goal is to build a new page in the `apps/web` dashboard that provides a human-readable summary of the Archivist agent's actions. It will display the 10 most recently processed `raw_events` and detail the specific database records that were created for each one, explaining why they were created.

This visibility layer helps users understand what the Archivist is doing behind the scenes and provides transparency into the entity extraction, relationship mapping, and signal assignment processes.

---

## Phase 1: Backend - The Log Aggregation API Endpoint

The first step is to create a new API endpoint that can gather all the necessary information. A single `raw_event` can trigger the creation of dozens of related records, so this endpoint will need to perform several queries to assemble a complete picture.

### 1. Create a New API Route: `/api/archivist-log`

**File**: `apps/web/app/api/archivist-log/route.ts`

**Method**: `GET`

**Architecture Note**: This endpoint lives in the Next.js web app (`apps/web`), not in the Python AI Core (`apps/ai-core`). The web app has direct Supabase access via the shared `@repo/db` package. The API route will query the database directly to fetch the processing results created by the Archivist agent.

### 2. Implement the Logic

The endpoint will fetch the 10 most recent `raw_events` that have a status of `'processed'` or `'error'`, ordered by `created_at DESC`.

**IMPORTANT**: Only events with `status='processed'` have gone through the Archivist. Events with other statuses:
- `'pending_triage'`: Automatic webhooks waiting for user classification
- `'pending_processing'`: Ready for processing but not yet processed
- `'ignored'`: User-marked as irrelevant, will never be processed

For this visibility layer, we only want `'processed'` events to show what the Archivist has actually done.

For each of these 10 events, it will then perform a series of related queries:

1. **Fetch Created Entities**:
   ```sql
   SELECT * FROM entity WHERE source_event_id = [current_event.id]
   ```

2. **Fetch Created Edges**:
   - Find all `edge` records where `from_id` OR `to_id` is one of the newly created entity IDs
   - Fetch the titles of the entities on both sides of the edge to make them readable
   ```sql
   SELECT e.*,
          from_entity.title as from_title,
          from_entity.type as from_type,
          to_entity.title as to_title,
          to_entity.type as to_type
   FROM edge e
   JOIN entity from_entity ON e.from_id = from_entity.id
   JOIN entity to_entity ON e.to_id = to_entity.id
   WHERE e.from_id IN ([list_of_new_entity_ids])
      OR e.to_id IN ([list_of_new_entity_ids])
   ```

3. **Count Chunks & Embeddings**:
   - Get a count of `chunk` and `embedding` records associated with the new entities
   ```sql
   SELECT COUNT(*) FROM chunk WHERE entity_id IN ([list_of_new_entity_ids])
   SELECT COUNT(*) FROM embedding
   WHERE chunk_id IN (
     SELECT id FROM chunk WHERE entity_id IN ([list_of_new_entity_ids])
   )
   ```

4. **Fetch Signals**:
   ```sql
   SELECT * FROM signal WHERE entity_id IN ([list_of_new_entity_ids])
   ```

### 3. Define the API Response Payload

The endpoint will return a JSON array, where each object represents a fully processed event and its consequences.

```typescript
// Type definitions for the API response
interface ArchivistLogEntry {
  rawEvent: {
    id: string;
    payload: {
      type: string;
      content: string;
      metadata: Record<string, any>;
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

// Example API Response Structure
[
  {
    "rawEvent": {
      "id": "uuid-123",
      "payload": {
        "type": "text",
        "content": "Had a great meeting with Sarah about the Feed feature...",
        "metadata": {}
      },
      "source": "quick_capture",
      "status": "processed",
      "created_at": "2025-10-05T10:35:00Z"
    },
    "createdEntities": [
      { "id": "uuid-1", "title": "Feed", "type": "feature", "summary": "Feed feature for Willow" },
      { "id": "uuid-2", "title": "Sarah", "type": "person", "summary": "Team member" }
    ],
    "createdEdges": [
      {
        "id": "edge-1",
        "fromEntity": { "id": "uuid-1", "title": "Feed", "type": "feature" },
        "toEntity": { "id": "uuid-3", "title": "Willow Project", "type": "project" },
        "kind": "belongs_to"
      }
    ],
    "summary": {
      "chunkCount": 5,
      "embeddingCount": 5,
      "signalCount": 2
    },
    "signals": [
      { "entity_id": "uuid-1", "importance": 0.8, "recency": 1.0, "novelty": 0.6 },
      { "entity_id": "uuid-2", "importance": 0.7, "recency": 1.0, "novelty": 0.8 }
    ]
  }
  // ... 9 more log objects
]
```

### 4. Implementation Notes

- Use the shared `@repo/db` package for Supabase client access
- Implement proper error handling for database queries
- Consider using Supabase's `.rpc()` for complex queries if needed
- Return empty arrays for entities/edges/signals if none exist
- Handle the case where an event has status='error' gracefully

### 5. Understanding Entity Types and Hub-Spoke Pattern

Based on the database structure, here are the valid entity types:

**Work-related**:
- `project` - Major initiatives (e.g., "Willow Project")
- `feature` - Product features (e.g., "Feed")
- `task` - Action items

**Relationship**:
- `person` - People mentioned (e.g., "Sarah")
- `company` - Organizations

**Thought entities**:
- `meeting_note` - Meeting transcripts/notes
- `reflection` - Personal reflections
- `decision` - Important decisions made

**Knowledge**:
- `core_identity` - User's values, mission, principles (importance=1.0)
- `reference_document` - External research, documentation

**Hub-and-Spoke Model**:
Complex entities (projects, features, decisions) use a hub-and-spoke structure:
- **Hub**: One core entity (e.g., type='feature', title='Feed')
- **Spokes**: Many linked entities (meeting_note, reflection, task, code_commit)
- Spokes connect to hub via `relates_to` edges
- Check entity metadata for `is_hub: true` and `is_spoke: true` flags

**Edge Types** (from database structure):
- `belongs_to` - Hierarchical ownership (Feature belongs_to Project)
- `modifies` - Changes/updates (Meeting modifies Feature via rename)
- `mentions` - References (Reflection mentions Person)
- `informs` - Knowledge transfer (Research informs Decision)
- `blocks` - Dependencies (Task blocks Task)
- `contradicts` - Tensions (Strategy contradicts Previous approach)
- `relates_to` - General connection (Spoke relates_to Hub)

---

## Phase 2: Frontend - The Visibility UI

Next, we'll build the React components to display this aggregated data in a clean, intuitive way.

### 1. Create a New Page: `/log`

**File**: `apps/web/app/log/page.tsx`

This page will be a server component that fetches data from the `/api/archivist-log` endpoint when it renders.

```typescript
// apps/web/app/log/page.tsx
import { LogList } from '@/components/LogList';

export default async function ArchivistLogPage() {
  const response = await fetch('http://localhost:3001/api/archivist-log', {
    cache: 'no-store' // Always fetch fresh data
  });

  const logs = await response.json();

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6">Archivist Activity Log</h1>
      <LogList logs={logs} />
    </div>
  );
}
```

### 2. Design the LogItem Component

This component will receive one of the log objects from the API response and render it.

**File**: `apps/web/components/LogItem.tsx`

The goal is to tell a story for each event.

**UI Mockup**:

```
┌───────────────────────────────────────────────────────────┐
│ 📦 RAW EVENT [ID: abc-123...]                             │
│ --------------------------------------------------------- │
│ 🗓️ Timestamp: October 5, 2025, 10:35 AM                   │
│ ✍️ Source: quick_capture                                   │
│ ✅ Status: processed                                      │
│                                                           │
│ > Had a great meeting with Sarah about the Feed feature.  │
│ > We decided to rename it from 'school-update'.           │
├───────────────────────────────────────────────────────────┤
│ 🧠 ARCHIVIST'S ACTIONS                                    │
│ --------------------------------------------------------- │
│                                                           │
│ ✨ Entities Created (3):                                  │
│    • 🚀 Feature: "Feed"                                  │
│      → Signals: I=0.80, R=1.00, N=0.60                   │
│    • 👤 Person: "Sarah"                                   │
│      → Signals: I=0.70, R=1.00, N=0.80                   │
│    • 📝 Meeting Note: "Meeting about Feed Feature..."     │
│      → Signals: I=0.50, R=1.00, N=1.00                   │
│                                                           │
│ 🔗 Relationships Mapped (3):                              │
│    • "Feed" --[belongs_to]--> "Willow Project"           │
│    • "Meeting Note" --[relates_to]--> "Feed" (SPOKE→HUB) │
│    • "Meeting Note" --[mentions]--> "Sarah"               │
│                                                           │
│ 📊 Data Processed:                                        │
│    • Text split into 5 chunks                             │
│    • 5 vector embeddings generated (1536 dimensions)      │
│    • 3 signals assigned to new entities                   │
└───────────────────────────────────────────────────────────┘
```

### 3. Component Structure

**LogList Component** (`components/LogList.tsx`):
```typescript
interface LogListProps {
  logs: ArchivistLogEntry[];
}

export function LogList({ logs }: LogListProps) {
  if (logs.length === 0) {
    return <p>No processed events yet. The Archivist is waiting...</p>;
  }

  return (
    <div className="space-y-6">
      {logs.map((log) => (
        <LogItem key={log.rawEvent.id} log={log} />
      ))}
    </div>
  );
}
```

**LogItem Component** (`components/LogItem.tsx`):
```typescript
interface LogItemProps {
  log: ArchivistLogEntry;
}

export function LogItem({ log }: LogItemProps) {
  const { rawEvent, createdEntities, createdEdges, summary, signals } = log;

  return (
    <div className="border rounded-lg p-6 bg-white shadow-sm">
      {/* Raw Event Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold">📦 RAW EVENT</h3>
        <p className="text-sm text-gray-600">ID: {rawEvent.id.slice(0, 8)}...</p>
        <p className="text-sm">🗓️ {new Date(rawEvent.created_at).toLocaleString()}</p>
        <p className="text-sm">✍️ Source: {rawEvent.source}</p>
        <p className="text-sm">Status: {rawEvent.status}</p>
        <blockquote className="mt-2 border-l-4 pl-4 italic text-gray-700">
          {rawEvent.payload.content}
        </blockquote>
      </div>

      {/* Archivist Actions */}
      <div className="border-t pt-4">
        <h4 className="font-semibold mb-2">🧠 ARCHIVIST'S ACTIONS</h4>

        {/* Entities */}
        {createdEntities.length > 0 && (
          <div className="mb-3">
            <p className="font-medium">✨ Entities Created ({createdEntities.length}):</p>
            <ul className="ml-4 space-y-1">
              {createdEntities.map((entity) => {
                const entitySignal = signals.find(s => s.entity_id === entity.id);
                return (
                  <li key={entity.id}>
                    {getEntityEmoji(entity.type)} {entity.type}: "{entity.title}"
                    {entitySignal && (
                      <span className="text-xs text-gray-500 ml-2">
                        → Signals: I={entitySignal.importance.toFixed(2)},
                        R={entitySignal.recency.toFixed(2)},
                        N={entitySignal.novelty.toFixed(2)}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Edges */}
        {createdEdges.length > 0 && (
          <div className="mb-3">
            <p className="font-medium">🔗 Relationships Mapped ({createdEdges.length}):</p>
            <ul className="ml-4 space-y-1">
              {createdEdges.map((edge) => {
                // Detect hub-spoke relationships
                const isHubSpoke = edge.kind === 'relates_to' &&
                  (edge.fromEntity.type === 'meeting_note' ||
                   edge.fromEntity.type === 'reflection' ||
                   edge.toEntity.type === 'project' ||
                   edge.toEntity.type === 'feature' ||
                   edge.toEntity.type === 'decision');

                return (
                  <li key={edge.id}>
                    "{edge.fromEntity.title}" --[{edge.kind}]--> "{edge.toEntity.title}"
                    {isHubSpoke && <span className="text-xs text-blue-600 ml-2">(SPOKE→HUB)</span>}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Summary */}
        <div className="mb-3">
          <p className="font-medium">📊 Data Processed:</p>
          <ul className="ml-4 space-y-1">
            <li>• Text split into {summary.chunkCount} chunks</li>
            <li>• {summary.embeddingCount} vector embeddings generated (1536 dimensions)</li>
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
```

### 4. Styling Considerations

- Use Tailwind CSS classes for styling (already configured)
- Consider adding a "Refresh" button to manually reload the log
- Add loading states while fetching data
- Consider pagination if more than 10 events are needed in the future
- Add color coding for different entity types

---

## Phase 3: Database Optimization

To ensure this new page loads quickly, we need to add an index to the database.

### 1. Add Index to `entity` Table

Run the following SQL command in your Supabase SQL Editor:

```sql
CREATE INDEX IF NOT EXISTS idx_entity_source_event_id ON entity(source_event_id);
```

**Why**: This will make the query `SELECT * FROM entity WHERE source_event_id = ?` extremely fast, which is the most critical query for this feature.

### 2. Additional Recommended Indexes

Consider adding these for optimal performance:

```sql
-- Index for edge lookups by entity ID
CREATE INDEX IF NOT EXISTS idx_edge_from_to ON edge(from_id, to_id);

-- Index for chunk lookups by entity ID (may already exist)
CREATE INDEX IF NOT EXISTS idx_chunk_entity_id ON chunk(entity_id);

-- Index for signal lookups by entity ID
CREATE INDEX IF NOT EXISTS idx_signal_entity_id ON signal(entity_id);
```

---

## Success Criteria

- ✅ A new API endpoint at `/api/archivist-log` is created and returns the correct data structure
- ✅ A new page exists at `/log` in the web app
- ✅ The page successfully fetches and displays the 10 most recent processed events
- ✅ Each event log clearly and accurately displays:
  - The original raw text
  - The list of new entities created (with their types and titles)
  - Signal scores for each entity (importance, recency, novelty)
  - The list of new relationships mapped between entities
  - A summary of how many chunks, embeddings, and signals were created
- ✅ The page is readable and provides clear insight into the Archivist's process
- ✅ The new database index is added to maintain performance
- ✅ Error states are handled gracefully (empty logs, failed queries)
- ✅ The UI is responsive and works on different screen sizes

---

## Implementation Order

1. **Phase 3 First**: Add database indexes (quick, no dependencies)
2. **Phase 1**: Build the API endpoint and test with sample data
3. **Phase 2**: Build the frontend components and integrate with API

---

## Future Enhancements (Post-MVP)

- **Real-time updates**: Use Supabase Realtime to auto-refresh when new events are processed
- **Filtering**: Add filters for event source, status, date range
- **Pagination**: Load more than 10 events
- **Search**: Search through processed events by content
- **Event replay**: Add a "Re-process" button to retry failed events
- **Detailed view**: Click an entity to see its full graph neighborhood
- **Export**: Export logs as JSON or CSV for analysis

---

## Notes

- This visibility layer is crucial for debugging the Archivist during development
- It helps users understand the value the system is providing
- The log page should be the first place to check when something seems wrong with entity extraction
- Consider adding this page to the main navigation menu for easy access

---

*Document Created: 2025-10-05*
