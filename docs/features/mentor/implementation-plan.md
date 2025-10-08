# Mentor Agent & Feedback Loop: Implementation Plan

## Overview

**Goal**: Build the Mentor agent that generates daily insights from the knowledge graph, and implement the feedback loop that allows the system to learn from user responses.

**Status**: Not started (prerequisite: Archivist is complete ✅)

**Estimated Timeline**: 3-4 weeks

---

## Architecture Overview

### Components to Build

1. **Mentor Agent** (Python) - Generates insights from knowledge graph
2. **Daily Digest UI** (Next.js) - Displays insights with Acknowledge/Dismiss buttons
3. **Feedback API** (Next.js API routes) - Handles user feedback
4. **Feedback Processor** (Python) - Updates signals based on feedback
5. **Insights API** (Next.js API routes) - Queries and manages insights

### Data Flow

```
Morning (7 AM):
  Mentor Agent → Analyzes graph → Generates 3 insights → Stores in DB

User opens app:
  Daily Digest UI → Fetches open insights → Displays cards

User clicks Acknowledge/Dismiss:
  Frontend → Feedback API → AI Core → Updates signals → Records patterns

Next morning:
  Mentor Agent → Checks signals + dismissed patterns → Generates adapted insights
```

---

## Phase 1: Database Setup (Day 1)

### 1.1 Create Dismissed Patterns Table

**File**: `docs/migrations/create_dismissed_patterns_table.sql`

```sql
-- Table to store patterns user has dismissed
CREATE TABLE dismissed_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_type TEXT NOT NULL,           -- 'Delta Watch', 'Connection', 'Prompt'
    driver_entity_types TEXT[],           -- ['feature', 'project', 'person']
    pattern_signature JSONB,              -- Flexible pattern data
    dismissed_count INTEGER DEFAULT 1,    -- How many times dismissed
    first_dismissed_at TIMESTAMPTZ DEFAULT NOW(),
    last_dismissed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying patterns by type
CREATE INDEX idx_dismissed_patterns_type ON dismissed_patterns(insight_type);

-- Index for querying by timestamp
CREATE INDEX idx_dismissed_patterns_last_dismissed ON dismissed_patterns(last_dismissed_at DESC);
```

### 1.2 Add Indexes to Existing Tables

**File**: `docs/migrations/add_mentor_indexes.sql`

```sql
-- Index for fetching open insights
CREATE INDEX IF NOT EXISTS idx_insight_status ON insight(status);

-- Index for fetching recent insights
CREATE INDEX IF NOT EXISTS idx_insight_created_at ON insight(created_at DESC);

-- Index for entity lookups with signals (for Mentor queries)
CREATE INDEX IF NOT EXISTS idx_signal_importance_recency
ON signal(importance DESC, recency DESC);

-- Index for finding core identity entities (user's values/goals)
CREATE INDEX IF NOT EXISTS idx_entity_type_metadata
ON entity(type) WHERE type = 'core_identity';
```

### Success Criteria
- ✅ `dismissed_patterns` table created
- ✅ All indexes added
- ✅ Can insert/query patterns successfully
- ✅ Migration tested in development

---

## Phase 2: Mentor Agent - Core Infrastructure (Days 2-3)

### 2.1 Create Mentor Agent File

**File**: `apps/ai-core/agents/mentor.py`

```python
from anthropic import Anthropic
from datetime import datetime, timedelta
from services.database import db
from config import settings
import logging
import json

logger = logging.getLogger(__name__)

class Mentor:
    """
    The Mentor agent generates insights from the knowledge graph
    by analyzing patterns, connections, and user priorities.
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-5"

    def generate_daily_digest(self) -> dict:
        """
        Generate 3 insight cards for daily digest

        Returns:
            {
                'delta_watch': insight_dict,
                'connection': insight_dict,
                'prompt': insight_dict
            }
        """
        logger.info("Generating daily digest...")

        # Gather context from knowledge graph
        context = self._gather_context()

        # Generate each card type
        delta_watch = self._generate_delta_watch(context)
        connection = self._generate_connection(context)
        prompt = self._generate_prompt(context)

        return {
            'delta_watch': delta_watch,
            'connection': connection,
            'prompt': prompt
        }

    def _gather_context(self) -> dict:
        """Gather relevant context from knowledge graph"""

        # Get user's core identity (values, goals, mission)
        core_identity = db.get_entities_by_type('core_identity')

        # Get recent activity (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_entities = db.get_entities_created_since(yesterday)

        # Get high-importance entities
        high_priority = db.get_entities_by_signal_threshold(
            importance_min=0.7,
            limit=20
        )

        # Get recent high-recency entities (active work)
        recent_work = db.get_entities_by_signal_threshold(
            recency_min=0.8,
            limit=20
        )

        # Get dismissed patterns (to avoid)
        dismissed = db.get_dismissed_patterns(days_back=30)

        return {
            'core_identity': core_identity,
            'recent_entities': recent_entities,
            'high_priority': high_priority,
            'recent_work': recent_work,
            'dismissed_patterns': dismissed
        }

    def _generate_delta_watch(self, context: dict) -> dict:
        """Generate Delta Watch insight (goal alignment check)"""

        # Extract stated goals from core identity
        goals = [e for e in context['core_identity']
                if 'goal' in e.get('metadata', {}).get('tags', [])]

        # Get what user actually worked on
        actual_work = context['recent_work']

        # Build prompt for Claude
        prompt = self._build_delta_watch_prompt(goals, actual_work, context['dismissed_patterns'])

        # Call Claude
        response = self._call_claude(prompt, "delta_watch")

        # Parse and store insight
        insight_data = json.loads(response)
        insight_id = db.create_insight({
            'title': f"Delta Watch: {insight_data['title']}",
            'body': insight_data['body'],
            'drivers': {
                'entity_ids': insight_data['driver_entity_ids'],
                'edge_ids': []
            },
            'status': 'open'
        })

        return {'id': insight_id, **insight_data}

    def _generate_connection(self, context: dict) -> dict:
        """Generate Connection insight (historical patterns)"""

        # Get recent work and search for similar past work
        recent = context['recent_entities'][:5]  # Last 5 entities

        # For each recent entity, find semantically similar historical entities
        # (This would use embeddings if they were enabled)
        historical_connections = []
        for entity in recent:
            similar = db.get_similar_entities(
                entity_id=entity['id'],
                limit=3,
                exclude_recent_days=30  # Only historical
            )
            if similar:
                historical_connections.append({
                    'current': entity,
                    'historical': similar
                })

        if not historical_connections:
            return None  # No connection found

        # Build prompt
        prompt = self._build_connection_prompt(historical_connections, context['dismissed_patterns'])

        # Call Claude
        response = self._call_claude(prompt, "connection")

        # Parse and store
        insight_data = json.loads(response)
        insight_id = db.create_insight({
            'title': f"Connection: {insight_data['title']}",
            'body': insight_data['body'],
            'drivers': {
                'entity_ids': insight_data['driver_entity_ids'],
                'edge_ids': insight_data.get('driver_edge_ids', [])
            },
            'status': 'open'
        })

        return {'id': insight_id, **insight_data}

    def _generate_prompt(self, context: dict) -> dict:
        """Generate Prompt insight (forward-looking question)"""

        # Use recent work to generate a challenging question
        recent_work = context['recent_work']
        goals = [e for e in context['core_identity']
                if 'goal' in e.get('metadata', {}).get('tags', [])]

        # Build prompt
        prompt = self._build_prompt_card_prompt(recent_work, goals, context['dismissed_patterns'])

        # Call Claude
        response = self._call_claude(prompt, "prompt")

        # Parse and store
        insight_data = json.loads(response)
        insight_id = db.create_insight({
            'title': f"Prompt: {insight_data['title']}",
            'body': insight_data['body'],
            'drivers': {
                'entity_ids': insight_data['driver_entity_ids'],
                'edge_ids': []
            },
            'status': 'open'
        })

        return {'id': insight_id, **insight_data}

    def _call_claude(self, prompt: str, insight_type: str) -> str:
        """Make API call to Claude"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.7,  # Higher for creative insights
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            content = response.content[0].text.strip()

            # Strip markdown if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            return content

        except Exception as e:
            logger.error(f"Error calling Claude for {insight_type}: {e}")
            return self._fallback_insight(insight_type)

    def _fallback_insight(self, insight_type: str) -> str:
        """Return fallback insight if Claude fails"""
        fallbacks = {
            'delta_watch': {
                'title': 'Daily Check-In',
                'body': 'How does today\'s work align with your stated goals?',
                'driver_entity_ids': []
            },
            'connection': {
                'title': 'Past Learning',
                'body': 'What past experiences might inform today\'s challenges?',
                'driver_entity_ids': []
            },
            'prompt': {
                'title': 'Key Question',
                'body': 'What\'s the most important question you should ask today?',
                'driver_entity_ids': []
            }
        }
        return json.dumps(fallbacks.get(insight_type, {}))

    def _build_delta_watch_prompt(self, goals, actual_work, dismissed_patterns) -> str:
        """Build prompt for Delta Watch card"""
        # TODO: Implement prompt engineering
        pass

    def _build_connection_prompt(self, connections, dismissed_patterns) -> str:
        """Build prompt for Connection card"""
        # TODO: Implement prompt engineering
        pass

    def _build_prompt_card_prompt(self, recent_work, goals, dismissed_patterns) -> str:
        """Build prompt for Prompt card"""
        # TODO: Implement prompt engineering
        pass

# Singleton instance
mentor = Mentor()
```

