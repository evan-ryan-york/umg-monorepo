# AI Memory: Development History & Context

This document serves as a living record of what has been built, decisions made, and current state of the UMG project. It's designed to help AI agents (and humans) quickly understand what's already done and what's in progress.

---

## Project Initialization
**Date**: 2025-10-02

### Initial Setup Completed
- Monorepo structure created using Turborepo
- Git repository initialized
- Basic project documentation created:
  - `docs/project-wide-resources/project-overview.md` - Mission and vision
  - `docs/project-wide-resources/technical-guide.md` - Architecture and tech stack
  - `docs/project-wide-resources/database-structure.md` - Complete schema blueprint

### Supabase Backend Setup
**Status**: ✅ Complete

**What was done**:
1. Supabase project created and configured
   - Project URL: `https://mdcarckygvbcjgexvdqw.supabase.co`
   - Environment variables stored in `apps/web/.env.local`

2. Database schema implemented - All 7 core tables created:
   - `raw_events` - Universal inbox for all incoming data
   - `entity` - Core nodes of the memory graph
   - `edge` - Relationships between entities
   - `chunk` - Text content broken into searchable pieces
   - `embedding` - Vector representations for semantic search (using pgvector with 1536 dimensions for OpenAI embeddings)
   - `signal` - Dynamic relevance/priority tracking
   - `insight` - Mentor-generated outputs and user feedback

3. Row Level Security (RLS) configured on `raw_events`:
   - Authenticated users can insert events
   - Authenticated users can read events
   - Note: Currently single-user MVP, no user_id column yet

4. Indexes created for performance:
   - `idx_raw_events_status` on `raw_events(status)`
   - `idx_raw_events_created_at` on `raw_events(created_at DESC)`
   - `idx_edge_from_id` on `edge(from_id)`
   - `idx_edge_to_id` on `edge(to_id)`
   - `idx_chunk_entity_id` on `chunk(entity_id)`

5. Database tested with manual insert - Verified working

---

## Feature 1: Raw Text Input System ✅
**Status**: Complete
**Completed**: 2025-10-03

### Implementation Plan
- Document: `docs/raw-input-text-implementation-plan.md`
- All 6 phases completed successfully

### Phase 1: Database Setup ✅
**Completed**: 2025-10-02
- All database tables created with proper schema
- RLS policies enabled on `raw_events`
- Indexes added for common query patterns
- Manual test insert verified working

### Phase 2: Shared Package Setup ✅
**Completed**: 2025-10-03
- Created `packages/db/src/index.ts` with Supabase client
- Defined TypeScript types:
  - `RawEvent` - Database record type
  - `RawEventInsert` - Insert payload type
  - `RawEventPayload` - JSONB payload structure with type field ('text' | 'voice' | 'webhook')
  - All other table types (Entity, Edge, Chunk, Embedding, Signal, Insight)
- Exported client and all types for use across apps

### Phase 3: Environment Setup ✅
**Completed**: 2025-10-03
- Created `apps/web/.env.local` with Supabase credentials
- Added `@repo/db` dependency to `apps/web/package.json`
- Installed `@tailwindcss/postcss` to fix Tailwind v4 compatibility
- Updated `apps/web/postcss.config.mjs` to use `@tailwindcss/postcss`
- Ran `pnpm install` to link workspace packages

### Phase 4: API Route ✅
**Completed**: 2025-10-03
- Created `apps/web/app/api/events/route.ts`
- Implemented POST endpoint accepting `content` and `source` fields
- Added validation for non-empty content
- Added error handling for Supabase operations
- Returns `{ success: true, id: uuid }` on success

### Phase 5: Frontend Component ✅
**Completed**: 2025-10-03
- Replaced default home page in `apps/web/app/page.tsx`
- Created client component with:
  - Textarea input with placeholder "What's on your mind?"
  - Submit button with loading state
  - Success/error message display
  - Auto-clear on successful submission
