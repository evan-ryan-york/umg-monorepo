# Database Migrations

This directory contains SQL migration files for the UMG database schema.

## How to Run Migrations

### Option 1: Supabase Dashboard (Recommended for Development)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Click **+ New Query**
4. Copy and paste the migration SQL
5. Click **Run** to execute

### Option 2: Supabase CLI

```bash
# Install Supabase CLI if not already installed
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref mdcarckygvbcjgexvdqw

# Run migration
supabase db push
```

### Option 3: Direct psql Connection

```bash
# Connect using service role key
psql "postgresql://postgres:[SERVICE_ROLE_KEY]@db.mdcarckygvbcjgexvdqw.supabase.co:5432/postgres"

# Run migration file
\i /path/to/migration.sql
```

## Migration Files

### Phase 1: Initial Setup (2025-10-02)
- Initial schema created via Supabase dashboard
- 7 core tables: raw_events, entity, edge, chunk, embedding, signal, insight

### Phase 2: Entity Resolution (2025-10-06)
- **`add_source_event_id_to_edge.sql`** - Adds source_event_id column to edge table for provenance tracking

### Phase 3: Mentor Agent Setup (2025-10-07)
- **`create_dismissed_patterns_table.sql`** - Creates table for storing dismissed insight patterns
- **`add_mentor_indexes.sql`** - Adds performance indexes for Mentor queries

### Phase 4: Relationship Engine (2025-11-08)
- **`add_relationship_engine_columns.sql`** - Adds weight and last_reinforced_at columns for Hebbian learning

## Migration Order

Run migrations in this order:

1. ✅ Initial setup (already done via Supabase dashboard)
2. ✅ `add_source_event_id_to_edge.sql` (may already be run)
3. ✅ `create_dismissed_patterns_table.sql` (may already be run)
4. ✅ `add_mentor_indexes.sql` (may already be run)
5. ⏳ `add_relationship_engine_columns.sql` (NEW - **APPLY THIS NOW**)

## Rollback

If you need to rollback a migration:

### Rollback Relationship Engine columns
```sql
-- Remove indexes
DROP INDEX IF EXISTS idx_edge_weight;
DROP INDEX IF EXISTS idx_edge_last_reinforced;
DROP INDEX IF EXISTS idx_edge_from_weight;

-- Remove columns
ALTER TABLE edge DROP COLUMN IF EXISTS weight;
ALTER TABLE edge DROP COLUMN IF EXISTS last_reinforced_at;
```

### Rollback dismissed_patterns table
```sql
DROP TABLE IF EXISTS dismissed_patterns;
```

### Rollback Mentor indexes
```sql
DROP INDEX IF EXISTS idx_insight_status;
DROP INDEX IF EXISTS idx_insight_created_at;
DROP INDEX IF EXISTS idx_insight_status_created;
DROP INDEX IF EXISTS idx_signal_importance_recency;
DROP INDEX IF EXISTS idx_signal_recency;
DROP INDEX IF EXISTS idx_entity_type_core_identity;
DROP INDEX IF EXISTS idx_entity_created_at;
DROP INDEX IF EXISTS idx_entity_type_created_at;
```

## Verification

After running migrations, verify they worked:

### Check Relationship Engine columns
```sql
-- Check columns exist
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'edge'
AND column_name IN ('weight', 'last_reinforced_at');

-- Should return 2 rows showing the new columns

-- Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'edge'
AND indexname LIKE 'idx_edge_%';

-- Verify backfill
SELECT COUNT(*) FROM edge WHERE weight IS NOT NULL;
SELECT COUNT(*) FROM edge WHERE last_reinforced_at IS NOT NULL;
```

Or use the verification script:
```bash
python apps/ai-core/scripts/check_and_apply_migration.py
```

### Check dismissed_patterns table
```sql
-- Should return table structure
\d dismissed_patterns;

-- Should return 0 rows (new table)
SELECT COUNT(*) FROM dismissed_patterns;
```

### Check indexes
```sql
-- List all indexes on insight table
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'insight';

-- List all indexes on signal table
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'signal';

-- List all indexes on entity table
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'entity';
```

## Notes

- Always backup your database before running migrations in production
- Test migrations in development environment first
- Indexes may take time to build on large tables
- Some indexes are partial (with WHERE clauses) for better performance

---

*Last Updated: 2025-10-07*