### 2.2 Add Mentor Endpoints to FastAPI

**File**: `apps/ai-core/main.py` (add to existing file)

```python
from agents.mentor import mentor

@app.post("/mentor/generate-digest")
async def generate_daily_digest():
    """Manually trigger daily digest generation"""
    try:
        digest = mentor.generate_daily_digest()
        return {
            "status": "success",
            "insights_generated": 3,
            "digest": digest
        }
    except Exception as e:
        logger.error(f"Error generating digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mentor/status")
async def mentor_status():
    """Check Mentor status and recent activity"""
    recent_insights = db.get_recent_insights(limit=10)
    return {
        "status": "ready",
        "recent_insights_count": len(recent_insights),
        "last_digest": recent_insights[0]['created_at'] if recent_insights else None
    }
```

### 2.3 Add Database Methods

**File**: `apps/ai-core/services/database.py` (add to existing)

```python
def get_entities_by_type(self, entity_type: str) -> List[Dict]:
    """Get all entities of a specific type"""
    response = self.client.table('entity') \
        .select('*') \
        .eq('type', entity_type) \
        .execute()
    return response.data

def get_entities_created_since(self, since: datetime) -> List[Dict]:
    """Get entities created after a specific time"""
    response = self.client.table('entity') \
        .select('*') \
        .gte('created_at', since.isoformat()) \
        .order('created_at', desc=True) \
        .execute()
    return response.data

def get_entities_by_signal_threshold(
    self,
    importance_min: float = None,
    recency_min: float = None,
    limit: int = 20
) -> List[Dict]:
    """Get entities with signals above thresholds"""
    query = self.client.table('entity').select(
        'id, title, type, summary, metadata, '
        'signal(importance, recency, novelty)'
    )

    # Filter by signal thresholds (requires RLS or service role)
    # Note: Supabase doesn't support filtering on joined tables directly
    # We'll fetch and filter in Python

    response = query.limit(limit * 3).execute()  # Over-fetch
    entities = response.data

    # Filter based on signals
    filtered = []
    for entity in entities:
        signal = entity.get('signal')
        if not signal:
            continue

        if importance_min and signal['importance'] < importance_min:
            continue
        if recency_min and signal['recency'] < recency_min:
            continue

        filtered.append(entity)

    return filtered[:limit]

def get_dismissed_patterns(self, days_back: int = 30) -> List[Dict]:
    """Get dismissed patterns from last N days"""
    cutoff = datetime.now() - timedelta(days=days_back)

    response = self.client.table('dismissed_patterns') \
        .select('*') \
        .gte('last_dismissed_at', cutoff.isoformat()) \
        .order('last_dismissed_at', desc=True) \
        .execute()

    return response.data

def create_insight(self, insight_data: dict) -> str:
    """Create new insight, return ID"""
    response = self.client.table('insight') \
        .insert(insight_data) \
        .execute()
    return response.data[0]['id']

def get_recent_insights(self, limit: int = 10) -> List[Dict]:
    """Get recent insights"""
    response = self.client.table('insight') \
        .select('*') \
        .order('created_at', desc=True) \
        .limit(limit) \
        .execute()
    return response.data

def get_similar_entities(
    self,
    entity_id: str,
    limit: int = 5,
    exclude_recent_days: int = 30
) -> List[Dict]:
    """Find similar entities (placeholder - needs embeddings)"""
    # TODO: Implement with vector similarity when embeddings work
    # For now, use simple heuristic: same type, older than X days

    entity = self.get_entity_by_id(entity_id)
    cutoff = datetime.now() - timedelta(days=exclude_recent_days)

    response = self.client.table('entity') \
        .select('*') \
        .eq('type', entity['type']) \
        .lt('created_at', cutoff.isoformat()) \
        .neq('id', entity_id) \
        .limit(limit) \
        .execute()

    return response.data
```