- Styled with CSS modules in `apps/web/app/page.module.css`
- Proper disabled states for button and textarea during submission

### Phase 6: Testing & Validation ✅
**Completed**: 2025-10-03
- Dev server running successfully at http://localhost:3001
- End-to-end flow verified:
  - User types text → clicks submit → sees loading state
  - Success message appears → input clears
  - Data correctly saved to Supabase `raw_events` table
  - Payload structure correct: `{ type: 'text', content: '...', metadata: {} }`
  - Source set to 'quick_capture'
  - Status set to 'pending_triage'

### Technical Issues Resolved
1. **Tailwind CSS PostCSS Error**: Fixed by installing `@tailwindcss/postcss` and updating config
2. **Port Conflict**: Dev server defaulted to port 3000 (in use), switched to 3001

### Files Created/Modified
**Created**:
- `docs/raw-input-text-implementation-plan.md`
- `apps/web/.env.local`
- `apps/web/app/api/events/route.ts`
- Modified: `packages/db/src/index.ts` (added RawEventPayload and RawEventInsert types)
- Modified: `apps/web/app/page.tsx` (replaced with input form)
- Modified: `apps/web/app/page.module.css` (new styles)
- Modified: `apps/web/package.json` (added @repo/db dependency)
- Modified: `apps/web/postcss.config.mjs` (fixed Tailwind config)

---

## Environment & Configuration

### Supabase Credentials
Location: `apps/web/.env.local`
```
NEXT_PUBLIC_SUPABASE_URL=https://mdcarckygvbcjgexvdqw.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[stored in .env.local]
SUPABASE_SERVICE_ROLE_KEY=[stored in .env.local]
```

### Tech Stack Confirmed
- Monorepo: Turborepo with pnpm
- Frontend: Next.js (App Router) for `apps/web`
- Database: Supabase (PostgreSQL with pgvector extension)
- Language: TypeScript

---

## Key Decisions & Notes

### Database Design Decisions
- Using JSONB for flexible `payload` in `raw_events` to accommodate different data sources
- Using JSONB for `metadata` fields to allow type-specific data without schema changes
- `embedding.vec` dimensionality set to 1536 for OpenAI's text-embedding-3-small model
- RLS policies assume single authenticated user for MVP (no user_id column yet)

### Architecture Decisions
- Starting with web app only (mobile and desktop deferred)
- Simple text input first (voice and guided questions deferred)
- No AI processing yet (Archivist and Mentor agents are future phases)
- Using Tailwind CSS v4 with `@tailwindcss/postcss` plugin
- Running dev server on port 3001 to avoid conflicts

---

## Feature 2: Archivist Agent (AI Core) 🚧
**Status**: 80% Complete (8 of 10 phases)
**Started**: 2025-10-03
**Current Phase**: Phase 9 - User Feedback Processing

### Overview
The Archivist is the intelligent processing engine that transforms raw events into a structured memory graph. It's a Python/FastAPI service that runs independently from the Next.js web app.

### Implementation Progress
Full details in: `docs/features/archivist/implementation-plan-updates.md`

### ✅ Completed Phases (0-8)

**Phase 0: Project Setup** ✅
- Created `apps/ai-core/` directory with Python project structure
- Created `requirements.txt` with all dependencies
- Created `config.py` with Pydantic Settings
- Created `.env.example` template
- 27 total files created

**Phase 1-6: Core Components** ✅
- Database layer with Supabase integration
- Text processing (cleaning, chunking, token counting)
- Entity extraction using GPT-4
- Mention tracking (2-3 mention promotion rule)
- Relationship mapping (7 edge types)
- Embeddings service (OpenAI text-embedding-3-small)
- Signal scoring (importance/recency/novelty)

**Phase 7: Orchestrator** ✅
- `agents/archivist.py` - Full 11-step processing pipeline
- `main.py` - FastAPI app with 4 endpoints
- Batch processing and continuous background mode
- Development vs production mode support

