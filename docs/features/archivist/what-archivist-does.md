The Archivist Agent: What It Actually Does

  The Archivist is your intelligent librarian that turns messy thoughts into an organized, searchable memory system.

  The Problem It Solves

  You capture thoughts throughout the day:
  - "Had a meeting with Sarah about the Feed feature"
  - "We renamed school-update to just 'feed' for clarity"
  - "Need to update docs and tell the team"

  This text sits in a database as unstructured data. You can't ask questions like:
  - "What's the status of the Feed feature?"
  - "What did Sarah and I discuss?"
  - "What tasks are blocking this project?"

  The Archivist makes this raw text queryable by building a knowledge graph.

  ---
  What It Does (The 9-Step Pipeline)

  Step 1: Monitors the Inbox

  - Watches the raw_events table for new entries with status='pending_processing'
  - Pulls them in batches of 10

  Step 2: Cleans the Text

  - Removes weird formatting, extra spaces, markdown artifacts
  - Normalizes quotes and punctuation
  - Makes text ready for AI processing

  Step 3: Identifies Important Concepts (Entities)

  Uses GPT-4 to extract:
  - People: "Sarah"
  - Projects: "Willow Education"
  - Features: "Feed feature"
  - Tasks: "Update docs", "Tell the team"
  - Decisions: "We decided to rename it"

  Smart part: Doesn't create an entity for every mention!
  - First mention → Just tags it in metadata
  - 2-3 mentions across different events → Promotes to full entity
  - Primary subject of your note → Immediate entity

  Step 4: Tracks Name Changes (Aliases)

  Detects when you rename things:
  - Sees "renamed school-update to feed"
  - Updates the Feed entity's metadata with alias: ["school-update"]
  - Future searches for either name find the same entity

  Step 5: Connects Related Concepts (Relationships/Edges)

  Creates typed connections between entities:
  - Feed feature belongs_to → Willow project
  - Today's meeting modifies → Feed feature (because of rename)
  - Meeting mentions → Sarah (person)
  - Task "Update docs" belongs_to → Feed feature

  Step 6: Builds Hub-and-Spoke Structures

  For complex topics like "Feed feature":
  - Hub: One core Feed feature entity
  - Spokes: All related stuff (meeting notes, tasks, reflections, code commits)
  - Everything connects to the hub, creating a constellation of knowledge

  Step 7: Breaks Content into Searchable Chunks

  Long documents get split into ~500 token pieces:
  - Meeting transcript (10,000 tokens) → 15-20 chunks by topic
  - Each chunk gets its own unique hash
  - Prevents duplicates, enables precise retrieval

  Step 8: Generates Semantic Embeddings

  Each chunk becomes a 1,536-dimension vector via OpenAI:
  - Enables semantic search (meaning-based, not keyword-based)
  - "What did I decide about user retention?" finds "keeping students engaged over time" even though words differ

  Step 9: Assigns Priority Scores (Signals)

  Each entity gets three scores:

  Importance (0.0 to 1.0):
  - Core identity documents: 1.0
  - Active projects: 0.85
  - Tasks: 0.6
  - Old reference docs: 0.4

  Recency (0.0 to 1.0):
  - New/updated: 1.0
  - Decays over time (30-day half-life)
  - Refreshed when mentioned again

  Novelty (0.0 to 1.0):
  - Few connections: Novel (0.8-1.0)
  - Well-integrated: Not novel (0.1-0.3)

  ---
  The Result: A Living Knowledge Graph

  Before Archivist:
  Raw text blobs in a database
  ↓
  Can't query, can't connect, can't search by meaning

  After Archivist:
  Entities (nodes) + Edges (relationships) + Embeddings (semantic search)
  ↓
  "What did I decide about the Feed feature?"
    → Finds: Decision entity, meeting notes, related tasks
    → Follows edges to Sarah (person), Willow (project)
    → Surfaces historical context from 3 months ago
    → All because the graph connects everything

  ---
  Why This Matters

  1. Connects the Dots You Can't See

  6 months ago you solved a problem in WaterOS. Today you face similar challenge in Willow. The graph surfaces that connection because the embeddings detect semantic
   similarity.

  2. Preserves Context Forever

  "Why did we rename that feature?"
  - The Archivist traced it back: meeting note → modifies edge → Feed entity → alias metadata
  - Complete provenance from source event to final answer

  3. Handles Messy Reality

  - You call it "school-update" in week 1
  - Rename to "feed" in week 2
  - Mention "the feed thing" in week 3
  - The Archivist knows it's all the same concept (via aliases and fuzzy matching)

  4. Learns What Matters

  When you acknowledge/dismiss insights:
  - Acknowledged → boosts importance scores for related entities
  - Dismissed → lowers scores, records pattern to avoid similar insights
  - System adapts to your preferences

  ---
  Real Example: Following One Event Through the Pipeline

  Input: You type in the web app:
  "Had a great meeting with Sarah about the Feed feature. We decided to rename it from 'school-update' to just 'feed' for clarity. Need to update docs and tell the
  team."

  Archivist Processing:

  1. Cleans: Removes extra spaces, normalizes text
  2. Extracts Entities:
    - Sarah (person, confidence 0.95)
    - Feed feature (feature, confidence 0.98, primary subject)
    - "Update docs" (task, confidence 0.88)
    - "Tell the team" (task, confidence 0.85)
    - Rename decision (decision, confidence 0.96)
  3. Checks Mentions:
    - Sarah: First mention → just metadata tag
    - Feed: Primary subject → immediate entity creation
    - Tasks: Explicit actions → immediate entities
  4. Detects Alias:
    - Sees "renamed from school-update to feed"
    - Updates Feed entity metadata: aliases: ["school-update"]
  5. Creates Relationships:
    - Meeting note → modifies → Feed (because of rename)
    - Task "Update docs" → belongs_to → Feed
    - Task "Tell team" → belongs_to → Feed
    - Meeting → mentions → Sarah
  6. Hub-Spoke:
    - Feed is a hub entity (type='feature')
    - Creates spoke: meeting_note about Feed
    - Edge: spoke → relates_to → hub
  7. Chunks:
    - Text is short (< 500 tokens) → Single chunk
    - Hash: a3f2b9... (prevents duplicates)
  8. Embedding:
    - Generates 1,536-dim vector for the chunk
    - Stores in embedding table with chunk_id
  9. Signals:
    - Feed entity: importance=0.8 (feature type), recency=1.0 (just created), novelty=0.6 (some connections)
    - Task entities: importance=0.6, recency=1.0, novelty=0.8 (fewer connections)

  Output in Database:
  - 1 raw_event (status → 'processed')
  - 4 entities (Feed, Update docs task, Tell team task, Rename decision)
  - 5 edges (relationships between them)
  - 1 chunk (the text content)
  - 1 embedding (vector for semantic search)
  - 4 signal records (priority scores)

  Now You Can Query:
  - "What's the Feed feature?" → Finds entity + all spokes
  - "What did Sarah and I discuss?" → Finds meeting via mention edge
  - "What tasks do I have for Feed?" → Follows belongs_to edges
  - "We changed the name of something..." → Vector search finds rename decision

  ---
  The Archivist's Philosophy

  Capture everything, organize thoughtfully, preserve forever.

  - Never deletes
  - Never judges
  - Never forgets
  - Just builds an ever-growing constellation of knowledge
  - Connections that seem irrelevant today may be invaluable tomorrow

  It's not trying to replace your thinking. It's building the foundation that allows the Mentor agent to enhance it.