### Success Criteria
- ✅ Mentor agent can be initialized
- ✅ Database methods return expected data
- ✅ Can manually trigger digest generation via API
- ✅ Fallback insights work when Claude fails

---

## Phase 3: Prompt Engineering (Days 4-5)

### 3.1 Delta Watch Prompt

**Goal**: Compare stated goals with actual work, detect misalignment

```python
def _build_delta_watch_prompt(self, goals, actual_work, dismissed_patterns) -> str:
    goal_list = [f"- {g['title']}: {g['summary']}" for g in goals]
    work_list = [f"- {w['title']} ({w['type']}): {w['summary']}" for w in actual_work]

    # Build dismissed pattern context
    dismissed_context = ""
    delta_dismissed = [p for p in dismissed_patterns if p['insight_type'] == 'Delta Watch']
    if delta_dismissed:
        dismissed_context = f"\n\nIMPORTANT: The user previously dismissed these Delta Watch patterns - avoid similar insights:\n"
        for p in delta_dismissed[:3]:
            dismissed_context += f"- {p['pattern_signature']}\n"

    prompt = f"""You are analyzing a user's stated goals versus their actual work to detect potential misalignment.

User's Stated Goals (from core identity):
{chr(10).join(goal_list) if goal_list else "- No explicit goals stated"}

Actual Work (last 24 hours):
{chr(10).join(work_list) if work_list else "- No recent activity"}
{dismissed_context}

Task: Generate a "Delta Watch" insight that either:
1. Celebrates alignment (goals and work match)
2. Highlights drift (working on things not in goals - ask if pivot or distraction)
3. Suggests missing focus (goals stated but no work toward them)

Guidelines:
- Be specific and actionable
- Reference actual entity names from the data
- Don't moralize - be curious and supportive
- Keep it under 3 sentences
- If alignment is good, celebrate it briefly

Return ONLY a JSON object:
{{
    "title": "Brief headline (5-8 words)",
    "body": "2-3 sentence insight with specific examples",
    "driver_entity_ids": ["uuid1", "uuid2"],  // Entities that triggered this insight
    "alignment_score": 0.85,  // 0.0 (total drift) to 1.0 (perfect alignment)
}}"""

    return prompt
```

### 3.2 Connection Prompt

**Goal**: Surface relevant historical context

```python
def _build_connection_prompt(self, connections, dismissed_patterns) -> str:
    connection_list = []
    for conn in connections[:3]:  # Max 3 connections
        current = conn['current']
        historical = conn['historical'][0]  # Best match
        connection_list.append(
            f"Current: {current['title']} ({current['type']})\n"
            f"  → Historical: {historical['title']} from {historical['created_at'][:10]}"
        )

    dismissed_context = ""
    conn_dismissed = [p for p in dismissed_patterns if p['insight_type'] == 'Connection']
    if conn_dismissed:
        dismissed_context = f"\n\nIMPORTANT: User dismissed these Connection patterns - avoid:\n"
        for p in conn_dismissed[:3]:
            dismissed_context += f"- {p['pattern_signature']}\n"

    prompt = f"""You are finding valuable connections between current work and historical context.

Potential Connections:
{chr(10).join(connection_list)}
{dismissed_context}

Task: Create a "Connection" insight that shows how historical work informs current challenges.

Guidelines:
- Focus on actionable insights from the past
- Be specific about what was learned and how it applies
- Keep it under 3 sentences
- Make the connection clear and valuable

Return ONLY a JSON object:
{{
    "title": "Brief headline (5-8 words)",
    "body": "2-3 sentence insight connecting past to present",
    "driver_entity_ids": ["current_uuid", "historical_uuid"],
    "driver_edge_ids": [],  // If there are relevant edges
    "relevance_score": 0.75  // 0.0 (weak connection) to 1.0 (strong)
}}"""

    return prompt
```

### 3.3 Prompt Card Prompt

**Goal**: Generate forward-looking question

```python
def _build_prompt_card_prompt(self, recent_work, goals, dismissed_patterns) -> str:
    work_summary = [f"- {w['title']}: {w['summary']}" for w in recent_work[:5]]
    goal_summary = [f"- {g['title']}" for g in goals]

    dismissed_context = ""
    prompt_dismissed = [p for p in dismissed_patterns if p['insight_type'] == 'Prompt']
    if prompt_dismissed:
        dismissed_context = f"\n\nIMPORTANT: User dismissed these Prompt types - avoid:\n"
        for p in prompt_dismissed[:3]:
            dismissed_context += f"- {p['pattern_signature']}\n"

    prompt = f"""You are a thought partner helping the user think critically about their work.

Recent Work:
{chr(10).join(work_summary)}

Goals:
{chr(10).join(goal_summary) if goal_summary else "- No explicit goals"}
{dismissed_context}

Task: Generate a challenging, forward-looking question that:
1. Pushes the user to think deeper about their current work
2. Challenges assumptions or exposes blindspots
3. Connects to their larger goals and values
4. Is specific and actionable

Guidelines:
- Ask ONE powerful question
- Make it open-ended (not yes/no)
- Ground it in their actual work
- Be challenging but supportive

Return ONLY a JSON object:
{{
    "title": "The Question (as headline)",
    "body": "1-2 sentence setup explaining why this question matters now",
    "driver_entity_ids": ["uuid1", "uuid2"],  // Entities this question relates to
}}"""

    return prompt
```

### Success Criteria
- ✅ Prompts generate coherent, relevant insights
- ✅ Insights reference actual entities from user's graph
- ✅ Dismissed patterns are avoided
- ✅ JSON parsing succeeds reliably

---

## Phase 4: Feedback Processor (Days 6-7)

### 4.1 Create Feedback Processor

**File**: `apps/ai-core/agents/feedback_processor.py`

