# The Archivist Agent

## Overview

The Archivist is the "sense-making" agent at the heart of the UMG system. It transforms raw, unstructured data from the universal inbox (`raw_events` table) into a structured, interconnected memory graph. While you capture thoughts and experiences through various interfaces (voice, text, webhooks), the Archivist quietly works in the background to organize, connect, and preserve this information in a way that enables intelligent retrieval and insight generation.

**The Archivist is not a search engine or a simple parser—it's an intelligent librarian that understands context, identifies relationships, and builds a growing constellation of knowledge that compounds in value over time.**

---

## What Problem Does It Solve?

You capture thoughts throughout the day:
- "Had a meeting with Sarah about the Feed feature"
- "We renamed school-update to just 'feed' for clarity"
- "Need to update docs and tell the team"

This text sits in a database as unstructured data. You can't easily ask questions like:
- "What's the status of the Feed feature?"
- "What did Sarah and I discuss?"
- "What tasks are blocking this project?"

**The Archivist makes this raw text queryable by building a knowledge graph.**

---

## Core Responsibility

**Transform chaos into structure**: Take messy, unstructured raw events and convert them into a queryable, semantic graph of entities, relationships, chunks, and embeddings.

The Archivist's job is to answer the question: **"What does this mean, and how does it connect to everything else I know?"**

---

## How It Works: The 9-Step Pipeline

The Archivist operates as a continuous background process that monitors the `raw_events` table and processes entries with `status='pending_processing'`. Each event flows through a multi-stage pipeline:

### **Step 1: Monitors the Inbox**
- Watches the `raw_events` table for new entries with `status='pending_processing'`
- Pulls them in batches of 10 for efficient processing

### **Step 2: Cleans the Text**
- Removes formatting artifacts, extra spaces, markdown
- Normalizes quotes and punctuation
- Makes text ready for AI processing

### **Step 3: Identifies Important Concepts (Entities)**
Uses Claude to extract:
- **People**: "Sarah"
- **Projects**: "Willow Education"
- **Features**: "Feed feature"
- **Tasks**: "Update docs", "Tell the team"
- **Decisions**: "We decided to rename it"
- **Core Identity**: Values, goals, mission statements (e.g., "Impact rooted in Equity")

**Smart Extraction Strategy**:

The Archivist uses different strategies based on content type:

**For conversational/work notes** (e.g., "Had a meeting with Sarah about Feed"):
- Extracts people, projects, features, tasks, decisions
- Uses mention tracking to avoid creating entities for passing references
- First mention → Just tags in metadata
- 2-3 mentions across different events → Promotes to full entity
- Primary subject of your note → Immediate entity creation

**For biographical/core identity text** (e.g., "My mission is to solve the water crisis"):
- Extracts 3-5 core VALUES (not every value mentioned, only the fundamental ones)
- Extracts 1-3 primary GOALS (not sub-goals or means to an end)
- Extracts the ONE overarching MISSION (if clearly stated)
- Prefers consolidation over granularity
- Example: "Innovation and Independence" (merged) instead of two separate entities
- All core_identity entities are promoted immediately (importance=1.0)

**Why This Matters**: The Archivist adapts its extraction approach to match content type. Work notes need conservative extraction (avoid clutter), while core identity documents need comprehensive extraction (capture your values/goals completely). This ensures the Mentor has clean, consolidated data to detect goal alignment and challenge assumptions.

### **Step 4: Tracks Name Changes (Aliases)**
Detects when you rename things:
- Sees "renamed school-update to feed"
- Updates the Feed entity's metadata with `alias: ["school-update"]`
- Future searches for either name find the same entity

### **Step 5: Resolves Cross-Event References**
Connects entities across events:
- Event 1: "My name is Ryan York"
- Event 2: "I am starting Water OS"
- Result: Creates "Ryan York --[founded]--> Water OS" relationship

**Pronoun Resolution**: Maps "I/me/my" to your person entity

### **Step 6: Connects Related Concepts (Relationships/Edges)**
Creates typed connections between entities:
- Feed feature `belongs_to` → Willow project
- Today's meeting `modifies` → Feed feature (because of rename)
- Meeting `mentions` → Sarah (person)
- Task "Update docs" `belongs_to` → Feed feature

**7 Edge Types**: `belongs_to`, `modifies`, `mentions`, `informs`, `blocks`, `contradicts`, `relates_to`

### **Step 7: Builds Hub-and-Spoke Structures**
For complex topics like "Feed feature":
- **Hub**: One core Feed feature entity
- **Spokes**: All related stuff (meeting notes, tasks, reflections, code commits)
- Everything connects to the hub, creating a constellation of knowledge

