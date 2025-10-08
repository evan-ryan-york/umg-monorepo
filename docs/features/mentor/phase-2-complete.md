# Phase 2: Mentor Agent Core Infrastructure - Complete ✅

**Status**: Complete
**Date**: 2025-10-07

## What Was Built

### 1. Database Methods (database.py)

Added 9 new methods to `apps/ai-core/services/database.py`:

**Mentor-specific queries**:
- `get_entities_by_type(entity_type)` - Get all entities of a specific type (e.g., core_identity)
- `get_entities_created_since(since)` - Get entities created after a timestamp (recent activity)
- `get_entities_by_signal_threshold(importance_min, recency_min, limit)` - Filter by signal scores
- `get_dismissed_patterns(days_back)` - Get dismissed patterns from last N days
- `get_similar_entities(entity_id, limit, exclude_recent_days)` - Find similar historical entities

**Insight management**:
- `create_insight(insight_data)` - Create new insight, return ID
- `get_recent_insights(limit, status)` - Get recent insights, optionally filtered by status
- `update_insight_status(insight_id, status)` - Update insight status

**Helper**:
- `get_entity_by_title(title, entity_type)` - Case-insensitive title search

### 2. Mentor Agent (mentor.py)

Created `apps/ai-core/agents/mentor.py` (600+ lines):

**Core class**: `Mentor`
- Initializes with Anthropic client (Claude Sonnet 4.5)
- Uses DatabaseService for all queries
- Generates 3 daily insight types

**Main method**: `generate_daily_digest()`
- Returns dict with delta_watch, connection, prompt insights
- Handles errors gracefully with fallbacks

**Private methods**:
- `_gather_context()` - Queries graph for goals, recent work, high priority, dismissed patterns
- `_generate_delta_watch(context)` - Goal alignment check
- `_generate_connection(context)` - Historical pattern matching
- `_generate_prompt(context)` - Forward-looking question
- `_call_claude(prompt, insight_type)` - Claude API wrapper with markdown stripping
- `_create_fallback_insight(insight_type)` - Fallback when Claude fails
- `_build_delta_watch_prompt(goals, work, dismissed)` - Prompt engineering
- `_build_connection_prompt(connections, dismissed)` - Prompt engineering
- `_build_prompt_card_prompt(work, goals, dismissed)` - Prompt engineering

**Singleton**: `mentor` instance exported for use in FastAPI

### 3. FastAPI Endpoints (main.py)

Added 2 new endpoints to `apps/ai-core/main.py`:

**POST /mentor/generate-digest**
- Manually trigger daily digest generation
- Returns status, insights_generated count, and digest object
- Handles errors with 500 status code

**GET /mentor/status**
- Check Mentor status and recent activity
- Returns ready status, recent insights count, last digest timestamp, model name

### 4. Test Fixtures (mentor_fixtures.py)

Created `apps/ai-core/tests/fixtures/mentor_fixtures.py`:

**Sample data functions**:
- `sample_core_identity()` - 3 goal/value entities
- `sample_recent_work()` - 3 recent work entities with high recency
- `sample_high_priority_entities()` - 3 high importance entities
- `sample_historical_entities()` - 3 older entities for Connection insights
- `sample_insight_delta_watch()` - Example Delta Watch insight
- `sample_insight_connection()` - Example Connection insight
- `sample_insight_prompt()` - Example Prompt insight
- `sample_dismissed_pattern_delta_watch()` - Dismissed pattern example
- `sample_dismissed_pattern_connection()` - Dismissed pattern example
- `sample_context()` - Complete context object for testing

## Technical Details

### Prompt Engineering

All three insight types use structured prompts with:
- **Context**: User's goals, recent work, historical patterns
- **Dismissed patterns**: Avoid generating similar insights
- **Guidelines**: Specific instructions for tone and content
- **Output format**: Strict JSON schema (no markdown)

**JSON Response Schema**:
```json
{
    "title": "Brief headline (5-8 words)",
    "body": "2-3 sentence insight",
    "driver_entity_ids": ["uuid1", "uuid2"],
    "alignment_score": 0.85  // Delta Watch only
}
```

### Error Handling

- All database methods use try/catch with logging
- Claude API failures fall back to generic insights
- Database errors return empty arrays (graceful degradation)
- All errors logged with exc_info=True for debugging

### Markdown Stripping