```python
from services.database import db
from processors.signal_scorer import SignalScorer
from typing import List, Dict
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class FeedbackProcessor:
    """
    Processes user feedback (Acknowledge/Dismiss) and adjusts
    the knowledge graph accordingly.
    """

    def __init__(self):
        self.signal_scorer = SignalScorer()

    def process_acknowledge(self, insight_id: str) -> Dict:
        """
        User acknowledged an insight as valuable

        Actions:
        1. Boost importance scores for driver entities
        2. Refresh recency scores
        3. Update insight status
        """
        try:
            # Get insight and its drivers
            insight = db.get_insight_by_id(insight_id)
            driver_entity_ids = insight['drivers'].get('entity_ids', [])

            logger.info(f"Processing acknowledge for insight {insight_id}")

            # Boost signals for each driver entity
            entities_updated = []
            for entity_id in driver_entity_ids:
                updated = self._adjust_entity_signals(
                    entity_id,
                    importance_delta=0.1,
                    recency_boost=True
                )
                entities_updated.append(updated)

            # Update insight status
            db.update_insight_status(insight_id, 'acknowledged')

            logger.info(f"Acknowledged: Boosted {len(entities_updated)} entity signals")

            return {
                'status': 'success',
                'action': 'acknowledge',
                'entities_updated': len(entities_updated),
                'signal_changes': entities_updated
            }

        except Exception as e:
            logger.error(f"Error processing acknowledge: {e}")
            raise

    def process_dismiss(self, insight_id: str) -> Dict:
        """
        User dismissed an insight as not valuable

        Actions:
        1. Lower importance scores for driver entities
        2. Record pattern to avoid in future
        3. Update insight status
        """
        try:
            # Get insight and its drivers
            insight = db.get_insight_by_id(insight_id)
            driver_entity_ids = insight['drivers'].get('entity_ids', [])

            logger.info(f"Processing dismiss for insight {insight_id}")

            # Lower signals for each driver entity
            entities_updated = []
            for entity_id in driver_entity_ids:
                updated = self._adjust_entity_signals(
                    entity_id,
                    importance_delta=-0.1,
                    recency_boost=False
                )
                entities_updated.append(updated)

            # Record dismissed pattern
            pattern = self._extract_pattern(insight)
            db.record_dismissed_pattern(pattern)

            # Update insight status
            db.update_insight_status(insight_id, 'dismissed')

            logger.info(f"Dismissed: Lowered {len(entities_updated)} entity signals")

            return {
                'status': 'success',
                'action': 'dismiss',
                'entities_updated': len(entities_updated),
                'pattern_recorded': pattern,
                'signal_changes': entities_updated
            }

        except Exception as e:
            logger.error(f"Error processing dismiss: {e}")
            raise

    def _adjust_entity_signals(
        self,
        entity_id: str,
        importance_delta: float,
        recency_boost: bool
    ) -> Dict:
        """Adjust signal scores for an entity"""

        signal = db.get_signal_by_entity_id(entity_id)

        if not signal:
            logger.warning(f"No signal found for entity {entity_id}")
            return {'entity_id': entity_id, 'error': 'no_signal'}

        # Calculate new importance (clamped to [0.0, 1.0])
        old_importance = signal['importance']
        new_importance = max(0.0, min(1.0, old_importance + importance_delta))

        updates = {'importance': new_importance}

        # Boost recency if acknowledged
        if recency_boost:
            entity = db.get_entity_by_id(entity_id)
            new_recency = self.signal_scorer.calculate_recency(
                entity['created_at'],
                datetime.now()
            )
            updates['recency'] = new_recency
            updates['last_surfaced_at'] = datetime.now()

        # Apply updates
        db.update_signal(entity_id, updates)

        return {
            'entity_id': entity_id,
            'importance': {'old': old_importance, 'new': new_importance},
            'recency_boosted': recency_boost
        }

    def _extract_pattern(self, insight: Dict) -> Dict:
        """Extract dismissal pattern from insight"""

        # Get entity types of drivers
        driver_ids = insight['drivers'].get('entity_ids', [])
        driver_types = []

        for entity_id in driver_ids:
            entity = db.get_entity_by_id(entity_id)
            if entity:
                driver_types.append(entity['type'])

        # Extract insight type from title
        title = insight.get('title', '')
        insight_type = 'Unknown'
        if 'Delta Watch' in title:
            insight_type = 'Delta Watch'
        elif 'Connection' in title:
            insight_type = 'Connection'
        elif 'Prompt' in title:
            insight_type = 'Prompt'

        # Build pattern signature
        pattern_signature = {
            'insight_type': insight_type,
            'driver_types': list(set(driver_types)),
            'title_keywords': self._extract_keywords(title),
            'dismissed_at': datetime.now().isoformat()
        }

        return {
            'insight_type': insight_type,
            'driver_entity_types': driver_types,
            'pattern_signature': pattern_signature
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key terms from text"""
        # Simple keyword extraction
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        words = text.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        return keywords[:5]  # Top 5 keywords

# Singleton instance
feedback_processor = FeedbackProcessor()
```

### 4.2 Add Feedback Endpoints to FastAPI

**File**: `apps/ai-core/main.py` (add to existing)

```python
from agents.feedback_processor import feedback_processor

@app.post("/feedback/acknowledge")
async def acknowledge_insight(request: dict):
    """User acknowledged an insight as valuable"""
    insight_id = request.get('insight_id')

    if not insight_id:
        raise HTTPException(status_code=400, detail="insight_id required")

    result = feedback_processor.process_acknowledge(insight_id)
    return result

@app.post("/feedback/dismiss")
async def dismiss_insight(request: dict):
    """User dismissed an insight as not valuable"""
    insight_id = request.get('insight_id')

    if not insight_id:
        raise HTTPException(status_code=400, detail="insight_id required")

    result = feedback_processor.process_dismiss(insight_id)
    return result
```

### 4.3 Add Database Methods

**File**: `apps/ai-core/services/database.py` (add to existing)

```python
def update_insight_status(self, insight_id: str, status: str):
    """Update insight status"""
    self.client.table('insight') \
        .update({'status': status}) \
        .eq('id', insight_id) \
        .execute()

def record_dismissed_pattern(self, pattern: dict):
    """Record or update dismissed pattern"""
    # Check if similar pattern exists
    existing = self.client.table('dismissed_patterns') \
        .select('*') \
        .eq('insight_type', pattern['insight_type']) \
        .execute()

    # If exists, increment count
    if existing.data:
        # Simple approach: create new record
        # Advanced: check similarity and update count
        pass

    # Insert new pattern
    self.client.table('dismissed_patterns') \
        .insert({
            'insight_type': pattern['insight_type'],
            'driver_entity_types': pattern['driver_entity_types'],
            'pattern_signature': pattern['pattern_signature']
        }) \
        .execute()
```

