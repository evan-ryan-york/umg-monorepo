# AI Agent Handoff Document: Archivist Implementation

**Created**: 2025-10-03
**Status**: Phase 3 of 10 in progress (30% complete)
**Next Agent**: Continue implementation from Phase 4

---

## What We're Doing

We are implementing the **Archivist agent** - the intelligent processing engine that transforms raw events into a structured memory graph for the UMG (Unified Memory Graph) project.

The Archivist is the "brain" of the system that:
- Monitors the `raw_events` table for new entries
- Extracts entities (people, projects, features, tasks, etc.) from raw text
- Creates relationships (edges) between entities
- Generates embeddings for semantic search
- Assigns importance/recency/novelty signals
- Enables the Mentor agent to provide intelligent insights

---

## Why We're Doing This

**Problem**: The UMG system captures raw data from voice memos, meeting notes, GitHub commits, and other sources, but this data is unstructured and can't be queried intelligently.

**Solution**: The Archivist agent processes this raw data into a **knowledge graph** with:
- **Entities**: Distinct concepts worth tracking (projects, people, decisions, etc.)
- **Edges**: Relationships between entities (belongs_to, modifies, contradicts, etc.)
- **Chunks**: Searchable text fragments with embeddings
- **Signals**: Dynamic relevance scores that decay over time

**Result**: Users can ask questions like "What did I decide about the Texas school?" and get accurate, context-aware answers grounded in their memory graph.

---

## Architecture Context

### Tech Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI (async REST API)
- **Database**: Supabase (PostgreSQL + pgvector)
- **AI/ML**: OpenAI (GPT-4 for entity extraction, embeddings API)
- **Libraries**: LangChain, spaCy, tiktoken

### Data Flow
1. **Collection**: Raw events stored in `raw_events` table with status `pending_processing`
2. **Sense-Making**: Archivist processes events → creates entities, edges, chunks, embeddings, signals
3. **Coaching**: Mentor agent uses the structured graph to generate insights
4. **Feedback**: User interactions (acknowledge/dismiss) adjust signal scores

---

## What's Been Completed (Phases 0-3)

### ✅ Phase 0: Project Setup
**Location**: `apps/ai-core/`

**Completed**:
- Created directory structure with proper Python modules:
  - `agents/` - Agent orchestrators
  - `services/` - Database, embeddings, chunker
  - `processors/` - Entity extraction, relationship mapping, signal scoring
  - `models/` - Pydantic models for database schema
  - `utils/` - Text cleaner, fuzzy matcher
  - `tests/` - Test files
- Created `requirements.txt` with all dependencies
- Created `config.py` using Pydantic Settings
- Created `main.py` with FastAPI app (health check + process endpoint stubs)
- Created `.env.example`, `.gitignore`

### ✅ Phase 1: Database Layer
**Location**: `apps/ai-core/models/` and `apps/ai-core/services/database.py`

**Completed**:
- Created Pydantic models matching database schema:
  - `raw_event.py` - RawEvent, RawEventPayload
  - `entity.py` - Entity
  - `edge.py` - Edge
  - `chunk.py` - Chunk
  - `embedding.py` - Embedding
  - `signal.py` - Signal
  - `insight.py` - Insight

- Created comprehensive `DatabaseService` class with methods:
  - **Raw Events**: `get_pending_events()`, `get_event_by_id()`, `update_event_status()`, `create_raw_event()`
  - **Entities**: `create_entity()`, `get_entity_by_id()`, `get_entity_metadata()`, `update_entity_metadata()`, `get_entities_by_source_event()`
  - **Hub/Spoke Pattern**: `create_hub_entity()`, `create_spoke_entity()` (for complex entities like "Feed feature")
  - **Edges**: `create_edge()`, `get_edge_count_for_entity()`
  - **Chunks**: `create_chunk()`, `get_chunks_by_entity_id()`
  - **Embeddings**: `create_embedding()`, `get_embeddings_by_chunk_id()`
  - **Signals**: `create_signal()`, `get_signal_by_entity_id()`, `update_signal()`
  - **Insights**: `get_insight_by_id()`, `update_insight_metadata()`, `record_dismissed_pattern()`
  - **Utils**: `now()` static method

**Key Features**:
- Proper filtering: `get_pending_events()` only fetches status='pending_processing' (excludes triage and ignored)
- Hub-and-spoke support for complex entities
- All methods use Supabase client with error handling