**Smart Spoke Creation**:
- **Regular work notes**: Creates spoke entities (meeting notes, reflections) linked to hubs
- **Core identity documents**: Skips spoke creation if 2+ core_identity entities detected
- **Why**: Core identity text is already structured into discrete entities (values, goals, mission). Creating a reflection spoke would be redundant and clutter the graph.

### **Step 8: Breaks Content into Searchable Chunks**
Long documents get split into ~500 token pieces:
- Meeting transcript (10,000 tokens) → 15-20 chunks by topic
- Each chunk gets its own unique hash
- Prevents duplicates, enables precise retrieval

### **Step 9: Assigns Priority Scores (Signals)**
Each entity gets three scores:

**Importance (0.0 to 1.0)**:
- Core identity documents: 1.0
- Active projects: 0.85
- Tasks: 0.6
- Old reference docs: 0.4

**Recency (0.0 to 1.0)**:
- New/updated: 1.0
- Decays over time (30-day half-life)
- Refreshed when mentioned again

**Novelty (0.0 to 1.0)**:
- Few connections: Novel (0.8-1.0)
- Well-integrated: Not novel (0.1-0.3)

---

## The Result: A Living Knowledge Graph

**Before Archivist**:
Raw text blobs in a database → Can't query, can't connect, can't search by meaning

**After Archivist**:
Entities (nodes) + Edges (relationships) + Embeddings (semantic search)
→ "What did I decide about the Feed feature?"
  - Finds: Decision entity, meeting notes, related tasks
  - Follows edges to Sarah (person), Willow (project)
  - Surfaces historical context from 3 months ago
  - All because the graph connects everything

---

## Why This Matters

### 1. **Connects the Dots You Can't See**
6 months ago you solved a problem in WaterOS. Today you face a similar challenge in Willow. The graph surfaces that connection because the embeddings detect semantic similarity.

### 2. **Preserves Context Forever**
"Why did we rename that feature?"
- The Archivist traced it back: meeting note → modifies edge → Feed entity → alias metadata
- Complete provenance from source event to final answer

### 3. **Handles Messy Reality**
- You call it "school-update" in week 1
- Rename to "feed" in week 2
- Mention "the feed thing" in week 3
- The Archivist knows it's all the same concept (via aliases and fuzzy matching)

### 4. **Learns What Matters**
When you acknowledge/dismiss insights:
- Acknowledged → boosts importance scores for related entities
- Dismissed → lowers scores, records pattern to avoid similar insights
- System adapts to your preferences

---

## Real Examples: Following Events Through the Pipeline

### **Example 1: Work Note (Meeting About Feed Feature)**

**Input**: You type in the web app:
```
"Had a great meeting with Sarah about the Feed feature. We decided to rename it from
'school-update' to just 'feed' for clarity. Need to update docs and tell the team."
```

**Archivist Processing**:

1. **Cleans**: Removes extra spaces, normalizes text
2. **Extracts Entities**:
   - Sarah (person, confidence 0.95)
   - Feed feature (feature, confidence 0.98, primary subject)
   - "Update docs" (task, confidence 0.88)
   - "Tell the team" (task, confidence 0.85)
   - Rename decision (decision, confidence 0.96)
3. **Checks Mentions**:
   - Sarah: First mention → just metadata tag
   - Feed: Primary subject → immediate entity creation
   - Tasks: Explicit actions → immediate entities
4. **Detects Alias**:
   - Sees "renamed from school-update to feed"
   - Updates Feed entity metadata: `aliases: ["school-update"]`
5. **Creates Relationships**:
   - Meeting note → modifies → Feed (because of rename)
   - Task "Update docs" → belongs_to → Feed
   - Task "Tell team" → belongs_to → Feed
   - Meeting → mentions → Sarah
6. **Hub-Spoke**:
   - Feed is a hub entity (type='feature')
   - Creates spoke: meeting_note about Feed
   - Edge: spoke → relates_to → hub
7. **Chunks**:
   - Text is short (< 500 tokens) → Single chunk
   - Hash: a3f2b9... (prevents duplicates)
8. **Signals**:
   - Feed entity: importance=0.8 (feature type), recency=1.0 (just created), novelty=0.6 (some connections)
   - Task entities: importance=0.6, recency=1.0, novelty=0.8 (fewer connections)

**Output in Database**:
- 1 raw_event (status → 'processed')
- 4 entities (Feed, Update docs task, Tell team task, Rename decision)
- 5 edges (relationships between them)
- 1 chunk (the text content)
- 4 signal records (priority scores)