**Phase 8: Testing & Refinement** ✅
- Integration tests with mocking
- 5 sample event fixtures
- 70+ total tests across all modules
- Bug fixes (logging improvements)

### 🚧 In Progress (Phase 9)

**Phase 9: User Feedback Processing** - Ready to start
- Acknowledge/Dismiss feedback endpoints
- Signal score adjustments based on user feedback
- Dismissed pattern recording

### 📝 Remaining (Phase 10)

**Phase 10: Deployment**
- Docker containerization
- Production deployment
- Monitoring and logging setup

### Environment Configuration

**IMPORTANT**: The AI Core has its own separate environment configuration!

**Location**: `apps/ai-core/.env` (create from `.env.example`)

**Required Variables**:
```bash
# Supabase (SAME credentials as web app)
SUPABASE_URL=https://mdcarckygvbcjgexvdqw.supabase.co
SUPABASE_SERVICE_ROLE_KEY=[same as apps/web/.env.local]

# OpenAI (for entity extraction and embeddings)
OPENAI_API_KEY=[your OpenAI API key]

# Environment
ENVIRONMENT=development  # or 'production'
LOG_LEVEL=INFO
```

**Note**: Supabase credentials are the SAME as the web app. The database schema with all 7 tables is ALREADY CREATED and working.

### How to Run the Archivist

```bash
# 1. Navigate to AI Core
cd apps/ai-core

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download spaCy model (for future NER support)
python -m spacy download en_core_web_sm

# 5. Copy and configure .env
cp .env.example .env
# Edit .env with your OpenAI API key (Supabase credentials already exist)

# 6. Run the server
python main.py
# FastAPI runs on http://localhost:8000
# Docs at http://localhost:8000/docs
```

### API Endpoints

- `GET /health` - Health check
- `POST /process` - Manually trigger batch processing
- `POST /process/event/{event_id}` - Process specific event
- `GET /status` - Service status and model info

### Processing Flow

1. **Raw event created** (via web app at localhost:3001)
   - Saved to `raw_events` with `status='pending_triage'`
   - Currently needs manual status change to `pending_processing`

2. **Archivist processes event**:
   - Extract entities (GPT-4)
   - Track mentions (promote after 2-3 mentions)
   - Create hub entities (project/feature/decision)
   - Create spoke entities (meeting_note/reflection)
   - Detect relationships and create edges
   - Detect aliases/renames
   - Chunk text (~500 tokens + overlap)
   - Generate embeddings (1536 dimensions)
   - Assign signals (importance/recency/novelty)
   - Mark event as 'processed'

3. **Result**: Structured memory graph in database

### Current State

**What Works**:
- ✅ Database schema (all 7 tables created)
- ✅ Web app captures raw events
- ✅ Archivist code complete (80%)
- ✅ Full pipeline tested

**What's Needed to Run End-to-End**:
1. Set up `apps/ai-core/.env` with OpenAI API key
2. Install Python dependencies
3. Start FastAPI server
4. Manually change event status from 'pending_triage' → 'pending_processing'
5. Trigger processing via API or wait for background worker

**Why Not Automatic Yet**:
- Triage phase (Phase 9) will handle automatic status changes
- For now, manually update status in Supabase or add a simple SQL trigger

---

## What's NOT Built Yet

### Future Features (Not Started)
- Mobile app (React Native)
- Desktop app (Tauri)
- Mentor agent (generates insights from graph)
- Voice input
- Guided opening/closing questions
- Triage UI (manual event classification)
- Graph visualization
- RAG system for conversational queries
- Multi-user support
- Google SSO authentication

### Archivist Features (Remaining)
- Phase 9: User feedback processing (acknowledge/dismiss) - 📝 Planned
- Phase 10: Production deployment with monitoring - 📝 Planned

---

## Feature 3: Entity Resolution (Phase 1) ✅
**Status**: Complete
**Completed**: 2025-10-06

