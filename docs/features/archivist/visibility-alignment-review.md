# Archivist Visibility Layer - Alignment Review

**Date**: 2025-10-05

## Review Findings

The visibility implementation plan has been reviewed against the project's technical guide and database structure documentation. Below are the key alignments and enhancements made.

---

## ✅ Alignment Confirmations

### 1. **Architecture Alignment**
- **Correct**: API endpoint in `apps/web` (Next.js), not in `apps/ai-core` (Python)
- **Reason**: Web app has direct Supabase access via `@repo/db` package
- **Implementation**: Next.js API route queries database directly for Archivist's results

### 2. **Database Schema Alignment**
All table queries and fields match the documented schema:
- ✅ `raw_events` table with `status` field (pending_triage, pending_processing, processed, ignored, error)
- ✅ `entity` table with `source_event_id` foreign key
- ✅ `edge` table with proper relationship types
- ✅ `chunk` and `embedding` tables linked to entities
- ✅ `signal` table with importance/recency/novelty scores

### 3. **Status Flow Alignment**
Documented the proper status progression:
- Manual entries → `pending_processing` (skip triage)
- Automatic webhooks → `pending_triage` → user triages → `pending_processing`
- After Archivist → `processed` or `error`
- User dismisses → `ignored`

---

## 🔧 Enhancements Made

### 1. **Added Entity Type Documentation**
Documented all valid entity types from database structure:

**Work-related**:
- `project`, `feature`, `task`

**Relationship**:
- `person`, `company`

**Thought entities**:
- `meeting_note`, `reflection`, `decision`

**Knowledge**:
- `core_identity`, `reference_document`

### 2. **Hub-and-Spoke Pattern Documentation**
Added detailed explanation of the hub-spoke model:
- Hubs: Complex entities (projects, features, decisions)
- Spokes: Related entities (meeting_note, reflection, task)
- Connection via `relates_to` edges
- Metadata flags: `is_hub: true`, `is_spoke: true`

### 3. **Edge Type Documentation**
Listed all 7 edge types with examples:
- `belongs_to` - Hierarchical ownership
- `modifies` - Changes/updates (e.g., renames)
- `mentions` - References
- `informs` - Knowledge transfer
- `blocks` - Dependencies
- `contradicts` - Tensions
- `relates_to` - Hub-spoke connections

### 4. **UI Enhancements**
Updated UI mockup and component code to:
- Show hub-spoke relationships with "(SPOKE→HUB)" label
- Include all entity types with proper emojis
- Display all 7 edge relationship types
- Add `core_identity` emoji (⭐) for values/mission entities

### 5. **Implementation Notes**
Added critical reminders:
- Use `@repo/db` package for Supabase access
- Filter for `status='processed'` only (not all statuses)
- Handle empty results gracefully
- Detect hub-spoke patterns in edge rendering
- Show 1536 dimensions for embeddings (OpenAI text-embedding-3-small)

---

## 📋 Key Corrections Made

### Original Plan Issues:
1. ❌ Missing status flow explanation
2. ❌ No hub-spoke pattern documentation
3. ❌ Incomplete entity type list
4. ❌ Missing edge type definitions
5. ❌ No architecture clarification (web vs AI core)

### Corrections Applied:
1. ✅ Added full status flow with triage workflow
2. ✅ Documented hub-spoke model with metadata flags
3. ✅ Listed all 10 entity types from database structure
4. ✅ Documented all 7 edge types with examples
5. ✅ Clarified Next.js API route architecture

---

## 🎯 Final Alignment Status

**FULLY ALIGNED** ✅

The visibility implementation plan now:
- Matches the database schema exactly
- Follows the documented status flow
- Implements the hub-and-spoke pattern correctly
- Uses proper entity and edge types
- Fits within the established architecture (Next.js API in web app)
- Includes all necessary indexes for performance

---

## 📝 Implementation Checklist

When implementing, ensure:

- [ ] API route uses `@repo/db` package
- [ ] Query filters for `status='processed'` only
- [ ] All 10 entity types rendered with correct emojis
- [ ] All 7 edge types displayed properly
- [ ] Hub-spoke relationships labeled in UI
- [ ] Signal scores shown (importance, recency, novelty)
- [ ] Database index created: `idx_entity_source_event_id`
- [ ] Error states handled (empty logs, failed events)
- [ ] Embedding dimensions shown as 1536

---

## 📚 Reference Documents

This alignment review is based on:
1. `docs/project-wide-resources/technical-guide.md` - Architecture and data flow
2. `docs/project-wide-resources/database-structure.md` - Complete schema blueprint
3. `docs/features/archivist/implementation-plan-updates.md` - Archivist progress (80% complete)

---

*Review Completed: 2025-10-05*
