# RelationshipEngine Test Suite

Comprehensive unit and integration tests for the Relationship Engine.

## Test Coverage

**Total Tests: 16**
**Status: ✅ All Passing**

### Test Breakdown

#### 1. Pattern-Based Strategy Tests (4 tests)
- ✅ `test_role_at_organization_basic` - Basic "at" pattern (CTO at Company)
- ✅ `test_role_comma_organization` - Comma pattern (Director, School)
- ✅ `test_no_match_when_org_missing` - No edge when organization doesn't exist
- ✅ `test_multiple_roles_multiple_orgs` - Multiple simultaneous connections

**Purpose:** Regression test for the role→organization bug

#### 2. Semantic LLM Strategy Tests (1 test)
- ✅ `test_llm_strategy_basic` - Verify LLM strategy exists and is callable

**Purpose:** Ensure LLM detection strategy is implemented

#### 3. Temporal Strategy Tests (2 tests)
- ✅ `test_temporal_overlap_detected` - Detect overlapping time periods
- ✅ `test_no_overlap_no_relationship` - No edge when dates don't overlap

**Purpose:** Validate temporal overlap detection

#### 4. Graph Topology Strategy Tests (1 test)
- ✅ `test_transitive_connection_detection` - Find A→B→C, create A→C

**Purpose:** Validate transitive connection inference

#### 5. Edge Reinforcement Tests (2 tests)
- ✅ `test_new_edge_creation` - New edges start with weight=1.0
- ✅ `test_edge_reinforcement_increases_weight` - Repeated detection increases weight

**Purpose:** Test Hebbian learning (LTP analog)

#### 6. Edge Decay & Pruning Tests (2 tests)
- ✅ `test_global_decay_reduces_weights` - Decay multiplies weights by factor
- ✅ `test_prune_weak_edges` - Remove edges below threshold

**Purpose:** Test synaptic homeostasis

#### 7. Confidence Filtering Tests (1 test)
- ✅ `test_filter_low_confidence_relationships` - Filter below min_confidence

**Purpose:** Ensure quality control

#### 8. Operating Mode Tests (2 tests)
- ✅ `test_incremental_mode_analyzes_event_entities` - Incremental mode works
- ✅ `test_nightly_mode_runs_all_strategies` - Nightly runs all 5 strategies

**Purpose:** Validate operating modes

#### 9. Integration Tests (1 test)
- ✅ `test_full_pipeline_pattern_based` - End-to-end pattern detection

**Purpose:** Full pipeline validation

---

## Running Tests

### Run All Tests
```bash
pytest tests/test_relationship_engine.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_relationship_engine.py::TestPatternBasedStrategy -v
```

### Run Single Test
```bash
pytest tests/test_relationship_engine.py::TestPatternBasedStrategy::test_role_at_organization_basic -v
```

### Run with Coverage
```bash
pytest tests/test_relationship_engine.py --cov=engines.relationship_engine --cov-report=html
```

---

## Test Strategy

### Unit Tests
Tests for individual strategies and components in isolation using mocks.

### Integration Tests
Tests for full pipeline with multiple components working together.

### Regression Tests
Tests that verify the role→organization bug fix (pattern-based strategy tests).

---

## Mocking Strategy

Tests use `unittest.mock` to:
- Mock database calls (`DatabaseService`)
- Mock LLM API calls (`Anthropic`)
- Mock existing edges for reinforcement tests
- Isolate each component for true unit testing

---

## Known Warnings

**Pydantic Deprecation Warnings (12 warnings):**
- `Config` class-based configuration is deprecated
- Will be updated to `ConfigDict` in future Pydantic migration
- Does not affect functionality

---

## Next Steps

### Additional Tests to Consider:
1. **Embedding Similarity Tests** - Test semantic similarity detection with mock embeddings
2. **Error Handling Tests** - Test graceful degradation when strategies fail
3. **Performance Tests** - Test with large entity sets (1000+ entities)
4. **Concurrent Tests** - Test nightly mode with real database
5. **End-to-End Tests** - Test Archivist→RelationshipEngine integration

### Real Data Validation:
After code tests pass, validate with real data:
1. Process a test event
2. Verify role→org edges created
3. Check edge weights are tracked
4. Run nightly consolidation
5. Verify edge reinforcement works

---

## Test Metrics

- **Test Count:** 16
- **Pass Rate:** 100%
- **Execution Time:** ~0.6 seconds
- **Code Coverage:** (Run with --cov to measure)

---

*Last Updated: 2025-11-08*