Claude sometimes returns markdown code blocks despite instructions. The `_call_claude` method strips:
- Opening/closing triple backticks
- `json` language identifier
- Extra whitespace

## Files Modified/Created

### Modified (2 files)
1. ✅ `apps/ai-core/services/database.py` (+160 lines)
   - Added 9 new methods for Mentor queries
   - Added logging import
   - All methods include error handling

2. ✅ `apps/ai-core/main.py` (+59 lines)
   - Added Mentor import
   - Added 2 new endpoints
   - Integrated with existing FastAPI app

### Created (2 files)
3. ✅ `apps/ai-core/agents/mentor.py` (600+ lines)
   - Complete Mentor agent implementation
   - 3 insight generators with prompt engineering
   - Fallback mechanisms

4. ✅ `apps/ai-core/tests/fixtures/mentor_fixtures.py` (350+ lines)
   - Comprehensive test fixtures
   - Sample data for all entity types
   - Example insights and dismissed patterns

## Success Criteria ✅

- [x] Mentor agent can be initialized
- [x] Database methods return expected data structures
- [x] Can manually trigger digest generation via API
- [x] Fallback insights work when Claude unavailable
- [x] All Python syntax valid (verified with py_compile)
- [x] Comprehensive test fixtures available
- [x] Error handling throughout
- [x] Logging statements for debugging

## How to Test

### 1. Start the AI Core server

```bash
pnpm run dev:web
# Or directly:
cd apps/ai-core
uvicorn main:app --reload --port 8000
```

### 2. Check Mentor status

```bash
curl http://localhost:8000/mentor/status
```

Expected response:
```json
{
    "status": "ready",
    "recent_insights_count": 0,
    "last_digest": null,
    "model": "claude-sonnet-4-5"
}
```

### 3. Generate digest manually

```bash
curl -X POST http://localhost:8000/mentor/generate-digest
```

Expected response:
```json
{
    "status": "success",
    "insights_generated": 0-3,
    "digest": {
        "delta_watch": { ... } or null,
        "connection": { ... } or null,
        "prompt": { ... } or null
    }
}
```

**Note**: With empty database, insights will be null or use fallbacks.

### 4. Add test data for meaningful insights

To get real insights, you need:
1. **Core identity entities** (goals/values) with `tags: ["goal"]` in metadata
2. **Recent entities** (created in last 24 hours) with signals
3. **Historical entities** (30+ days old) for Connection insights

Create via Quick Capture UI at http://localhost:3110

## Known Limitations

### 1. Embeddings Not Used
- `get_similar_entities()` uses simple type matching (same entity type)
- True semantic similarity requires embeddings (Anthropic doesn't provide)
- This is acceptable for Phase 2 MVP

### 2. In-Memory Only
- Mentor agent is stateless
- No caching of context between digest generations
- Each digest generation queries database fresh

### 3. Requires Manual Trigger
- Phase 6 will add scheduled generation (7 AM daily)
- For now, must call `/mentor/generate-digest` manually

### 4. No User Feedback Yet
- Insights are generated but feedback loop not connected
- Phase 4 will implement Acknowledge/Dismiss handling

## What's Next: Phase 3

**Prompt Engineering Refinement** (2 days)

1. Test with real data
2. Refine prompts based on output quality
3. Add more sophisticated pattern matching
4. Improve dismissed pattern detection
5. Fine-tune insight relevance

## Dependencies

### Python Packages (already in requirements.txt)
- `anthropic` - Claude API client
- `supabase` - Database client
- `fastapi` - Web framework
- `pydantic` - Settings management

### Database
- `dismissed_patterns` table (Phase 1 migration)
- Mentor indexes (Phase 1 migration)

### Environment Variables
- `ANTHROPIC_API_KEY` - Must be set
- `SUPABASE_URL` - Already configured
- `SUPABASE_SERVICE_ROLE_KEY` - Already configured

## Notes

- All code follows existing patterns (Archivist agent structure)
- Logging uses same format as Archivist
- Database methods are consistent with existing ones
- Error handling matches project standards
- No breaking changes to existing code

---

**Phase 2 Status**: ✅ COMPLETE

**Ready for**: Phase 3 (Prompt Engineering) or Phase 4 (Feedback Processor)

**Estimated completion**: Phase 2 completed in ~1 hour (ahead of 2-day estimate)