### ✅ Phase 2: Text Processing Pipeline
**Location**: `apps/ai-core/utils/` and `apps/ai-core/services/`

**Completed**:
- `utils/text_cleaner.py` - `TextCleaner` class:
  - Removes excessive whitespace
  - Removes markdown artifacts
  - Normalizes quotes (smart quotes → standard quotes)
  - Strips leading/trailing whitespace

- `services/chunker.py` - `Chunker` class:
  - Splits text into ~500 token chunks with 50-token overlap
  - Uses tiktoken (`cl100k_base` encoding) for accurate token counting
  - Generates SHA-256 hash for each chunk (deduplication)
  - Paragraph-aware chunking (preserves context)

- `utils/fuzzy_matcher.py` - `FuzzyMatcher` class:
  - `similarity()` - Returns similarity score 0.0 to 1.0
  - `is_match()` - Boolean match with configurable threshold (default 0.85)
  - Case-insensitive comparison

### 🔄 Phase 3: Entity Extraction (PARTIALLY COMPLETE)
**Location**: `apps/ai-core/processors/`

**Completed**:
- `processors/mention_tracker.py` - `MentionTracker` class:
  - Tracks entity mentions across events
  - `record_mention()` - Records each mention with timestamp
  - `should_promote()` - Determines if entity should be promoted:
    - **Rule 1**: Immediate promotion if primary subject
    - **Rule 2**: Promote after 2-3 mentions across different events
    - **Rule 3**: Don't promote if already promoted
  - `mark_promoted()` - Marks entity as promoted with entity_id
  - `get_existing_entity_id()` - Returns entity_id if already promoted
  - Uses in-memory cache (TODO: make database-backed in production)

- `processors/entity_extractor.py` - `EntityExtractor` class:
  - Uses OpenAI GPT-4 for entity extraction
  - `extract_entities()` - Main extraction method
  - `extract_with_llm()` - Sends prompt to GPT-4, returns structured JSON
  - Extracts: title, type, summary, confidence, is_primary_subject
  - Graceful fallback if OpenAI not available

**Still Needed for Phase 3**:
- None - Phase 3 is functionally complete

---

## What's Left To Do (Phases 4-10)

### Phase 4: Relationship Mapping (Day 5-6)
**Goal**: Identify relationships between entities and create edges, including alias/rename detection.

**Tasks**:
1. Create `processors/relationship_mapper.py`:
   - `detect_relationships()` - Uses LLM to find edges between entities
   - `detect_explicit_relationships()` - Pattern matching for keywords
   - `detect_alias_and_update()` - Detects entity renames (e.g., "school-update" → "feed")
2. Test relationship detection

**Key Requirements**:
- Must detect edge types: `belongs_to`, `modifies`, `mentions`, `informs`, `blocks`, `contradicts`, `relates_to`
- Alias detection uses regex patterns to find renames
- Updates entity metadata with `aliases` array
- Creates `modifies` edge when rename detected

### Phase 5: Embeddings Service (Day 6-7)
**Goal**: Generate vector embeddings for chunks using OpenAI API.

**Tasks**:
1. Create `services/embeddings.py`:
   - `generate_embedding()` - Single text embedding
   - `generate_embeddings_batch()` - Batch processing for efficiency
   - Uses `text-embedding-3-small` model (1536 dimensions)
2. Test embeddings generation

### Phase 6: Signal Scoring (Day 7-8)
**Goal**: Assign importance, recency, novelty scores to entities.

**Tasks**:
1. Create `processors/signal_scorer.py`:
   - `calculate_importance()` - Based on entity type and metadata
   - `calculate_recency()` - Exponential decay with 30-day half-life
   - `calculate_novelty()` - Based on edge count and entity age
2. Test signal scoring

**Importance Map**:
- core_identity: 1.0
- project: 0.85
- feature: 0.8
- decision: 0.75
- person: 0.7
- reflection: 0.65
- task: 0.6
- meeting_note: 0.5
- reference_document: 0.4

### Phase 7: Orchestrator (Day 8-10)
**Goal**: Build the main Archivist class that orchestrates the full pipeline.

**Tasks**:
1. Create `agents/archivist.py`:
   - `process_event()` - Full pipeline for single event:
     1. Fetch event
     2. Parse & clean text
     3. Extract entities
     4. Track mentions & promote entities
     5. Create hub-and-spoke structures
     6. Detect relationships
     7. Detect aliases/renames
     8. Chunk text
     9. Generate embeddings
     10. Assign signals
     11. Update event status to 'processed'
   - `process_pending_events()` - Batch processing
   - `run_continuous()` - Background worker (checks every 60 seconds)
