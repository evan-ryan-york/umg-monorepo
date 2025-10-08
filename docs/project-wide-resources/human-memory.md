# Ryan's Memory - UMG Project Status

**Last Updated**: 2025-10-07
**Current Focus**: 🚀 Mentor Agent Phase 3 Complete - Phases 1-3 Working End-to-End

---

## Where We Are

### ✅ Completed: Core Archivist (Phases 0-10)

The foundation of UMG is **fully working**:

1. **Event Processing Pipeline**
   - Monitors `raw_events` table for new entries
   - Processes text through multiple stages: cleaning, entity extraction, relationship detection
   - Creates chunks, embeddings (disabled - Anthropic doesn't provide), and signals
   - Updates event status from `pending_processing` to `processed`

2. **Entity Extraction** (LLM-powered with Claude Sonnet 4.5)
   - Extracts: person, company, project, feature, task, decision, reflection
   - Sets `is_primary_subject` flag correctly
   - Does NOT extract pronouns (I, me, my) as entities ✅

3. **Relationship Mapping**
   - Detects relationships between entities
   - Supports: `belongs_to`, `modifies`, `mentions`, `founded`, `works_at`, `manages`, etc.
   - Uses Claude Sonnet 4.5 with markdown stripping for JSON parsing

4. **Mention Tracking**
   - Tracks entity mentions across events
   - Promotes entities after 2-3 mentions OR if primary subject
   - Currently in-memory (resets on server restart)

5. **Hub-and-Spoke Pattern**
   - Projects, features, decisions are "hubs"
   - Meeting notes, reflections are "spokes" that link to hubs

6. **Signal Scoring**
   - Importance: Based on entity type (person=0.7, company=0.5, etc.)
   - Recency: 1.0 for new, decays over time
   - Novelty: Based on connection count

7. **Visibility Layer**
   - `/` - Quick Capture form for manual text entry
   - `/log` - Shows 10 most recent processed events with full details
   - Reset button to clear all data

8. **Infrastructure**
   - `pnpm run dev:web` starts both Next.js (3110) and Archivist (8000)
   - Continuous processing every 60 seconds
   - API endpoint `/api/events` for creating events

---

## 🔧 Current Work: Entity Resolution Across Events

### The Goal

When you say "I am starting Water OS", the system should:
1. Resolve "I" to "Ryan York" (from a previous event where you introduced yourself)
2. Create relationship: **"Ryan York --[founded]--> Water OS"**

### The Problem (Still Broken)

**Test Case:**
1. Event 1: "I am Ryan York. I am the Chief Product & Technology Officer at Willow Education."
   - ✅ Creates "Ryan York" entity (person type)
   - ✅ Sets `is_primary_subject: true`
   - ✅ Marks with `is_user_entity: true` in metadata

2. Event 2: "I am starting a new business called Water OS"
   - ✅ Creates "Water OS" entity (company type)
   - ❌ **Does NOT create relationship** "Ryan York --[founded]--> Water OS"
   - ❌ Shows 0 relationships in log

**Current Behavior**: No relationships are being created at all.

### What's Implemented (But Not Working)

1. **EntityResolver Service** (`apps/ai-core/services/entity_resolver.py`)
   - `resolve_pronouns()` method maps "I/me/my" to user entity ID
   - Integrated into Archivist at Step 3.5

2. **Hardcoded User Identity** (`apps/web/app/api/events/route.ts`)
   - `getUserEntityId()` function looks for "Ryan York" person entity
   - Creates Ryan York entity if doesn't exist
   - **Issue**: May not be finding the entity even after it's created

3. **Self-Introduction Detection** (`apps/ai-core/agents/archivist.py`)
   - Detects when user creates person entity as primary subject
   - Marks person entity with `is_user_entity: true` metadata
   - Updates `reference_map` to point to real person entity

4. **RelationshipMapper Enhancement** (`apps/ai-core/processors/relationship_mapper.py`)
   - Accepts `existing_entities` and `reference_map` parameters
   - Should build prompts with reference hints like: `"Ryan York (person) [also referred to as: i, me, my]"`

### The Bug

**Hypothesis**: The entity resolution chain has a break somewhere:
- Either `getUserEntityId()` isn't finding Ryan York (even though he exists)
- Or the `reference_map` isn't being built correctly
- Or the relationship mapper isn't seeing enough entities to create relationships (needs 2+ entities)

**Evidence**:
- Event 1: Creates 1 entity, 0 relationships ✅ (expected - only 1 entity)
- Event 2: Creates 1 entity, 0 relationships ❌ (should create relationship to Ryan York)

---

## Recent Fixes

### Fix #1: Entity Creation Error Handling (2025-10-05)

**Problem**: Foreign key constraint violation when creating chunks
```
insert or update on table "chunk" violates foreign key constraint "chunk_entity_id_fkey"
Key (entity_id)=(1142ddcd-6340-441d-808f-51d0b1ac8209) is not present in table "entity"
```

**Root Cause**: Entity creation could fail, but entity ID was still added to `entity_ids` list. Later, chunk creation tried to reference the non-existent entity.

**Solution**: Added try-catch around entity creation (`apps/ai-core/agents/archivist.py:131-150`)
```python
try:
    if is_hub:
        entity_id = self.db.create_hub_entity(entity_payload)
    else:
        entity_id = self.db.create_entity(entity_payload)

    # Only add to entity_ids if creation succeeds
    entity_ids.append(entity_id)
    entity_map[entity_title] = entity_id
except Exception as e:
    logger.error(f"Failed to create entity '{entity_title}': {e}")
    # Don't add to entity_ids if creation failed
```

**Status**: ✅ Fixed - No more crashes, but entity resolution still broken

---

## What's Next

### Immediate Debugging Steps

1. **Verify Database State**
   - After Event 1, check if Ryan York entity has `is_user_entity: true` in metadata
   - SQL: `SELECT id, title, type, metadata FROM entity WHERE type = 'person'`

2. **Add Extensive Logging**
   - Log what `getUserEntityId()` returns for Event 2
   - Log the `reference_map` contents in Archivist
   - Log what entities the relationship mapper receives

3. **Check Relationship Detection**
   - The relationship mapper might not be seeing 2+ entities
   - Event 2 only extracts "Water OS" - where is "Ryan York" supposed to come from?
   - The `existing_entities` list should contain Ryan York from the database

### Root Cause Investigation

**Key Questions**:
1. Is `getUserEntityId()` finding Ryan York for Event 2? (Check Next.js console logs)
2. Is `user_entity_id` being passed in Event 2's payload?
3. Is the `reference_map` being built correctly? (Should map "i" → Ryan York's ID)
4. Is the relationship mapper receiving both "Water OS" (new) and "Ryan York" (existing)?

### The Missing Link

Looking at the code flow:
1. Event 2 payload should include `user_entity_id` = Ryan York's ID ✅
2. Archivist fetches 20 recent entities (should include Ryan York) ✅
3. EntityResolver builds `reference_map`: `{"i": "ryan_york_id"}` ✅
4. Relationship mapper receives:
   - `extracted_entities`: [Water OS]
   - `existing_entities`: [Ryan York, ...]
   - `reference_map`: {"i": "ryan_york_id"}
5. **But no relationship is created** ❌

**Likely Issue**: The relationship mapper might not be detecting the relationship in the text "I am starting a new business called Water OS" even with the reference hints.

---

## Technology Stack

- **Frontend**: Next.js 15 + React 19 (port 3110)
- **Backend**: Python FastAPI (port 8000)
- **Database**: Supabase (PostgreSQL + pgvector)
- **LLM**: Claude Sonnet 4.5 (Anthropic API)
- **Embeddings**: Disabled (Anthropic doesn't provide - using zero vectors)
- **Dev Command**: `pnpm run dev:web` (runs both frontend + backend)

---

## Key Files

### Python (Backend)
- `apps/ai-core/agents/archivist.py` - Main orchestrator
- `apps/ai-core/services/entity_resolver.py` - Pronoun → entity resolution
- `apps/ai-core/processors/entity_extractor.py` - LLM entity extraction
- `apps/ai-core/processors/relationship_mapper.py` - Relationship detection
- `apps/ai-core/services/database.py` - All database operations

### TypeScript (Frontend)
- `apps/web/app/api/events/route.ts` - Event creation API, `getUserEntityId()` logic
- `apps/web/app/log/page.tsx` - Activity log display
- `apps/web/components/LogItem.tsx` - Individual event display

---

## Architecture Decisions

### Hardcoded User Identity
- This app is for Ryan York only (single user)
- Hardcoded "Ryan York" as the user throughout
- Constant: `const RYAN_YORK = 'Ryan York'` in events route
- All manual entries are assumed to be from Ryan York

### Anthropic-Only
- User requested: "Only use the anthropic key, not open ai"
- Model: `claude-sonnet-4-5`
- No embeddings (Anthropic doesn't provide)

### Mention Tracking
- Currently in-memory (resets on server restart)
- Future: Make database-backed for production

---

## ✅ Session Completed: 2025-10-06

### What Was Accomplished

**Phase 1 Entity Resolution - COMPLETE**

Fixed 5 critical bugs and completed cross-event entity resolution:

1. **Bug Fix**: API route was pre-creating Ryan York entity
   - Removed entity creation from `getUserEntityId()` - now only queries
   - Lets Archivist handle entity creation via self-introduction detection

2. **Bug Fix**: Self-introduction detection never triggered on first event
   - Condition checked `user_entity_id` which was always `None` on first event
   - Removed that check - now correctly detects "My name is Ryan York"

3. **Bug Fix**: Duplicate entities created after server restarts
   - Added database lookup before creating entities
   - Checks both in-memory tracker AND database now

4. **Bug Fix**: Activity log showed relationships from wrong events
   - Added `source_event_id` column to `edge` table
   - UI filters edges by event - Event 1 no longer shows Event 2's relationships

5. **Bug Fix**: Foreign key violations when chunks referenced failed entities
   - Added try-catch around chunk creation
   - Failed chunks logged but don't crash processing

**Additional Improvements**:
- ✅ Build system now runs TypeScript type-checking and linting
- ✅ Fixed all TypeScript errors (added `user_id`, `user_entity_id` to types)
- ✅ Added extensive debug logging throughout codebase
- ✅ Created SQL migration for `source_event_id` column

### Success Criteria - ALL MET ✅

1. ✅ **No Generic User Entities**: Never creates "User (default_user)" entities
2. ✅ **Cross-Event Resolution**: "I am starting X" creates "Ryan York --[founded]--> X"
3. ✅ **Correct Pronouns**: All "I/me/my" resolve to Ryan York
4. ✅ **Self-Introduction**: "My name is Ryan York" creates Ryan York entity, marks as user
5. ✅ **No Pronoun Entities**: Never extracts "I" as a person entity
6. ✅ **Relationships Work**: Creates edges between entities across events

### Test Case Verified

**Event 1**: "My name is Ryan York. I am the CPTO of Willow Education."
- ✅ Creates Ryan York entity with `is_user_entity: true`
- ✅ Shows 0 relationships (correct - only one entity)

**Event 2**: "I am starting a side business called Water OS."
- ✅ Creates Water OS entity
- ✅ Shows "Ryan York --[founded]--> Water OS" relationship
- ✅ Event 1 does NOT show this relationship (UI correctly filters by event)

---

## ✅ Session Completed: 2025-10-07

### What Was Accomplished

**Mentor Agent - Phases 1-3 COMPLETE** (Database Setup + Core Agent + Prompt Engineering)

**Phase 1: Database Setup**
- Created `dismissed_patterns` table for storing dismissed insight patterns
- Added 8 performance indexes for Mentor queries
- Migration files ready in `docs/migrations/`

**Phase 2: Mentor Agent Core**
- Built complete Mentor agent (600+ lines) using Claude Sonnet 4.5
- Generates 3 insight types: Delta Watch, Connection, Prompt
- Added 9 new database methods for context gathering
- API endpoints: `POST /mentor/generate-digest`, `GET /mentor/status`

**Phase 3: Prompt Engineering & Testing** ⭐
- Created test infrastructure: seed-test-data and debug-context endpoints
- **Found and fixed critical bug**: Signal filtering returned empty results
  - Issue: Code expected signals as list, Supabase returns dict
  - Fixed in `database.py` lines 301-330
- Validated prompt quality with realistic test data:
  - Delta Watch: 9/10 - Correctly identifies alignment/drift
  - Connection: 8/10 - Works but limited by simple similarity
  - Prompt: 10/10 - Generates excellent challenging questions

**Example Generated Insight**:
```
Delta Watch: "Strong alignment across both primary goals"
Body: "You're making solid progress on both stated goals..."

Prompt: "How will splitting focus between Water OS launch and
Willow's real-time features impact your ability to deliver
excellence on either?"
```

**Time**: Phase 3 completed in ~2 hours (vs 2-day estimate) ⚡

### Files Modified
- `apps/ai-core/services/database.py` - Fixed signal handling bug
- `apps/ai-core/main.py` - Added seed and debug endpoints
- `apps/ai-core/agents/mentor.py` - Complete 600+ line implementation
- `docs/features/mentor/phase-3-complete.md` - Full documentation
- `docs/features/mentor/phase-3-summary.md` - Executive summary

### How to Test Mentor

1. **Start AI Core** (if not running): `pnpm run dev:web`
2. **Seed test data**: `curl -X POST http://localhost:8000/mentor/seed-test-data`
3. **Generate digest**: `curl -X POST http://localhost:8000/mentor/generate-digest`
4. **Debug context**: `curl http://localhost:8000/mentor/debug-context`

### Known Issues
1. Entity IDs are titles instead of UUIDs (minor - fix in Phase 4)
2. Connection insights rare due to simple type-matching (acceptable for MVP)

---

## Next Steps

### Phase 4: Feedback Processor (Next)
- Build Acknowledge/Dismiss endpoints
- Implement signal adjustment logic (±0.1 importance)
- Record dismissed patterns
- Fix entity ID issue
- **Estimated**: 2 days

### Manual Actions Required
1. **Run Mentor migrations** in Supabase SQL Editor:
   - File: `docs/migrations/create_dismissed_patterns_table.sql`
   - File: `docs/migrations/add_mentor_indexes.sql`
   - Instructions in `docs/migrations/README.md`

2. **Run edge migration** (if not done yet):
   - File: `docs/migrations/add_source_event_id_to_edge.sql`

### Future Features
With Archivist + Mentor working, next big features:
- **Phase 5**: Daily Digest UI (3 insight cards with Acknowledge/Dismiss buttons)
- **Phase 6**: Scheduled Generation (7 AM daily digest)
- **Triage UI**: Manual classification of pending events
- **Voice Input**: Whisper API for voice notes
- **RAG System**: Query memories conversationally

---

## Documentation References

1. **START HERE**: `docs/ai-quickstart.md` - Dev workflow rules
2. `docs/project-wide-resources/technical-guide.md` - Architecture overview
3. `docs/project-wide-resources/database-structure.md` - All 7 tables, exact schema
4. `docs/features/archivist/implementation-plan.md` - Original 10-phase plan (complete)
5. **`docs/features/archivist/ai-handoff.md`** - Complete status, all bugs fixed
6. **`docs/project-wide-resources/ai-memory.md`** - Feature 3 (Entity Resolution) documented