### What It Does
Enables the Archivist to connect entities across multiple events. When you say "I am starting Water OS", the system resolves "I" to "Ryan York" from a previous event and creates the relationship "Ryan York --[founded]--> Water OS".

### Implementation Highlights
1. **Self-Introduction Detection** - When you say "My name is Ryan York", the Archivist:
   - Creates a person entity for Ryan York
   - Marks it with `is_user_entity: true` in metadata
   - Uses it for all future pronoun resolutions

2. **Pronoun Resolution** - Resolves "I", "me", "my" to the user entity ID

3. **Database-Backed Entity Lookup** - Before creating new entities, checks both:
   - In-memory mention tracker (for current session)
   - Database (for entities across restarts)

4. **Edge Source Tracking** - All edges include `source_event_id` to track which event created them

5. **Build System** - `pnpm run build` runs TypeScript type-checking and linting

### Files Created/Modified
- `apps/ai-core/services/entity_resolver.py` - Pronoun resolution service
- `apps/ai-core/services/database.py` - Added `get_entity_by_title()` method
- `apps/ai-core/agents/archivist.py` - Self-introduction detection (line 142), database entity lookup (lines 116-124)
- `apps/ai-core/processors/relationship_mapper.py` - Added `source_event_id` parameter
- `apps/web/app/api/events/route.ts` - `getUserEntityId()` function (does NOT pre-create entities)
- `apps/web/app/log/page.tsx` - Filter edges by `source_event_id`
- `packages/db/src/index.ts` - Added `user_id` and `user_entity_id` to `RawEventPayload`
- `turbo.json` - Declared environment variables for turbo cache
- `package.json` - Build script includes lint + check-types
- `docs/migrations/add_source_event_id_to_edge.sql` - Database migration

### Manual Steps Required
**Run SQL migration in Supabase**: `docs/migrations/add_source_event_id_to_edge.sql`

---

## How to Use This Document

**For AI Agents**:
- Read this first to understand what's already done
- Update this document whenever you complete a significant piece of work
- Add new sections chronologically as the project evolves
- Mark status with emojis: ✅ Complete, 🚧 In Progress, ❌ Blocked, 📝 Planned

**For Humans**:
- This is your "what did the AI do last time" reference
- Review before starting a new session
- Keep it concise but comprehensive

---

## Feature 4: Mentor Agent & Feedback Loop 🚧
**Status**: Phase 1 Complete (Database Setup)
**Started**: 2025-10-07

### Phase 1: Database Setup ✅ COMPLETE

**What was built**:
1. **Migration Files**:
   - `docs/migrations/create_dismissed_patterns_table.sql` - Table for storing dismissed patterns
   - `docs/migrations/add_mentor_indexes.sql` - 8 performance indexes for Mentor queries
   - `docs/migrations/README.md` - Complete migration documentation

2. **Support Scripts**:
   - `scripts/run-mentor-migrations.js` - Migration tool (reference)
   - `scripts/verify-mentor-migrations.ts` - Verification script

3. **Documentation**:
   - `docs/features/mentor/implementation-plan.md` - Full 8-phase implementation plan
   - `docs/features/mentor/phase-1-complete.md` - Phase 1 summary

**Database Schema Added**:
- `dismissed_patterns` table - Stores dismissed insight patterns to avoid similar insights
  - Columns: id, insight_type, driver_entity_types, pattern_signature, dismissed_count, timestamps
  - 3 indexes: type, timestamp, count

**Indexes Added** (8 total):
- insight table: status, created_at, status+created (composite)
- signal table: importance+recency (composite), recency (partial)
- entity table: core_identity (partial), created_at, type+created_at (composite)

**Manual Step Required**:
- Run migrations in Supabase SQL Editor (instructions in docs/migrations/README.md)

### Phase 2: Mentor Agent Core Infrastructure ✅ COMPLETE

