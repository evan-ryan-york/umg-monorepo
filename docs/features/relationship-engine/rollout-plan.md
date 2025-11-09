# RelationshipEngine Rollout Plan

Safe, phased deployment plan for the RelationshipEngine to production.

**Version**: 1.0
**Target Date**: TBD
**Owner**: Ryan York
**Last Updated**: 2025-11-08

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Rollout Checklist](#pre-rollout-checklist)
3. [Rollout Phases](#rollout-phases)
4. [Monitoring & Metrics](#monitoring--metrics)
5. [Rollback Plan](#rollback-plan)
6. [Post-Rollout Tasks](#post-rollout-tasks)

---

## Overview

### Goals

1. ✅ Fix role→organization bug (8 roles, 10 orgs, 0 edges → should have 8 edges)
2. ✅ Enable cross-event relationship detection
3. ✅ Implement Hebbian learning for edge reinforcement
4. ✅ Maintain system stability (no regressions)

### Success Criteria

**Functional**:
- ✅ Pattern-based strategy creates role→org edges
- ✅ LLM strategy detects complex relationships
- ✅ Edge reinforcement increases weight
- ✅ Nightly decay and pruning work correctly
- ✅ All 16 tests passing

**Performance**:
- ⏱️ Incremental mode: < 5s per event (currently 2-3s)
- ⏱️ Nightly mode: < 60s for 24h window (currently 45s)
- 💰 LLM costs: < $5/day (estimated $2/day)

**Reliability**:
- 🔒 No data loss (entities/edges)
- 🔒 No event processing failures
- 🔒 Graceful degradation if LLM fails

---

## Pre-Rollout Checklist

### Code Readiness

- [x] All tests passing (16/16 ✅)
- [x] Code reviewed and documented
- [x] API reference created
- [x] Troubleshooting guide created
- [ ] Performance testing completed
- [ ] Load testing completed (100+ events)

### Infrastructure Readiness

- [x] Database migration applied (weight + last_reinforced_at columns)
- [x] Database migration verified (236 edges backfilled)
- [x] Indexes created (idx_edge_weight)
- [ ] Database backup taken before rollout
- [ ] Monitoring dashboards created
- [ ] Alert thresholds configured

### Configuration

- [x] Environment variables set (.env)
- [x] Anthropic API key valid
- [x] Supabase credentials valid
- [ ] Nightly scheduler configured (3 AM timezone)
- [ ] Log rotation configured
- [ ] Error notification webhook configured (Slack/email)

### Documentation

- [x] API reference published
- [x] Troubleshooting guide published
- [x] Architecture documentation updated
- [x] Archivist docs updated (relationship detection removed)
- [ ] User-facing documentation (if needed)
- [ ] Internal team training (if applicable)

---

## Rollout Phases

### Phase 1: Shadow Mode (Week 1)

**Goal**: Run RelationshipEngine alongside existing system without affecting production

**Actions**:

1. **Deploy code** (but disable writes to database)
   ```python
   # In relationship_engine.py
   SHADOW_MODE = True  # Logs only, no DB writes

   def create_or_update_edge(relationship):
       if SHADOW_MODE:
           logger.info(f"[SHADOW] Would create edge: {relationship}")
           return False
       else:
           # Normal DB write
   ```

2. **Enable logging**
   ```bash
   LOG_LEVEL=DEBUG
   ```

3. **Monitor logs**
   - Check for errors/exceptions
   - Validate relationships detected
   - Compare with expected behavior

4. **Collect metrics**
   - Incremental mode latency
   - Nightly mode latency
   - Relationships detected per event
   - LLM API costs

**Exit Criteria**:
- ✅ No errors in logs for 7 days
- ✅ Relationships detected match expectations
- ✅ Performance within targets (< 5s incremental, < 60s nightly)

**Rollback**: Disable shadow mode, no production impact

---

### Phase 2: Parallel Mode (Week 2)

**Goal**: Enable database writes, but keep old system running as backup

**Actions**:

1. **Enable database writes**
   ```python
   SHADOW_MODE = False
   ```

2. **Keep old relationship_mapper.py** (don't delete yet)
   - Old system still creates edges
   - New system also creates edges
   - Potential duplicates (handled by unique constraint)

3. **Compare outputs**
   ```sql
   -- Edges created by old system
   SELECT COUNT(*) FROM edge WHERE source_event_id IN (
     SELECT id FROM raw_events WHERE created_at > '2025-11-08'
   ) AND weight = 1.0 AND created_at < '2025-11-08';

   -- Edges created by new system
   SELECT COUNT(*) FROM edge WHERE source_event_id IN (
     SELECT id FROM raw_events WHERE created_at > '2025-11-08'
   ) AND weight = 1.0 AND last_reinforced_at > '2025-11-08';
   ```

4. **Monitor edge quality**
   - Check for unexpected edge types
   - Verify confidence scores reasonable
   - Validate weight increases on reinforcement

5. **Test nightly consolidation**
   - Run manually first: `python scripts/run_relationship_engine.py --mode nightly`
   - Verify decay and pruning work correctly
   - Check no important edges pruned
   - Enable scheduler after manual validation

**Exit Criteria**:
- ✅ New system creates all expected edges
- ✅ No quality regressions (unexpected edges)
- ✅ Nightly consolidation stable for 7 days
- ✅ Edge reinforcement working (weights > 1.0)

**Rollback**: Disable new system, keep old system running

---

### Phase 3: Full Cutover (Week 3)

**Goal**: Disable old system, run only RelationshipEngine

**Actions**:

1. **Remove old relationship_mapper.py calls**
   ```python
   # In archivist.py
   # BEFORE:
   # relationships = relationship_mapper.detect_relationships(...)
   # for rel in relationships:
   #     db.create_edge(rel)

   # AFTER:
   # (Already done - this is just cleanup)
   # Old code already removed, just verify
   ```

2. **Enable all strategies in nightly mode**
   - Pattern-based ✅
   - Semantic LLM ✅
   - Embedding similarity ✅
   - Temporal analysis ✅
   - Graph topology ✅

3. **Monitor full pipeline**
   - Event processing (Archivist → RelationshipEngine)
   - Nightly consolidation (all strategies + decay + pruning)
   - Edge weight distribution
   - Pruned edges (ensure not too aggressive)

4. **Validate key use cases**
   - ✅ Role→organization edges created (fixes original bug)
   - ✅ Cross-event relationships detected
   - ✅ Edge reinforcement working
   - ✅ Weak edges pruned after inactivity

**Exit Criteria**:
- ✅ System stable for 7 days
- ✅ No regressions in event processing
- ✅ All 5 strategies working correctly
- ✅ Edge decay and pruning balanced (not too aggressive)

**Rollback**: Re-enable old system, disable RelationshipEngine

---

### Phase 4: Optimization (Week 4+)

**Goal**: Fine-tune parameters based on real-world usage

**Tuning Parameters**:

1. **Confidence Threshold**
   ```python
   # Current
   MIN_CONFIDENCE = 0.3

   # If too many low-quality edges:
   MIN_CONFIDENCE = 0.5

   # If missing important edges:
   MIN_CONFIDENCE = 0.2
   ```

2. **Decay Factor**
   ```python
   # Current (1% decay per night)
   DECAY_FACTOR = 0.99

   # Slower decay (0.5% per night)
   DECAY_FACTOR = 0.995

   # Faster decay (5% per night)
   DECAY_FACTOR = 0.95
   ```

3. **Prune Threshold**
   ```python
   # Current
   PRUNE_THRESHOLD = 0.1

   # More aggressive pruning
   PRUNE_THRESHOLD = 0.5

   # Less aggressive pruning
   PRUNE_THRESHOLD = 0.05
   ```

4. **Nightly Window**
   ```python
   # Current (last 24 hours)
   if not full_scan:
       entities = db.get_recent_entities(hours=24)

   # Larger window (last 7 days)
   entities = db.get_recent_entities(hours=168)

   # Full scan (entire graph)
   entities = db.get_all_entities()
   ```

**Actions**:
- Collect metrics (edge creation rate, pruning rate, weight distribution)
- Adjust parameters based on data
- A/B test different configurations
- Document optimal settings

**Exit Criteria**:
- ✅ Parameters tuned for production workload
- ✅ Documentation updated with recommended settings

---

## Monitoring & Metrics

### Key Metrics to Track

#### Functional Metrics

**Edge Creation Rate**:
```sql
-- Edges created per day
SELECT DATE(created_at), COUNT(*)
FROM edge
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY DATE(created_at);

-- Expected: 10-50 edges/day (depends on event volume)
```

**Edge Reinforcement Rate**:
```sql
-- Edges with weight > 1.0
SELECT COUNT(*), AVG(weight)
FROM edge
WHERE weight > 1.0;

-- Expected: 20-40% of edges reinforced after 1 week
```

**Edge Pruning Rate**:
```sql
-- Edges pruned per nightly run (check logs)
grep "Pruned" logs/relationship_engine.log | tail -7

-- Expected: 0-5% of edges pruned per night
```

#### Performance Metrics

**Incremental Mode Latency**:
```bash
# Check logs for processing time
grep "Incremental.*complete" logs/relationship_engine.log | \
  grep -oP "processing_time: \K[\d\.]+" | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count, "s"}'

# Target: < 5s average
```

**Nightly Mode Latency**:
```bash
# Check logs for nightly processing time
grep "Nightly consolidation complete" logs/relationship_engine.log | \
  grep -oP "processing_time: \K[\d\.]+"

# Target: < 60s for 24h window
```

**LLM API Costs**:
```bash
# Track API calls and costs
# Anthropic dashboard: https://console.anthropic.com/settings/usage

# Target: < $5/day
```

#### Quality Metrics

**Edge Confidence Distribution**:
```sql
SELECT
  CASE
    WHEN confidence < 0.3 THEN '<0.3'
    WHEN confidence < 0.5 THEN '0.3-0.5'
    WHEN confidence < 0.7 THEN '0.5-0.7'
    WHEN confidence < 0.9 THEN '0.7-0.9'
    ELSE '>=0.9'
  END as confidence_range,
  COUNT(*)
FROM edge
GROUP BY confidence_range;

-- Expected: Most edges 0.7-0.9
```

**Edge Weight Distribution**:
```sql
SELECT
  CASE
    WHEN weight < 0.5 THEN '<0.5'
    WHEN weight < 1.0 THEN '0.5-1.0'
    WHEN weight < 2.0 THEN '1.0-2.0'
    WHEN weight < 5.0 THEN '2.0-5.0'
    ELSE '>=5.0'
  END as weight_range,
  COUNT(*)
FROM edge
GROUP BY weight_range;

-- Expected: Most edges 1.0-2.0, some 2.0-5.0
```

**Relationship Type Distribution**:
```sql
SELECT kind, COUNT(*)
FROM edge
GROUP BY kind
ORDER BY COUNT(*) DESC;

-- Expected: role_at, founded, worked_at as top 3
```

---

### Alerts

Configure alerts for:

**Critical**:
- ❌ RelationshipEngine crashes or hangs
- ❌ Database connection failures
- ❌ Nightly consolidation fails

**Warning**:
- ⚠️ Incremental mode > 10s (2x target)
- ⚠️ Nightly mode > 120s (2x target)
- ⚠️ LLM API costs > $10/day (2x target)
- ⚠️ > 10% edges pruned in single night (too aggressive)

**Info**:
- ℹ️ Nightly consolidation started
- ℹ️ Nightly consolidation completed
- ℹ️ Daily summary (edges created, reinforced, pruned)

---

## Rollback Plan

### Scenario 1: RelationshipEngine Crashes

**Symptoms**: Exceptions in logs, events not processed, edges not created

**Immediate Action**:
1. Disable RelationshipEngine trigger in Archivist
   ```python
   # In archivist.py
   ENABLE_RELATIONSHIP_ENGINE = False  # Add this flag
   ```

2. Re-enable old relationship_mapper.py (if still in codebase)
   ```python
   # In archivist.py
   if ENABLE_RELATIONSHIP_ENGINE:
       engine = RelationshipEngine()
       engine.run_incremental(event_id)
   else:
       # Old approach
       relationships = relationship_mapper.detect_relationships(...)
       for rel in relationships:
           db.create_edge(rel)
   ```

3. Investigate root cause in logs
4. Fix issue, test, redeploy

**Data Impact**: No data loss, but no new edges created during downtime

---

### Scenario 2: Too Many Edges Pruned

**Symptoms**: Important relationships disappearing, edge count dropping rapidly

**Immediate Action**:
1. Disable nightly consolidation
   ```bash
   # Stop scheduler
   pkill -f nightly_consolidation.py
   ```

2. Increase prune threshold
   ```python
   PRUNE_THRESHOLD = 0.05  # Was 0.1
   ```

3. Decrease decay factor
   ```python
   DECAY_FACTOR = 0.995  # Was 0.99 (slower decay)
   ```

4. Restore edges from database backup (if needed)
   ```sql
   -- Restore edge table from backup taken before rollout
   ```

5. Re-enable nightly consolidation with new parameters

**Data Impact**: Potential edge loss, but can be restored from backup

---

### Scenario 3: Low-Quality Edges Created

**Symptoms**: Nonsensical relationships, low confidence scores, user complaints

**Immediate Action**:
1. Increase confidence threshold
   ```python
   MIN_CONFIDENCE = 0.5  # Was 0.3
   ```

2. Delete low-quality edges
   ```sql
   DELETE FROM edge WHERE confidence < 0.4 AND created_at > '2025-11-08';
   ```

3. Review LLM prompts for improvements
4. Add human review for confidence < 0.7

**Data Impact**: Delete some edges, but improves overall quality

---

### Scenario 4: Performance Degradation

**Symptoms**: Event processing slow, nightly consolidation timeout

**Immediate Action**:
1. Disable slow strategies
   ```python
   # In run_nightly(), comment out slow strategies
   # rels = engine.strategy_embedding_similarity(entities)  # SLOW
   # rels = engine.strategy_graph_topology(entity_ids)      # SLOW
   ```

2. Reduce nightly window
   ```python
   # Analyze last 12 hours instead of 24
   entities = db.get_recent_entities(hours=12)
   ```

3. Increase nightly schedule interval
   ```python
   # Run every 2 days instead of daily
   scheduler.add_job(run_nightly, 'cron', hour=3, day='*/2')
   ```

4. Optimize database queries (add indexes, use explain analyze)

**Data Impact**: No data loss, but some relationships detected later

---

## Post-Rollout Tasks

### Week 1 After Full Cutover

- [ ] Monitor all metrics daily
- [ ] Review edge quality manually (sample 50 edges)
- [ ] Check for any user-reported issues
- [ ] Tune parameters if needed
- [ ] Document any issues and resolutions

### Week 2-4 After Full Cutover

- [ ] Collect performance data
- [ ] Analyze edge weight distribution
- [ ] Review pruned edges (ensure not important)
- [ ] Optimize slow strategies if needed
- [ ] Update documentation with lessons learned

### Month 2+

- [ ] Enable advanced features (if implemented):
  - [ ] User-facing edge visualization
  - [ ] Manual edge creation/deletion
  - [ ] Edge weight visualization
- [ ] Plan next phase enhancements:
  - [ ] Additional detection strategies
  - [ ] Contextual reference resolution
  - [ ] Temporal state tracking

---

## Risk Assessment

### High Risk

**Risk**: Database migration fails or corrupts data
- **Mitigation**: Take full backup before migration, test on staging first
- **Probability**: Low
- **Impact**: High

**Risk**: RelationshipEngine creates too many low-quality edges
- **Mitigation**: Start with high confidence threshold, lower gradually
- **Probability**: Medium
- **Impact**: Medium

**Risk**: Nightly consolidation times out or crashes
- **Mitigation**: Start with small window (12h), increase gradually
- **Probability**: Low
- **Impact**: Medium

### Medium Risk

**Risk**: LLM API costs exceed budget
- **Mitigation**: Monitor costs daily, set API rate limits, batch requests
- **Probability**: Medium
- **Impact**: Low

**Risk**: Edge pruning too aggressive, important edges deleted
- **Mitigation**: Start with low prune threshold (0.05), increase gradually
- **Probability**: Medium
- **Impact**: Medium

**Risk**: Performance degradation in event processing
- **Mitigation**: Monitor latency, optimize queries, cache entities
- **Probability**: Low
- **Impact**: Medium

### Low Risk

**Risk**: Edge reinforcement not working correctly
- **Mitigation**: Comprehensive tests already written and passing
- **Probability**: Low
- **Impact**: Low

**Risk**: Schema changes break existing queries
- **Mitigation**: Added columns with defaults, backward compatible
- **Probability**: Low
- **Impact**: Low

---

## Success Metrics (1 Month Post-Rollout)

### Functional Success

- ✅ Role→organization bug fixed (8 edges created for 8 roles)
- ✅ Cross-event relationships detected (mentored_by, inspired_by, etc.)
- ✅ Edge reinforcement working (20%+ edges with weight > 1.0)
- ✅ Graph quality improved (higher confidence relationships)

### Performance Success

- ✅ Incremental mode: < 5s average
- ✅ Nightly mode: < 60s for 24h window
- ✅ LLM API costs: < $5/day
- ✅ Zero downtime

### Reliability Success

- ✅ No data loss
- ✅ No event processing failures
- ✅ Graceful degradation (continues if one strategy fails)
- ✅ 99.9%+ uptime

### User Success

- ✅ Better entity graph visualizations (more connections)
- ✅ More accurate Mentor responses (richer context)
- ✅ No user-reported issues with edge quality

---

## Rollout Timeline

| Phase | Duration | Start Date | End Date | Status |
|-------|----------|------------|----------|--------|
| Pre-rollout Checklist | 3 days | TBD | TBD | ⏳ Pending |
| Phase 1: Shadow Mode | 7 days | TBD | TBD | ⏳ Pending |
| Phase 2: Parallel Mode | 7 days | TBD | TBD | ⏳ Pending |
| Phase 3: Full Cutover | 7 days | TBD | TBD | ⏳ Pending |
| Phase 4: Optimization | Ongoing | TBD | - | ⏳ Pending |

**Total Estimated Time**: 24 days from start to full cutover

---

## Stakeholder Communication

### Before Rollout

**Audience**: Development team, stakeholders
**Message**: "We're deploying the RelationshipEngine to fix the role→organization bug and enable cross-event relationship detection. Rollout will be phased over 3 weeks with monitoring at each stage."

### During Rollout (Weekly Updates)

**Audience**: Development team, stakeholders
**Template**:
```
RelationshipEngine Rollout - Week X Update

Current Phase: [Shadow/Parallel/Cutover/Optimization]

Metrics:
- Edges created: X
- Edges reinforced: X
- Avg incremental latency: Xs
- Avg nightly latency: Xs
- Issues: [None / See details below]

Next Steps:
- [Actions for next week]

Status: 🟢 On track / 🟡 Minor issues / 🔴 Blocked
```

### After Rollout (Final Report)

**Audience**: Development team, stakeholders
**Content**:
- Summary of goals and success criteria
- Final metrics and performance data
- Issues encountered and resolutions
- Lessons learned
- Next steps and future enhancements

---

**End of Rollout Plan**

**Approval**: TBD
**Last Reviewed**: 2025-11-08
**Next Review**: Before rollout start date

See also:
- `docs/features/relationship-engine/feature-details.md`
- `docs/features/relationship-engine/api-reference.md`
- `docs/features/relationship-engine/troubleshooting.md`
