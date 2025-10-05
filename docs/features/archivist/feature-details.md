# The Archivist Agent: Feature Specification

## Overview

The Archivist is the "sense-making" agent at the heart of the UMG system. It transforms raw, unstructured data from the universal inbox (`raw_events` table) into a structured, interconnected memory graph. While users capture thoughts and experiences through various interfaces (voice, text, webhooks), the Archivist quietly works in the background to organize, connect, and preserve this information in a way that enables intelligent retrieval and insight generation.

The Archivist is not a search engine or a simple parserit's an intelligent librarian that understands context, identifies relationships, and builds a growing constellation of knowledge that compounds in value over time.

## Core Responsibility

**Transform chaos into structure**: Take messy, unstructured raw events and convert them into a queryable, semantic graph of entities, relationships, chunks, and embeddings.

The Archivist's job is to answer the question: "What does this mean, and how does it connect to everything else I know?"

## The Processing Pipeline

The Archivist operates as a continuous background process that monitors the `raw_events` table and processes entries with `status='pending_processing'`. Each event flows through a multi-stage pipeline:

### Stage 1: Parse & Clean

**Input**: Raw JSONB payload from `raw_events` table
**Output**: Structured, cleaned text ready for analysis

**What happens:**
- Extract text content from the payload (handling different source types)
- Clean up formatting artifacts (markdown, HTML, transcription errors)
- Normalize whitespace and punctuation
- Preserve metadata about the source and capture method

**Example:**
```
Input payload:
{
  "type": "text",
  "content": "Had a great meeting with Sarah about the Feed feature. We decided to rename it from 'school-update' to just 'feed' for clarity. Need to update docs and tell the team.",
  "metadata": {}
}

Cleaned output:
"Had a great meeting with Sarah about the Feed feature. We decided to rename it from 'school-update' to just 'feed' for clarity. Need to update docs and tell the team."
```

### Stage 2: Entity Recognition

**Input**: Cleaned text
**Output**: List of identified entities with types and confidence scores

**What happens:**
The Archivist uses a combination of NER (Named Entity Recognition) and LLM-based extraction to identify meaningful concepts worth tracking:

**Entity Types:**
- **People**: "Sarah", "the investor from yesterday"
- **Companies**: "Granola", "OpenAI"
- **Projects**: "WaterOS", "Willow Education"
- **Features**: "Feed feature", "voice debrief"
- **Tasks**: "Update docs", "tell the team"
- **Decisions**: "We decided to rename..."
- **Reflections**: Extended thoughts about strategy, learning, etc.
- **Core Identity**: Values, mission statements, principles
- **Reference Documents**: Research, external knowledge

**Intelligence Layer:**
The Archivist doesn't blindly create entities for every mention. It follows specific rules:

1. **Immediate Creation (Direct Action)**:
   - Explicitly creating a task ’ immediate entity
   - "I need to..." ’ task entity
   - "We decided..." ’ decision entity
   - Central subject of intentional capture ’ entity

2. **Signal Accumulation (Multiple Mentions)**:
   - First mention: Tagged in metadata only
   - Second mention (different event): Promoted to entity
   - Third mention: Definitely an entity, retroactively link all previous references

3. **Never Created (Passing References)**:
   - "Have you heard of X?" ’ just metadata
   - Background mentions in context ’ not elevated

**Example:**
```
Text: "Had a great meeting with Sarah about the Feed feature. We decided to rename it from 'school-update' to just 'feed' for clarity. Need to update docs and tell the team."

Identified entities:
- Person: "Sarah" (confidence: 0.95)
- Feature: "Feed feature" (confidence: 0.98)
- Feature (alias): "school-update" (confidence: 0.92)
- Task: "Update docs" (confidence: 0.88)
- Task: "Tell the team" (confidence: 0.85)
- Decision: "Rename feature from school-update to feed" (confidence: 0.96)
```

### Stage 3: Entity Creation/Update

**Input**: List of identified entities
**Output**: Records in `entity` table with proper metadata

**What happens:**

**For New Entities:**
- Create entry in `entity` table
- Set `source_event_id` to link back to raw event (provenance)
- Generate concise `title` (human-readable name)
- Create AI-generated `summary` (1-2 sentence description)
- Populate `metadata` with type-specific data:
  - Tasks: `{"status": "pending", "priority": "medium"}`
  - Features: `{"aliases": [], "status": "active"}`
  - People: `{"last_mentioned": "2025-10-03", "context": "colleague"}`
- Set `created_at` and `updated_at` timestamps