### Success Criteria
- ✅ Acknowledge endpoint boosts entity signals
- ✅ Dismiss endpoint lowers entity signals
- ✅ Patterns are recorded in dismissed_patterns table
- ✅ Signal changes are logged and returned

---

## Phase 5: Daily Digest UI (Days 8-10)

### 5.1 Create Insights API Route

**File**: `apps/web/app/api/insights/route.ts`

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get('status') || 'open';

  try {
    const { data: insights, error } = await supabase
      .from('insight')
      .select('*')
      .eq('status', status)
      .order('created_at', { ascending: false })
      .limit(10);

    if (error) throw error;

    return Response.json(insights);
  } catch (error) {
    console.error('Error fetching insights:', error);
    return Response.json({ error: 'Failed to fetch insights' }, { status: 500 });
  }
}
```

### 5.2 Create Feedback API Routes

**File**: `apps/web/app/api/feedback/acknowledge/[id]/route.ts`

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const AI_CORE_URL = process.env.AI_CORE_URL || 'http://localhost:8000';

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  const insightId = params.id;

  try {
    // Update insight status in DB
    const { error: updateError } = await supabase
      .from('insight')
      .update({ status: 'acknowledged' })
      .eq('id', insightId);

    if (updateError) throw updateError;

    // Call AI Core to update signals
    const response = await fetch(`${AI_CORE_URL}/feedback/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ insight_id: insightId })
    });

    if (!response.ok) {
      throw new Error('AI Core feedback processing failed');
    }

    const result = await response.json();

    return Response.json({
      success: true,
      action: 'acknowledged',
      ...result
    });

  } catch (error) {
    console.error('Error acknowledging insight:', error);
    return Response.json(
      { error: 'Failed to acknowledge insight' },
      { status: 500 }
    );
  }
}
```

**File**: `apps/web/app/api/feedback/dismiss/[id]/route.ts`

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const AI_CORE_URL = process.env.AI_CORE_URL || 'http://localhost:8000';

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  const insightId = params.id;

  try {
    // Update insight status in DB
    const { error: updateError } = await supabase
      .from('insight')
      .update({ status: 'dismissed' })
      .eq('id', insightId);

    if (updateError) throw updateError;

    // Call AI Core to update signals and record pattern
    const response = await fetch(`${AI_CORE_URL}/feedback/dismiss`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ insight_id: insightId })
    });

    if (!response.ok) {
      throw new Error('AI Core feedback processing failed');
    }

    const result = await response.json();

    return Response.json({
      success: true,
      action: 'dismissed',
      ...result
    });

  } catch (error) {
    console.error('Error dismissing insight:', error);
    return Response.json(
      { error: 'Failed to dismiss insight' },
      { status: 500 }
    );
  }
}
```

### 5.3 Create Daily Digest Page

**File**: `apps/web/app/digest/page.tsx`

```typescript
import { createClient } from '@supabase/supabase-js';
import { InsightCard } from '@/components/InsightCard';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export default async function DigestPage() {
  const { data: insights } = await supabase
    .from('insight')
    .select('*')
    .eq('status', 'open')
    .order('created_at', { ascending: false })
    .limit(3);

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-2">🌅 Daily Digest</h1>
      <p className="text-gray-600 mb-8">
        {new Date().toLocaleDateString('en-US', {
          weekday: 'long',
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        })}
      </p>

      {!insights || insights.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-600">
            No insights generated yet. The Mentor will create your daily digest soon.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {insights.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}
    </div>
  );
}
```

### 5.4 Create Insight Card Component

**File**: `apps/web/components/InsightCard.tsx`

```typescript
'use client';

import { useState } from 'react';

interface Insight {
  id: string;
  title: string;
  body: string;
  drivers: {
    entity_ids: string[];
    edge_ids: string[];
  };
  status: string;
  created_at: string;
}

export function InsightCard({ insight }: { insight: Insight }) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  // Determine card icon based on insight type
  const getIcon = () => {
    if (insight.title.includes('Delta Watch')) return '📊';
    if (insight.title.includes('Connection')) return '🔗';
    if (insight.title.includes('Prompt')) return '❓';
    return '💡';
  };

  // Get card color based on type
  const getCardStyle = () => {
    if (insight.title.includes('Delta Watch')) return 'border-blue-200 bg-blue-50';
    if (insight.title.includes('Connection')) return 'border-purple-200 bg-purple-50';
    if (insight.title.includes('Prompt')) return 'border-green-200 bg-green-50';
    return 'border-gray-200 bg-white';
  };

  const handleAcknowledge = async () => {
    setIsProcessing(true);

    try {
      const response = await fetch(`/api/feedback/acknowledge/${insight.id}`, {
        method: 'POST'
      });

      if (response.ok) {
        // Insight acknowledged - remove from view
        setIsDismissed(true);
      } else {
        console.error('Failed to acknowledge insight');
      }
    } catch (error) {
      console.error('Error acknowledging insight:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDismiss = async () => {
    setIsProcessing(true);

    try {
      const response = await fetch(`/api/feedback/dismiss/${insight.id}`, {
        method: 'POST'
      });

      if (response.ok) {
        // Insight dismissed - remove from view
        setIsDismissed(true);
      } else {
        console.error('Failed to dismiss insight');
      }
    } catch (error) {
      console.error('Error dismissing insight:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  if (isDismissed) {
    return null; // Hide dismissed cards
  }

  return (
    <div className={`border-2 rounded-lg p-6 transition-all ${getCardStyle()}`}>
      <div className="flex items-start gap-3 mb-4">
        <span className="text-3xl">{getIcon()}</span>
        <div className="flex-1">
          <h3 className="text-lg font-semibold mb-2">{insight.title}</h3>
          <p className="text-gray-700 whitespace-pre-wrap">{insight.body}</p>
        </div>
      </div>

      <div className="flex gap-3 mt-4">
        <button
          onClick={handleAcknowledge}
          disabled={isProcessing}
          className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          👍 Acknowledge
        </button>
        <button
          onClick={handleDismiss}
          disabled={isProcessing}
          className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          👎 Dismiss
        </button>
      </div>

      {isProcessing && (
        <p className="text-sm text-gray-500 mt-2 text-center">Processing...</p>
      )}
    </div>
  );
}
```

### 5.5 Update Navigation

**File**: `apps/web/components/NavBar.tsx` (update existing)

