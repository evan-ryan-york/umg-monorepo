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
Uses Claude to extract entities based on **salience** (how important/central they are to the text):

**21 Entity Types** organized into categories:

**People & Organizations:**
- **People**: "Sarah", "Ryan York"
- **Organizations**: "Willow Education", "The Gathering Place"
- **Teams**: "Product Team", "Engineering Team"

**Work & Career:**
- **Projects**: Major initiatives like "WaterOS pilot"
- **Products**: Features being built like "AI college advisory"
- **Roles**: Job positions like "CTO at Willow Education"
- **Skills**: Capabilities like "JavaScript", "Product Design"
- **Tasks**: Action items like "Update docs"
- **Goals**: Objectives like "Scale to 10,000 students"
- **Milestones**: Achievements like "Won Sally Ride award"

**Knowledge & Identity:**
- **Core Identity**: Values, mission, principles that define you
- **Concepts**: Abstract ideas like "0-to-1 Systems Building"
- **Decisions**: Important choices made
- **Insights**: Realizations and learnings
- **Sources**: Books, articles, research

**Temporal & Spatial:**
- **Events**: Conferences, launches, pivotal moments
- **Locations**: Places that matter like "San Antonio, TX"

**Captured Thoughts:**
- **Meeting Notes**: Transcripts and summaries
- **Reflections**: Personal journal entries

**Smart Extraction Strategy**:

The Archivist extracts based on **salience**, not document type:
- **Primary subjects** → Extract immediately (is_primary_subject: true)
- **Concepts mentioned multiple times or with detail** → Extract
- **Passing references** → Skip unless critical context

