# Relationship Engine - Implementation Plan

## Overview

This document details the step-by-step implementation plan for building the Relationship Engine as a separate, asynchronous component in the UMG architecture. It includes all architectural changes, code modifications, and migration strategies.

---

## 📁 Context & Reference Files for Implementation

**IMPORTANT**: Read these files and sections carefully before implementing. They provide critical context about the existing architecture, neuroscientific principles, and design decisions.

### Core Documentation

| File | Purpose | What to Read |
|------|---------|--------------|
| `docs/features/relationship-engine/feature-details.md` | Complete feature specification | Read ENTIRE file - explains what the engine does and why |
| `docs/project-wide-resources/brain-reference.md` | Neuroscientific foundation | Sections 2.1, 2.4, 2.5 (consolidation, Hebbian learning, offline processing) |
| `docs/features/archivist/feature-details.md` | Archivist architecture | Understand what Archivist currently does |
| `docs/migrations/00_initial_schema.sql` | Database schema | Lines 50-82 (edge table definition) |

### Existing Code to Review

| File | Lines | Purpose |
|------|-------|---------|
| `apps/ai-core/agents/archivist.py` | 1-533 | **FULL FILE** - Current entity extraction and relationship creation pipeline |
| `apps/ai-core/agents/archivist.py` | 285-320 | **CRITICAL** - Relationship detection code that will be REMOVED |
| `apps/ai-core/processors/relationship_mapper.py` | 1-458 | **FULL FILE** - Current relationship detection logic (to be replaced) |
| `apps/ai-core/processors/relationship_mapper.py` | 64-195 | Current LLM prompt (too prescriptive - use as reference but improve) |
| `apps/ai-core/processors/entity_extractor.py` | 35-89 | Entity types and extraction prompt |
| `apps/ai-core/services/database.py` | All | Database service methods (you'll need to add new methods) |
| `apps/ai-core/services/embeddings.py` | All | Embedding generation (needed for Strategy 3) |
| `apps/ai-core/config.py` | All | Configuration and settings |

### Database Schema Files

| File | Purpose |
|------|---------|
| `docs/migrations/00_initial_schema.sql` | Initial database schema - shows edge table structure |
| `docs/migrations/refactor_edges_table_schema.sql` | Previous edge table changes - shows migration pattern |
| `docs/migrations/add_source_event_id_to_edge.sql` | Shows how to add columns to edge table |

### Test Files to Reference

| File | Purpose |
|------|---------|
| `apps/ai-core/tests/test_archivist.py` | Archivist test patterns |
| `apps/ai-core/tests/test_relationship_mapper.py` | Existing relationship tests |

### Key Concepts to Understand

1. **Event-Driven Architecture**: The system processes "raw events" which contain user input (text, voice, etc.)
2. **Entity Types**: 15 different types (person, organization, role, skill, etc.) - see `entity_extractor.py:37-52`
3. **Edge Schema**: Edges have `kind`, `confidence`, `importance`, `description`, `start_date`, `end_date`, `metadata`
4. **Current Limitation**: Relationships only created within single event context, prescriptive types only
5. **Hebbian Learning**: "Neurons that fire together, wire together" - edges should strengthen with repeated co-occurrence
6. **NREM Pruning**: Weak edges should decay and be removed (synaptic homeostasis)

### Codebase Structure

```
apps/ai-core/
├── agents/
│   ├── archivist.py          ← Will be modified (Phase 4)
│   ├── mentor.py              ← Uses graph for retrieval
│   └── feedback_processor.py
├── processors/
│   ├── entity_extractor.py    ← Read for entity types
│   ├── relationship_mapper.py ← Will be deprecated
│   ├── signal_scorer.py
│   └── mention_tracker.py
├── services/
│   ├── database.py            ← Will need new methods
│   ├── embeddings.py          ← Use for Strategy 3
│   └── entity_resolver.py
├── engines/                   ← NEW - create this directory
│   └── relationship_engine.py ← NEW - implement here
├── tests/
│   ├── test_archivist.py
│   └── test_relationship_engine.py  ← NEW - create this
└── config.py

apps/web/
└── app/api/
    └── relationship-engine/   ← NEW - create this
        └── route.ts           ← NEW - API endpoint

docs/
├── features/
│   ├── archivist/
│   └── relationship-engine/
│       ├── feature-details.md
│       └── implementation-plan.md  ← You are here
└── migrations/
    └── add_relationship_engine_columns.sql  ← NEW - create this
```

### Important Design Decisions

1. **Why Separate from Archivist?**
   - Archivist = fast, event-scoped entity extraction
   - RelationshipEngine = slow, graph-scoped edge creation
   - Mirrors brain: hippocampus (encoding) vs. neocortical consolidation (offline)
   - See `feature-details.md` section "Why It Exists"

2. **Why Multiple Strategies?**
   - Different connection types need different detection methods
   - Pattern-based: fast, deterministic (e.g., "Title at Organization")
   - LLM-based: semantic, flexible (e.g., novel relationship types)
   - Embeddings: finds distant similarities (expensive, nightly only)
   - See `feature-details.md` section "Detection Strategies"

3. **Why Edge Weighting?**
   - Implements Hebbian learning (LTP)
   - Repeated co-occurrence = stronger synapse
   - Enables retrieval ranking by connection strength
   - See `brain-reference.md` Section 2.4

4. **Why Pruning?**
   - Prevents graph bloat
   - Implements synaptic homeostasis (NREM sleep)
   - Only strong, reinforced connections persist
   - See `brain-reference.md` Section 2.5

---

## Current State Analysis

### What Currently Exists

**In `archivist.py` (lines 285-320):**
```python
# Step 6: Relationship Mapping
relationships = self.relationship_mapper.detect_relationships(
    cleaned_text,
    extracted_entities,
    existing_entities=existing_entities_dict,
    reference_map=reference_map
)

# Create edges from relationships
edges_created = 0
for rel in relationships:
    success = self.relationship_mapper.create_edge_from_relationship(
        rel,
        complete_entity_map,
        self.db,
        source_event_id=event_id
    )
    if success:
        edges_created += 1
```

**In `relationship_mapper.py`:**
- `detect_relationships()`: Uses LLM to find relationships within one event's context
- `create_edge_from_relationship()`: Creates edges in the database
- Prescriptive relationship types (limited to predefined templates)
- No cross-event analysis
- No edge weighting or reinforcement

### What Needs to Change

1. **Archivist** must STOP creating relationships entirely
2. **RelationshipMapper** will be deprecated/replaced by the new engine
3. **New component** `relationship_engine.py` will handle all edge creation
4. **Database schema** may need additions for edge weights and metadata
5. **Scheduling system** needed for nightly batch processing
6. **API endpoints** for on-demand mode

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         RAW EVENT                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                 ┌───────────────┐
                 │   ARCHIVIST   │
                 │  (Simplified) │
                 └───────┬───────┘
                         │
                         │ Creates entities only
                         │ (NO edge creation)
                         ▼
                 ┌───────────────┐
                 │ ENTITY NODES  │
                 │   (Database)  │
                 └───────┬───────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌────────┐    ┌──────────┐    ┌─────────┐
    │Incremental   │  Nightly │    │On-Demand│
    │  Mode    │    │   Mode   │    │  Mode   │
    └────┬────┘    └────┬─────┘    └────┬────┘
         │              │               │
         └──────────────┼───────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │ RELATIONSHIP     │
              │    ENGINE        │
              │                  │
              │ • Semantic       │
              │ • Pattern-based  │
              │ • Embeddings     │
              │ • Temporal       │
              │ • Graph topology │
              └────────┬─────────┘
                       │
                       │ Creates/updates edges
                       ▼
              ┌─────────────────┐
              │  EDGE TABLE     │
              │  (with weights) │
              └─────────────────┘
```

## Implementation Phases

### Phase 0: Preparation & Planning
**Duration:** 1 day
**Risk:** Low

#### 📖 Required Reading Before Starting:
1. **Read `docs/features/relationship-engine/feature-details.md`** - ENTIRE FILE (understand what you're building and why)
2. **Read `docs/project-wide-resources/brain-reference.md`** - Sections 2.1, 2.4, 2.5 (neuroscientific foundation)
3. **Read `apps/ai-core/agents/archivist.py`** - Lines 285-320 (current relationship code you'll be replacing)
4. **Read `apps/ai-core/processors/relationship_mapper.py`** - FULL FILE (understand current limitations)
5. **Read `docs/migrations/00_initial_schema.sql`** - Lines 50-82 (current edge table schema)

#### Tasks:
1. **Create feature directory structure**
   ```bash
   mkdir -p apps/ai-core/engines
   touch apps/ai-core/engines/__init__.py
   touch apps/ai-core/engines/relationship_engine.py
   ```

2. **Review and document current relationship detection**
   - Query database: `SELECT DISTINCT kind FROM edge;` to see all current relationship types
   - Query: `SELECT COUNT(*) FROM edge;` to see total edge count
   - Analyze `relationship_mapper.py:64-195` - document all prescriptive relationship types
   - Test case: Query for role→organization edges (should find ZERO - this is the bug we're fixing)
   - Document which detection patterns are working vs. failing

3. **Database schema review**
   - Read `docs/migrations/00_initial_schema.sql` lines 50-82 (edge table)
   - Check if these fields exist: `weight`, `last_reinforced_at`
   - If not, you'll add them in Phase 1
   - Review `metadata JSONB` field - understand it's flexible for strategy-specific data

#### Context Files for This Phase:
- `docs/migrations/00_initial_schema.sql` - Database schema
- `apps/ai-core/processors/relationship_mapper.py` - Current relationship detection
- `apps/ai-core/services/database.py` - Look for edge-related methods

#### Deliverables:
- [ ] Feature directory created
- [ ] Current edge audit completed (document: total edges, distinct types, missing role→org connections)
- [ ] Database requirements documented
- [ ] All required reading completed

---

### Phase 1: Database Schema Updates
**Duration:** 1-2 days
**Risk:** Medium (requires migration)

#### 📖 Required Reading for This Phase:
- `docs/migrations/00_initial_schema.sql` - Lines 50-82 (current edge table)
- `docs/migrations/add_source_event_id_to_edge.sql` - Pattern for adding columns
- `docs/migrations/refactor_edges_table_schema.sql` - Pattern for edge migrations
- `apps/ai-core/services/database.py` - Edge-related methods you'll need to update

#### Changes Needed to `edge` table:

Check current schema:
```sql
-- Current edge table (from 00_initial_schema.sql)
CREATE TABLE edge (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_id UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  to_id UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  start_date DATE,
  end_date DATE,
  confidence FLOAT DEFAULT 1.0,
  importance FLOAT,
  description TEXT,
  metadata JSONB DEFAULT '{}',
  source_event_id UUID REFERENCES raw_events(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Add new columns:**
```sql
-- Migration: Add relationship engine columns
ALTER TABLE edge ADD COLUMN IF NOT EXISTS weight FLOAT DEFAULT 1.0;
ALTER TABLE edge ADD COLUMN IF NOT EXISTS last_reinforced_at TIMESTAMPTZ DEFAULT NOW();

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_edge_weight ON edge(weight);
CREATE INDEX IF NOT EXISTS idx_edge_last_reinforced ON edge(last_reinforced_at);

COMMENT ON COLUMN edge.weight IS 'Synaptic strength - increases with reinforcement, decreases with pruning';
COMMENT ON COLUMN edge.last_reinforced_at IS 'When this edge was last strengthened';
```

**Update metadata schema** to support:
```javascript
{
  "source_strategy": "semantic_llm" | "pattern_based" | "embedding_similarity" | "temporal" | "graph_topology",
  "reinforcement_count": 0,
  "detected_in_events": ["event_id_1", "event_id_2"],
  "pattern_match": "role_at_organization", // for pattern-based
  "embedding_score": 0.85, // for embedding-based
  "version": "1.0" // engine version that created this
}
```

#### Tasks:
1. Create migration file: `docs/migrations/add_relationship_engine_columns.sql`
2. Test migration on local database
3. Run migration on production (if applicable)
4. Update database service to handle new columns

#### Deliverables:
- [ ] Migration file created and tested
- [ ] Database schema updated
- [ ] DatabaseService updated to read/write new fields

---

### Phase 2: Build Relationship Engine Core
**Duration:** 3-4 days
**Risk:** Low

#### 📖 Required Reading for This Phase:
- `docs/features/relationship-engine/feature-details.md` - Section "How It Works" (operating modes and strategies)
- `apps/ai-core/processors/relationship_mapper.py` - Reference for pattern-based detection (don't copy, improve)
- `apps/ai-core/services/database.py` - Study edge creation methods (`create_edge()`, etc.)
- `apps/ai-core/agents/archivist.py` - Lines 1-33 (initialization pattern to follow)
- `apps/ai-core/config.py` - How to access settings (API keys, etc.)
- `docs/project-wide-resources/brain-reference.md` - Section 2.4 (Hebbian learning for edge creation logic)

#### Create `apps/ai-core/engines/relationship_engine.py`

**Core class structure:**
```python
from typing import List, Dict, Optional
from services.database import DatabaseService
from anthropic import Anthropic
from config import settings
import logging

logger = logging.getLogger(__name__)


class RelationshipEngine:
    """
    Discovers and creates relationships (edges) between entities in the graph.

    Operates independently of the Archivist to enable cross-event analysis,
    iterative refinement, and flexible detection strategies.
    """

    def __init__(self):
        self.db = DatabaseService()
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Strategy weights (can be tuned)
        self.strategy_weights = {
            'semantic_llm': 1.0,
            'pattern_based': 1.0,
            'embedding_similarity': 0.8,
            'temporal': 0.7,
            'graph_topology': 0.6
        }

        # Thresholds
        self.min_confidence = 0.5  # Don't create edges below this
        self.max_edges_per_run = 10000  # Safety limit

        logger.info("RelationshipEngine initialized")

    # ==================== PUBLIC API ====================

    def run_incremental(self, event_id: str) -> Dict:
        """
        Incremental Mode: Analyze entities from a single event.

        Called after Archivist processes an event. Finds relationships
        between newly created entities and existing entities.

        Args:
            event_id: The event that was just processed

        Returns:
            {
                'edges_created': int,
                'edges_updated': int,
                'strategies_used': [str],
                'processing_time': float
            }
        """
        pass

    def run_nightly(self, full_scan: bool = False) -> Dict:
        """
        Nightly Mode: Deep graph analysis during idle time.

        Runs expensive strategies (embeddings, graph topology) to find
        distant connections across the entire graph.

        Args:
            full_scan: If True, re-analyze all entities. If False, only
                      analyze entities created/updated since last run.

        Returns:
            {
                'edges_created': int,
                'edges_updated': int,
                'edges_pruned': int,
                'entities_analyzed': int,
                'processing_time': float
            }
        """
        pass

    def run_on_demand(self, entity_ids: Optional[List[str]] = None) -> Dict:
        """
        On-Demand Mode: User-triggered analysis.

        Allows manual graph refinement or testing new strategies.

        Args:
            entity_ids: If provided, only analyze these entities.
                       If None, analyze entire graph.

        Returns: Same as run_nightly()
        """
        pass

    # ==================== DETECTION STRATEGIES ====================

    def strategy_semantic_llm(
        self,
        entities: List[Dict],
        context_text: Optional[str] = None
    ) -> List[Dict]:
        """
        Strategy 1: Semantic Co-Occurrence (LLM-Based)

        Uses Claude to analyze entities and their context to find
        meaningful relationships. NOT prescriptive - allows Claude
        to infer relationship types from the semantic content.

        Args:
            entities: List of entity dicts with id, title, type, summary
            context_text: Optional text context where entities appear

        Returns:
            List of relationship dicts:
            {
                'from_id': str,
                'to_id': str,
                'kind': str,
                'confidence': float,
                'importance': float,
                'description': str,
                'start_date': str | None,
                'end_date': str | None
            }
        """
        pass

    def strategy_pattern_based(self, entities: List[Dict]) -> List[Dict]:
        """
        Strategy 2: Pattern-Based Inference

        Fast, deterministic pattern matching. No LLM required.

        Patterns:
        - "Title at Organization" → role --role_at--> organization
        - Skill + Person in same event → person --manages--> skill
        - Temporal co-occurrence → weak relates_to edge

        Args:
            entities: List of entity dicts

        Returns: List of relationship dicts
        """
        pass

    def strategy_embedding_similarity(
        self,
        entities: List[Dict],
        similarity_threshold: float = 0.75
    ) -> List[Dict]:
        """
        Strategy 3: Embedding Similarity

        Expensive - run during nightly mode only.
        Finds semantically similar entities using vector embeddings.

        Args:
            entities: List of entity dicts
            similarity_threshold: Minimum cosine similarity to create edge

        Returns: List of relationship dicts
        """
        pass

    def strategy_temporal(self, entities: List[Dict]) -> List[Dict]:
        """
        Strategy 4: Temporal Analysis

        Analyzes entities with temporal metadata (start_date, end_date).
        Finds overlapping periods, sequences, causality.

        Args:
            entities: List of entity dicts with temporal data

        Returns: List of relationship dicts
        """
        pass

    def strategy_graph_topology(self, entity_ids: List[str]) -> List[Dict]:
        """
        Strategy 5: Graph Topology

        Analyzes existing graph structure to infer missing connections.
        Example: A→B, B→C, but no A→C edge (transitive inference)

        Args:
            entity_ids: Entities to analyze for topology patterns

        Returns: List of relationship dicts
        """
        pass

    # ==================== EDGE MANAGEMENT ====================

    def create_or_update_edge(self, relationship: Dict) -> bool:
        """
        Create a new edge or reinforce an existing one.

        Implements Hebbian learning: if edge exists, strengthen it
        (LTP analog). If new, create it.

        Args:
            relationship: Dict with from_id, to_id, kind, confidence, etc.

        Returns:
            True if edge was created/updated, False otherwise
        """
        pass

    def prune_weak_edges(self, threshold: float = 0.1) -> int:
        """
        Remove edges below weight threshold.

        Implements synaptic homeostasis: weak, unreinforced edges
        are removed to prevent graph bloat.

        Args:
            threshold: Minimum weight to keep

        Returns:
            Number of edges deleted
        """
        pass

    def apply_global_decay(self, decay_factor: float = 0.99) -> int:
        """
        Apply global weight decay to all edges.

        Implements "use-it-or-lose-it" mechanism from NREM sleep.
        All edges are slightly weakened; only reinforced ones stay strong.

        Args:
            decay_factor: Multiply all weights by this (< 1.0)

        Returns:
            Number of edges updated
        """
        pass

    # ==================== UTILITIES ====================

    def _check_duplicate_edge(self, from_id: str, to_id: str, kind: str) -> Optional[str]:
        """Check if edge already exists. Returns edge_id if found."""
        pass

    def _calculate_salience(self, relationship: Dict, context: Dict) -> float:
        """Calculate salience score for LTP threshold check."""
        pass

    def _filter_by_confidence(self, relationships: List[Dict]) -> List[Dict]:
        """Filter out low-confidence relationships."""
        pass
```

#### Tasks:
1. Create the core `RelationshipEngine` class
2. Implement the three public API methods (incremental, nightly, on-demand) as stubs
3. Implement `strategy_pattern_based()` first (simplest, no LLM)
4. Implement `create_or_update_edge()` with reinforcement logic
5. Write unit tests for pattern-based strategy

#### Deliverables:
- [ ] `relationship_engine.py` created with full structure
- [ ] Pattern-based strategy working
- [ ] Edge creation/reinforcement logic working
- [ ] Unit tests passing

---

### Phase 3: Implement Semantic LLM Strategy
**Duration:** 2-3 days
**Risk:** Medium (depends on LLM prompt quality)

#### 📖 Required Reading for This Phase:
- `apps/ai-core/processors/relationship_mapper.py` - Lines 64-195 (current LLM prompt - understand but DON'T copy)
- `apps/ai-core/processors/entity_extractor.py` - Lines 30-89 (LLM prompt pattern, JSON parsing)
- `docs/features/relationship-engine/feature-details.md` - Section "Strategy 1: Semantic Co-Occurrence"
- **CRITICAL**: Read the "Real-World Example of Failure" in feature-details.md (role→org bug)

#### Migrate and Improve Current LLM Logic

The current `relationship_mapper.py` has a good LLM prompt foundation, but it's too prescriptive. We need to make it more flexible.

**Current prompt issues:**
- Lists "SUPPORTED RELATIONSHIP TYPES" as a constraint
- Only looks for predefined patterns
- Limits creativity

**New prompt approach:**
```python
def strategy_semantic_llm(self, entities: List[Dict], context_text: Optional[str] = None) -> List[Dict]:
    """Uses Claude to find ALL meaningful relationships, not just predefined types."""

    if len(entities) < 2:
        return []

    # Build entity list
    entity_list = "\n".join([
        f"- {e['title']} (type: {e['type']}, id: {e['id'][:8]}...)"
        for e in entities
    ])

    prompt = f"""You are analyzing entities in a personal knowledge graph to find meaningful connections.

ENTITIES:
{entity_list}

{f"CONTEXT TEXT:\\n{context_text}\\n" if context_text else ""}

Your task: Find ALL meaningful relationships between these entities.

CRITICAL RULES:
1. Look for ANY connection type that makes semantic sense
2. Do NOT limit yourself to predefined relationship types
3. If two entities are clearly related, connect them - even if the relationship type is novel
4. Infer relationship_type from the context (e.g., "role_at", "worked_at", "inspired_by", "contradicts")
5. Be creative but grounded in the evidence

For each relationship, provide:
- from_entity_id: The source entity ID (use the short form shown above)
- to_entity_id: The target entity ID
- relationship_type: A concise, meaningful type name (snake_case)
- confidence: 0.0 to 1.0 (how certain are you?)
- importance: 0.0 to 1.0 (how significant is this connection?)
- description: Rich context (1-2 sentences)
- start_date: YYYY-MM-DD or null
- end_date: YYYY-MM-DD or null

EXAMPLES:

Input:
- Executive Director at Youth Empowerment Through Arts and Humanities (type: role, id: abc123)
- Youth Empowerment Through Arts and Humanities (type: organization, id: def456)

Output:
{{
  "relationships": [
    {{
      "from_entity_id": "abc123",
      "to_entity_id": "def456",
      "relationship_type": "role_at",
      "confidence": 0.95,
      "importance": 0.85,
      "description": "Leadership position at the organization",
      "start_date": null,
      "end_date": null
    }}
  ]
}}

Return ONLY valid JSON with a "relationships" array. If no relationships exist, return {{"relationships": []}}.
"""

    # Call Claude
    response = self.client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8192,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse and return
    # ... (similar parsing logic to current relationship_mapper)
```

#### Tasks:
1. Implement `strategy_semantic_llm()` with new flexible prompt
2. Add entity ID mapping (prompt uses short IDs, need to map back to full UUIDs)
3. Add error handling for LLM failures
4. Test with real entity pairs that currently fail (like role→org)
5. Compare results against old relationship_mapper

#### Deliverables:
- [ ] LLM strategy implemented
- [ ] Tested on role→organization case (must succeed)
- [ ] Tested on 10+ diverse entity pairs
- [ ] Performance benchmarked (LLM latency, cost)

---

### Phase 4: Remove Relationship Logic from Archivist
**Duration:** 1 day
**Risk:** High (breaks existing functionality temporarily)

#### 📖 CRITICAL - Read Before Modifying Archivist:
- `apps/ai-core/agents/archivist.py` - **READ ENTIRE FILE** (understand full pipeline before modifying)
- `apps/ai-core/agents/archivist.py` - Lines 285-320 (**THESE EXACT LINES will be deleted**)
- `apps/ai-core/tests/test_archivist.py` - All tests (you'll need to update expectations)
- `docs/features/relationship-engine/feature-details.md` - Section "Why Separate from Archivist"

#### ⚠️ WARNING:
- Create a new git branch BEFORE making these changes: `git checkout -b feature/relationship-engine`
- This phase WILL break tests - that's expected
- The Archivist will no longer create edges - RelationshipEngine will do it asynchronously
- DO NOT delete `relationship_mapper.py` yet - it might be referenced elsewhere

#### Changes to `archivist.py`

**File: `apps/ai-core/agents/archivist.py`**

**Remove these sections:**

1. **Remove RelationshipMapper import** (line 6):
   ```python
   # DELETE THIS LINE:
   from processors.relationship_mapper import RelationshipMapper
   ```

2. **Remove RelationshipMapper initialization** (line 28):
   ```python
   # DELETE THIS LINE:
   self.relationship_mapper = RelationshipMapper()
   ```

3. **Remove entire relationship detection section** (lines 285-320):
   ```python
   # DELETE THIS ENTIRE BLOCK:
   # Step 6: Relationship Mapping (UPDATED - now includes existing entities and reference map)
   # ... all relationship code ...
   # logger.info(f"Created {edges_created} edges from {len(relationships)} detected relationships")
   ```

4. **Update the return statistics** (line 427-435):
   ```python
   # REMOVE edges_created from return dict
   return {
       'event_id': event_id,
       'status': 'success',
       'entities_created': len(entity_ids),
       # 'edges_created': edges_created,  # DELETE THIS LINE
       'chunks_created': len(chunks),
       'aliases_updated': len(alias_updates),
       'processing_time_seconds': elapsed_time
   }
   ```

5. **Add RelationshipEngine trigger** (NEW - after entity creation):
   ```python
   # After Step 4.5 (line 257), ADD:

   # Step 5: Trigger Incremental Relationship Detection
   # Now that entities are created, queue them for relationship analysis
   if entity_ids:
       try:
           from engines.relationship_engine import RelationshipEngine
           engine = RelationshipEngine()
           rel_result = engine.run_incremental(event_id)
           logger.info(f"Relationship engine created {rel_result.get('edges_created', 0)} edges")
       except Exception as e:
           logger.error(f"Relationship engine failed: {e}")
           # Don't fail the entire event if relationship detection fails
   ```

**Important:** This means old Steps 5, 6, 7 become Steps 6, 7, 8. Update all step numbers in comments.

#### Tasks:
1. Create a new git branch: `feature/relationship-engine`
2. Make all changes to `archivist.py`
3. Update step numbering in comments
4. Run existing Archivist tests (some will fail - that's expected)
5. Fix broken tests to work with new architecture

#### Deliverables:
- [ ] Archivist simplified (no relationship logic)
- [ ] Incremental mode trigger added
- [ ] Tests updated and passing
- [ ] No regression in entity extraction

---

### Phase 5: Implement Remaining Strategies
**Duration:** 3-4 days
**Risk:** Low-Medium

#### Strategy 3: Embedding Similarity

**Dependencies:**
- Need entity embeddings (currently only chunk embeddings exist)
- Need to generate embeddings for entity titles/summaries

**Implementation:**
```python
def strategy_embedding_similarity(self, entities: List[Dict], similarity_threshold: float = 0.75) -> List[Dict]:
    """Find related entities using embedding similarity."""

    from services.embeddings import EmbeddingsService
    embeddings_service = EmbeddingsService()

    relationships = []

    # Generate embeddings for each entity
    entity_texts = [f"{e['title']}. {e.get('summary', '')}" for e in entities]
    embeddings = embeddings_service.generate_embeddings_batch(entity_texts)

    # Compare all pairs
    for i, entity_a in enumerate(entities):
        for j, entity_b in enumerate(entities[i+1:], start=i+1):
            # Calculate cosine similarity
            similarity = self._cosine_similarity(embeddings[i], embeddings[j])

            if similarity >= similarity_threshold:
                relationships.append({
                    'from_id': entity_a['id'],
                    'to_id': entity_b['id'],
                    'kind': 'semantically_related',
                    'confidence': similarity,
                    'importance': 0.6,  # Medium importance for inferred connections
                    'description': f'Semantically similar (score: {similarity:.2f})',
                    'start_date': None,
                    'end_date': None
                })

    logger.info(f"Embedding strategy found {len(relationships)} connections")
    return relationships

def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import numpy as np
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
```

#### Strategy 4: Temporal Analysis

```python
def strategy_temporal(self, entities: List[Dict]) -> List[Dict]:
    """Find relationships based on temporal overlap."""

    from datetime import datetime

    relationships = []

    # Filter entities with temporal data
    temporal_entities = [
        e for e in entities
        if e.get('metadata', {}).get('start_date') or e.get('metadata', {}).get('end_date')
    ]

    for i, entity_a in enumerate(temporal_entities):
        for entity_b in temporal_entities[i+1:]:
            # Check for temporal overlap
            overlap = self._check_temporal_overlap(entity_a, entity_b)

            if overlap:
                relationships.append({
                    'from_id': entity_a['id'],
                    'to_id': entity_b['id'],
                    'kind': 'temporal_overlap',
                    'confidence': 0.7,
                    'importance': 0.5,
                    'description': f"Co-occurred during {overlap['period']}",
                    'start_date': overlap['start'],
                    'end_date': overlap['end']
                })

    return relationships

def _check_temporal_overlap(self, entity_a: Dict, entity_b: Dict) -> Optional[Dict]:
    """Check if two entities have overlapping time periods."""
    # Implementation details...
    pass
```

#### Strategy 5: Graph Topology

```python
def strategy_graph_topology(self, entity_ids: List[str]) -> List[Dict]:
    """Find missing transitive connections in graph."""

    relationships = []

    for entity_id in entity_ids:
        # Get all outgoing edges from this entity
        outgoing = self.db.get_outgoing_edges(entity_id)

        for edge in outgoing:
            # For each connected entity, get ITS outgoing edges
            second_order = self.db.get_outgoing_edges(edge.to_id)

            for second_edge in second_order:
                # Check if we have a direct edge from entity_id to second_edge.to_id
                direct_edge = self._check_duplicate_edge(
                    entity_id,
                    second_edge.to_id,
                    'inferred_from_graph'
                )

                if not direct_edge and entity_id != second_edge.to_id:
                    # Missing transitive edge - create it
                    relationships.append({
                        'from_id': entity_id,
                        'to_id': second_edge.to_id,
                        'kind': 'inferred_connection',
                        'confidence': 0.5,  # Lower confidence for inferred
                        'importance': 0.4,
                        'description': f"Inferred via {edge.to_id[:8]}...",
                        'start_date': None,
                        'end_date': None
                    })

    return relationships
```

#### Tasks:
1. Implement embedding similarity strategy
2. Add cosine similarity utility function
3. Implement temporal overlap strategy
4. Implement graph topology strategy
5. Test each strategy independently
6. Benchmark performance (especially embeddings - expensive!)

#### Deliverables:
- [ ] All 5 strategies implemented
- [ ] Each strategy tested with real data
- [ ] Performance benchmarks documented

---

### Phase 6: Implement Operating Modes
**Duration:** 2-3 days
**Risk:** Medium

#### 📖 Required Reading for This Phase:
- `docs/features/relationship-engine/feature-details.md` - Section "Operating Modes" (understand all 3 modes)
- `apps/ai-core/agents/archivist.py` - Lines 257 (where you added the incremental trigger in Phase 4)
- `apps/ai-core/services/database.py` - Methods for querying entities (you'll need `get_entities_by_event()`, etc.)
- `docs/project-wide-resources/brain-reference.md` - Section 2.5 (NREM consolidation - nightly mode analog)

#### Database Methods You'll Need to Add to `services/database.py`:
Before implementing the modes, check if these methods exist in `database.py`. If not, you'll need to add them:
- `get_entities_by_event(event_id)` - Get all entities created from a specific event
- `get_entities_since_timestamp(timestamp)` - Get entities created/updated after a timestamp
- `get_all_entities()` - Get all entities (for full scans)
- `get_recent_entities(limit)` - Get N most recent entities
- `get_all_edges()` - Get all edges (for pruning)
- `get_outgoing_edges(entity_id)` - Get edges from an entity (for graph topology)
- `delete_edges_below_weight(threshold)` - Delete weak edges (for pruning)

#### Incremental Mode (runs after each event)

```python
def run_incremental(self, event_id: str) -> Dict:
    """
    Analyze entities from a single event.
    Fast, focused analysis using cheap strategies.
    """
    import time
    start_time = time.time()

    # Get entities created by this event
    entities = self.db.get_entities_by_event(event_id)

    if len(entities) < 2:
        logger.info(f"Event {event_id} has <2 entities, skipping incremental analysis")
        return {'edges_created': 0, 'edges_updated': 0}

    # Get text context for this event
    event = self.db.get_event_by_id(event_id)
    context_text = event.payload.get('content', '') if event else None

    # Also get recent entities for cross-event connections
    existing_entities = self.db.get_recent_entities(limit=50)
    all_entities = entities + [
        {'id': e.id, 'title': e.title, 'type': e.type, 'summary': e.summary}
        for e in existing_entities
    ]

    # Run CHEAP strategies only (fast, synchronous)
    strategies = [
        ('pattern_based', self.strategy_pattern_based(all_entities)),
        ('semantic_llm', self.strategy_semantic_llm(all_entities, context_text))
    ]

    edges_created = 0
    edges_updated = 0

    for strategy_name, relationships in strategies:
        filtered = self._filter_by_confidence(relationships)

        for rel in filtered:
            # Add metadata about source strategy
            rel['metadata'] = rel.get('metadata', {})
            rel['metadata']['source_strategy'] = strategy_name
            rel['metadata']['source_event_id'] = event_id

            # Create or reinforce edge
            updated = self.create_or_update_edge(rel)
            if updated:
                edges_updated += 1
            else:
                edges_created += 1

    elapsed = time.time() - start_time

    result = {
        'edges_created': edges_created,
        'edges_updated': edges_updated,
        'strategies_used': [s[0] for s in strategies],
        'processing_time': elapsed
    }

    logger.info(f"Incremental mode: {result}")
    return result
```

#### Nightly Mode (scheduled batch job)

```python
def run_nightly(self, full_scan: bool = False) -> Dict:
    """
    Deep graph analysis during idle time.
    Runs expensive strategies and performs pruning.
    """
    import time
    start_time = time.time()

    logger.info(f"Starting nightly mode (full_scan={full_scan})")

    # Determine scope
    if full_scan:
        entities = self.db.get_all_entities()
    else:
        # Only entities created/updated in last 24 hours
        entities = self.db.get_entities_since_timestamp(
            timestamp=datetime.now() - timedelta(days=1)
        )

    entity_dicts = [
        {'id': e.id, 'title': e.title, 'type': e.type, 'summary': e.summary}
        for e in entities
    ]

    # Run ALL strategies (including expensive ones)
    strategies = [
        ('pattern_based', self.strategy_pattern_based(entity_dicts)),
        ('semantic_llm', self.strategy_semantic_llm(entity_dicts)),
        ('embedding_similarity', self.strategy_embedding_similarity(entity_dicts)),
        ('temporal', self.strategy_temporal(entity_dicts)),
        ('graph_topology', self.strategy_graph_topology([e['id'] for e in entity_dicts]))
    ]

    edges_created = 0
    edges_updated = 0

    for strategy_name, relationships in strategies:
        filtered = self._filter_by_confidence(relationships)

        for rel in filtered:
            rel['metadata'] = rel.get('metadata', {})
            rel['metadata']['source_strategy'] = strategy_name

            updated = self.create_or_update_edge(rel)
            if updated:
                edges_updated += 1
            else:
                edges_created += 1

    # Phase 2: Pruning (NREM sleep analog)
    logger.info("Applying global decay and pruning weak edges")

    edges_decayed = self.apply_global_decay(decay_factor=0.99)
    edges_pruned = self.prune_weak_edges(threshold=0.1)

    elapsed = time.time() - start_time

    result = {
        'edges_created': edges_created,
        'edges_updated': edges_updated,
        'edges_pruned': edges_pruned,
        'entities_analyzed': len(entities),
        'processing_time': elapsed
    }

    logger.info(f"Nightly mode complete: {result}")
    return result
```

#### On-Demand Mode (user-triggered)

```python
def run_on_demand(self, entity_ids: Optional[List[str]] = None) -> Dict:
    """
    User-triggered analysis.
    Allows manual refinement or testing.
    """
    if entity_ids:
        entities = [self.db.get_entity_by_id(eid) for eid in entity_ids]
        entities = [e for e in entities if e]  # Filter out None
        logger.info(f"On-demand mode: analyzing {len(entities)} specified entities")
    else:
        entities = self.db.get_all_entities()
        logger.info(f"On-demand mode: analyzing entire graph ({len(entities)} entities)")

    # Run with same logic as nightly mode
    return self.run_nightly(full_scan=True)
```

#### Tasks:
1. Implement all three mode functions
2. Add database methods: `get_entities_by_event()`, `get_entities_since_timestamp()`
3. Test incremental mode after Archivist runs
4. Create a script to manually trigger nightly mode
5. Create API endpoint for on-demand mode

#### Deliverables:
- [ ] All three modes implemented
- [ ] Incremental mode integrated with Archivist
- [ ] Nightly mode script created
- [ ] On-demand API endpoint created

---

### Phase 7: Edge Reinforcement & Pruning
**Duration:** 1-2 days
**Risk:** Low

#### Implement Hebbian Learning

```python
def create_or_update_edge(self, relationship: Dict) -> bool:
    """
    Create edge or reinforce existing one (LTP analog).

    Returns:
        True if edge was updated (reinforced), False if newly created
    """
    from_id = relationship['from_id']
    to_id = relationship['to_id']
    kind = relationship['kind']

    # Check if edge already exists
    existing_edge_id = self._check_duplicate_edge(from_id, to_id, kind)

    if existing_edge_id:
        # Edge exists - REINFORCE it (LTP)
        edge = self.db.get_edge_by_id(existing_edge_id)

        # Increase weight
        new_weight = edge.weight + 1.0

        # Update metadata
        metadata = edge.metadata or {}
        metadata['reinforcement_count'] = metadata.get('reinforcement_count', 0) + 1

        # Track which events contributed
        if 'detected_in_events' not in metadata:
            metadata['detected_in_events'] = []

        event_id = relationship.get('metadata', {}).get('source_event_id')
        if event_id and event_id not in metadata['detected_in_events']:
            metadata['detected_in_events'].append(event_id)

        # Update edge
        self.db.update_edge(existing_edge_id, {
            'weight': new_weight,
            'last_reinforced_at': datetime.now(),
            'metadata': metadata,
            'confidence': max(edge.confidence, relationship.get('confidence', 0.5))  # Take higher confidence
        })

        logger.info(f"Reinforced edge {existing_edge_id[:8]}... (weight: {edge.weight} → {new_weight})")
        return True  # Updated

    else:
        # New edge - CREATE it
        edge_data = {
            'from_id': from_id,
            'to_id': to_id,
            'kind': kind,
            'confidence': relationship.get('confidence', 1.0),
            'importance': relationship.get('importance'),
            'description': relationship.get('description'),
            'start_date': relationship.get('start_date'),
            'end_date': relationship.get('end_date'),
            'weight': 1.0,  # Initial weight
            'last_reinforced_at': datetime.now(),
            'metadata': relationship.get('metadata', {})
        }

        # Initialize metadata
        edge_data['metadata']['reinforcement_count'] = 0
        edge_data['metadata']['detected_in_events'] = []

        event_id = relationship.get('metadata', {}).get('source_event_id')
        if event_id:
            edge_data['metadata']['detected_in_events'].append(event_id)
            edge_data['source_event_id'] = event_id

        edge_id = self.db.create_edge(edge_data)
        logger.info(f"Created edge {edge_id[:8]}... ({kind}): {from_id[:8]}... → {to_id[:8]}...")
        return False  # Created
```

#### Implement Pruning (Synaptic Homeostasis)

```python
def apply_global_decay(self, decay_factor: float = 0.99) -> int:
    """
    Apply global weight decay (NREM sleep analog).
    All edges lose strength; only reinforced ones stay strong.
    """
    # Get all edges
    edges = self.db.get_all_edges()

    updated_count = 0

    for edge in edges:
        new_weight = edge.weight * decay_factor

        self.db.update_edge(edge.id, {
            'weight': new_weight,
            'updated_at': datetime.now()
        })

        updated_count += 1

    logger.info(f"Applied global decay ({decay_factor}) to {updated_count} edges")
    return updated_count


def prune_weak_edges(self, threshold: float = 0.1) -> int:
    """
    Delete edges below weight threshold.
    Use-it-or-lose-it synaptic pruning.
    """
    deleted_count = self.db.delete_edges_below_weight(threshold)

    logger.info(f"Pruned {deleted_count} edges below weight {threshold}")
    return deleted_count
```

#### Tasks:
1. Implement `create_or_update_edge()` with full reinforcement logic
2. Implement `apply_global_decay()`
3. Implement `prune_weak_edges()`
4. Add database methods: `get_edge_by_id()`, `update_edge()`, `delete_edges_below_weight()`
5. Test reinforcement: create edge twice, verify weight increases
6. Test pruning: create weak edges, run pruning, verify deletion

#### Deliverables:
- [ ] Reinforcement working (weights increase with repeated detection)
- [ ] Decay working (weights decrease over time)
- [ ] Pruning working (weak edges removed)
- [ ] Tests passing

---

### Phase 8: Scheduling & Integration
**Duration:** 2 days
**Risk:** Low

#### Create Nightly Job Scheduler

**Option A: Python cron (APScheduler)**

Create `apps/ai-core/schedulers/nightly_consolidation.py`:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from engines.relationship_engine import RelationshipEngine
import logging

logger = logging.getLogger(__name__)

def run_nightly_consolidation():
    """Runs every night at 3 AM."""
    logger.info("Starting nightly consolidation job")

    engine = RelationshipEngine()
    result = engine.run_nightly(full_scan=False)

    logger.info(f"Nightly consolidation complete: {result}")

def start_scheduler():
    """Start the background scheduler."""
    scheduler = BackgroundScheduler()

    # Run every day at 3 AM
    scheduler.add_job(
        run_nightly_consolidation,
        'cron',
        hour=3,
        minute=0,
        id='nightly_consolidation'
    )

    scheduler.start()
    logger.info("Nightly consolidation scheduler started (runs at 3 AM)")
```

**Option B: System cron**

Create `scripts/run_nightly_consolidation.py`:

```python
#!/usr/bin/env python3
"""
Nightly consolidation script.
Run via cron: 0 3 * * * /path/to/venv/bin/python /path/to/run_nightly_consolidation.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'ai-core'))

from engines.relationship_engine import RelationshipEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Running nightly consolidation")

    engine = RelationshipEngine()
    result = engine.run_nightly(full_scan=False)

    logger.info(f"Complete: {result}")
    sys.exit(0)
```

#### Create On-Demand API Endpoint

Add to `apps/web/app/api/relationship-engine/route.ts`:

```typescript
import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function POST(request: Request) {
  try {
    const { mode, entityIds } = await request.json();

    // Build Python command
    let command = 'cd ../ai-core && ../../venv/bin/python -c "';
    command += 'from engines.relationship_engine import RelationshipEngine; ';
    command += 'engine = RelationshipEngine(); ';

    if (mode === 'incremental') {
      command += `print(engine.run_incremental(\\"${entityIds[0]}\\"))"`;
    } else if (mode === 'on-demand') {
      if (entityIds && entityIds.length > 0) {
        command += `print(engine.run_on_demand(${JSON.stringify(entityIds)}))"`;
      } else {
        command += 'print(engine.run_on_demand())"';
      }
    } else {
      return NextResponse.json({ error: 'Invalid mode' }, { status: 400 });
    }

    const { stdout, stderr } = await execAsync(command);

    if (stderr) {
      console.error('Relationship engine stderr:', stderr);
    }

    return NextResponse.json({
      success: true,
      result: stdout,
      mode
    });

  } catch (error) {
    console.error('Relationship engine error:', error);
    return NextResponse.json(
      { error: 'Failed to run relationship engine' },
      { status: 500 }
    );
  }
}
```

#### Tasks:
1. Choose scheduling approach (APScheduler vs. system cron)
2. Implement chosen scheduler
3. Create API endpoint for on-demand mode
4. Test nightly job (manually trigger, verify it runs)
5. Test API endpoint (trigger from web UI)

#### Deliverables:
- [ ] Nightly scheduler working
- [ ] API endpoint working
- [ ] Documentation for how to trigger on-demand mode

---

### Phase 9: Testing & Validation
**Duration:** 2-3 days
**Risk:** Low

#### Create Comprehensive Test Suite

**Unit Tests** (`apps/ai-core/tests/test_relationship_engine.py`):

```python
import pytest
from engines.relationship_engine import RelationshipEngine

class TestRelationshipEngine:

    def test_pattern_based_role_to_org(self):
        """Test that role → organization pattern works."""
        engine = RelationshipEngine()

        entities = [
            {'id': 'role-123', 'title': 'CTO at Willow Education', 'type': 'role'},
            {'id': 'org-456', 'title': 'Willow Education', 'type': 'organization'}
        ]

        relationships = engine.strategy_pattern_based(entities)

        assert len(relationships) == 1
        assert relationships[0]['from_id'] == 'role-123'
        assert relationships[0]['to_id'] == 'org-456'
        assert relationships[0]['kind'] == 'role_at'

    def test_edge_reinforcement(self):
        """Test that edges are reinforced when detected multiple times."""
        engine = RelationshipEngine()

        # Create edge first time
        rel = {
            'from_id': 'entity-a',
            'to_id': 'entity-b',
            'kind': 'test_relationship',
            'confidence': 0.9
        }

        was_updated = engine.create_or_update_edge(rel)
        assert was_updated == False  # New edge

        # Create same edge again
        was_updated = engine.create_or_update_edge(rel)
        assert was_updated == True  # Reinforced

        # Check weight increased
        edge = engine.db.get_edge_by_from_to_kind('entity-a', 'entity-b', 'test_relationship')
        assert edge.weight == 2.0

    def test_global_decay(self):
        """Test that decay reduces all edge weights."""
        # ... implementation

    def test_pruning(self):
        """Test that weak edges are deleted."""
        # ... implementation
```

**Integration Tests:**

```python
class TestRelationshipEngineIntegration:

    def test_incremental_mode_after_event(self):
        """Test that incremental mode runs after Archivist processes event."""
        # Create a test event with entities
        # Run Archivist
        # Verify RelationshipEngine was triggered
        # Verify edges were created

    def test_nightly_mode_full_scan(self):
        """Test that nightly mode analyzes entire graph."""
        # Create multiple events with entities
        # Run nightly mode
        # Verify cross-event relationships were found

    def test_missing_role_org_connection(self):
        """
        Regression test: The exact issue that started this feature.
        Ensure role → organization connections are always created.
        """
        # Create event with text: "I was Executive Director at Youth Empowerment..."
        # Run Archivist (creates entities)
        # Run RelationshipEngine
        # Verify edge exists between role and organization
```

#### Validation Against Real Data

1. **Audit Current Graph:**
   - Count total entities
   - Count total edges
   - Identify obvious missing connections

2. **Run Full Migration:**
   - Run RelationshipEngine on entire existing graph
   - Count new edges created
   - Manually review sample of new edges (are they meaningful?)

3. **Specific Test Cases:**
   - Find all role entities
   - Verify each has edge to corresponding organization
   - Find all skills
   - Verify each has edge to person or project

#### Tasks:
1. Write unit tests for all strategies
2. Write integration tests for all modes
3. Create regression test for role→org issue
4. Run on production data and audit results
5. Fix any bugs discovered
6. Document test coverage

#### Deliverables:
- [ ] 20+ unit tests passing
- [ ] 10+ integration tests passing
- [ ] Regression test for role→org passing
- [ ] Production data validated
- [ ] Test coverage >80%

---

### Phase 10: Documentation & Rollout
**Duration:** 1-2 days
**Risk:** Low

#### Update Documentation

1. **Update `docs/features/archivist/feature-details.md`:**
   - Remove relationship detection from responsibilities
   - Add note: "Archivist creates entities. RelationshipEngine creates edges."

2. **Create `docs/features/relationship-engine/api-reference.md`:**
   - Document all public methods
   - Document all strategies
   - Document all operating modes
   - Include code examples

3. **Create `docs/features/relationship-engine/troubleshooting.md`:**
   - Common issues and solutions
   - How to manually trigger modes
   - How to inspect edge weights
   - How to tune thresholds

4. **Update main README:**
   - Add RelationshipEngine to architecture diagram
   - Explain the separation of concerns

#### Gradual Rollout Plan

**Week 1: Shadow Mode**
- RelationshipEngine runs but doesn't create edges (dry-run mode)
- Log all edges it WOULD create
- Compare against old relationship_mapper output
- Validate quality

**Week 2: Parallel Mode**
- Both systems run simultaneously
- Old edges tagged with `source: 'legacy_mapper'`
- New edges tagged with `source: 'relationship_engine'`
- Compare results, fix discrepancies

**Week 3: Full Cutover**
- Disable old relationship_mapper completely
- RelationshipEngine is sole source of edges
- Monitor for issues

**Week 4: Optimization**
- Tune thresholds based on real data
- Adjust strategy weights
- Optimize performance

#### Tasks:
1. Update all documentation
2. Create migration guide for other developers
3. Implement shadow mode (dry-run)
4. Run shadow mode for 1 week
5. Implement parallel mode
6. Run parallel mode for 1 week
7. Full cutover
8. Monitor and optimize

#### Deliverables:
- [ ] All documentation updated
- [ ] Shadow mode tested
- [ ] Parallel mode tested
- [ ] Full cutover completed
- [ ] No regressions detected

---

## Success Criteria

The Relationship Engine implementation is considered successful when:

1. **✅ Role→Organization Bug Fixed**
   - All role entities have edges to their organizations
   - Pattern-based strategy handles this automatically

2. **✅ No Prescriptive Constraints**
   - LLM can create any relationship type it infers
   - Novel relationship types appear in the graph

3. **✅ Cross-Event Connections**
   - Entities from different events are connected
   - Nightly mode finds distant relationships

4. **✅ Edge Reinforcement Working**
   - Repeated mentions increase edge weights
   - Strong connections rank higher in retrieval

5. **✅ Pruning Maintains Graph Health**
   - Weak edges are automatically removed
   - Graph doesn't bloat over time

6. **✅ Performance Acceptable**
   - Incremental mode completes in <5 seconds
   - Nightly mode completes in <30 minutes (for 10K entities)
   - No impact on Archivist performance

7. **✅ All Tests Passing**
   - 20+ unit tests
   - 10+ integration tests
   - Regression test for role→org

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| LLM strategy too slow | High | Medium | Run only in incremental mode for recent entities; use pattern-based for real-time |
| Graph bloat (too many edges) | Medium | High | Tune min_confidence threshold; aggressive pruning; regular audits |
| Missing edges (too conservative) | Medium | High | Start with low threshold (0.5), tune up based on quality |
| Breaking existing functionality | Low | High | Comprehensive tests; parallel mode; gradual rollout |
| Nightly job fails silently | Medium | Medium | Add monitoring/alerts; log to dedicated channel |
| Embedding cost explosion | High | Medium | Only run during nightly mode; cache embeddings; limit batch size |

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 0: Preparation | 1 day | None |
| 1: Database Schema | 1-2 days | Phase 0 |
| 2: Engine Core | 3-4 days | Phase 1 |
| 3: LLM Strategy | 2-3 days | Phase 2 |
| 4: Remove from Archivist | 1 day | Phase 2, 3 |
| 5: Remaining Strategies | 3-4 days | Phase 2 |
| 6: Operating Modes | 2-3 days | Phase 5 |
| 7: Reinforcement & Pruning | 1-2 days | Phase 6 |
| 8: Scheduling | 2 days | Phase 6 |
| 9: Testing | 2-3 days | Phase 7, 8 |
| 10: Documentation & Rollout | 1-2 days | Phase 9 |

**Total: 18-28 days (3.5-5.5 weeks)**

With parallel work on independent phases, realistic timeline: **4 weeks**

## Next Steps

1. Review this implementation plan
2. Get approval on database schema changes
3. Create feature branch: `feature/relationship-engine`
4. Begin Phase 0 (preparation)
5. Schedule weekly check-ins to track progress
6. Adjust timeline as needed based on discoveries

---

---

## 🚀 Quick Start Guide for Implementers

**If you're an LLM implementing this feature, follow these steps in order:**

### Step 1: Understand the Context (Day 1)
Read these files in this exact order:

1. **`docs/features/relationship-engine/feature-details.md`** (30 min)
   - Read ENTIRE file
   - This explains WHAT you're building and WHY
   - Understand the neuroscientific principles

2. **`docs/project-wide-resources/brain-reference.md`** (20 min)
   - Section 2.1 (Systems Consolidation)
   - Section 2.4 (Hebbian Learning - this is HOW edges are created)
   - Section 2.5 (Offline Processing - this is WHEN edges are created)

3. **`apps/ai-core/agents/archivist.py`** (15 min)
   - Read lines 1-100 (understand initialization and overall flow)
   - Read lines 285-320 (relationship code you'll REPLACE)
   - Understand: Archivist processes ONE event at a time

4. **`apps/ai-core/processors/relationship_mapper.py`** (10 min)
   - Read FULL FILE
   - Understand: This is the OLD way (too prescriptive, event-scoped only)
   - Lines 64-195: The LLM prompt (you'll improve this)

5. **`docs/migrations/00_initial_schema.sql`** (5 min)
   - Lines 50-82: Current edge table schema
   - Understand: Edges have kind, confidence, importance, start_date, end_date, metadata

### Step 2: Plan Your Implementation (Day 1)
- Complete Phase 0 tasks (preparation)
- Query the database to understand current state
- Verify which database methods already exist in `services/database.py`

### Step 3: Start Building (Days 2-20)
- Follow phases 1-10 in order
- Each phase has a "Required Reading" section - READ THOSE FILES FIRST
- Don't skip phases - they build on each other
- Run tests after each phase

### Step 4: Test the Critical Use Case (Throughout)
**The bug we're fixing**: Role entity → Organization entity connection missing

Test case:
```python
# After implementing each strategy, test this:
entities = [
    {'id': 'role-123', 'title': 'Executive Director at Youth Empowerment Through Arts and Humanities', 'type': 'role'},
    {'id': 'org-456', 'title': 'Youth Empowerment Through Arts and Humanities', 'type': 'organization'}
]

# Run your strategy
relationships = engine.strategy_pattern_based(entities)  # or strategy_semantic_llm

# MUST find this relationship:
assert len(relationships) > 0
assert relationships[0]['from_id'] == 'role-123'
assert relationships[0]['to_id'] == 'org-456'
```

If this test fails, your implementation is incomplete.

### Key Files You'll Create:
- `apps/ai-core/engines/relationship_engine.py` (600-800 lines)
- `apps/ai-core/tests/test_relationship_engine.py` (200-300 lines)
- `docs/migrations/add_relationship_engine_columns.sql` (20 lines)
- `scripts/run_nightly_consolidation.py` (30 lines)
- `apps/web/app/api/relationship-engine/route.ts` (50 lines)

### Key Files You'll Modify:
- `apps/ai-core/agents/archivist.py` (remove ~40 lines, add ~10 lines)
- `apps/ai-core/services/database.py` (add 7-10 new methods)

### Key Files You'll Reference (Don't Modify):
- `apps/ai-core/processors/entity_extractor.py` (entity types, LLM patterns)
- `apps/ai-core/services/embeddings.py` (for Strategy 3)
- `apps/ai-core/config.py` (settings access)

### Common Pitfalls to Avoid:
1. **Don't copy the old relationship_mapper.py prompt** - it's too prescriptive
2. **Don't forget edge weighting** - this is critical for Hebbian learning
3. **Don't skip pruning** - without it, the graph will bloat
4. **Don't create edges in Archivist** - that's the old way, engine does it now
5. **Don't forget to test cross-event connections** - that's the main improvement
6. **Don't make relationship types prescriptive** - let the LLM infer them

### Success Criteria Checklist:
Before considering the implementation complete, verify:

- [ ] Role→Organization connections are automatically created
- [ ] LLM can create novel relationship types (not limited to predefined list)
- [ ] Entities from different events can be connected
- [ ] Edge weights increase when connections are reinforced
- [ ] Weak edges are pruned during nightly mode
- [ ] Incremental mode completes in <5 seconds
- [ ] All unit tests pass (20+ tests)
- [ ] Integration tests pass (10+ tests)
- [ ] Regression test for role→org bug passes

---

## 🔍 Debugging & Verification Queries

Use these SQL queries to verify your implementation at each stage:

### Check Current State (Phase 0)
```sql
-- Total entities and edges
SELECT
  (SELECT COUNT(*) FROM entity) as total_entities,
  (SELECT COUNT(*) FROM edge) as total_edges;

-- All relationship types currently in use
SELECT kind, COUNT(*) as count
FROM edge
GROUP BY kind
ORDER BY count DESC;

-- Find all role entities
SELECT id, title, type
FROM entity
WHERE type = 'role'
LIMIT 10;

-- Check if role→org edges exist (should be ZERO before implementation)
SELECT e.*,
       e1.title as from_title, e1.type as from_type,
       e2.title as to_title, e2.type as to_type
FROM edge e
JOIN entity e1 ON e.from_id = e1.id
JOIN entity e2 ON e.to_id = e2.id
WHERE e1.type = 'role' AND e2.type = 'organization';
```

### Verify Schema Changes (After Phase 1)
```sql
-- Check if new columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'edge'
AND column_name IN ('weight', 'last_reinforced_at');

-- Check all edge columns
\d edge
```

### Verify Edge Creation (After Phase 2-3)
```sql
-- Check edges created by RelationshipEngine
SELECT kind,
       metadata->>'source_strategy' as strategy,
       COUNT(*) as count
FROM edge
WHERE metadata->>'source_strategy' IS NOT NULL
GROUP BY kind, metadata->>'source_strategy'
ORDER BY count DESC;

-- Verify role→org connections exist now
SELECT e.kind, e.confidence, e.weight,
       e1.title as role_title,
       e2.title as org_title
FROM edge e
JOIN entity e1 ON e.from_id = e1.id
JOIN entity e2 ON e.to_id = e2.id
WHERE e1.type = 'role' AND e2.type = 'organization'
LIMIT 20;
```

### Verify Reinforcement (After Phase 7)
```sql
-- Find edges with high weights (reinforced multiple times)
SELECT e.kind, e.weight,
       e.metadata->>'reinforcement_count' as times_reinforced,
       e1.title as from_title,
       e2.title as to_title
FROM edge e
JOIN entity e1 ON e.from_id = e1.id
JOIN entity e2 ON e.to_id = e2.id
WHERE e.weight > 1.0
ORDER BY e.weight DESC
LIMIT 20;

-- Check weight distribution
SELECT
  CASE
    WHEN weight < 0.5 THEN '< 0.5 (weak)'
    WHEN weight < 1.0 THEN '0.5-1.0 (medium)'
    WHEN weight < 2.0 THEN '1.0-2.0 (strong)'
    ELSE '> 2.0 (very strong)'
  END as weight_range,
  COUNT(*) as count
FROM edge
GROUP BY weight_range
ORDER BY weight_range;
```

### Verify Pruning (After Phase 7)
```sql
-- Count edges before and after pruning
-- Run this BEFORE running prune_weak_edges()
SELECT COUNT(*) as edges_before_pruning FROM edge;

-- Run this AFTER running prune_weak_edges(threshold=0.1)
SELECT COUNT(*) as edges_after_pruning FROM edge;

-- See which edges would be pruned (don't actually delete)
SELECT e.kind, e.weight, e.confidence,
       e1.title as from_title,
       e2.title as to_title
FROM edge e
JOIN entity e1 ON e.from_id = e1.id
JOIN entity e2 ON e.to_id = e2.id
WHERE e.weight < 0.1
LIMIT 50;
```

### Verify Cross-Event Connections (After Phase 6)
```sql
-- Find edges connecting entities from different events
SELECT e.kind, e.confidence, e.weight,
       e1.title as from_title, e1.source_event_id as from_event,
       e2.title as to_title, e2.source_event_id as to_event,
       e.metadata->>'source_strategy' as strategy
FROM edge e
JOIN entity e1 ON e.from_id = e1.id
JOIN entity e2 ON e.to_id = e2.id
WHERE e1.source_event_id != e2.source_event_id
LIMIT 20;
```

### Performance Monitoring
```sql
-- Average edges per entity (graph density)
SELECT AVG(edge_count) as avg_edges_per_entity
FROM (
  SELECT from_id, COUNT(*) as edge_count
  FROM edge
  GROUP BY from_id
) subquery;

-- Entities with most connections (hubs)
SELECT e1.title, e1.type, COUNT(*) as connection_count
FROM edge e
JOIN entity e1 ON e.from_id = e1.id
GROUP BY e1.id, e1.title, e1.type
ORDER BY connection_count DESC
LIMIT 20;

-- Edge creation timeline (by strategy)
SELECT
  DATE(created_at) as date,
  metadata->>'source_strategy' as strategy,
  COUNT(*) as edges_created
FROM edge
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY date, strategy
ORDER BY date DESC, edges_created DESC;
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-08
**Owner:** Relationship Engine Feature Team
