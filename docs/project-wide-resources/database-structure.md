Unified Memory Graph (UMG) Database Structure
This is the complete blueprint for the seven core tables of the Unified Memory Graph (UMG). This is the full technical schema based on our entire conversation.

1. raw_events Table
Purpose: The universal, immutable inbox for all incoming raw data from any source. This is the starting point for everything in the system. Nothing is ever lost—even if AI processing makes mistakes, you can always return to the original data.

Properties:
id (UUID, Primary Key): A unique identifier for the raw event.
payload (JSONB): The raw, unprocessed data (e.g., a full meeting transcript, a GitHub webhook JSON, a voice memo text).
source (TEXT): The origin of the event (e.g., 'voice_debrief', 'quick_capture', 'github_webhook', 'granola_api').
status (TEXT): The processing state of the event:
  - 'pending_triage': Automatic entries waiting for human classification
  - 'pending_processing': Ready for Archivist agent processing
  - 'processed': Successfully processed into entities/edges
  - 'ignored': User-marked as not relevant
created_at (TIMESTAMPTZ): When the event was captured.
Connections: This table is the source of truth. It doesn't connect out to other tables, but the entity table links back to it via the source_event_id.

Status Flow:
- Manual entries (voice debrief, quick capture): Created with 'pending_processing' (skip triage)
- Automatic entries (webhooks): Created with 'pending_triage' → user triages → 'pending_processing'

Triage Workflow (for automatic entries only):
1. User sees queue of unclassified events in Triage UI
2. Quick actions: Delete (status → 'ignored') or Tag importance (low/medium/high)
3. Optional: Add brief notes about why it matters
4. Status changes to 'pending_processing' for Archivist to process

Read/Write Flow:
Written To: By your capture interfaces (the voice app, quick capture tool) and any external API/webhook integrations.
Read By: The Triage UI (for you to classify events) and the "Archivist" agent, which pulls events with a 'pending_processing' status.
2. entity Table
Purpose: The core nodes of your memory graph. Each row represents a distinct person, project, task, reflection, or any other significant concept. Entities are the "nouns" of your life—concepts worth tracking independently.

Properties:
id (UUID, Primary Key): A unique identifier for the entity.
source_event_id (UUID, Foreign Key to raw_events.id): The ID of the raw event that caused this entity's creation.
type (TEXT): The category of the entity:
  - 'project', 'feature', 'task': Work-related entities
  - 'person', 'company': Relationship entities
  - 'meeting_note', 'reflection', 'decision': Thought entities
  - 'core_identity', 'reference_document': Knowledge entities
title (TEXT): A concise, human-readable name for the entity.
summary (TEXT): A brief, AI-generated summary.
metadata (JSONB): Flexible, type-specific data:
  - Task: {"status": "in-progress", "priority": "high"}
  - Feature: {"aliases": ["old-name", "previous-name"], "status": "active"}
  - Core Identity: {"pinned": true} (always referenced by Mentor)
  - Reference Document: {"source": "Kampala research", "date": "2024-03"}
uri (TEXT): A deep link to the original source if it exists (e.g., a URL to a GitHub issue).
created_at (TIMESTAMPTZ): When the entity was created.
updated_at (TIMESTAMPTZ): When the entity was last modified.
Connections: It links to raw_events for provenance. It is the central table that edge, chunk, and signal tables all link to.

Entity Creation Rules:
The Archivist decides when to create an entity based on these rules:

1. Immediate Creation (Direct Action):
   - Creating a task about something → immediate entity
   - Explicitly referencing in intentional capture → immediate entity

2. After Multiple Mentions (Signal Accumulation):
   - Concept mentioned 2-3 times across different events → promoted to entity
   - All previous references linked via edges

3. Never Created (Passing Mentions):
   - Single mention in context ("Have you heard of X?") → tagged in metadata only
   - Background references → not elevated to entity

Hub-and-Spoke Model:
Complex entities like "Feed feature" use a hub-and-spoke structure:
- Hub (One Core Entity): type='feature', title='Feed', metadata includes aliases
- Spokes (Many Linked Entities): meeting_note, reflection, task, code_commit
- All spokes connect to hub via edges, creating a constellation of related information

Example: Feed Feature Renamed
- Original: entity with title="school-update feature"
- Meeting note: "We're renaming it to 'feed'"
- Archivist recognizes this → adds "school-update feature" to aliases in metadata
- Creates 'modifies' edge from meeting_note to feature entity
- Future queries for "feed" OR "school-update" both find this entity