```typescript
// Add "Daily Digest" link to navigation
<Link
  href="/digest"
  className={pathname === '/digest' ? 'text-blue-600 font-semibold' : ''}
>
  🌅 Daily Digest
</Link>
```

### Success Criteria
- ✅ Daily Digest page displays open insights
- ✅ Acknowledge button updates signals and hides card
- ✅ Dismiss button records pattern and hides card
- ✅ UI is responsive and accessible
- ✅ Error handling works gracefully

---

## Phase 6: Scheduled Digest Generation (Days 11-12)

### 6.1 Add Cron Job Support

**Option A: Use APScheduler (Python)**

**File**: `apps/ai-core/main.py` (add to existing)

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Initialize scheduler
scheduler = BackgroundScheduler()

def generate_daily_digest_job():
    """Scheduled job to generate daily digest"""
    try:
        logger.info("Running scheduled daily digest generation...")
        digest = mentor.generate_daily_digest()
        logger.info(f"Daily digest generated: {digest}")
    except Exception as e:
        logger.error(f"Error in scheduled digest generation: {e}")

# Schedule for 7 AM every day
scheduler.add_job(
    generate_daily_digest_job,
    trigger=CronTrigger(hour=7, minute=0),
    id='daily_digest',
    name='Generate Daily Digest'
)

@app.on_event("startup")
async def startup_event():
    # Start Archivist continuous processing
    # ... existing code ...

    # Start scheduler
    if settings.ENVIRONMENT == 'production':
        scheduler.start()
        logger.info("Scheduler started - daily digest will run at 7 AM")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
```

**Option B: External Cron/Cloud Scheduler**

Create endpoint to trigger via external scheduler:

```python
@app.post("/mentor/trigger-daily-digest")
async def trigger_daily_digest(api_key: str):
    """Trigger daily digest via external scheduler"""

    # Simple API key auth
    if api_key != settings.CRON_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    digest = mentor.generate_daily_digest()
    return {
        "status": "success",
        "digest_generated": True,
        "insights_created": 3
    }
```

Then use:
- Railway Cron Jobs
- Vercel Cron
- GitHub Actions with cron trigger
- System crontab

### 6.2 Add Configuration

**File**: `apps/ai-core/config.py` (add to existing)

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Mentor Settings
    ENABLE_DAILY_DIGEST: bool = True
    DAILY_DIGEST_HOUR: int = 7  # 7 AM
    CRON_API_KEY: str = "change-me-in-production"

    # Scheduler Settings
    ENABLE_SCHEDULER: bool = True
```

### Success Criteria
- ✅ Daily digest generates automatically at 7 AM
- ✅ Scheduler starts/stops with app lifecycle
- ✅ Manual trigger endpoint works
- ✅ Errors are logged and don't crash scheduler

---

## Phase 7: Testing & Refinement (Days 13-14)

### 7.1 Create Test Fixtures

**File**: `apps/ai-core/tests/fixtures/mentor_fixtures.py`

```python
def sample_core_identity():
    """Sample core identity entities"""
    return [
        {
            'id': 'uuid-goal-1',
            'type': 'core_identity',
            'title': 'Launch Water OS in Ghana',
            'summary': 'Primary Q4 goal: Launch Water OS pilot in Ghana by December',
            'metadata': {'tags': ['goal', 'Q4'], 'priority': 'high'}
        },
        {
            'id': 'uuid-value-1',
            'type': 'core_identity',
            'title': 'Impact rooted in Equity',
            'summary': 'Core value: Build solutions that address fundamental inequities',
            'metadata': {'tags': ['value'], 'importance': 1.0}
        }
    ]

def sample_recent_work():
    """Sample recent work entities"""
    return [
        {
            'id': 'uuid-work-1',
            'type': 'feature',
            'title': 'Feed Feature for Willow',
            'summary': 'Building feed feature for Willow Education app',
            'created_at': '2025-10-06T14:00:00Z',
            'signal': {'importance': 0.8, 'recency': 1.0, 'novelty': 0.6}
        },
        {
            'id': 'uuid-work-2',
            'type': 'feature',
            'title': 'Feed Feature (continued)',
            'summary': 'More work on Willow feed',
            'created_at': '2025-10-07T10:00:00Z',
            'signal': {'importance': 0.8, 'recency': 1.0, 'novelty': 0.5}
        }
    ]

def sample_insight():
    """Sample generated insight"""
    return {
        'id': 'uuid-insight-1',
        'title': 'Delta Watch: Goal Drift Detected',
        'body': 'Your Q4 goal was to launch Water OS in Ghana, but you\'ve spent 80% of this week on Willow\'s Feed feature. Pivot or distraction?',
        'drivers': {
            'entity_ids': ['uuid-goal-1', 'uuid-work-1', 'uuid-work-2'],
            'edge_ids': []
        },
        'status': 'open',
        'created_at': '2025-10-07T07:00:00Z'
    }
```

### 7.2 Create Integration Tests

**File**: `apps/ai-core/tests/test_mentor.py`

