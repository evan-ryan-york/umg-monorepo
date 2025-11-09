# RelationshipEngine API Reference

Complete API reference for the RelationshipEngine - neuroscience-inspired relationship detection system for Universal Memory Graph.

**Version**: 1.0
**Last Updated**: 2025-11-08

---

## Table of Contents

1. [Python API](#python-api)
2. [CLI Interface](#cli-interface)
3. [REST API](#rest-api)
4. [Detection Strategies](#detection-strategies)
5. [Return Values](#return-values)
6. [Error Handling](#error-handling)

---

## Python API

### Class: `RelationshipEngine`

**Location**: `apps/ai-core/engines/relationship_engine.py`

#### Constructor

```python
from engines.relationship_engine import RelationshipEngine

engine = RelationshipEngine()
```

**Parameters**: None (uses DatabaseService internally)

**Returns**: RelationshipEngine instance

---

### Core Methods

#### `run_incremental(event_id: str) -> Dict`

Runs incremental relationship detection after event processing (called by Archivist).

**Parameters**:
- `event_id` (str): UUID of the processed event

**Strategies Used**:
- Pattern-based
- Semantic LLM

**Returns**:
```python
{
    "edges_created": 5,         # Number of new edges created
    "edges_updated": 2,         # Number of edges reinforced
    "entities_analyzed": 12,    # Total entities analyzed
    "processing_time": 2.34,    # Seconds
    "strategies_used": ["pattern_based", "semantic_llm"]
}
```

**Example**:
```python
engine = RelationshipEngine()
result = engine.run_incremental("uuid-event-123")
print(f"Created {result['edges_created']} new relationships")
```

---

#### `run_nightly(full_scan: bool = False) -> Dict`

Runs nightly consolidation with all 5 strategies, decay, and pruning.

**Parameters**:
- `full_scan` (bool):
  - `False` (default) - Analyze entities from last 24 hours
  - `True` - Analyze entire graph (use sparingly, expensive)

**Strategies Used**:
- Pattern-based
- Semantic LLM
- Embedding similarity
- Temporal analysis
- Graph topology

**Additional Operations**:
- Global decay (weight *= 0.99)
- Pruning (removes edges with weight < 0.1)

**Returns**:
```python
{
    "edges_created": 23,
    "edges_updated": 45,
    "edges_decayed": 236,
    "edges_pruned": 12,
    "entities_analyzed": 150,
    "processing_time": 45.2,
    "strategies_used": [
        "pattern_based",
        "semantic_llm",
        "embedding_similarity",
        "temporal",
        "graph_topology"
    ]
}
```

**Example**:
```python
# Normal nightly run (last 24 hours)
engine = RelationshipEngine()
result = engine.run_nightly()

# Full graph scan (expensive, use rarely)
result = engine.run_nightly(full_scan=True)
```

---

#### `run_on_demand(entity_ids: Optional[List[str]] = None) -> Dict`

Manually trigger relationship detection (user-initiated or debugging).

**Parameters**:
- `entity_ids` (List[str], optional):
  - `None` - Analyze all entities
  - `["uuid-1", "uuid-2"]` - Analyze specific entities

**Strategies Used**:
- All 5 strategies

**Returns**:
```python
{
    "edges_created": 8,
    "edges_updated": 12,
    "entities_analyzed": 25,
    "processing_time": 8.7,
    "strategies_used": ["pattern_based", "semantic_llm", ...]
}
```

**Example**:
```python
# Analyze specific entities
engine = RelationshipEngine()
result = engine.run_on_demand(entity_ids=["uuid-role-1", "uuid-org-1"])

# Analyze all entities
result = engine.run_on_demand()
```

---

### Detection Strategy Methods

These methods are called internally by the core methods above, but can be used directly for testing or custom workflows.

#### `strategy_pattern_based(entities: List[Dict]) -> List[Dict]`

Detects role→organization relationships using regex patterns.

**Patterns**:
- `"CTO at Company"` → `role_at` edge
- `"Director, School"` → `role_at` edge

**Parameters**:
```python
entities = [
    {
        'id': 'role-1',
        'title': 'CTO at Willow Education',
        'type': 'role',
        'summary': None,
        'metadata': {}
    },
    {
        'id': 'org-1',
        'title': 'Willow Education',
        'type': 'organization',
        'summary': None,
        'metadata': {}
    }
]
```

**Returns**:
```python
[
    {
        'from_id': 'role-1',
        'to_id': 'org-1',
        'kind': 'role_at',
        'confidence': 0.95,
        'importance': 0.8,
        'description': 'Role at organization (detected via pattern)',
        'start_date': None,
        'end_date': None,
        'metadata': {}
    }
]
```

**Example**:
```python
engine = RelationshipEngine()
entities = db.get_entities_by_event("event-id")
relationships = engine.strategy_pattern_based(entities)
```

---

#### `strategy_semantic_llm(entities: List[Dict], context_text: str) -> List[Dict]`

Uses Claude Sonnet 4.5 to detect complex relationships.

**Parameters**:
- `entities` (List[Dict]): Entities to analyze
- `context_text` (str): Original text from event for context

**Detected Relationships**:
- `mentored_by`
- `inspired_by`
- `collaborated_with`
- `founded`
- `led`
- Any relationship the LLM can infer from context

**Returns**: Same format as `strategy_pattern_based`

**Example**:
```python
entities = [
    {'id': 'person-1', 'title': 'John', 'type': 'person', ...},
    {'id': 'person-2', 'title': 'Jane', 'type': 'person', ...}
]
text = "John learned everything from Jane, his mentor."
relationships = engine.strategy_semantic_llm(entities, text)
# Returns: [{'from_id': 'person-1', 'to_id': 'person-2', 'kind': 'mentored_by', ...}]
```

---

#### `strategy_embedding_similarity(entities: List[Dict]) -> List[Dict]`

Detects semantically similar entities using embedding cosine similarity.

**Threshold**: 0.85 (configurable)

**Returns**: Edges with `kind='semantically_related'`

**Example**:
```python
entities = db.get_all_entities()
relationships = engine.strategy_embedding_similarity(entities)
```

---

#### `strategy_temporal(entities: List[Dict]) -> List[Dict]`

Detects entities that overlap in time (co-occurrence).

**Requirements**:
- Entities must have `start_date` and `end_date` in metadata

**Returns**: Edges with `kind='temporal_overlap'`

**Example**:
```python
entities = [
    {
        'id': 'role-1',
        'metadata': {
            'start_date': '2020-01-01',
            'end_date': '2022-12-31'
        }
    },
    {
        'id': 'project-1',
        'metadata': {
            'start_date': '2021-06-01',
            'end_date': '2021-12-31'
        }
    }
]
relationships = engine.strategy_temporal(entities)
# Returns temporal_overlap edge (project occurred during role)
```

---

#### `strategy_graph_topology(entity_ids: List[str]) -> List[Dict]`

Detects transitive connections (A→B→C implies A→C).

**Parameters**:
- `entity_ids` (List[str]): Entity IDs to analyze

**Returns**: Edges with `kind='inferred_connection'`, `confidence=0.5`

**Example**:
```python
# If edges exist: person-1 → company-1 (worked_at)
#                company-1 → city-1 (located_in)
# Then infers: person-1 → city-1 (inferred_connection)
entity_ids = ['person-1', 'company-1', 'city-1']
relationships = engine.strategy_graph_topology(entity_ids)
```

---

### Edge Management Methods

#### `create_or_update_edge(relationship: Dict) -> bool`

Creates a new edge or reinforces existing edge (Hebbian learning).

**Parameters**:
```python
relationship = {
    'from_id': 'entity-1',
    'to_id': 'entity-2',
    'kind': 'founded',
    'confidence': 0.8,
    'importance': 0.7,
    'description': 'Founded the company',
    'start_date': None,
    'end_date': None,
    'metadata': {}
}
```

**Returns**:
- `True` - Edge already existed and was reinforced (weight increased)
- `False` - New edge created (weight = 1.0)

**Behavior**:
```python
# New edge
edge = create_or_update_edge(relationship)
# Creates edge with weight=1.0, last_reinforced_at=NOW()

# Existing edge
edge = create_or_update_edge(relationship)
# Updates: weight = weight + 1.0, last_reinforced_at=NOW()
```

**Example**:
```python
rel = {
    'from_id': 'ryan-york',
    'to_id': 'water-os',
    'kind': 'founded',
    'confidence': 0.95,
    'importance': 0.85,
    'description': 'Founded Water OS',
    'start_date': None,
    'end_date': None,
    'metadata': {}
}
was_reinforced = engine.create_or_update_edge(rel)
if was_reinforced:
    print("Edge already existed, weight increased")
else:
    print("New edge created")
```

---

#### `apply_global_decay(decay_factor: float = 0.99) -> int`

Applies synaptic decay to all edges (synaptic homeostasis).

**Parameters**:
- `decay_factor` (float): Multiplier for all weights (default: 0.99)

**Returns**: Number of edges decayed

**Formula**: `new_weight = old_weight * decay_factor`

**Example**:
```python
# Decay all edges by 1%
count = engine.apply_global_decay(decay_factor=0.99)
print(f"Decayed {count} edges")

# Aggressive decay (10%)
count = engine.apply_global_decay(decay_factor=0.90)
```

---

#### `prune_weak_edges(threshold: float = 0.1) -> int`

Removes edges below weight threshold.

**Parameters**:
- `threshold` (float): Minimum weight to keep (default: 0.1)

**Returns**: Number of edges deleted

**Example**:
```python
# Remove edges with weight < 0.1
count = engine.prune_weak_edges(threshold=0.1)
print(f"Pruned {count} weak edges")

# More aggressive pruning
count = engine.prune_weak_edges(threshold=0.5)
```

---

## CLI Interface

### Script: `run_relationship_engine.py`

**Location**: `apps/ai-core/scripts/run_relationship_engine.py`

#### Incremental Mode

Process relationships for a specific event.

```bash
python scripts/run_relationship_engine.py \
  --mode incremental \
  --event-id <event-uuid>
```

**Example**:
```bash
python scripts/run_relationship_engine.py \
  --mode incremental \
  --event-id 550e8400-e29b-41d4-a716-446655440000
```

**Output**:
```
✅ Incremental relationship detection complete:
   - Edges created: 5
   - Edges updated: 2
   - Entities analyzed: 12
   - Processing time: 2.34s
```

---

#### Nightly Mode

Run full consolidation with all strategies.

```bash
# Analyze last 24 hours (default)
python scripts/run_relationship_engine.py --mode nightly

# Full graph scan (expensive)
python scripts/run_relationship_engine.py --mode nightly --full-scan
```

**Output**:
```
🌙 Nightly consolidation complete:
   - Edges created: 23
   - Edges updated: 45
   - Edges decayed: 236
   - Edges pruned: 12
   - Entities analyzed: 150
   - Processing time: 45.2s
```

---

#### On-Demand Mode

Manually trigger analysis.

```bash
# Analyze all entities
python scripts/run_relationship_engine.py --mode on-demand --all

# Analyze specific entities
python scripts/run_relationship_engine.py \
  --mode on-demand \
  --entity-ids uuid-1,uuid-2,uuid-3
```

**Output**:
```
🔍 On-demand analysis complete:
   - Edges created: 8
   - Edges updated: 12
   - Entities analyzed: 25
   - Processing time: 8.7s
```

---

## REST API

### Endpoint: `/api/relationship-engine`

**Base URL**: `http://localhost:3110/api/relationship-engine`

**Methods**: `POST`, `GET`

---

#### POST Request

Trigger relationship detection manually.

**Request Body**:
```json
{
  "mode": "incremental" | "nightly" | "on-demand",
  "eventId": "uuid-123",           // Required for incremental
  "fullScan": true,                // Optional for nightly (default: false)
  "entityIds": ["uuid-1", "uuid-2"] // Optional for on-demand
}
```

**Examples**:

**Incremental Mode**:
```bash
curl -X POST http://localhost:3110/api/relationship-engine \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "incremental",
    "eventId": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Nightly Mode (last 24h)**:
```bash
curl -X POST http://localhost:3110/api/relationship-engine \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "nightly"
  }'
```

**Nightly Mode (full scan)**:
```bash
curl -X POST http://localhost:3110/api/relationship-engine \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "nightly",
    "fullScan": true
  }'
```

**On-Demand Mode**:
```bash
curl -X POST http://localhost:3110/api/relationship-engine \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "on-demand",
    "entityIds": ["uuid-1", "uuid-2"]
  }'
```

**Response** (200 OK):
```json
{
  "success": true,
  "result": {
    "edges_created": 5,
    "edges_updated": 2,
    "entities_analyzed": 12,
    "processing_time": 2.34,
    "strategies_used": ["pattern_based", "semantic_llm"]
  }
}
```

**Error Response** (400 Bad Request):
```json
{
  "success": false,
  "error": "Invalid mode. Must be incremental, nightly, or on-demand"
}
```

**Error Response** (500 Internal Server Error):
```json
{
  "success": false,
  "error": "RelationshipEngine failed: [error details]"
}
```

---

#### GET Request

Get current status and configuration.

```bash
curl http://localhost:3110/api/relationship-engine
```

**Response** (200 OK):
```json
{
  "status": "ready",
  "version": "1.0",
  "strategies": [
    "pattern_based",
    "semantic_llm",
    "embedding_similarity",
    "temporal",
    "graph_topology"
  ],
  "config": {
    "min_confidence": 0.3,
    "decay_factor": 0.99,
    "prune_threshold": 0.1
  }
}
```

---

## Detection Strategies

### Strategy Comparison

| Strategy | Speed | Precision | Recall | Use Case |
|----------|-------|-----------|--------|----------|
| Pattern-based | ⚡⚡⚡ Fast | 🎯 High (0.95) | 🔍 Low | Known patterns (role→org) |
| Semantic LLM | 🐌 Slow | 🎯 Medium (0.7-0.9) | 🔍 High | Complex relationships |
| Embedding similarity | ⚡⚡ Medium | 🎯 Medium (0.5-0.8) | 🔍 Medium | Semantic similarity |
| Temporal | ⚡⚡⚡ Fast | 🎯 High (0.8) | 🔍 Low | Time-based connections |
| Graph topology | ⚡⚡ Medium | 🎯 Low (0.5) | 🔍 Medium | Transitive inference |

---

### Strategy Selection

**Incremental Mode** (fast, post-event):
- ✅ Pattern-based (fast, high precision)
- ✅ Semantic LLM (catches complex relationships)
- ❌ Embedding similarity (requires cross-event context)
- ❌ Temporal (requires cross-event context)
- ❌ Graph topology (requires full graph)

**Nightly Mode** (comprehensive, slow):
- ✅ All 5 strategies
- ✅ Global decay
- ✅ Pruning

**On-Demand Mode** (debugging, custom):
- ✅ All 5 strategies
- ❌ No decay/pruning (user-initiated, don't modify existing edges)

---

## Return Values

### Standard Result Object

All main methods return this structure:

```python
{
    # Edges
    "edges_created": int,       # New edges created
    "edges_updated": int,       # Existing edges reinforced
    "edges_decayed": int,       # Edges decayed (nightly only)
    "edges_pruned": int,        # Edges deleted (nightly only)

    # Analysis
    "entities_analyzed": int,   # Number of entities processed
    "processing_time": float,   # Seconds

    # Strategies
    "strategies_used": List[str]  # Which strategies ran
}
```

### Relationship Object

Strategy methods return lists of these objects:

```python
{
    "from_id": str,             # Source entity UUID
    "to_id": str,               # Target entity UUID
    "kind": str,                # Relationship type
    "confidence": float,        # 0.0-1.0 (how confident)
    "importance": float,        # 0.0-1.0 (how important) [optional]
    "description": str,         # Human-readable description [optional]
    "start_date": date,         # When relationship started [optional]
    "end_date": date,           # When relationship ended [optional]
    "metadata": dict            # Additional context
}
```

**Supported Relationship Kinds**:
```python
# Pattern-based
"role_at"

# Semantic LLM (examples)
"mentored_by", "inspired_by", "collaborated_with",
"founded", "led", "worked_at", "manages", "owns"

# Embedding similarity
"semantically_related"

# Temporal
"temporal_overlap"

# Graph topology
"inferred_connection"

# See models/edge.py for full list of supported types
```

---

## Error Handling

### Common Errors

#### 1. Missing Event ID

```python
result = engine.run_incremental(None)
# Raises: ValueError("event_id is required for incremental mode")
```

**Solution**: Always provide valid event UUID

---

#### 2. Invalid Entity IDs

```python
result = engine.run_on_demand(entity_ids=["invalid-id"])
# Returns: {"edges_created": 0, "entities_analyzed": 0, ...}
# Logs: WARNING: Entity invalid-id not found
```

**Solution**: Verify entity IDs exist in database

---

#### 3. LLM API Failure

```python
# If Anthropic API fails
# Logs: ERROR: LLM strategy failed: API timeout
# Continues with other strategies
```

**Behavior**: Gracefully degrades, logs error, continues with other strategies

---

#### 4. Database Connection Error

```python
# If Supabase connection fails
# Raises: Exception("Database connection failed")
```

**Solution**: Check `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`

---

### Logging

All errors and warnings are logged to console:

```python
import logging
logger = logging.getLogger(__name__)

# Set log level in .env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

**Log Examples**:
```
INFO: RelationshipEngine: Starting incremental mode for event uuid-123
INFO: Pattern-based strategy found 2 relationships
WARNING: LLM strategy failed for entity-pair (person-1, person-2): API timeout
INFO: Created 5 edges, reinforced 2 edges
INFO: Processing complete in 2.34s
```

---

## Configuration

### Environment Variables

**File**: `apps/ai-core/.env`

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...
SUPABASE_URL=https://....supabase.co
SUPABASE_SERVICE_ROLE_KEY=...

# Optional (defaults shown)
MIN_CONFIDENCE=0.3          # Filter relationships below this
DECAY_FACTOR=0.99           # Nightly decay multiplier
PRUNE_THRESHOLD=0.1         # Remove edges below this weight
EMBEDDING_SIMILARITY_THRESHOLD=0.85  # Cosine similarity threshold
```

### Tuning Parameters

**Confidence Threshold**:
```python
engine.min_confidence = 0.5  # Higher = fewer, higher-quality edges
engine.min_confidence = 0.2  # Lower = more edges, some false positives
```

**Decay Rate**:
```python
engine.apply_global_decay(0.99)   # Gentle (1% decay per night)
engine.apply_global_decay(0.95)   # Moderate (5% decay per night)
engine.apply_global_decay(0.90)   # Aggressive (10% decay per night)
```

**Pruning Threshold**:
```python
engine.prune_weak_edges(0.1)   # Remove very weak edges
engine.prune_weak_edges(0.5)   # Remove moderately weak edges
```

---

## Performance Considerations

### Expected Performance

| Operation | Entities | Time | API Calls |
|-----------|----------|------|-----------|
| Incremental (2 strategies) | 10-20 | 2-5s | 1-2 |
| Nightly (last 24h) | 50-200 | 30-60s | 5-20 |
| Nightly (full scan) | 500+ | 5-15min | 50-200 |
| On-demand (specific) | 10 | 5-10s | 2-5 |

### Optimization Tips

1. **Incremental mode** - Use after each event (fast, targeted)
2. **Nightly mode** - Use with `full_scan=False` (analyzes last 24h only)
3. **Batch API calls** - LLM strategy batches entity pairs when possible
4. **Cache embeddings** - Embeddings are cached, only generated once per entity
5. **Index database** - Ensure indexes on `edge.weight`, `edge.from_id`, `edge.to_id`

---

## Examples

### Complete Workflow

```python
from engines.relationship_engine import RelationshipEngine

# 1. Initialize engine
engine = RelationshipEngine()

# 2. After event processing (Archivist calls this)
event_result = engine.run_incremental("event-uuid-123")
print(f"Incremental: {event_result['edges_created']} edges created")

# 3. Nightly consolidation (scheduler calls this at 3 AM)
nightly_result = engine.run_nightly(full_scan=False)
print(f"Nightly: {nightly_result['edges_created']} created, "
      f"{nightly_result['edges_pruned']} pruned")

# 4. Manual debugging (on-demand)
debug_result = engine.run_on_demand(entity_ids=["uuid-1", "uuid-2"])
print(f"On-demand: {debug_result['edges_created']} edges")
```

### Custom Strategy Pipeline

```python
# Get entities
entities = db.get_entities_by_event("event-id")

# Run individual strategies
pattern_rels = engine.strategy_pattern_based(entities)
llm_rels = engine.strategy_semantic_llm(entities, context_text)

# Combine results
all_rels = pattern_rels + llm_rels

# Filter by confidence
high_conf_rels = [r for r in all_rels if r['confidence'] >= 0.8]

# Create edges
for rel in high_conf_rels:
    engine.create_or_update_edge(rel)
```

---

**End of API Reference**

For implementation details, see:
- `docs/features/relationship-engine/feature-details.md`
- `docs/features/relationship-engine/troubleshooting.md`