**No Arbitrary Limits**:
- If there are 8 values, extract all 8 (don't consolidate to hit quotas)
- If there are 2 goals, extract 2 (don't invent more)
- Only consolidate concepts that are ACTUALLY THE SAME thing phrased differently

**Why This Matters**: The Archivist captures ALL salient entities regardless of content type. Resume data gets full extraction (roles, organizations, skills, milestones with dates). Core identity documents get complete extraction (all values, all goals). No artificial limits or content-type branching.

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
Creates typed connections between entities with **temporal data** and **descriptions**:

**Examples:**
- Ryan York `worked_at` Willow Education (start: 2024-01-01, end: null, description: "Chief Technology Officer")
- Ryan York `founded` The Gathering Place (start: 2018-05-01, end: 2023-12-31, description: "Co-Founder")
- Feed product `belongs_to` → Willow project
- Today's meeting `modifies` → Feed product (because of rename)
- Meeting `mentions` → Sarah (person)
- Task "Update docs" `belongs_to` → Feed product

**Relationship Types** (16 types):

**Work & Career:**
- `worked_at` - Employment relationships with dates and role descriptions
- `attended` - Education with dates and degree info
- `founded` - Created organizations
- `led` - Leadership roles with temporal bounds
- `participated_in` - Project participation

**Knowledge & Learning:**
- `learned_from` - Knowledge sources
- `achieved` - Milestones reached (with achievement date)

**Location & Temporal:**
- `lived_in` - Residency with date ranges

**Hierarchical & Structural:**
- `belongs_to`, `modifies`, `mentions`, `informs`

**Dependencies & Conflicts:**
- `blocks`, `contradicts`

**General & Identity:**
- `relates_to`, `values`, `owns`, `manages`, `contributes_to`

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

The Archivist recognizes and creates 21 entity types organized into 6 categories:

**People & Organizations:**
- `person` - Individuals (e.g., "Sarah", "Ryan York")
- `organization` - Companies, nonprofits, schools (e.g., "Willow Education", "The Gathering Place")
- `team` - Groups within organizations (e.g., "Product Team")

**Work & Career:**
- `project` - Major initiatives (e.g., "WaterOS pilot")
- `product` - Features/products being built (e.g., "AI college advisory", "Feed feature")
- `role` - Job titles/positions (e.g., "CTO at Willow Education", "Principal at RePublic High School")
- `skill` - Capabilities, expertise (e.g., "JavaScript", "Product Design")
- `task` - Action items (e.g., "Update docs")
- `goal` - Objectives being worked toward (e.g., "Scale to 10,000 students")
- `milestone` - Significant achievements (e.g., "Won Sally Ride award", "Secured $3M funding")

**Knowledge & Identity:**
- `core_identity` - Values, mission, principles that define you (importance=1.0)
- `concept` - Abstract ideas, frameworks (e.g., "0-to-1 Systems Building")
- `decision` - Important choices made (e.g., "Chose to expose company failure")
- `insight` - Realizations, learnings (e.g., "Failure is misallocation of energy")
- `source` - Books, articles, podcasts, research (e.g., "The Lean Startup")

**Temporal & Spatial:**
- `event` - Discrete happenings (e.g., "Nashville charter partnership launch", "School facility acquisition")
- `location` - Places that matter (e.g., "San Antonio, TX", "Nashville, TN")

**Captured Thoughts:**
- `meeting_note` - Meeting transcripts/notes
- `reflection` - Personal reflections, journal entries

---

## Relationship Types

The Archivist creates 16 typed edges between entities, with support for temporal data (start_date, end_date), descriptions, and confidence scoring:

**Work & Career** (with temporal support):
- **worked_at**: Employment relationships (e.g., "Ryan York worked_at Willow Education from 2024-01-01, description: 'CTO'")
- **attended**: Education (e.g., "Ryan York attended Middle Tennessee State University from 2003-2007, description: 'Bachelor of Science'")
- **founded**: Created organizations (e.g., "Ryan York founded The Gathering Place in 2018-05-01")
- **led**: Leadership roles with date ranges and descriptions
- **participated_in**: Project participation with timeframes

**Knowledge & Learning:**
- **learned_from**: Knowledge sources (Person → Source)
- **achieved**: Milestones reached (Person → Milestone, with achievement date)

**Location & Temporal:**
- **lived_in**: Residency with date ranges (Person → Location)

**Hierarchical & Structural:**
- **belongs_to**: Hierarchical ownership (Product belongs_to Project)
- **modifies**: Changes/updates (Meeting modifies Product via rename)
- **mentions**: References (Reflection mentions Person)
- **informs**: Knowledge transfer (Research informs Decision)

**Dependencies & Conflicts:**
- **blocks**: Dependencies (Task blocks Task)
- **contradicts**: Tensions (Strategy contradicts Previous approach)

**General & Identity:**
- **relates_to**: General connection (Spoke relates_to Hub)
- **values**: Identity relationship (Person values Core_identity)
- **owns**: Ownership/responsibility (Person owns Goal/Project)
- **manages**: Management (Person manages Team/Project)
- **contributes_to**: Contribution (Person contributes_to Project)

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

**✅ Fully Operational** (as of 2025-10-26)

**Implemented Features**:
- Full 9-step processing pipeline
- **Salience-based entity extraction** - extracts based on importance, not document type
- **21 entity types** - complete taxonomy including role, organization, skill, milestone, location, event
- **No arbitrary limits** - extracts all salient entities (no more "3-5 values" quotas)
- **Temporal relationships** - edges support start_date, end_date, description, confidence, importance
- **16 relationship types** - including worked_at, founded, led, achieved, attended
- **Optimized database schema** - structured columns with indexes for fast agent queries
- **Cache management** - in-memory mention tracker with synchronized reset capability
- **Smart Reset All Data** - clears database AND in-memory cache to ensure consistency
- Mention tracking with promotion rules
- Hub-and-spoke architecture
- Alias detection and updates
- Cross-event entity resolution (pronouns)
- Signal scoring with exponential recency decay
- Visibility layer at `/log` for monitoring

**Known Limitations**:
- Embeddings disabled (Anthropic doesn't provide - using zero vectors)
- Mention tracker is in-memory (resets on restart, but entities persist via database)
- Single-user system (hardcoded for Ryan York)

---

## Cache Management

The Archivist maintains an in-memory cache (MentionTracker) that tracks entity mentions across events. This cache is critical for entity promotion logic but can cause issues if not properly synchronized with the database.

### In-Memory Cache

**Purpose**: Tracks how many times entities are mentioned to determine when they should be promoted from metadata tags to full entities.

**Structure**:
```python
mention_cache = {
    "entity-name": {
        "mention_count": 3,
        "events": ["uuid-1", "uuid-2", "uuid-3"],
        "is_promoted": True,
        "entity_id": "uuid-entity"
    }
}
```

**Lifecycle**:
- Created when ai-core service starts
- Persists for the life of the service process
- **Resets when service restarts**
- **Can be manually cleared via `/reset-cache` endpoint**

### Reset All Data Functionality

When you click the "Reset All Data" button in the Activity Log UI, the system performs a coordinated reset:

**Step 1**: Delete all Archivist data from database (entities, edges, chunks, embeddings, signals, raw_events)

**Step 2**: Clear the in-memory cache by calling `http://127.0.0.1:8000/reset-cache`

**Step 3**: Return success status

**Why Both Steps Are Needed**:
- Database deletion alone leaves stale entity IDs in the cache
- Subsequent entity lookups will return HTTP 406 errors (entity doesn't exist)
- This causes foreign key constraint violations when creating edges
- Result: Partial data extraction with missing relationships

**Implementation**:
- Web API: `/api/archivist-reset` (route.ts)
- Python API: `/reset-cache` endpoint (main.py)
- Archivist method: `clear_cache()` (agents/archivist.py)

**Code**:
```python
# apps/ai-core/agents/archivist.py
def clear_cache(self) -> None:
    """Clear all in-memory caches (called after database reset)"""
    logger.info("Clearing Archivist in-memory cache")
    self.mention_tracker = MentionTracker()  # Reinitialize with empty cache
    logger.info("Cache cleared successfully")
```

---

## Troubleshooting

### Common Setup Issues

#### Environment Variables Not Loading
**Symptom**: Service connects to wrong Supabase URL or shows authentication errors

**Cause**: Multiple `.env` files with conflicting values, or Next.js caching old values

**Solution**:
1. Check all `.env` files in the monorepo:
   - `/Users/ryanyork/Software/umg-monorepo/.env.local` (root)
   - `/Users/ryanyork/Software/umg-monorepo/apps/web/.env.local`
   - `/Users/ryanyork/Software/umg-monorepo/apps/ai-core/.env`
2. Ensure all have matching Supabase credentials
3. Delete `.next` folder: `rm -rf apps/web/.next`
4. Restart dev server: `pnpm dev:web`

#### Schema Mismatches
**Symptom**: Errors like "Could not find the 'hash' column" or "Could not find 'vec' column"

**Cause**: Database schema doesn't match code expectations (common after migrations)

**Known Schema Issues**:
- Chunk table: Code expects `hash` (not `content_hash`), `text` (not `content`), `token_count` column
- Embedding table: Code expects `vec` (not `vector`)

**Solution**: Run schema fixes in Supabase SQL Editor:
```sql
-- Fix chunk table
ALTER TABLE chunk RENAME COLUMN content_hash TO hash;
ALTER TABLE chunk RENAME COLUMN content TO text;
ALTER TABLE chunk ADD COLUMN IF NOT EXISTS token_count INTEGER NOT NULL DEFAULT 0;

-- Fix embedding table
ALTER TABLE embedding RENAME COLUMN vector TO vec;
```

#### Reset All Data Doesn't Clear Everything
**Symptom**: After clicking "Reset All Data", subsequent event processing shows HTTP 406 errors or missing entities

**Cause**: In-memory cache not cleared (only database was reset)

**Solution**: This should not happen if you're on the latest code. If it does:
1. Verify the web API calls `/reset-cache`: Check browser network tab
2. Verify ai-core service is running: `curl http://127.0.0.1:8000/health`
3. Manually restart ai-core service as a workaround
4. Check logs for errors in cache reset call

#### Entities Not Being Created
**Symptom**: Raw events processed but no entities/edges in database

**Cause 1**: Row Level Security (RLS) blocking inserts

**Solution**: Disable RLS for development:
```sql
ALTER TABLE entity DISABLE ROW LEVEL SECURITY;
ALTER TABLE edge DISABLE ROW LEVEL SECURITY;
ALTER TABLE chunk DISABLE ROW LEVEL SECURITY;
ALTER TABLE embedding DISABLE ROW LEVEL SECURITY;
ALTER TABLE signal DISABLE ROW LEVEL SECURITY;
```

**Cause 2**: Entity extraction returning empty results

**Solution**: Check ai-core logs for Claude API errors or invalid JSON parsing

#### Foreign Key Constraint Violations
**Symptom**: Errors like "violates foreign key constraint" when creating chunks or edges

**Cause**: Entity creation failed silently but processing continued

**Solution**:
1. Check that entity IDs are being returned correctly
2. Verify entities exist in database: `SELECT * FROM entity WHERE id = 'uuid'`
3. Check ai-core logs for entity creation errors
4. Ensure cache is synchronized (run Reset All Data)

---

## Next Steps

**Future Enhancements**:
- Contextual reference resolution ("the company", "this project")
- LLM-powered entity resolution for complex references
- Entity augmentation (update existing entities with new info)
- Temporal understanding (track entity state changes over time)
- Multi-user support

---

## Design Philosophy: Completeness Based on Salience

### The Problem We Solved

**Before (with content-type branching and arbitrary limits)**:
- Resume data treated as "reference material" → only 1-3 entities extracted
- Biographical text forced into "3-5 values, 1-3 goals" quotas → artificial consolidation
- Organizations, roles, skills, milestones ignored
- No temporal data on relationships
- Result: **Incomplete graph, missing critical career/biographical data**

**After (salience-based extraction, no limits)**:
- Resume data fully extracted → all organizations, roles, skills, milestones with dates
- Biographical text extracts ALL salient values/goals (no quotas)
- Only consolidates concepts that are ACTUALLY THE SAME thing
- Temporal relationships capture career timeline
- Result: **Complete graph with all salient entities, ready for agent queries**

### Examples of What's Now Possible

**Career Timeline Queries:**
```sql
-- "What was Ryan doing in 2015?"
SELECT e.title, r.description, r.start_date, r.end_date
FROM entity e
JOIN edge r ON r.to_id = e.id
WHERE r.from_id = 'ryan-york-id'
  AND r.start_date <= '2015-12-31'
  AND (r.end_date IS NULL OR r.end_date >= '2015-01-01')
ORDER BY r.start_date;
```

**Current Work:**
```sql
-- "What is Ryan currently working on?"
SELECT e.title, r.kind, r.description
FROM edge r
JOIN entity e ON e.id = r.to_id
WHERE r.from_id = 'ryan-york-id'
  AND r.end_date IS NULL
  AND r.kind IN ('worked_at', 'founded', 'led');
```

**Skills Analysis:**
```sql
-- "What skills does Ryan have?"
SELECT title, summary FROM entity
WHERE type = 'skill'
ORDER BY created_at DESC;
```

### Why This Matters for Agents

Agents can now:
1. **Build career timelines** → Complete work history with dates and roles
2. **Analyze skill evolution** → Track when skills were acquired/used
3. **Query temporal context** → "What was I working on when I learned X?"
4. **Detect patterns** → Career trajectory, role progression, skill gaps
5. **Make connections** → "You solved a similar problem at RePublic Schools in 2016"

### The Trade-Off

**We chose**: Completeness over consolidation
**We accept**: More entities in the graph (but all meaningful)
**We gain**: Agents can query complete biographical/career data with temporal precision

**The principle**: The Archivist captures ALL salient information. Agents decide what's relevant for their specific tasks. Better to have complete data than to prematurely consolidate.

---

For detailed technical implementation information, see [feature-details.md](./feature-details.md).
