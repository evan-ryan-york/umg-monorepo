# Phase 0 Audit - Current State Before Relationship Engine

**Date:** 2025-11-08
**Status:** ✅ Complete

## Summary

This audit documents the current state of the relationship detection system before implementing the Relationship Engine. This provides baseline metrics to validate improvements after implementation.

## Key Findings

### 1. BUG CONFIRMED: Missing Role→Organization Edges

- **Role entities:** 8
- **Organization entities:** 10
- **Edges from role→organization:** **0** ❌

**Example role entities that should have organization connections:**
1. "Co-Founder, Co-CEO at The Gathering Place"
2. "Director of Academics at Caliber Schools"
3. "Chief Information Officer at RePublic Schools"
4. "Principal at Nashville Academy of Computer Science"
5. "Interim Principal at RePublic High School"

These role entities clearly mention organizations in their titles, but the current relationship_mapper.py has no pattern to extract and connect them.

### 2. Current Graph Statistics

- **Total entities:** 109
- **Total edges:** 236
- **Average edges per entity:** 2.17
- **Distinct relationship types:** 10

### 3. Current Relationship Types (from database)

| Relationship Type | Edge Count | Notes |
|-------------------|------------|-------|
| manages | 100 | Person→Skill connections |
| achieved | 61 | Person→Milestone |
| worked_at | 24 | Person→Organization (but missing role→org!) |
| relates_to | 22 | Generic connections |
| values | 9 | Person→Core Identity |
| owns | 6 | Person→Goal |
| founded | 6 | Person→Organization |
| attended | 6 | Person→Organization (education) |
| led | 1 | Person→Organization/Project |
| lived_in | 1 | Person→Location |

### 4. Prescriptive Relationship Types (from relationship_mapper.py)

The current `relationship_mapper.py` (lines 93-124) defines these **SUPPORTED RELATIONSHIP TYPES**:

**Work & Career:**
- worked_at, attended, founded, led, participated_in

**Location & Temporal:**
- lived_in

**Knowledge & Learning:**
- learned_from, achieved

**Hierarchical & Structural:**
- belongs_to, modifies, mentions, informs

**Dependencies & Conflicts:**
- blocks, contradicts

**General & Identity:**
- relates_to, values, owns, manages, contributes_to

**Problem:** This prescriptive list prevents novel relationship types. If the LLM detects a relationship that doesn't match one of these types, it can't create it.

### 5. Missing Database Schema Columns

Current edge table is **missing** these columns needed for the Relationship Engine:

- ❌ `weight` - For Hebbian learning (edge reinforcement)
- ❌ `last_reinforced_at` - Timestamp of last reinforcement

**Current edge columns:**
- id, from_id, to_id, kind
- start_date, end_date, description
- confidence, importance
- metadata (JSONB)
- source_event_id
- created_at, updated_at

### 6. Current Limitations

#### A. Event-Scoped Only
The current relationship detection (in `archivist.py` lines 285-320) runs during event processing and can only find relationships between entities **in the same event**. Cross-event connections are impossible.

#### B. No Edge Weighting
Edges have confidence scores but no reinforcement mechanism. If the same relationship is detected multiple times, the edge isn't strengthened.

#### C. No Pruning
Once created, edges never decay or get removed. The graph can only grow, not prune weak connections.

#### D. Prescriptive Types Only
The LLM prompt explicitly lists "SUPPORTED RELATIONSHIP TYPES" which constrains what can be created. Novel relationship types like "mentored_by", "inspired_by", "contradicts" are impossible unless added to the hardcoded list.

## Entity Type Distribution

| Entity Type | Count |
|-------------|-------|
| milestone | 32 |
| skill | 32 |
| organization | 10 |
| role | 8 |
| core_identity | 6 |
| location | 6 |
| project | 4 |
| decision | 3 |
| goal | 3 |
| product | 3 |
| person | 1 |
| reflection | 1 |

## Temporal Data

- **Edges with start_date:** 72 (30.5%)
- **Ongoing edges** (start_date but no end_date): 12
- **Edges with non-empty metadata:** 1 (0.4%)

## Relationship Mapper Analysis

### Current Implementation (`apps/ai-core/processors/relationship_mapper.py`)

**Key method:** `detect_relationships()` (lines 17-235)

**How it works:**
1. Takes text + entities + optional existing entities
2. Builds prompt with entity list and supported relationship types
3. Calls Claude with prescriptive prompt (lines 64-195)
4. Parses JSON response
5. Returns list of relationship dicts

**LLM Prompt Issues:**
- Lines 93-124: Hardcoded list of "SUPPORTED RELATIONSHIP TYPES"
- Line 86: "relationship_type: One of the supported types below" (constraint)
- No flexibility for novel relationship types

**Positive aspects to preserve:**
- Good temporal extraction (lines 126-131)
- Confidence and importance scoring
- Reference map support for pronouns

### Pattern-Based Detection

**Method:** `detect_explicit_relationships()` (lines 237-292)

Uses regex patterns for:
- Rename/modification signals
- Hierarchical ownership ("belongs to", "part of")
- Blocking/dependency ("blocked by", "depends on")
- Information flow ("learned from", "based on")
- Contradiction ("contradicts", "conflicts with")

This is good and should be preserved in the new engine's pattern-based strategy.

## What the Relationship Engine Will Fix

1. ✅ **Role→Organization connections** via pattern-based strategy
2. ✅ **Cross-event relationships** via nightly mode full graph analysis
3. ✅ **Novel relationship types** via flexible LLM prompt (not prescriptive)
4. ✅ **Edge reinforcement** via Hebbian learning (weight increases with repeated detection)
5. ✅ **Graph pruning** via decay and threshold-based removal
6. ✅ **Distant connections** via embedding similarity strategy

## Next Steps

- ✅ Phase 0 Complete - Audit documented
- ⏭️ Phase 1: Create database migration to add `weight` and `last_reinforced_at` columns