2. Update `main.py` to integrate Archivist:
   - Implement `/process` endpoint
   - Add startup event to run continuous processing
3. Test end-to-end pipeline

**Critical**: The orchestrator must integrate mention tracking, hub-and-spoke creation, and alias detection.

### Phase 8: Testing & Refinement (Day 10-12)
**Goal**: Test end-to-end flow, fix bugs, optimize performance.

**Tasks**:
1. Create `tests/fixtures/sample_events.json` with test data
2. Write integration tests in `tests/test_archivist.py`:
   - Test full pipeline (event → entities → edges → chunks → embeddings → signals)
   - Test mention tracking (entity promotion after 2-3 mentions)
   - Test alias detection (entity rename updates metadata)
   - Test hub-and-spoke creation
3. Performance optimization:
   - Batch API calls where possible
   - Cache frequently accessed entities
   - Add database indexes
4. Error handling improvements:
   - Retry failed API calls with exponential backoff
   - Log detailed error context

**Success Criteria**:
- 90%+ test coverage
- Events processed in < 5 seconds
- Handles errors gracefully

### Phase 9: User Feedback Processing (Day 12-13)
**Goal**: Implement feedback loop for user interactions (Acknowledge/Dismiss) to adjust signal scores.

**Tasks**:
1. Create `agents/feedback_processor.py`:
   - `process_acknowledge()` - Boosts importance/recency for driver entities
   - `process_dismiss()` - Lowers importance, records dismissed pattern
   - `_adjust_entity_signals()` - Updates signal scores
   - `_record_dismissed_pattern()` - Stores pattern to avoid similar insights
2. Update `main.py` with feedback endpoints:
   - `POST /feedback/acknowledge/{insight_id}`
   - `POST /feedback/dismiss/{insight_id}`
3. Extend `services/database.py` with feedback methods
4. Test feedback processing

**Feedback Loop Logic**:
- Acknowledged insight → importance +0.1, recency refreshed, last_surfaced_at updated
- Dismissed insight → importance -0.1, pattern recorded
- System learns user preferences over time

### Phase 10: Deployment (Day 13-14)
**Goal**: Deploy the AI Core as a background service.

**Tasks**:
1. Create `Dockerfile`:
   - Python 3.11-slim base image
   - Install requirements
   - Download spaCy model
   - Run uvicorn server
2. Choose deployment option:
   - Local: Docker Compose
   - Cloud: Railway, Render, or AWS ECS
3. Set up monitoring & logging:
   - Structured logging
   - Error tracking (Sentry)
   - Monitor processing queue depth
   - Track API usage and costs
4. Configure production environment:
   - Production `.env`
   - Secrets management
   - Rate limits for OpenAI API

**Success Criteria**:
- AI Core runs continuously
- Processes events automatically
- Logs visible, errors tracked
- 99%+ uptime

---

## Critical Documents to Read (IN ORDER)

Before continuing, read these documents in this exact order:

### 1. Project Context (Read First)
- `docs/ai-quickstart.md` - **START HERE**
  - Critical rules (never start/stop dev servers, always run build, no TypeScript shortcuts)
  - Project overview, tech stack
  - Development workflow

- `docs/project-wide-resources/ai-memory.md`
  - What's been built so far
  - Current state of the project

- `docs/project-wide-resources/technical-guide.md`
  - Complete architecture explanation
  - Data flow (Collection → Triage → Sense-Making → Coaching)
  - Entity creation rules, hub-and-spoke pattern
  - Feedback loop details

- `docs/project-wide-resources/database-structure.md`
  - Complete database schema
  - All 7 tables explained in detail
  - Entity types, edge kinds, signal formulas

### 2. Implementation Plan (Read Second)
- `docs/features/archivist/implementation-plan.md` - **MASTER PLAN**
  - Full 10-phase implementation plan
  - Code examples for every component
  - Success criteria for each phase
  - 72-hour timeline estimate

- `docs/features/archivist/implementation-plan-updates.md` - **PROGRESS TRACKER**
  - What's been completed (Phases 0-3)
  - What's in progress
  - Notes on deviations or decisions