```python
import pytest
from agents.mentor import Mentor
from services.database import db
from tests.fixtures.mentor_fixtures import *

def test_mentor_initialization():
    mentor = Mentor()
    assert mentor.client is not None
    assert mentor.model == "claude-sonnet-4-5"

@pytest.mark.integration
def test_generate_daily_digest(mocker):
    # Mock database calls
    mocker.patch.object(db, 'get_entities_by_type', return_value=sample_core_identity())
    mocker.patch.object(db, 'get_entities_created_since', return_value=sample_recent_work())
    mocker.patch.object(db, 'get_entities_by_signal_threshold', return_value=sample_recent_work())
    mocker.patch.object(db, 'get_dismissed_patterns', return_value=[])
    mocker.patch.object(db, 'create_insight', return_value='uuid-new-insight')

    # Mock Claude API
    mocker.patch.object(Mentor, '_call_claude', return_value='{"title":"Test","body":"Test body","driver_entity_ids":[]}')

    mentor = Mentor()
    digest = mentor.generate_daily_digest()

    assert 'delta_watch' in digest
    assert 'connection' in digest
    assert 'prompt' in digest
    assert digest['delta_watch']['id'] == 'uuid-new-insight'

@pytest.mark.integration
def test_feedback_acknowledge_boosts_signals(mocker):
    from agents.feedback_processor import FeedbackProcessor

    # Mock insight with drivers
    mocker.patch.object(db, 'get_insight_by_id', return_value=sample_insight())

    # Mock signal
    mocker.patch.object(db, 'get_signal_by_entity_id', return_value={
        'importance': 0.5,
        'recency': 0.5,
        'novelty': 0.5
    })

    # Mock entity
    mocker.patch.object(db, 'get_entity_by_id', return_value={
        'created_at': '2025-10-01T00:00:00Z'
    })

    update_spy = mocker.patch.object(db, 'update_signal')

    processor = FeedbackProcessor()
    result = processor.process_acknowledge('uuid-insight-1')

    # Verify signals were updated
    assert result['status'] == 'success'
    assert result['entities_updated'] == 3

    # Check that update_signal was called with boosted values
    calls = update_spy.call_args_list
    for call in calls:
        entity_id, updates = call[0]
        assert updates['importance'] == 0.6  # 0.5 + 0.1
        assert updates['recency'] == 1.0  # Refreshed

@pytest.mark.integration
def test_feedback_dismiss_records_pattern(mocker):
    from agents.feedback_processor import FeedbackProcessor

    mocker.patch.object(db, 'get_insight_by_id', return_value=sample_insight())
    mocker.patch.object(db, 'get_signal_by_entity_id', return_value={'importance': 0.5})
    mocker.patch.object(db, 'update_signal', return_value=None)

    record_spy = mocker.patch.object(db, 'record_dismissed_pattern')

    processor = FeedbackProcessor()
    result = processor.process_dismiss('uuid-insight-1')

    # Verify pattern was recorded
    assert result['status'] == 'success'
    assert record_spy.called

    pattern = record_spy.call_args[0][0]
    assert pattern['insight_type'] == 'Delta Watch'
    assert 'feature' in pattern['driver_entity_types']
```

### 7.3 End-to-End Testing

**Manual Test Flow**:

1. **Setup**: Reset database, create core identity entities
2. **Generate Test Data**: Create recent work entities
3. **Trigger Digest**: Call `/mentor/generate-digest` endpoint
4. **Verify Insights**: Check that 3 insights created in DB
5. **View UI**: Open `/digest` page, see 3 cards
6. **Acknowledge**: Click Acknowledge on Delta Watch card
7. **Check Signals**: Verify importance scores increased
8. **Dismiss**: Click Dismiss on Connection card
9. **Check Patterns**: Verify pattern recorded in dismissed_patterns
10. **Re-Generate**: Trigger digest again next day
11. **Verify Adaptation**: Check that dismissed pattern is avoided

### Success Criteria
- ✅ All unit tests pass
- ✅ Integration tests pass with mocked dependencies
- ✅ End-to-end manual test succeeds
- ✅ Insights are coherent and relevant
- ✅ Feedback loop demonstrably changes future insights

---

## Phase 8: Documentation & Deployment (Day 15)

### 8.1 Update AI Memory Document

**File**: `docs/project-wide-resources/ai-memory.md` (add section)

```markdown
## Feature 4: Mentor Agent & Feedback Loop ✅
**Status**: Complete
**Completed**: 2025-10-XX

### What It Does
The Mentor agent analyzes the knowledge graph daily and generates 3 insight cards:
- Delta Watch: Goal alignment check
- Connection: Historical context
- Prompt: Forward-looking question

Users respond with Acknowledge (valuable) or Dismiss (not valuable), which adjusts signal scores and trains the system.

### Implementation Highlights
1. **Mentor Agent** (`apps/ai-core/agents/mentor.py`)
   - Queries graph for goals, recent work, high-priority entities
   - Uses Claude to generate contextual insights
   - Stores in `insight` table

2. **Feedback Processor** (`apps/ai-core/agents/feedback_processor.py`)
   - Acknowledge: +0.1 importance, refresh recency
   - Dismiss: -0.1 importance, record pattern

3. **Daily Digest UI** (`apps/web/app/digest/page.tsx`)
   - Displays 3 insight cards with Acknowledge/Dismiss buttons
   - Real-time feedback processing

4. **Scheduled Generation**
   - APScheduler runs at 7 AM daily
   - Manual trigger via `/mentor/generate-digest`

### Files Created
- `apps/ai-core/agents/mentor.py`
- `apps/ai-core/agents/feedback_processor.py`
- `apps/web/app/digest/page.tsx`
- `apps/web/components/InsightCard.tsx`
- `apps/web/app/api/insights/route.ts`
- `apps/web/app/api/feedback/acknowledge/[id]/route.ts`
- `apps/web/app/api/feedback/dismiss/[id]/route.ts`
- `docs/migrations/create_dismissed_patterns_table.sql`

### Database Changes
- Added `dismissed_patterns` table
- Added indexes for insight queries

### How to Use
1. Navigate to `/digest` in web app
2. View 3 daily insight cards
3. Click Acknowledge or Dismiss on each
4. System adapts future insights based on feedback
```

### 8.2 Create User Guide

**File**: `docs/features/mentor/user-guide.md`

```markdown
# Mentor Agent User Guide

## What is the Mentor?

The Mentor is your AI thinking partner that analyzes your work patterns and generates daily insights to help you:
- Stay aligned with your goals
- Learn from past experiences
- Ask yourself important questions

## Daily Digest

Every morning at 7 AM, the Mentor generates 3 insight cards:

### 📊 Delta Watch
Compares your stated goals with your actual work.

**Example**: "Your Q4 goal was to launch Water OS, but you spent 80% of this week on Willow features. Pivot or distraction?"

**Purpose**: Keep you honest about goal alignment.

### 🔗 Connection
Surfaces relevant historical context from your past work.

**Example**: "This Water OS challenge relates to a similar problem you solved in Willow 3 months ago. Check the user retention work."

**Purpose**: Help you learn from your own experience.

### ❓ Prompt
Asks a forward-looking question to deepen your thinking.

**Example**: "Based on yesterday's work, what's the most important question you should ask about Ghana market validation?"

**Purpose**: Challenge assumptions and expose blindspots.

## How to Respond

Each insight card has two buttons:

**👍 Acknowledge** - "This is valuable, show me more like this"
- Boosts importance of related topics
- Refreshes recency scores
- More similar insights in future

**👎 Dismiss** - "This is noise, don't show me this again"
- Lowers importance of related topics
- Records pattern to avoid
- Fewer similar insights in future

## The Learning Loop

Your feedback trains the system:

1. You acknowledge Delta Watch about Water OS → Water OS entities get higher importance
2. Next day, Mentor surfaces more Water OS insights
3. You dismiss Connection about old Willow work → Willow importance drops
4. Future Connection cards avoid that pattern

## Tips for Best Results

1. **Be honest with feedback** - Don't acknowledge everything, only what's truly valuable
2. **Review daily** - The system learns from consistent feedback
3. **Look for patterns** - If you dismiss several similar insights, the system will adapt
4. **Give it time** - The Mentor gets smarter as it learns your preferences

## Manual Controls

- **Generate Now**: Trigger digest manually via API: `POST /mentor/generate-digest`
- **View History**: See past insights at `/digest?status=acknowledged`
- **Check Patterns**: Admin can view dismissed patterns in DB

## Troubleshooting

**No insights showing?**
- Check that daily digest ran at 7 AM (logs in AI Core)
- Manually trigger via API endpoint
- Ensure you have entities in your knowledge graph

**Insights not relevant?**
- Dismiss them! The system will learn
- Check your core identity entities (goals, values)
- Add more context by capturing more work

**Same insight repeating?**
- This shouldn't happen - dismissed patterns are recorded
- Report bug if pattern persists after dismissal
```