**For Existing Entities (detected via fuzzy matching):**
- Update `summary` if new information emerges
- Append to `metadata.aliases` if new name detected
- Update `updated_at` timestamp
- Preserve full edit history via linked events

**Hub-and-Spoke Architecture:**

Complex, evolving entities (like "Feed feature") use a hub-and-spoke model:
- **Hub**: One core entity (type='feature', title='Feed')
- **Spokes**: All related content (meeting notes, tasks, reflections, code commits)
- All spokes link to hub via edges, creating a rich constellation

**Example:**
```
Entity created:
{
  "id": "uuid-123",
  "source_event_id": "uuid-abc",
  "type": "feature",
  "title": "Feed",
  "summary": "Feature for displaying updates in the Willow app. Previously called 'school-update feature'.",
  "metadata": {
    "aliases": ["school-update", "school-update feature"],
    "status": "active",
    "project": "Willow Education"
  },
  "created_at": "2025-10-03T14:30:00Z",
  "updated_at": "2025-10-03T14:30:00Z"
}
```

### Stage 4: Relationship Mapping

**Input**: List of entities from current event + existing entities in graph
**Output**: Records in `edge` table connecting related entities

**What happens:**
The Archivist identifies relationships between entities and creates edges to represent them. Edges are directed and typed.

**Edge Types:**

1. **belongs_to**: Hierarchical ownership
   - Feature `belongs_to` Project
   - Task `belongs_to` Feature

2. **modifies**: Changes or updates
   - Meeting note `modifies` Feature (e.g., renaming)
   - Decision `modifies` Strategy

3. **mentions**: Simple reference
   - Reflection `mentions` Person
   - Meeting note `mentions` Company

4. **informs**: Knowledge transfer
   - Research `informs` Decision
   - Previous experience `informs` Current approach

5. **blocks**: Dependencies and blockers
   - Task `blocks` another Task
   - Issue `blocks` Feature launch

6. **contradicts**: Tensions and conflicts
   - New strategy `contradicts` Previous approach
   - Recent decision `contradicts` Stated goal

**Intelligence Layer:**

The Archivist uses both explicit signals (keywords like "renamed", "decided", "blocks") and semantic analysis to detect relationships:

- **Explicit Detection**: "We renamed X to Y" ’ creates `modifies` edge
- **Semantic Detection**: Vector similarity between entities ’ creates `informs` edge
- **Temporal Detection**: Same entity mentioned across multiple events ’ creates `modifies` edges linking the narrative

**Why Edges Matter:**
- **Preserve History**: When "school-update" becomes "feed", edge maintains connection
- **Surface Tensions**: When decisions contradict, edges make it visible for Mentor to highlight
- **Enable Traversal**: "Show me all tasks blocking this feature" uses `blocks` edges
- **Build Context**: "What did I learn about this project?" follows `informs` edges

**Example:**
```
Edges created:
1. meeting_note (this event) ’ modifies ’ Feed feature
   metadata: {"change_type": "rename", "old_value": "school-update"}

2. Task "Update docs" ’ belongs_to ’ Feed feature
   metadata: {"priority": "high"}

3. Task "Tell the team" ’ belongs_to ’ Feed feature
   metadata: {"priority": "medium"}

4. Feed feature ’ belongs_to ’ Willow project
   metadata: {}

5. meeting_note ’ mentions ’ Sarah (Person)
   metadata: {"role": "collaborator"}
```

### Stage 5: Chunking

**Input**: Full text content from raw event
**Output**: Multiple records in `chunk` table

**What happens:**

Large documents can't be searched efficiently as single blocks. The Archivist breaks content into smaller, semantically coherent pieces optimized for retrieval.

**Chunking Strategy:**

1. **Token Budget**: Target ~500 tokens per chunk (fits well in embedding model context)
2. **Semantic Boundaries**: Split on natural breaks (paragraphs, topic shifts)
3. **Overlap**: Include 50-100 token overlap between chunks to preserve context
4. **Hash Deduplication**: Generate hash of each chunk to prevent duplicates

**For Different Content Types:**

- **Short text captures** (< 500 tokens): Single chunk
- **Meeting transcripts** (3,000-10,000 tokens): 6-20 chunks by topic
- **Long documents** (20,000+ tokens): 40+ chunks with careful boundary detection

**Why Chunking Matters:**
- Enables precise retrieval (get paragraph 12 of research doc, not entire 20 pages)
- Improves embedding quality (focused text yields better vectors)
- Reduces AI context usage (Mentor gets only relevant sections)
- Supports multi-hop reasoning (chunks from different sources combine to answer questions)