**Now You Can Query**:
- "What's the Feed feature?" → Finds entity + all spokes
- "What did Sarah and I discuss?" → Finds meeting via mention edge
- "What tasks do I have for Feed?" → Follows belongs_to edges
- "We changed the name of something..." → Vector search finds rename decision

---

### **Example 2: Core Identity Document (About Me)**

**Input**: You paste a biographical text describing your values, mission, and goals:
```
"Ryan York is, at his core, a 0-to-1 Systems Builder. His work is fueled by a clear set of values:
Impact rooted in Equity, Innovation, and Independence. His life-defining mission is tackling the
global water crisis through WaterOS. Success means building a self-sustaining engine of impact at scale..."
```

**Archivist Processing**:

1. **Cleans**: Normalizes the biographical text
2. **Extracts Entities** (with consolidation strategy):
   - Ryan York (person, primary subject)
   - Impact rooted in Equity (core_identity)
   - Innovation and Independence (core_identity - merged two related values)
   - Tackle the global water crisis (core_identity - mission)
   - Build self-sustaining engine of impact at scale (core_identity - success definition)
   - WaterOS (company)
   - Chose to expose company failure... (decision)
3. **Promotion Check**:
   - All core_identity entities promoted immediately (type='core_identity' → auto-promote)
   - Company and decision entities also promoted immediately (high-value types)
4. **Creates Relationships**:
   - Ryan York → owns → Impact rooted in Equity
   - Ryan York → owns → Innovation and Independence
   - Ryan York → owns → Tackle the global water crisis
   - Ryan York → owns → Build self-sustaining engine...
   - Ryan York → founded → WaterOS
   - Impact rooted in Equity → informs → Tackle the global water crisis
   - WaterOS → relates_to → Tackle the global water crisis
5. **Hub-Spoke Check**:
   - WaterOS is a hub (company type)
   - Detects 4 core_identity entities → **Skips spoke creation** (no redundant reflection entity)
6. **Signals**:
   - All core_identity entities: importance=1.0, recency=1.0, novelty=0.88-0.95
   - WaterOS: importance=0.5, recency=1.0, novelty=0.88
   - Decision: importance=0.75, recency=1.0, novelty=0.92

**Output in Database**:
- 1 raw_event (status → 'processed')
- **7 entities** (not 17! consolidated and clean)
- 10 relationships (all meaningful connections)
- 1 chunk
- 7 signal records

**Why This Is Better**:
- **No redundancy**: "Innovation and Independence" merged (not 2 separate entities)
- **No sub-goals**: "Ensure water access" folded into "Tackle water crisis" (not extracted separately)
- **No reflection spoke**: The extracted entities ARE the memory (no duplicate text blob)
- **Mentor-ready**: Clean data for detecting goal alignment and challenging assumptions

**Now the Mentor Can**:
- Detect drift: "Your mission is to tackle the global water crisis, but you spent 80% of time on Willow features..."
- Reference values: "Your commitment to Impact rooted in Equity (proven when you exposed that company failure) suggests..."
- Challenge assumptions: "Your goal is building a self-sustaining engine at scale. Is WaterOS architected to be self-sustaining, or does it depend on you personally?"

---

## Entity Types

The Archivist recognizes and creates these entity types:

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
- `core_identity` - Your values, mission, principles (importance=1.0)
- `reference_document` - External research, documentation

---

## Relationship Types

The Archivist creates these typed edges between entities:

- **belongs_to**: Hierarchical ownership (Feature belongs_to Project)
- **modifies**: Changes/updates (Meeting modifies Feature via rename)
- **mentions**: References (Reflection mentions Person)
- **informs**: Knowledge transfer (Research informs Decision)
- **blocks**: Dependencies (Task blocks Task)
- **contradicts**: Tensions (Strategy contradicts Previous approach)
- **relates_to**: General connection (Spoke relates_to Hub)

---

## The Archivist's Philosophy

> **Capture everything, organize thoughtfully, preserve forever.**

- Never deletes
- Never judges
- Never forgets
- Just builds an ever-growing constellation of knowledge
- Connections that seem irrelevant today may be invaluable tomorrow

**It's not trying to replace your thinking. It's building the foundation that allows the Mentor agent to enhance it.**

---

## Technical Architecture

**Language**: Python 3.11
**Framework**: FastAPI (async REST API)
**AI Model**: Claude Sonnet 4.5 (Anthropic)
**Database**: Supabase (PostgreSQL + pgvector)