### 8.3 Deployment Checklist

**File**: `docs/features/mentor/deployment-checklist.md`

```markdown
# Mentor Deployment Checklist

## Pre-Deployment

- [ ] Run all migrations:
  - [ ] `create_dismissed_patterns_table.sql`
  - [ ] `add_mentor_indexes.sql`

- [ ] Set environment variables:
  - [ ] `ENABLE_DAILY_DIGEST=true`
  - [ ] `DAILY_DIGEST_HOUR=7`
  - [ ] `ENABLE_SCHEDULER=true`
  - [ ] `CRON_API_KEY=<secure-random-key>`

- [ ] Test endpoints:
  - [ ] `POST /mentor/generate-digest`
  - [ ] `GET /mentor/status`
  - [ ] `POST /feedback/acknowledge`
  - [ ] `POST /feedback/dismiss`

- [ ] Verify UI:
  - [ ] `/digest` page renders
  - [ ] Insight cards display correctly
  - [ ] Acknowledge/Dismiss buttons work

## Deployment

- [ ] Deploy AI Core with scheduler enabled
- [ ] Deploy Next.js app with new routes
- [ ] Verify scheduler starts on AI Core startup
- [ ] Test manual digest generation

## Post-Deployment

- [ ] Monitor first scheduled run (7 AM next day)
- [ ] Check logs for successful insight generation
- [ ] Verify insights appear in UI
- [ ] Test full feedback loop (acknowledge + dismiss)
- [ ] Monitor signal updates in database

## Monitoring

- [ ] Set up alerts for:
  - [ ] Failed digest generation
  - [ ] Claude API errors
  - [ ] Feedback processing failures

- [ ] Track metrics:
  - [ ] Insights generated per day
  - [ ] Acknowledge vs dismiss ratio
  - [ ] Average response time
  - [ ] Pattern diversity

## Rollback Plan

If issues arise:
1. Disable scheduler: Set `ENABLE_SCHEDULER=false`
2. Restart AI Core
3. Insights will stop generating automatically
4. Manual trigger still available for testing
```

### Success Criteria
- ✅ Documentation complete and accurate
- ✅ User guide is clear and helpful
- ✅ Deployment checklist covers all steps
- ✅ AI memory document updated

---

## Timeline Summary

| Phase | Description | Duration | Dependencies |
|-------|-------------|----------|--------------|
| 1 | Database Setup | 1 day | None |
| 2 | Mentor Core | 2 days | Phase 1 |
| 3 | Prompt Engineering | 2 days | Phase 2 |
| 4 | Feedback Processor | 2 days | Phase 2 |
| 5 | Daily Digest UI | 3 days | Phase 4 |
| 6 | Scheduled Generation | 2 days | Phase 2 |
| 7 | Testing & Refinement | 2 days | Phases 2-6 |
| 8 | Documentation | 1 day | Phase 7 |

**Total**: 15 days (~3 weeks)

---

## Success Metrics

### Functional Metrics
- **Insight Generation Rate**: 3 insights/day, 100% success rate
- **Feedback Processing**: < 500ms response time
- **Signal Adjustment Accuracy**: Correct direction 100% of time
- **Pattern Avoidance**: Dismissed patterns not repeated within 30 days

### User Experience Metrics
- **Insight Relevance**: Target 70%+ acknowledge rate (vs dismiss)
- **Adaptation Speed**: Noticeable change in insights within 3-5 days of feedback
- **Diversity**: No duplicate insight patterns within 7 days

### Technical Metrics
- **API Reliability**: 99%+ uptime for feedback endpoints
- **Scheduler Reliability**: 100% successful scheduled runs
- **Claude API Costs**: < $0.10 per digest (3 insights)

---

## Future Enhancements

### Phase 9: Advanced Insight Types
- **Contradiction Detection**: "You said X last month, but did Y this week"
- **Opportunity Spotting**: "Based on your skills in X, you could apply them to Y"
- **Risk Alerts**: "This goal has had no progress for 2 weeks"

### Phase 10: Personalization
- **Learning Preferences**: Adapt tone, detail level, timing based on engagement
- **Custom Insight Types**: User-defined insight categories
- **Threshold Tuning**: Adjust signal boost/penalty amounts based on effectiveness

### Phase 11: Interactive Insights
- **Follow-up Questions**: Mentor can ask clarifying questions
- **Action Items**: Generate suggested tasks from insights
- **Insight Threads**: Link related insights over time

---

## Open Questions

1. **Insight Timing**: Is 7 AM optimal for all users? Should it be configurable?
2. **Insight Quantity**: Should we always generate 3, or adapt based on available patterns?
3. **Feedback Granularity**: Should users rate insights 1-5 instead of binary acknowledge/dismiss?
4. **Privacy**: If multi-user in future, how do we handle shared vs private insights?

---

## Dependencies

### External Services
- Anthropic API (Claude Sonnet 4.5)
- Supabase (PostgreSQL + pgvector)

### Internal Systems
- Archivist (must be running and processing events)
- Signal system (entities must have signals)
- Core identity entities (goals, values must exist)

### Python Packages
- `apscheduler` - For scheduled digest generation
- `anthropic` - Claude API client

### Configuration
- `ANTHROPIC_API_KEY` - Must be set
- `ENABLE_DAILY_DIGEST` - Feature flag
- `ENABLE_SCHEDULER` - Scheduler enable/disable

---

*Implementation Plan Created: 2025-10-07*