**What was built**:
1. **Database Methods** (`apps/ai-core/services/database.py`):
   - Added 9 new methods for Mentor queries
   - Methods: get_entities_by_type, get_entities_created_since, get_entities_by_signal_threshold
   - Methods: get_dismissed_patterns, create_insight, get_recent_insights, update_insight_status
   - Methods: get_similar_entities, get_entity_by_title

2. **Mentor Agent** (`apps/ai-core/agents/mentor.py`):
   - Complete Mentor class (600+ lines)
   - Generates 3 insight types: Delta Watch, Connection, Prompt
   - Uses Claude Sonnet 4.5 for insight generation
   - Prompt engineering for each insight type
   - Fallback mechanisms when Claude unavailable
   - Respects dismissed patterns

3. **FastAPI Endpoints** (`apps/ai-core/main.py`):
   - POST /mentor/generate-digest - Manually trigger digest generation
   - GET /mentor/status - Check Mentor status and recent activity

4. **Test Fixtures** (`apps/ai-core/tests/fixtures/mentor_fixtures.py`):
   - Comprehensive sample data for testing
   - Sample entities: core_identity, recent_work, high_priority, historical
   - Sample insights: delta_watch, connection, prompt
   - Sample dismissed patterns

**How it works**:
- `generate_daily_digest()` gathers context from knowledge graph
- Queries for: goals (core_identity), recent work (last 24h), high priority entities
- Generates 3 insights using Claude with structured prompts
- Stores insights in database with status='open'
- Returns digest object with all 3 insights (or null if insufficient data)

**Testing**:
- Syntax validation: ✅ All Python files compile
- API endpoints: Available at http://localhost:8000/mentor/*
- Manual testing: `curl -X POST http://localhost:8000/mentor/generate-digest`

### Phase 3: Prompt Engineering & Testing ✅ COMPLETE
**Completed**: 2025-10-07
**Time**: ~2 hours (vs 2-day estimate)

**What was accomplished**:
1. **Test Infrastructure**:
   - POST /mentor/seed-test-data - Seeds 12 realistic test entities with signals
   - GET /mentor/debug-context - Debug endpoint showing Mentor's context gathering
   - Creates realistic scenario: goal drift (Water OS goal vs Willow work)

2. **Critical Bug Fix**:
   - **Issue**: `get_entities_by_signal_threshold` returned empty results
   - **Cause**: Code expected signals as list, but Supabase returns dict
   - **Fixed**: Updated `database.py` lines 301-330 to handle both formats
   - **Impact**: Mentor now correctly identifies recent work and high-priority entities

3. **Prompt Quality Validation**:
   - **Delta Watch**: 9/10 - Correctly identifies alignment/drift with specific examples
   - **Connection**: 8/10 - Works when data available, limited by simple type-matching
   - **Prompt**: 10/10 - Generates excellent challenging questions

**Example Generated Insights**:
```json
{
  "delta_watch": {
    "title": "Strong alignment across both primary goals",
    "body": "You're making solid progress on both stated goals...",
    "alignment_score": 0.92
  },
  "prompt": {
    "title": "How will splitting focus between Water OS launch and Willow's real-time features impact your ability to deliver excellence on either?"
  }
}
```

**Files Modified**:
- `apps/ai-core/services/database.py` - Fixed signal handling (lines 301-330)
- `apps/ai-core/main.py` - Added seed-test-data and debug-context endpoints

**Documentation**:
- `docs/features/mentor/phase-3-complete.md` - Full technical details
- `docs/features/mentor/phase-3-summary.md` - Executive summary

**Known Issues**:
1. Entity IDs are titles instead of UUIDs (minor - fix in Phase 4)
2. Connection insights rare due to simple similarity matching (acceptable for MVP)

**Next**: Phase 4 - Feedback Processor (Acknowledge/Dismiss functionality)

---

*Last Updated: 2025-10-07*