**Key Components**:
- `agents/archivist.py` - Main orchestrator
- `processors/entity_extractor.py` - Entity recognition
- `processors/relationship_mapper.py` - Edge creation
- `processors/signal_scorer.py` - Importance/recency/novelty scoring
- `services/entity_resolver.py` - Cross-event pronoun resolution
- `services/chunker.py` - Text splitting
- `services/database.py` - All database operations

**Processing Mode**:
- Continuous background job checking every 60 seconds
- Batch processing (10 events at a time)
- Average processing time: 10-15 seconds per event

---

## Current Status

**✅ Fully Operational** (as of 2025-10-11)

**Implemented Features**:
- Full 9-step processing pipeline
- **Smart entity extraction** with content-aware strategies (work notes vs core identity documents)
- **Consolidated entity creation** - avoids redundancy (e.g., merges overlapping values)
- **Intelligent promotion rules** - auto-promotes core_identity, decision, project, company types
- **Smart spoke creation** - skips redundant reflection spokes for core identity documents
- Mention tracking with promotion rules
- Hub-and-spoke architecture
- Alias detection and updates
- Cross-event entity resolution (pronouns)
- Signal scoring with exponential recency decay
- Visibility layer at `/log` for monitoring

**Recent Improvements (2025-10-11)**:
- Enhanced entity extraction prompt to consolidate values/goals (avoids creating 17 entities from one bio text)
- Added immediate promotion for high-value types (core_identity, decision, project, company)
- Added spoke creation filter to prevent redundant reflection entities for core identity documents
- Result: Clean, Mentor-ready knowledge graph with 7 meaningful entities instead of 17 redundant ones

**Known Limitations**:
- Embeddings disabled (Anthropic doesn't provide - using zero vectors)
- Mention tracker is in-memory (resets on restart, but entities persist via database)
- Single-user system (hardcoded for Ryan York)

---

## Next Steps

**Future Enhancements**:
- Contextual reference resolution ("the company", "this project")
- LLM-powered entity resolution for complex references
- Entity augmentation (update existing entities with new info)
- Temporal understanding (track entity state changes over time)
- Multi-user support

---

## Design Philosophy: Quality Over Quantity

### The Problem We Solved

**Before (naive extraction)**:
- Extract every concept mentioned → 17 entities from one bio text
- Separate entities for "Innovation", "Independence", "Continuous Learning"
- Separate entities for "Tackle water crisis", "Ensure water access", "Build WaterOS to escape velocity"
- Create reflection spoke duplicating all extracted information
- Result: **Cluttered graph, redundant data, Mentor overwhelmed with similar entities**

**After (intelligent extraction)**:
- Consolidate overlapping values → "Innovation and Independence" (merged)
- Extract primary goals, not sub-goals → "Tackle the global water crisis" (includes water access)
- Extract success definition, not implementation details → "Build self-sustaining engine at scale" (includes escape velocity + empire)
- Skip reflection spoke for core identity documents (extracted entities ARE the memory)
- Result: **7 clean entities, each serving a distinct purpose, Mentor has exactly what it needs**

### Why This Matters for the Mentor Agent

The Mentor's job is to:
1. **Detect goal alignment/drift** → Needs your primary goals, not sub-goals
2. **Challenge assumptions** → Needs your values proven through action (decision entities)
3. **Connect past to present** → Needs clean relationships without noise

**Example of what's now possible**:

```
Mentor Delta Watch (daily digest):
"Your stated mission: Tackle the global water crisis
Your stated values: Impact rooted in Equity
Your recent work: 80% Willow features, 20% WaterOS fundraising

Question: Your commitment to equity was proven when you exposed a company
failure to protect vulnerable populations (Decision entity from 3 months ago).
Does this week's work allocation align with that same equity commitment, or
are you drifting toward what's comfortable rather than what's impactful?"
```

**This query is only possible because**:
- The mission is consolidated (not split into 3 goal entities)
- The values are consolidated (not split into 5 value entities)
- The decision is captured as high-value entity (not buried in a reflection spoke)
- Relationships connect values → decisions → mission

### The Trade-Off

**We chose**: Consolidation over granularity
**We accept**: Some nuance lost (e.g., "Continuous Learning" merged into broader values)
**We gain**: Mentor can reason about your goals/values without getting lost in 17 similar entities

**The principle**: The Archivist exists to serve the Mentor. If extracting more entities makes the Mentor less effective at coaching you, we extract fewer entities.

---

For detailed technical implementation information, see [feature-details.md](./feature-details.md).
