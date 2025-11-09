# RelationshipEngine Troubleshooting Guide

Common issues, debugging techniques, and solutions for the RelationshipEngine.

**Version**: 1.0
**Last Updated**: 2025-11-08

---

## Table of Contents

1. [Common Issues](#common-issues)
2. [Debugging Techniques](#debugging-techniques)
3. [Performance Problems](#performance-problems)
4. [Data Quality Issues](#data-quality-issues)
5. [API Errors](#api-errors)
6. [Database Issues](#database-issues)
7. [Migration Issues](#migration-issues)

---

## Common Issues

### Issue 1: No Relationships Created

**Symptom**: RelationshipEngine runs successfully but creates 0 edges.

```bash
✅ Incremental relationship detection complete:
   - Edges created: 0
   - Edges updated: 0
   - Entities analyzed: 5
```

**Possible Causes**:

#### Cause 1.1: Entities don't match patterns

**Check**: Pattern-based strategy requires specific formats

```python
# ✅ WILL MATCH
"CTO at Willow Education"
"Director of Academics, Caliber Schools"

# ❌ WON'T MATCH
"CTO for Willow Education"  # "for" not supported
"CTO - Willow Education"    # "-" not supported
```

**Solution**: Add more patterns to `strategy_pattern_based()`:
```python
# apps/ai-core/engines/relationship_engine.py (line ~420)
patterns = [
    r'\bat\s+(.+)',          # existing
    r',\s*(.+)',             # existing
    r'\bfor\s+(.+)',         # ADD THIS
    r'\s+-\s+(.+)',          # ADD THIS
]
```

---

#### Cause 1.2: Confidence below threshold

**Check**: Relationships filtered out by `min_confidence`

```python
# Default threshold
engine.min_confidence = 0.3

# Your relationships might be lower
{"kind": "role_at", "confidence": 0.25}  # ❌ Filtered out
```

**Solution**: Lower confidence threshold
```python
# In .env
MIN_CONFIDENCE=0.2

# Or in code
engine.min_confidence = 0.2
result = engine.run_incremental(event_id)
```

**Debug**: Check logs for filtered relationships
```
DEBUG: Filtered 3 relationships below confidence threshold 0.3
```

---

#### Cause 1.3: LLM strategy not finding relationships

**Check**: Entity summaries might be too sparse

```python
# ❌ BAD - Not enough context
{
    'title': 'John',
    'type': 'person',
    'summary': 'Person'  # Too generic
}

# ✅ GOOD - Rich context
{
    'title': 'John Doe',
    'type': 'person',
    'summary': 'Software engineer who mentored the team at TechCorp'
}
```

**Solution**: Improve entity extraction to include richer summaries

---

#### Cause 1.4: No matching organization entities

**Check**: Role entity mentions organization, but organization entity doesn't exist

```python
# Database has:
{
    'id': 'role-1',
    'title': 'CTO at Willow Education',  # Mentions "Willow Education"
    'type': 'role'
}

# But NO organization entity with title "Willow Education"
# ❌ No edge created
```

**Solution**: Ensure Archivist extracts organization entities from role titles
```python
# Archivist should extract BOTH:
1. Entity: "CTO at Willow Education" (type: role)
2. Entity: "Willow Education" (type: organization)

# Then RelationshipEngine creates edge between them
```

---

### Issue 2: Duplicate Edges Created

**Symptom**: Same relationship created multiple times

```sql
SELECT from_id, to_id, kind, COUNT(*)
FROM edge
GROUP BY from_id, to_id, kind
HAVING COUNT(*) > 1;

-- Returns duplicates
```

**Possible Causes**:

#### Cause 2.1: Edge reinforcement not working

**Check**: `get_edge_by_from_to_kind()` not finding existing edge

```python
# Debug logging
logger.debug(f"Checking for existing edge: {from_id} -> {to_id} ({kind})")
existing = db.get_edge_by_from_to_kind(from_id, to_id, kind)
logger.debug(f"Existing edge: {existing}")
```

**Solution**: Verify database method returns correct edge
```python
# apps/ai-core/services/database.py
def get_edge_by_from_to_kind(self, from_id: str, to_id: str, kind: str) -> Optional[Edge]:
    result = self.client.table('edge') \
        .select('*') \
        .eq('from_id', from_id) \
        .eq('to_id', to_id) \
        .eq('kind', kind) \
        .execute()

    if result.data and len(result.data) > 0:
        return Edge(**result.data[0])
    return None
```

---

#### Cause 2.2: Race condition (multiple strategies)

**Check**: Multiple strategies creating same edge simultaneously

**Solution**: Use database unique constraint
```sql
-- Add unique constraint to prevent duplicates
ALTER TABLE edge
ADD CONSTRAINT unique_edge_from_to_kind
UNIQUE (from_id, to_id, kind);
```

---

### Issue 3: Edges Not Being Reinforced

**Symptom**: Same relationship detected multiple times, but weight stays at 1.0

```sql
-- Check edge weights
SELECT kind, weight, last_reinforced_at
FROM edge
WHERE from_id = 'uuid-123';

-- All weights = 1.0, never reinforced
```

**Possible Causes**:

#### Cause 3.1: Update query not executing

**Check**: `update_edge()` method failing silently

```python
# Debug logging in create_or_update_edge()
logger.info(f"Edge exists, reinforcing: {existing_edge.id}")
new_weight = existing_edge.weight + 1.0
logger.info(f"Old weight: {existing_edge.weight}, New weight: {new_weight}")

db.update_edge(existing_edge.id, {
    'weight': new_weight,
    'last_reinforced_at': datetime.now()
})

# Verify update
updated = db.get_edge_by_id(existing_edge.id)
logger.info(f"Updated weight: {updated.weight}")  # Should be new_weight
```

**Solution**: Check database permissions and error logs

---

#### Cause 3.2: Edge model not including weight field

**Check**: Pydantic model missing `weight` field

```python
# apps/ai-core/models/edge.py
class Edge(BaseModel):
    id: str
    from_id: str
    to_id: str
    kind: str

    # ✅ MUST HAVE THESE
    weight: float = 1.0
    last_reinforced_at: Optional[datetime] = None
```

**Solution**: Ensure Edge model includes weight and last_reinforced_at

---

### Issue 4: Edges Being Pruned Too Aggressively

**Symptom**: Important edges disappear after nightly consolidation

```sql
-- Before nightly: 250 edges
-- After nightly: 120 edges (130 pruned)
```

**Possible Causes**:

#### Cause 4.1: Prune threshold too high

**Check**: Edges being removed that shouldn't be

```python
# Default threshold
PRUNE_THRESHOLD=0.1

# After a few nights of decay (0.99^10 ≈ 0.90)
# Even important edges might drop below 0.1 eventually
```

**Solution**: Lower threshold or increase decay factor
```bash
# In .env
PRUNE_THRESHOLD=0.05  # More lenient
DECAY_FACTOR=0.995    # Slower decay (0.5% instead of 1%)
```

---

#### Cause 4.2: Edges not being reinforced

**Check**: Important relationships detected only once, never re-detected

**Solution**: Ensure nightly mode re-detects static relationships
```python
# Pattern-based strategy should re-detect role→org edges every night
# This reinforces them, preventing decay
```

---

### Issue 5: Temporal Strategy Not Working

**Symptom**: Entities with overlapping dates not creating edges

**Possible Causes**:

#### Cause 5.1: Missing date fields in metadata

**Check**: Entities must have `start_date` and `end_date` in metadata

```python
# ❌ WON'T WORK
{
    'id': 'role-1',
    'type': 'role',
    'metadata': {}  # No dates
}

# ✅ WILL WORK
{
    'id': 'role-1',
    'type': 'role',
    'metadata': {
        'start_date': '2020-01-01',
        'end_date': '2022-12-31'
    }
}
```

**Solution**: Update entity extraction to capture dates
```python
# Archivist should extract dates from text
"I worked at TechCorp from 2020 to 2022"
# → Extract: start_date='2020-01-01', end_date='2022-12-31'
```

---

#### Cause 5.2: Date format incorrect

**Check**: Dates must be ISO format (YYYY-MM-DD)

```python
# ❌ BAD
'start_date': '01/01/2020'   # US format
'start_date': '2020'          # Year only

# ✅ GOOD
'start_date': '2020-01-01'
'start_date': '2020-01'       # Month precision OK
```

---

### Issue 6: Graph Topology Strategy Creating Too Many Edges

**Symptom**: Hundreds of `inferred_connection` edges created

```sql
SELECT COUNT(*) FROM edge WHERE kind = 'inferred_connection';
-- Returns: 500+ edges
```

**Possible Causes**:

#### Cause 6.1: Transitive inference on highly connected graph

**Check**: If entity A connects to 10 entities, each connecting to 10 more, creates 100 inferred edges

**Solution**: Add maximum distance limit
```python
# apps/ai-core/engines/relationship_engine.py
# In strategy_graph_topology(), limit to 2-hop connections only
MAX_HOPS = 2  # A→B→C, but not A→B→C→D
```

---

#### Cause 6.2: Low confidence threshold for inferred edges

**Check**: Inferred edges have confidence=0.5 (lower than pattern-based)

**Solution**: Filter inferred edges more strictly
```python
# Only keep inferred edges with additional evidence
if kind == 'inferred_connection' and confidence < 0.6:
    skip_edge()
```

---

## Debugging Techniques

### Enable Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG
```

**Restart ai-core**:
```bash
cd apps/ai-core
pnpm run dev
```

**Expected Output**:
```
DEBUG: RelationshipEngine: Starting incremental mode
DEBUG: Fetching entities for event uuid-123
DEBUG: Found 5 entities to analyze
DEBUG: Pattern-based strategy: checking 10 entity pairs
DEBUG: Found match: "CTO at Company" → Company
DEBUG: Creating edge: role-1 → org-1 (role_at)
DEBUG: Checking for existing edge...
DEBUG: No existing edge found, creating new
DEBUG: Edge created: edge-456
DEBUG: Filtered 2 relationships below confidence 0.3
INFO: Created 3 edges, reinforced 1 edge
```

---

### Manual Testing

#### Test Individual Strategies

```python
# apps/ai-core/scripts/test_strategy.py
from engines.relationship_engine import RelationshipEngine
from services.database import DatabaseService

db = DatabaseService()
engine = RelationshipEngine()

# Get entities
entities = db.get_entities_by_event("event-uuid")

# Test pattern-based
print("=== Pattern-based ===")
rels = engine.strategy_pattern_based(entities)
for rel in rels:
    print(f"  {rel['from_id']} → {rel['to_id']} ({rel['kind']})")

# Test semantic LLM
print("\n=== Semantic LLM ===")
event = db.get_event_by_id("event-uuid")
text = event.payload['content']
rels = engine.strategy_semantic_llm(entities, text)
for rel in rels:
    print(f"  {rel['from_id']} → {rel['to_id']} ({rel['kind']})")
```

---

#### Check Edge Weights

```sql
-- Find edges by weight
SELECT
    e1.title as from_entity,
    e2.title as to_entity,
    edge.kind,
    edge.weight,
    edge.last_reinforced_at
FROM edge
JOIN entity e1 ON edge.from_id = e1.id
JOIN entity e2 ON edge.to_id = e2.id
ORDER BY edge.weight DESC
LIMIT 20;
```

---

#### Simulate Decay and Pruning

```python
# Test decay/pruning without running full nightly
from engines.relationship_engine import RelationshipEngine

engine = RelationshipEngine()

# Simulate decay
print("Before decay:")
edges = db.get_all_edges()
print(f"  Avg weight: {sum(e.weight for e in edges) / len(edges):.2f}")

decayed = engine.apply_global_decay(decay_factor=0.99)
print(f"\nDecayed {decayed} edges")

print("After decay:")
edges = db.get_all_edges()
print(f"  Avg weight: {sum(e.weight for e in edges) / len(edges):.2f}")

# Simulate pruning
pruned = engine.prune_weak_edges(threshold=0.1)
print(f"\nPruned {pruned} weak edges")
```

---

### Inspect Database State

#### Check Entity Types

```sql
SELECT type, COUNT(*)
FROM entity
GROUP BY type
ORDER BY COUNT(*) DESC;

-- Expected output:
-- role: 8
-- organization: 10
-- person: 15
-- project: 5
```

#### Check Edge Types

```sql
SELECT kind, COUNT(*)
FROM edge
GROUP BY kind
ORDER BY COUNT(*) DESC;

-- Expected output:
-- role_at: 8
-- founded: 3
-- worked_at: 12
-- temporal_overlap: 5
```

#### Find Orphaned Edges

```sql
-- Edges with missing entities
SELECT edge.id, edge.from_id, edge.to_id
FROM edge
LEFT JOIN entity e1 ON edge.from_id = e1.id
LEFT JOIN entity e2 ON edge.to_id = e2.id
WHERE e1.id IS NULL OR e2.id IS NULL;

-- Should return 0 rows (foreign key constraints prevent this)
```

---

## Performance Problems

### Issue: Nightly Mode Takes Too Long

**Symptom**: Nightly consolidation takes 10+ minutes

**Possible Causes**:

#### Cause 1: Running full scan instead of incremental

```python
# ❌ SLOW (analyzes ALL entities)
result = engine.run_nightly(full_scan=True)

# ✅ FAST (analyzes last 24 hours only)
result = engine.run_nightly(full_scan=False)
```

**Solution**: Use `full_scan=False` for nightly scheduler

---

#### Cause 2: Too many API calls to LLM

**Check**: LLM strategy makes 1 call per entity pair

```
100 entities → 100 × 99 / 2 = 4,950 pairs → 4,950 API calls
```

**Solution**: Batch entity pairs in LLM strategy
```python
# Process 10 entity pairs per API call instead of 1
# Reduces 4,950 calls → 495 calls
```

---

#### Cause 3: Database indexes missing

**Check**: Query performance on edge table

```sql
-- Should use index
EXPLAIN SELECT * FROM edge WHERE from_id = 'uuid-123';

-- If not using index, create it
CREATE INDEX IF NOT EXISTS idx_edge_from_to ON edge(from_id, to_id);
CREATE INDEX IF NOT EXISTS idx_edge_weight ON edge(weight);
```

---

### Issue: Incremental Mode Slow After Events

**Symptom**: Archivist processing time increased from 5s to 15s

**Possible Causes**:

#### Cause 1: Analyzing too many entities

**Check**: Incremental mode analyzes new entities + recent entities

```python
# Default: analyzes last 20 entities
recent = db.get_recent_entities(limit=20)

# If processing time is issue, reduce
recent = db.get_recent_entities(limit=10)
```

---

#### Cause 2: LLM strategy timing out

**Check**: Anthropic API slow or rate-limited

```python
# Add timeout to LLM calls
import anthropic

client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY'),
    timeout=10.0  # 10 second timeout
)
```

---

## Data Quality Issues

### Issue: Low-Quality Relationships Created

**Symptom**: Edges with nonsensical connections

```sql
SELECT * FROM edge WHERE kind = 'semantically_related' AND confidence < 0.5;
-- Returns many edges
```

**Solutions**:

1. **Increase confidence threshold**:
```bash
MIN_CONFIDENCE=0.5  # Was 0.3
```

2. **Review LLM prompts**: Improve prompt engineering in `strategy_semantic_llm()`

3. **Add human review**: Flag edges with confidence < 0.7 for review

---

### Issue: Missing Expected Relationships

**Symptom**: Known relationships not detected

**Example**: "Ryan York founded Water OS" processed, but no `founded` edge

**Debug Steps**:

1. **Check entity extraction**:
```sql
SELECT * FROM entity WHERE title ILIKE '%Ryan York%';
SELECT * FROM entity WHERE title ILIKE '%Water OS%';
-- Both should exist
```

2. **Check event text**:
```sql
SELECT payload->'content' FROM raw_events WHERE id = 'event-uuid';
-- Should contain relationship context
```

3. **Test LLM strategy manually**:
```python
entities = [
    {'id': 'person-1', 'title': 'Ryan York', 'type': 'person', ...},
    {'id': 'company-1', 'title': 'Water OS', 'type': 'company', ...}
]
text = "Ryan York founded Water OS"
rels = engine.strategy_semantic_llm(entities, text)
print(rels)  # Should include founded relationship
```

---

## API Errors

### Error: "Invalid mode"

**Full Error**:
```json
{
  "success": false,
  "error": "Invalid mode. Must be incremental, nightly, or on-demand"
}
```

**Cause**: Invalid `mode` parameter in API request

**Solution**:
```bash
# ❌ BAD
curl -X POST /api/relationship-engine -d '{"mode": "manual"}'

# ✅ GOOD
curl -X POST /api/relationship-engine -d '{"mode": "on-demand"}'
```

---

### Error: "event_id required for incremental mode"

**Cause**: Missing `eventId` in request body

**Solution**:
```bash
curl -X POST /api/relationship-engine \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "incremental",
    "eventId": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

---

### Error: "RelationshipEngine failed"

**Cause**: Python exception in RelationshipEngine

**Debug**:
```bash
# Check ai-core logs
cd apps/ai-core
tail -f logs/app.log

# Or check process output
pnpm run dev
```

**Common causes**:
- Anthropic API key invalid/missing
- Supabase connection failed
- Database schema mismatch

---

## Database Issues

### Issue: Migration Not Applied

**Symptom**: `weight` and `last_reinforced_at` columns missing

**Check**:
```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'edge'
  AND column_name IN ('weight', 'last_reinforced_at');

-- Should return 2 rows
```

**Solution**: Apply migration manually via Supabase SQL Editor
```sql
-- docs/migrations/add_relationship_engine_columns.sql
ALTER TABLE edge ADD COLUMN IF NOT EXISTS weight FLOAT DEFAULT 1.0;
ALTER TABLE edge ADD COLUMN IF NOT EXISTS last_reinforced_at TIMESTAMPTZ DEFAULT NOW();
CREATE INDEX IF NOT EXISTS idx_edge_weight ON edge(weight);

-- Backfill existing edges
UPDATE edge SET weight = 1.0 WHERE weight IS NULL;
UPDATE edge SET last_reinforced_at = NOW() WHERE last_reinforced_at IS NULL;
```

---

### Issue: Foreign Key Constraint Violations

**Error**:
```
ERROR: insert or update on table "edge" violates foreign key constraint "edge_from_id_fkey"
DETAIL: Key (from_id)=(uuid-123) is not present in table "entity"
```

**Cause**: Trying to create edge with non-existent entity ID

**Solution**: Verify entities exist before creating edge
```python
# In create_or_update_edge()
from_entity = db.get_entity_by_id(relationship['from_id'])
to_entity = db.get_entity_by_id(relationship['to_id'])

if not from_entity or not to_entity:
    logger.warning(f"Skipping edge: entity not found")
    return False

# Continue with edge creation...
```

---

## Migration Issues

### Issue: Backfill Failed

**Symptom**: Some edges have NULL weight after migration

**Check**:
```sql
SELECT COUNT(*) FROM edge WHERE weight IS NULL;
-- Should return 0
```

**Solution**: Run backfill query again
```sql
UPDATE edge
SET weight = 1.0,
    last_reinforced_at = NOW()
WHERE weight IS NULL
   OR last_reinforced_at IS NULL;
```

---

### Issue: Index Not Created

**Symptom**: Slow queries on edge.weight

**Check**:
```sql
SELECT indexname
FROM pg_indexes
WHERE tablename = 'edge'
  AND indexname = 'idx_edge_weight';

-- Should return 1 row
```

**Solution**: Create index manually
```sql
CREATE INDEX IF NOT EXISTS idx_edge_weight ON edge(weight);
```

---

## Getting Help

### Collect Debug Information

Before reporting an issue, collect:

1. **Logs**:
```bash
cd apps/ai-core
grep "RelationshipEngine" logs/app.log > relationship_engine_logs.txt
```

2. **Database state**:
```sql
-- Entity counts
SELECT type, COUNT(*) FROM entity GROUP BY type;

-- Edge counts
SELECT kind, COUNT(*) FROM edge GROUP BY kind;

-- Edge weight distribution
SELECT
  CASE
    WHEN weight < 0.1 THEN '<0.1'
    WHEN weight < 0.5 THEN '0.1-0.5'
    WHEN weight < 1.0 THEN '0.5-1.0'
    WHEN weight < 2.0 THEN '1.0-2.0'
    ELSE '>2.0'
  END as weight_range,
  COUNT(*)
FROM edge
GROUP BY weight_range;
```

3. **Configuration**:
```bash
# Sanitized .env (remove API keys)
cat apps/ai-core/.env | grep -v API_KEY
```

4. **Version info**:
```bash
# Python version
python --version

# Package versions
pip list | grep -E "anthropic|supabase|pydantic"
```

---

### Contact

For issues not covered in this guide:

1. Check GitHub Issues: `https://github.com/your-repo/issues`
2. Create new issue with debug information above
3. Tag with `relationship-engine` label

---

**End of Troubleshooting Guide**

See also:
- `docs/features/relationship-engine/api-reference.md`
- `docs/features/relationship-engine/feature-details.md`
- `apps/ai-core/tests/test_relationship_engine.py`