**Example:**
```
Input text (1,200 tokens total):
"Had a great meeting with Sarah about the Feed feature. We decided to rename it from 'school-update' to just 'feed' for clarity. Need to update docs and tell the team.

[...more content about technical implementation...]

[...discussion about timeline and launch plan...]"

Chunks created:
1. chunk_1 (450 tokens): Meeting decision and renaming discussion
2. chunk_2 (500 tokens): Technical implementation details (with 50 token overlap from chunk_1)
3. chunk_3 (350 tokens): Timeline and launch plan (with 50 token overlap from chunk_2)

Each chunk stored with:
- entity_id: Links to meeting_note entity
- text: The chunk content
- token_count: Calculated count
- hash: SHA-256 hash for deduplication
```

### Stage 6: Embedding Generation

**Input**: Chunks from previous stage
**Output**: Vector embeddings in `embedding` table

**What happens:**

Each chunk is sent to an embedding API (OpenAI's `text-embedding-3-small`) to generate a 1,536-dimension vector representation. This vector encodes the semantic meaning of the text in a way that allows for similarity search.

**Process:**
1. Send chunk text to embedding API
2. Receive 1,536-dimension float vector
3. Store in `embedding` table with:
   - `chunk_id`: Links to specific chunk
   - `vec`: The vector data (using pgvector type)
   - `model`: Name of embedding model used

**Why Embeddings Matter:**

Embeddings enable semantic searchfinding content by meaning, not just keywords.

**Example:**
```
Query: "What did I decide about user retention?"

Without embeddings (keyword search):
- Only finds chunks containing exact words "user retention"
- Misses "keeping students engaged over time" (same concept, different words)
- Misses "re-engagement strategy" (related but no keyword match)

With embeddings (semantic search):
1. Generate embedding for query: vec_query
2. Use pgvector to find chunks with high cosine similarity to vec_query
3. Finds:
   - "keeping students engaged over time" (similarity: 0.89)
   - "re-engagement strategy discussion" (similarity: 0.85)
   - "user retention metrics we should track" (similarity: 0.92)
4. Mentor receives all relevant context, regardless of exact wording
```

### Stage 7: Signal Assignment

**Input**: Newly created entity
**Output**: Record in `signal` table with scoring

**What happens:**

The Archivist assigns dynamic relevance scores to each entity to help the Mentor prioritize what matters.

**Signal Scores:**

1. **Importance** (0.0 to 1.0): How critical is this entity?
   - Core identity documents: 1.0 (always reference)
   - Active projects: 0.7-0.9 (high priority)
   - Reference documents: 0.3-0.5 (access when relevant)
   - Archived concepts: 0.1-0.2 (low priority)

   **Calculation**: Based on entity type, user feedback, and mention frequency

2. **Recency** (0.0 to 1.0): How recently was this updated?
   - New entities: 1.0
   - Updated entities: 1.0 (refreshed on any modification)
   - Old entities: Exponential decay over time

   **Decay**: Configurable half-life (e.g., 30 days ’ recency = 0.5)

3. **Novelty** (0.0 to 1.0): How new is this information to the graph?
   - Few connections: High novelty (0.8-1.0)
   - Well-integrated: Low novelty (0.1-0.3)

   **Calculation**: Based on edge count and connection diversity

4. **last_surfaced_at**: When did Mentor last show this to the user?
   - Prevents repetition
   - Allows "reminder" logic after certain time period

**Why Signals Matter:**

Signals solve the problem of evolving priorities. A project from 6 months ago may still be important (high importance) but not currently active (low recency). The Mentor weighs both to surface the right context at the right time.

**Example:**
```
Signal created for "Feed feature" entity:
{
  "entity_id": "uuid-123",
  "importance": 0.85,  // Active feature in important project
  "recency": 1.0,      // Just created/updated
  "novelty": 0.6,      // Some connections, but still evolving
  "last_surfaced_at": null  // Never shown yet
}
```

### Stage 8: Provenance Preservation

**Input**: All created entities, edges, chunks, embeddings
**Output**: Complete audit trail linking back to source

**What happens:**

Every piece of processed data maintains a link back to its source:
- All entities have `source_event_id` pointing to original raw event
- All edges capture the event that identified the relationship
- All chunks belong to entities which link to source events
- Raw events are NEVER deleted or modified

**Why Provenance Matters:**
- **Debugging**: When AI makes a mistake, trace back to source
- **Reprocessing**: Change algorithm, re-run on all raw events
- **Trust**: User can always verify "why did the system say this?"
- **Learning**: Analyze which events yield valuable insights

**Example Audit Trail:**
```
User asks: "Why does the system think the Feed feature was renamed?"

Trace back:
1. Mentor surfaced insight about "Feed feature"
2. Entity ID: uuid-123
3. Entity created from source_event_id: uuid-abc
4. Raw event contains: "We decided to rename it from 'school-update' to just 'feed'"
5. Edge created: modifies relationship with metadata about rename
6. User can see exact source and reasoning
```

### Stage 9: Status Update

**Input**: Successfully processed raw event
**Output**: Updated `raw_events` record

**What happens:**
- Update `status` from `pending_processing` to `processed`
- Add processing metadata (timestamp, entities created, chunks generated)
- Log any errors or warnings for debugging

**This completes the loop**: Event moves from inbox ’ structured graph ’ ready for Mentor to query.

## Entity Evolution: Handling Change Over Time

A critical capability of the Archivist is managing entities that evolve, change names, or shift in meaning.

### The "Feed Feature" Example

**Week 1**: User captures "working on school-update feature"
- Archivist creates entity: title="school-update feature", type='feature'

**Week 2**: User captures "We renamed school-update to 'feed' for clarity"
- Archivist detects: This is talking about same feature (fuzzy matching + context)
- Updates entity: title="Feed", adds "school-update" to metadata.aliases
- Creates edge: meeting_note ’ modifies ’ Feed feature
- Future queries for either "feed" OR "school-update" find this entity

**Week 3**: User captures "Feed feature is launching tomorrow"
- Archivist recognizes "Feed" as existing entity
- Creates edge: new event ’ mentions ’ Feed feature
- Updates signal.recency to 1.0 (active again)

### Multi-Entity References

When a single event references multiple entities, the Archivist creates the full relationship graph:

```
Event: "Need to talk to Sarah about the Feed feature before the WaterOS investor meeting next week."

Entities identified:
- Person: Sarah
- Feature: Feed
- Project: WaterOS
- Task: "Talk to Sarah about Feed" (implicit)
- Event: Investor meeting

Edges created:
- Task ’ mentions ’ Sarah
- Task ’ belongs_to ’ Feed feature
- Task ’ informs ’ Investor meeting
- Investor meeting ’ belongs_to ’ WaterOS project
```

This creates a rich semantic web that the Mentor can traverse to answer questions like:
- "What do I need to do before the investor meeting?"
- "What have Sarah and I discussed recently?"
- "What's the status of the Feed feature?"

## Performance Considerations

### Batch Processing
The Archivist processes events in batches to optimize API calls:
- Pull 10 events at a time from `raw_events`
- Process entities in parallel where possible
- Batch embedding API calls (send multiple chunks at once)

### Error Handling
If processing fails:
- Status remains `pending_processing`
- Error logged to event metadata
- Retry with exponential backoff
- Alert on repeated failures

### Idempotency
Processing the same event twice should be safe:
- Entity creation checks for duplicates via fuzzy matching + hash
- Chunks deduplicated via content hash
- Edges checked for duplicates before creation

## Success Metrics

The Archivist is working well when:

1. **High Extraction Accuracy**: 90%+ of important entities captured
2. **Good Relationship Detection**: Edges connect related concepts meaningfully
3. **Optimal Chunk Size**: Chunks retrieve precise context without truncation
4. **Fast Processing**: Events processed within 5 seconds on average
5. **User Trust**: Minimal "why did the system miss this?" moments

## Future Enhancements

**v1 (MVP)**:
- Basic entity extraction (NER + simple LLM prompts)
- Simple chunking (paragraph-based)
- Single embedding model

**v2 (Enhanced)**:
- Multi-model entity extraction (combine multiple NER approaches)
- Smarter chunking (topic segmentation, semantic boundaries)
- Relationship inference beyond explicit mentions
- Entity merging and deduplication UI

**v3 (Advanced)**:
- Temporal reasoning (detect goal drift, track entity lifecycle)
- Cross-reference external knowledge graphs
- Custom embedding fine-tuning for user's domain
- Automated taxonomy building

## The Archivist's Philosophy

The Archivist operates on a core principle: **Capture everything, organize thoughtfully, preserve forever.**

It never forgets, never judges, never deletes. It simply builds an ever-growing constellation of knowledge, trusting that connections which seem irrelevant today may become invaluable tomorrow.

Every reflection you capture, every decision you document, every insight you preserve becomes a permanent part of your extended memorynot trapped in a rigid hierarchy, but woven into a living graph that grows smarter as you do.

The Archivist is not trying to replace your thinking. It's building the foundation that allows the Mentor to enhance it.