Document Classification (via type and metadata):
- Core Identity (type='core_identity'): User's values, mission, principles
  - importance=1.0, always referenced by Mentor
- Reference Documents (type='reference_document'): Research, external knowledge
  - importance=0.3-0.5, accessed only when relevant
- Both live in same table, connected via edges to other entities

Read/Write Flow:
Written To: By the "Archivist" agent after it processes a raw event.
Read By: All agents (especially the "Mentor") to understand the "what" of your memory. This is the most frequently read table.
3. edge Table
Purpose: Defines the relationships between entities, turning individual memories into a connected graph of knowledge. Relationships are where intelligence emerges—they capture connections, tensions, and evolutions in your thinking.

Properties:
id (UUID, Primary Key): A unique identifier for the relationship.
from_id (UUID, Foreign Key to entity.id): The ID of the source entity.
to_id (UUID, Foreign Key to entity.id): The ID of the destination entity.
kind (TEXT): The type of relationship:
  - 'belongs_to': Feature belongs_to Project
  - 'modifies': Meeting note modifies Feature (e.g., renaming)
  - 'mentions': Reflection mentions Person
  - 'informs': Research informs Decision
  - 'blocks': Task blocks another Task
  - 'contradicts': New strategy contradicts Previous approach
metadata (JSONB): Extra context about the relationship itself.
created_at (TIMESTAMPTZ): When the relationship was created.
Connections: It has two foreign keys pointing to the entity table, creating the graph structure.

Example Relationships:
- Feed feature belongs_to Willow project
- Today's reflection modifies the Feed feature entity (renamed from "school-update")
- Meeting note mentions potential hire (Person entity)
- New strategy contradicts previous approach (surfaces tension for Mentor to highlight)

Why Edges Matter:
- Preserve history: When "school-update feature" becomes "feed", edge maintains connection
- Surface tensions: When decisions contradict, edges make it visible
- Enable traversal: "Show me all tasks blocking this feature" uses 'blocks' edges

Read/Write Flow:
Written To: By the "Archivist" agent when it identifies a connection between two entities during processing.
Read By: All agents to traverse the graph and discover connections between concepts.
4. chunk Table
Purpose: To hold the actual text content associated with an entity, broken down into small, digestible pieces for the AI to search. Large documents can't be searched efficiently as single blocks—chunking allows precise retrieval of relevant sections.

Properties:
id (UUID, Primary Key): A unique identifier for the chunk.
entity_id (UUID, Foreign Key to entity.id): The parent entity this text belongs to.
text (TEXT): The text content of the chunk itself.
token_count (INTEGER): The number of tokens in the chunk.
hash (TEXT): A unique hash of the text to prevent duplicate chunks.
Connections: Has a many-to-one relationship with the entity table (one entity can have many chunks).

Why Chunking Matters:
- Enables precise retrieval: 20-page Kampala water research becomes 50 searchable chunks
- Improves AI context: Instead of entire document, Mentor gets relevant paragraphs
- Supports semantic search: Embeddings work best on focused, coherent text blocks

Example:
A meeting transcript entity (10,000 tokens) becomes:
- 15 chunks, each covering a specific topic discussed
- Each chunk has its own embedding for semantic search
- Mentor retrieves only the 2-3 chunks relevant to current query

Read/Write Flow:
Written To: By the "Archivist" agent as it breaks down the content from a raw_event.
Read By: The RAG (Retrieval-Augmented Generation) system to fetch relevant context to feed to the Mentor.
5. embedding Table
Purpose: To store the vector representations (embeddings) of each chunk, enabling semantic search. This enables finding content by meaning, not just keywords.

Properties:
chunk_id (UUID, Primary Key, Foreign Key to chunk.id): Links directly to a specific chunk.
vec (VECTOR): The vector data itself. This requires the pgvector extension in Postgres.
model (TEXT): The name of the AI model used to create the embedding (e.g., 'text-embedding-3-small').
Connections: A one-to-one relationship with the chunk table.

Why Embeddings Matter:
When you ask "What did I learn about user retention?", the system finds semantically similar chunks even if they never use those exact words. A chunk about "keeping students engaged over time" has high vector similarity to "user retention" despite different vocabulary.