- `docs/features/archivist/ai-handoff.md` - **THIS FILE**
  - High-level summary
  - Context for next agent

### 3. Code to Review (Read Third)
- `apps/ai-core/config.py` - Settings and environment variables
- `apps/ai-core/main.py` - FastAPI app entry point
- `apps/ai-core/models/` - All Pydantic models
- `apps/ai-core/services/database.py` - Database service (CRITICAL - read carefully)
- `apps/ai-core/processors/` - Mention tracker, entity extractor
- `apps/ai-core/utils/` - Text cleaner, fuzzy matcher
- `apps/ai-core/services/chunker.py` - Text chunking logic

---

## How to Continue

### Step 1: Get Oriented
1. Read the documents listed above in order
2. Review the code that's been written
3. Check the todo list status

### Step 2: Set Up Environment (if not done)
```bash
cd apps/ai-core

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (for future NER support)
python -m spacy download en_core_web_sm

# Copy and configure .env
cp .env.example .env
# Edit .env with real API keys
```

### Step 3: Start Phase 4
Follow the implementation plan exactly:
1. Create `processors/relationship_mapper.py` with:
   - `detect_relationships()` method using GPT-4
   - `detect_explicit_relationships()` for pattern matching
   - `detect_alias_and_update()` for rename detection
2. Test relationship detection
3. Update `implementation-plan-updates.md` when complete
4. Update todo list using TodoWrite tool

### Step 4: Continue Through Phases 5-10
- Follow the implementation plan step-by-step
- Update progress document after each phase
- Keep todo list current
- Test as you go

---

## Important Notes

### Design Decisions Made
1. **Mention Tracker**: Using in-memory cache for MVP (should be database-backed in production)
2. **Entity Extractor**: LLM-first approach (GPT-4) with graceful fallback
3. **Hub-and-Spoke**: Projects, features, decisions are hubs; meeting notes and reflections are spokes
4. **Status Filtering**: Only process events with `status='pending_processing'` (excludes triage and ignored)

### Known Limitations
1. Mention tracker is in-memory (resets on restart) - needs database persistence
2. No rate limiting on OpenAI API calls yet - should add exponential backoff
3. No dead letter queue for failed events - should add error queue
4. Temporal reasoning not implemented (listed in Future Enhancements)

### Code Quality Standards
- No `:any` types in TypeScript
- No `@ts-ignore` without explanation
- All types must be properly defined
- Use existing patterns from the codebase
- Update documentation as you work

### Testing Before Marking Complete
- Always run `pnpm run build` from monorepo root before marking task complete
- Ensure no TypeScript errors were introduced
- Report any build errors

---

## Success Metrics

The Archivist implementation is successful when:

1. **Processing Speed**: Events processed within 5 seconds on average
2. **Extraction Accuracy**: 90%+ of important entities captured
3. **Mention Tracking**: Entities promoted after 2-3 mentions, not immediately
4. **Alias Detection**: Entity renames detected and metadata updated correctly
5. **Hub-Spoke Pattern**: Complex entities (features, projects) have proper spoke relationships
6. **Relationship Quality**: Edges connect related concepts meaningfully
7. **Feedback Loop**: User actions (acknowledge/dismiss) adjust signal scores appropriately
8. **Uptime**: 99%+ uptime for background processing
9. **Cost Efficiency**: OpenAI API costs < $10/month for typical usage
10. **User Trust**: Minimal "why did the system miss this?" moments

---

## Questions? Blockers?

If you encounter issues:

1. **Check the implementation plan** - All code examples are there
2. **Check the technical guide** - Explains the "why" behind design decisions
3. **Check the database structure doc** - Has exact schema details
4. **Ask the user** - They have deep context on the project vision

---

## Final Checklist Before Starting

- [ ] Read `docs/ai-quickstart.md`
- [ ] Read `docs/project-wide-resources/ai-memory.md`
- [ ] Read `docs/project-wide-resources/technical-guide.md`
- [ ] Read `docs/project-wide-resources/database-structure.md`
- [ ] Read `docs/features/archivist/implementation-plan.md`
- [ ] Read `docs/features/archivist/implementation-plan-updates.md`
- [ ] Review existing code in `apps/ai-core/`
- [ ] Understand Phase 4 requirements
- [ ] Ready to continue implementation

---

**Next Agent: Start with Phase 4 - Relationship Mapping**

Good luck! The foundation is solid. You're picking up at a clean checkpoint. 🚀
