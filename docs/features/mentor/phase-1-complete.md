# Phase 1: Database Setup - Complete ✅

**Status**: Files created, ready to execute
**Date**: 2025-10-07

## What Was Built

### Migration Files Created

1. **`docs/migrations/create_dismissed_patterns_table.sql`**
   - Creates `dismissed_patterns` table for storing dismissed insight patterns
   - Includes 3 indexes: type, timestamp, and count
   - Full documentation with comments

2. **`docs/migrations/add_mentor_indexes.sql`**
   - Adds 8 performance indexes for Mentor queries
   - Optimizes insight fetching, entity queries, and signal lookups
   - Includes partial indexes for better performance

3. **`docs/migrations/README.md`**
   - Complete migration documentation
   - Instructions for running migrations (3 methods)
   - Migration order and rollback procedures
   - Verification queries

### Support Scripts

4. **`scripts/run-mentor-migrations.js`**
   - Node.js migration tool (reference - cannot auto-execute)
   - Shows migration files and instructions

5. **`scripts/verify-mentor-migrations.ts`**
   - TypeScript verification script
   - Checks if migrations have been run
   - Provides clear instructions

## Database Schema Added

### dismissed_patterns Table

```sql
CREATE TABLE dismissed_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_type TEXT NOT NULL,           -- 'Delta Watch', 'Connection', 'Prompt'
    driver_entity_types TEXT[],           -- ['feature', 'project', 'person']
    pattern_signature JSONB,              -- Flexible pattern data
    dismissed_count INTEGER DEFAULT 1,    -- How many times dismissed
    first_dismissed_at TIMESTAMPTZ DEFAULT NOW(),
    last_dismissed_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Purpose**: Stores patterns that users have dismissed so the Mentor can avoid generating similar insights in the future.

### Indexes Added

**For insight table**:
- `idx_insight_status` - Query by status (open/acknowledged/dismissed)
- `idx_insight_created_at` - Query recent insights
- `idx_insight_status_created` - Composite for both

**For signal table**:
- `idx_signal_importance_recency` - Find high-priority entities
- `idx_signal_recency` - Find active work (recency >= 0.8)

**For entity table**:
- `idx_entity_type_core_identity` - Quick access to goals/values
- `idx_entity_created_at` - Recent entities
- `idx_entity_type_created_at` - Type-specific recent entities

**For dismissed_patterns table**:
- `idx_dismissed_patterns_type` - Query by insight type
- `idx_dismissed_patterns_last_dismissed` - Recent dismissals
- `idx_dismissed_patterns_count` - Pattern frequency

## How to Execute Migrations

### Step 1: Open Supabase SQL Editor

Go to: https://supabase.com/dashboard/project/mdcarckygvbcjgexvdqw/sql

### Step 2: Run Migration 1

1. Click "+ New Query"
2. Copy contents of `docs/migrations/create_dismissed_patterns_table.sql`
3. Paste and click "Run"

### Step 3: Run Migration 2

1. Click "+ New Query"
2. Copy contents of `docs/migrations/add_mentor_indexes.sql`
3. Paste and click "Run"

### Step 4: Verify

Run this query to verify:

```sql
-- Check table exists
SELECT COUNT(*) FROM dismissed_patterns;
-- Should return: 0 (empty table)

-- List indexes on insight table
SELECT indexname FROM pg_indexes WHERE tablename = 'insight';
-- Should show: idx_insight_status, idx_insight_created_at, idx_insight_status_created

-- List indexes on signal table
SELECT indexname FROM pg_indexes WHERE tablename = 'signal';
-- Should show: idx_signal_importance_recency, idx_signal_recency

-- List indexes on entity table
SELECT indexname FROM pg_indexes WHERE tablename = 'entity';
-- Should show: idx_entity_type_core_identity, idx_entity_created_at, idx_entity_type_created_at
```

## Success Criteria ✅

- [x] `dismissed_patterns` table SQL created
- [x] Index migration SQL created
- [x] Migration documentation complete
- [x] Verification scripts available
- [x] Rollback procedures documented

## What's Next: Phase 2

Once migrations are executed in Supabase:

1. Build Mentor Agent core (`apps/ai-core/agents/mentor.py`)
2. Add database methods for insight generation
3. Create FastAPI endpoints for digest generation
4. Test insight generation manually

**Estimated time**: 2 days

## Files Created (5 total)

```
docs/
├── migrations/
│   ├── create_dismissed_patterns_table.sql    ✅ NEW
│   ├── add_mentor_indexes.sql                 ✅ NEW
│   └── README.md                              ✅ NEW
└── features/
    └── mentor/
        └── phase-1-complete.md                ✅ NEW (this file)

scripts/
├── run-mentor-migrations.js                   ✅ NEW
└── verify-mentor-migrations.ts                ✅ NEW
```

## Notes

- Migrations are idempotent (safe to run multiple times)
- Indexes use `IF NOT EXISTS` to prevent errors
- Partial indexes (with WHERE clauses) reduce index size
- All SQL includes helpful comments for documentation

---

**Phase 1 Status**: ✅ COMPLETE (pending execution in Supabase)

**Ready for**: Phase 2 implementation