Example Query Flow:
1. User asks: "What did I decide about the water infrastructure approach?"
2. Query embedding generated: vec_query
3. pgvector finds top 5 chunks with highest cosine similarity to vec_query
4. Mentor receives those chunks as context for answer
5. Response synthesizes information across multiple related discussions

Read/Write Flow:
Written To: By the "Archivist" agent immediately after a chunk is created and sent to an embedding API.
Read By: The vector search function of your database to find the most semantically similar chunks to a user's query.
6. signal Table
Purpose: To track the dynamic relevance and priority of entities over time. This is the system's "working memory." Solves the problem of evolving priorities—importance is static history, recency is dynamic reality, and both matter.

Properties:
entity_id (UUID, Primary Key, Foreign Key to entity.id): Links directly to an entity.
importance (FLOAT): How critical is this entity? (0.0 to 1.0).
  - Core identity documents: 1.0
  - Active projects: 0.7-0.9
  - Reference documents: 0.3-0.5
  - Archived concepts: 0.1-0.2
recency (FLOAT): A score representing how recently this entity was created or interacted with.
  - Decays over time (e.g., exponential decay with configurable half-life)
  - Refreshed when entity is updated or mentioned
novelty (FLOAT): A score representing how new the information is.
  - High for entities with few connections
  - Decreases as entity becomes well-integrated into graph
last_surfaced_at (TIMESTAMPTZ): When the Mentor last presented this entity to you, to avoid repetition.
Connections: A one-to-one relationship with the entity table.

Time-Based Intelligence:
The signal table enables sophisticated prioritization:
- Texas online school project: importance=0.8 (still valuable), recency=0.1 (6 months old)
- New WaterOS feature: importance=0.9 (critical), recency=1.0 (active today)
- Mentor weighs both: Surfaces WaterOS in daily digest, but remembers Texas lessons when relevant

Old entities don't get retroactively changed—new events capture updated thinking with high recency. Mentor synthesizes both to understand the journey of an idea.

Feedback Loop:
When you dismiss/acknowledge insights:
- Dismissed insight → lowers importance of related entities
- Acknowledged insight → raises importance, updates recency
- System learns what's valuable to you over time

Read/Write Flow:
Written To: By the "Archivist" when an entity is created/updated. These scores can be periodically recalculated by a background job.
Read By: The "Mentor" agent to decide which information is most relevant to bring up in a conversation or daily digest.
7. insight Table
Purpose: To store the proactive outputs generated by the "Mentor" agent and to track your feedback on them. This closes the feedback loop—your actions teach the system what's valuable.

Properties:
id (UUID, Primary Key): A unique identifier for the insight.
title (TEXT): The headline of the insight (e.g., "Potential Conflict in Priorities", "Delta Watch: Goal Drift Detected").
body (TEXT): The full text of the insight or suggestion.
drivers (JSONB): The entity_ids and edge_ids that prompted the Mentor to generate this insight.
  - Provides provenance: trace back to source entities
  - Enables learning: which combinations of entities yield valuable insights?
status (TEXT): Your feedback on the insight:
  - 'open': Newly generated, not yet reviewed
  - 'acknowledged': User found it valuable
  - 'dismissed': User rejected it as not relevant
created_at (TIMESTAMPTZ): When the insight was generated.
Connections: Logically connects to the entity table via the drivers field.

Insight Types (via title prefix):
- Delta Watch: "Your goal was X, but you focused on Y. Pivot or distraction?"
  - Compares stated intentions with actual work
- Connection: "This insight relates to a pattern from 3 months ago..."
  - Surfaces relevant historical context
- Prompt: "Based on yesterday, what's the most important question today?"
  - Challenges assumptions, proposes reflection

Daily Digest Structure:
The Mentor generates 3 cards every morning (7 AM):
1. Delta Watch card (goal alignment check)
2. Connection card (historical context)
3. Prompt card (forward-looking question)

Feedback Loop in Action:
1. User dismisses a "Delta Watch" insight about time spent on feature X
2. System lowers importance score for feature X entities
3. Future Delta Watch insights weight feature X less heavily
4. User acknowledges a "Connection" insight linking water research to current work
5. System raises importance of research entities, updates recency
6. Mentor surfaces similar research connections more frequently

Read/Write Flow:
Written To: By the "Mentor" agent when it identifies a pattern or a point of feedback for you.
Read By: You, in your main UI. Your interaction (clicking "Acknowledge" or "Dismiss") writes back to the status field, creating the crucial feedback loop.
