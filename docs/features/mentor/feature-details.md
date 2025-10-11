# Mentor Agent: Technical Implementation Details

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Schema](#database-schema)
3. [Mentor Agent Implementation](#mentor-agent-implementation)
4. [Feedback Processor Implementation](#feedback-processor-implementation)
5. [Scheduled Generation](#scheduled-generation)
6. [API Reference](#api-reference)
7. [Prompt Engineering](#prompt-engineering)
8. [Signal System](#signal-system)
9. [Pattern Detection & Avoidance](#pattern-detection--avoidance)
10. [UI Components](#ui-components)
11. [Testing](#testing)
12. [Configuration](#configuration)
13. [Deployment](#deployment)
14. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Tech Stack

**Backend**:
- Python 3.13
- FastAPI (async REST API)
- Claude Sonnet 4.5 (Anthropic)
- APScheduler (cron-based scheduling)
- Supabase Python client

**Frontend**:
- Next.js 15 (App Router)
- React 19
- TypeScript
- Server-side rendering for digest page

**Database**:
- Supabase (PostgreSQL)
- Tables: `insight`, `dismissed_patterns`, `entity`, `signal`

### Project Structure

```
apps/ai-core/
├── agents/
│   ├── mentor.py                 # Main Mentor agent (insight generation)
│   └── feedback_processor.py     # Feedback processing logic
│
├── main.py                       # FastAPI app, scheduler setup
├── config.py                     # Environment configuration
│
├── services/
│   └── database.py               # Database queries for Mentor
│
└── tests/
    ├── test_mentor.py            # Unit & integration tests (23 tests)
    ├── test_feedback_loop.py     # E2E manual test
    └── fixtures/
        └── mentor_fixtures.py    # Test data

apps/web/
├── app/
│   ├── digest/
│   │   └── page.tsx              # Daily Digest UI
│   └── api/
│       ├── insights/
│       │   └── route.ts          # GET insights
│       └── feedback/
│           ├── acknowledge/[id]/
│           │   └── route.ts      # POST acknowledge
│           └── dismiss/[id]/
│               └── route.ts      # POST dismiss
│
└── components/
    └── InsightCard.tsx           # Insight card component
```

---

## Database Schema

### insight Table

```sql
CREATE TABLE insight (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  drivers JSONB NOT NULL,           -- { entity_ids: [...], edge_ids: [...] }
  status TEXT NOT NULL,             -- 'open', 'acknowledged', 'dismissed'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_insight_status_created_at ON insight(status, created_at DESC);
```

**Drivers Structure**:
```json
{
  "entity_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "edge_ids": [],
  "insight_type": "Delta Watch",
  "alignment_score": 0.3,
  "metadata": {
    "goals": ["Launch Water OS"],
    "actual_work": ["Willow Feed #1", "Willow Feed #2"]
  }
}
```

### dismissed_patterns Table

```sql
CREATE TABLE dismissed_patterns (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  insight_type TEXT NOT NULL,                    -- 'Delta Watch', 'Connection', 'Prompt'
  driver_entity_types TEXT[] NOT NULL,           -- ['feature', 'project']
  pattern_signature JSONB NOT NULL,              -- Full pattern details
  dismissed_count INTEGER DEFAULT 1,
  first_dismissed_at TIMESTAMPTZ DEFAULT NOW(),
  last_dismissed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dismissed_patterns_type ON dismissed_patterns(insight_type);
CREATE INDEX idx_dismissed_patterns_last_dismissed ON dismissed_patterns(last_dismissed_at DESC);
```

**Pattern Signature Structure**:
```json
{
  "insight_type": "Connection",
  "driver_types": ["feature", "feature"],
  "title_keywords": ["similar", "notification", "pattern"],
  "body_keywords": ["4 months ago", "engagement", "timing"],
  "entity_ids": ["uuid-feature-1", "uuid-feature-2"],
  "dismissed_at": "2025-10-08T09:06:00Z"
}
```

### Performance Indexes

```sql
-- Insight queries
CREATE INDEX idx_insight_status_created_at ON insight(status, created_at DESC);

-- Pattern queries
CREATE INDEX idx_dismissed_patterns_type ON dismissed_patterns(insight_type);
CREATE INDEX idx_dismissed_patterns_last_dismissed ON dismissed_patterns(last_dismissed_at DESC);

-- Signal queries (from Archivist)
CREATE INDEX idx_signal_importance ON signal(importance DESC);
CREATE INDEX idx_signal_recency ON signal(recency DESC);
CREATE INDEX idx_signal_novelty ON signal(novelty DESC);
```

---

## Mentor Agent Implementation

### File: `apps/ai-core/agents/mentor.py`

### Class Structure

```python
from anthropic import Anthropic
from services.database import DatabaseService
from config import settings
import logging

class Mentor:
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-5"
        self.db = DatabaseService()
        self.logger = logging.getLogger(__name__)

    async def generate_daily_digest(self) -> Dict[str, Any]:
        """Main entry point for daily digest generation"""
        pass

    async def gather_context(self) -> Dict[str, Any]:
        """Gather all context from knowledge graph"""
        pass

    async def generate_delta_watch(self, context: Dict) -> Optional[Dict]:
        """Generate Delta Watch insight"""
        pass

    async def generate_connection(self, context: Dict) -> Optional[Dict]:
        """Generate Connection insight"""
        pass

    async def generate_prompt(self, context: Dict) -> Optional[Dict]:
        """Generate Prompt insight"""
        pass

    async def call_claude(self, prompt: str) -> str:
        """Call Claude API with prompt"""
        pass
```

### Main Method: generate_daily_digest()

```python
async def generate_daily_digest(self) -> Dict[str, Any]:
    """
    Generate daily digest with 3 insights.
    Returns summary of insights created.
    """
    try:
        # Step 1: Gather context
        self.logger.info("Gathering context for daily digest...")
        context = await self.gather_context()

        if not context['core_identity']:
            self.logger.warning("No core identity found, using fallback insights")
            return await self._create_fallback_insights()

        # Step 2: Generate 3 insights
        self.logger.info("Generating insights...")
        insights = []

        # Delta Watch
        delta_watch = await self.generate_delta_watch(context)
        if delta_watch:
            insight_id = self.db.create_insight(delta_watch)
            insights.append({'type': 'Delta Watch', 'id': insight_id})

        # Connection
        connection = await self.generate_connection(context)
        if connection:
            insight_id = self.db.create_insight(connection)
            insights.append({'type': 'Connection', 'id': insight_id})

        # Prompt
        prompt_insight = await self.generate_prompt(context)
        if prompt_insight:
            insight_id = self.db.create_insight(prompt_insight)
            insights.append({'type': 'Prompt', 'id': insight_id})

        self.logger.info(f"Daily digest generated: {len(insights)} insights created")

        return {
            'success': True,
            'insights_created': len(insights),
            'insights': insights
        }

    except Exception as e:
        self.logger.error(f"Error generating daily digest: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
```

### Context Gathering

```python
async def gather_context(self) -> Dict[str, Any]:
    """
    Gather all necessary context from knowledge graph.

    Returns:
    {
      'core_identity': [...],      # User's goals, values, mission
      'recent_work': [...],         # Last 24 hours activity
      'high_priority': [...],       # Importance >= 0.7
      'active_work': [...],         # Recency >= 0.8
      'historical_entities': [...], # Older entities for connections
      'dismissed_patterns': [...]   # Patterns to avoid
    }
    """
    self.logger.debug("Gathering context from knowledge graph...")

    # Core identity (goals, values)
    core_identity = self.db.get_entities_by_type('core_identity')

    # Recent work (last 24 hours)
    recent_work = self.db.get_recent_entities(hours=24)

    # High priority entities (importance >= 0.7)
    high_priority = self.db.get_entities_by_signal_threshold(
        signal_type='importance',
        threshold=0.7,
        limit=20
    )

    # Active work (recency >= 0.8)
    active_work = self.db.get_entities_by_signal_threshold(
        signal_type='recency',
        threshold=0.8,
        limit=20
    )

    # Historical entities (older than 30 days for connections)
    historical_entities = self.db.get_historical_entities(
        days_back=30,
        limit=50
    )

    # Dismissed patterns (last 30 days)
    dismissed_patterns = self.db.get_dismissed_patterns(days_back=30)

    context = {
        'core_identity': core_identity,
        'recent_work': recent_work,
        'high_priority': high_priority,
        'active_work': active_work,
        'historical_entities': historical_entities,
        'dismissed_patterns': dismissed_patterns
    }

    self.logger.debug(f"Context gathered: {len(core_identity)} identity, "
                     f"{len(recent_work)} recent, "
                     f"{len(dismissed_patterns)} dismissed patterns")

    return context
```

### Delta Watch Generation

```python
async def generate_delta_watch(self, context: Dict) -> Optional[Dict]:
    """
    Generate Delta Watch insight: goal alignment check.

    Compares stated goals with actual work.
    """
    self.logger.info("Generating Delta Watch insight...")

    # Extract goals from core identity
    goals = []
    for entity in context['core_identity']:
        if 'goal' in entity.get('metadata', {}).get('tags', []):
            goals.append({
                'id': entity['id'],
                'title': entity['title'],
                'summary': entity.get('summary', '')
            })

    if not goals:
        self.logger.warning("No goals found in core identity")
        return None

    # Get actual work (high recency entities)
    actual_work = context['active_work']

    if not actual_work:
        self.logger.warning("No active work found")
        return None

    # Build prompt for Claude
    prompt = self._build_delta_watch_prompt(goals, actual_work, context['dismissed_patterns'])

    # Call Claude
    response = await self.call_claude(prompt)

    # Parse response (expects JSON)
    try:
        insight_data = json.loads(response)

        # Add metadata
        insight_data['drivers'] = {
            'entity_ids': [g['id'] for g in goals] + [w['id'] for w in actual_work[:3]],
            'edge_ids': [],
            'insight_type': 'Delta Watch',
            'metadata': {
                'goals': [g['title'] for g in goals],
                'actual_work': [w['title'] for w in actual_work[:5]]
            }
        }
        insight_data['status'] = 'open'

        return insight_data

    except json.JSONDecodeError as e:
        self.logger.error(f"Failed to parse Delta Watch response: {e}")
        return None
```

### Connection Generation

```python
async def generate_connection(self, context: Dict) -> Optional[Dict]:
    """
    Generate Connection insight: historical context surfacing.

    Finds past work relevant to current challenges.
    """
    self.logger.info("Generating Connection insight...")

    recent_work = context['recent_work']
    historical = context['historical_entities']

    if not recent_work or not historical:
        self.logger.warning("Insufficient data for Connection insight")
        return None

    # For each recent entity, find similar historical entities
    connections = []

    for recent_entity in recent_work[:5]:  # Top 5 recent
        # Simple similarity: same type, different time period
        similar_historical = [
            h for h in historical
            if h['type'] == recent_entity['type']
            and h['id'] != recent_entity['id']
        ]

        if similar_historical:
            connections.append({
                'current': recent_entity,
                'historical': similar_historical[0]  # Take first match
            })

    if not connections:
        self.logger.warning("No connections found between recent and historical work")
        return None

    # Take strongest connection
    connection = connections[0]

    # Build prompt
    prompt = self._build_connection_prompt(
        connection['current'],
        connection['historical'],
        context['dismissed_patterns']
    )

    # Call Claude
    response = await self.call_claude(prompt)

    # Parse response
    try:
        insight_data = json.loads(response)

        insight_data['drivers'] = {
            'entity_ids': [connection['current']['id'], connection['historical']['id']],
            'edge_ids': [],
            'insight_type': 'Connection',
            'metadata': {
                'current_entity': connection['current']['title'],
                'historical_entity': connection['historical']['title'],
                'time_gap_days': (
                    datetime.now() - connection['historical']['created_at']
                ).days
            }
        }
        insight_data['status'] = 'open'

        return insight_data

    except json.JSONDecodeError as e:
        self.logger.error(f"Failed to parse Connection response: {e}")
        return None
```

### Prompt Generation

```python
async def generate_prompt(self, context: Dict) -> Optional[Dict]:
    """
    Generate Prompt insight: forward-looking question.

    Challenges assumptions and exposes blindspots.
    """
    self.logger.info("Generating Prompt insight...")

    recent_work = context['recent_work']
    goals = [e for e in context['core_identity'] if 'goal' in e.get('metadata', {}).get('tags', [])]

    if not recent_work:
        self.logger.warning("No recent work for Prompt generation")
        return None

    # Build prompt for Claude
    prompt = self._build_prompt_prompt(recent_work, goals, context['dismissed_patterns'])

    # Call Claude
    response = await self.call_claude(prompt)

    # Parse response
    try:
        insight_data = json.loads(response)

        insight_data['drivers'] = {
            'entity_ids': [w['id'] for w in recent_work[:3]],
            'edge_ids': [],
            'insight_type': 'Prompt',
            'metadata': {
                'work_analyzed': [w['title'] for w in recent_work[:5]]
            }
        }
        insight_data['status'] = 'open'

        return insight_data

    except json.JSONDecodeError as e:
        self.logger.error(f"Failed to parse Prompt response: {e}")
        return None
```

### Claude API Call

```python
async def call_claude(self, prompt: str) -> str:
    """
    Call Claude API with prompt.
    Returns response text.
    """
    try:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text

        # Strip markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])

        return response_text

    except Exception as e:
        self.logger.error(f"Claude API call failed: {e}")
        raise
```

---

## Feedback Processor Implementation

### File: `apps/ai-core/agents/feedback_processor.py`

### Class Structure

```python
from services.database import DatabaseService
from config import settings
import logging
from typing import Dict, List, Any

class FeedbackProcessor:
    def __init__(self):
        self.db = DatabaseService()
        self.logger = logging.getLogger(__name__)

    async def process_acknowledge(self, insight_id: str) -> Dict[str, Any]:
        """Process acknowledge feedback"""
        pass

    async def process_dismiss(self, insight_id: str) -> Dict[str, Any]:
        """Process dismiss feedback"""
        pass

    def adjust_entity_signals(self, entity_ids: List[str], adjustment: float):
        """Adjust importance scores for entities"""
        pass

    def extract_pattern(self, insight: Dict) -> Dict:
        """Extract pattern signature from insight"""
        pass

    def record_pattern(self, pattern: Dict):
        """Record dismissed pattern in database"""
        pass
```

### Acknowledge Processing

```python
async def process_acknowledge(self, insight_id: str) -> Dict[str, Any]:
    """
    Process acknowledge feedback.

    Actions:
    1. Boost importance of driver entities (+0.1)
    2. Refresh recency to 1.0
    3. Update insight status to 'acknowledged'
    4. Return summary
    """
    self.logger.info(f"Processing acknowledge for insight {insight_id}")

    try:
        # Get insight from database
        insight = self.db.get_insight_by_id(insight_id)

        if not insight:
            return {'success': False, 'error': 'Insight not found'}

        # Extract driver entities
        driver_entity_ids = insight['drivers'].get('entity_ids', [])

        if not driver_entity_ids:
            self.logger.warning(f"No driver entities for insight {insight_id}")

        # Adjust signals
        changes = []
        for entity_id in driver_entity_ids:
            signal = self.db.get_signal_by_entity_id(entity_id)

            if not signal:
                self.logger.warning(f"No signal found for entity {entity_id}")
                continue

            # Boost importance (+0.1, clamped to 1.0)
            old_importance = signal['importance']
            new_importance = min(1.0, old_importance + 0.1)

            # Refresh recency to 1.0
            old_recency = signal['recency']
            new_recency = 1.0

            # Update signal
            self.db.update_signal(entity_id, {
                'importance': new_importance,
                'recency': new_recency,
                'last_surfaced_at': datetime.now()
            })

            changes.append({
                'entity_id': entity_id,
                'importance': {'old': old_importance, 'new': new_importance},
                'recency': {'old': old_recency, 'new': new_recency}
            })

            self.logger.debug(f"Entity {entity_id}: importance {old_importance:.2f} → {new_importance:.2f}")

        # Update insight status
        self.db.update_insight_status(insight_id, 'acknowledged')

        self.logger.info(f"Acknowledged insight {insight_id}: adjusted {len(changes)} entities")

        return {
            'success': True,
            'insight_id': insight_id,
            'entities_adjusted': len(changes),
            'changes': changes
        }

    except Exception as e:
        self.logger.error(f"Error processing acknowledge: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}
```

### Dismiss Processing

```python
async def process_dismiss(self, insight_id: str) -> Dict[str, Any]:
    """
    Process dismiss feedback.

    Actions:
    1. Lower importance of driver entities (-0.1)
    2. Extract pattern signature
    3. Record pattern in dismissed_patterns table
    4. Update insight status to 'dismissed'
    5. Return summary
    """
    self.logger.info(f"Processing dismiss for insight {insight_id}")

    try:
        # Get insight from database
        insight = self.db.get_insight_by_id(insight_id)

        if not insight:
            return {'success': False, 'error': 'Insight not found'}

        # Extract driver entities
        driver_entity_ids = insight['drivers'].get('entity_ids', [])

        # Adjust signals (lower importance)
        changes = []
        for entity_id in driver_entity_ids:
            signal = self.db.get_signal_by_entity_id(entity_id)

            if not signal:
                continue

            # Lower importance (-0.1, clamped to 0.0)
            old_importance = signal['importance']
            new_importance = max(0.0, old_importance - 0.1)

            # Update signal
            self.db.update_signal(entity_id, {
                'importance': new_importance,
                'last_surfaced_at': datetime.now()
            })

            changes.append({
                'entity_id': entity_id,
                'importance': {'old': old_importance, 'new': new_importance}
            })

            self.logger.debug(f"Entity {entity_id}: importance {old_importance:.2f} → {new_importance:.2f}")

        # Extract pattern
        pattern = self.extract_pattern(insight)

        # Record pattern
        self.record_pattern(pattern)

        # Update insight status
        self.db.update_insight_status(insight_id, 'dismissed')

        self.logger.info(f"Dismissed insight {insight_id}: "
                        f"adjusted {len(changes)} entities, "
                        f"recorded pattern {pattern['insight_type']}")

        return {
            'success': True,
            'insight_id': insight_id,
            'entities_adjusted': len(changes),
            'pattern_recorded': True,
            'changes': changes,
            'pattern': pattern
        }

    except Exception as e:
        self.logger.error(f"Error processing dismiss: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}
```

### Pattern Extraction

```python
def extract_pattern(self, insight: Dict) -> Dict:
    """
    Extract pattern signature from dismissed insight.

    Pattern signature includes:
    - insight_type
    - driver_entity_types
    - title_keywords
    - body_keywords
    - entity_ids
    """
    insight_type = insight['drivers'].get('insight_type', 'Unknown')

    # Get driver entity types
    driver_entity_ids = insight['drivers'].get('entity_ids', [])
    driver_entities = [
        self.db.get_entity_by_id(entity_id)
        for entity_id in driver_entity_ids
    ]
    driver_entity_types = [e['type'] for e in driver_entities if e]

    # Extract keywords from title and body
    title_keywords = self.extract_keywords(insight['title'])
    body_keywords = self.extract_keywords(insight['body'])

    pattern_signature = {
        'insight_type': insight_type,
        'driver_types': driver_entity_types,
        'title_keywords': title_keywords[:10],  # Top 10
        'body_keywords': body_keywords[:10],
        'entity_ids': driver_entity_ids,
        'dismissed_at': datetime.now().isoformat()
    }

    return {
        'insight_type': insight_type,
        'driver_entity_types': driver_entity_types,
        'pattern_signature': pattern_signature
    }

def extract_keywords(self, text: str) -> List[str]:
    """
    Extract keywords from text.
    Removes stop words, lowercases, returns unique words.
    """
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                  'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                  'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                  'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
                  'these', 'those', 'you', 'your', 'i', 'my', 'we', 'our'}

    words = text.lower().split()
    keywords = [
        word.strip('.,!?;:()[]{}')
        for word in words
        if word.lower() not in stop_words and len(word) > 3
    ]

    # Return unique keywords
    return list(dict.fromkeys(keywords))  # Preserves order
```

### Pattern Recording

```python
def record_pattern(self, pattern: Dict):
    """
    Record dismissed pattern in database.

    Checks if similar pattern exists (same type + similar keywords).
    If exists: increment dismissed_count
    If new: create new pattern record
    """
    insight_type = pattern['insight_type']
    pattern_signature = pattern['pattern_signature']

    # Check if similar pattern already exists
    existing = self.db.find_similar_pattern(
        insight_type=insight_type,
        driver_types=pattern['driver_entity_types'],
        keywords=pattern_signature['title_keywords']
    )

    if existing:
        # Increment dismissed count
        self.db.increment_pattern_dismissed_count(existing['id'])
        self.logger.debug(f"Incremented existing pattern {existing['id']}")
    else:
        # Create new pattern
        self.db.create_dismissed_pattern({
            'insight_type': insight_type,
            'driver_entity_types': pattern['driver_entity_types'],
            'pattern_signature': pattern_signature,
            'dismissed_count': 1
        })
        self.logger.debug(f"Created new dismissed pattern: {insight_type}")
```

---

## Scheduled Generation

### File: `apps/ai-core/main.py`

### Scheduler Setup

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from agents.mentor import Mentor
import logging

# Initialize scheduler
scheduler = BackgroundScheduler()
logger = logging.getLogger(__name__)

def generate_daily_digest_job():
    """
    Job function for scheduled digest generation.
    Runs every day at configured time (default: 7 AM).
    """
    logger.info("Running scheduled daily digest generation...")

    try:
        mentor = Mentor()
        result = mentor.generate_daily_digest()

        if result['success']:
            logger.info(f"Daily digest generated successfully: "
                       f"{result['insights_created']} insights created")
        else:
            logger.error(f"Daily digest generation failed: {result.get('error')}")

    except Exception as e:
        logger.error(f"Error in scheduled digest generation: {e}", exc_info=True)

# Configure scheduler
if settings.ENABLE_SCHEDULER and settings.ENABLE_DAILY_DIGEST:
    scheduler.add_job(
        generate_daily_digest_job,
        trigger=CronTrigger(
            hour=settings.DAILY_DIGEST_HOUR,
            minute=settings.DAILY_DIGEST_MINUTE
        ),
        id='daily_digest',
        name='Daily Digest Generation',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Scheduler started: Daily digest at {settings.DAILY_DIGEST_HOUR}:{settings.DAILY_DIGEST_MINUTE:02d}")
else:
    logger.info("Scheduler disabled via configuration")

# Shutdown scheduler on app shutdown
@app.on_event("shutdown")
async def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")
```

### Manual Trigger Endpoint

```python
@app.post("/mentor/trigger-daily-digest")
async def trigger_daily_digest(request: Request):
    """
    Manually trigger daily digest generation.
    Requires API key authentication.
    """
    # Check API key
    api_key = request.headers.get('X-API-Key')

    if api_key != settings.CRON_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Run digest generation
    mentor = Mentor()
    result = await mentor.generate_daily_digest()

    return result

@app.get("/mentor/status")
async def mentor_status():
    """
    Get Mentor status including scheduler info.
    """
    scheduler_info = {
        'enabled': settings.ENABLE_SCHEDULER,
        'running': scheduler.running if settings.ENABLE_SCHEDULER else False
    }

    if scheduler.running:
        jobs = scheduler.get_jobs()
        if jobs:
            next_run = jobs[0].next_run_time
            scheduler_info['next_run'] = next_run.isoformat() if next_run else None

    return {
        'status': 'running',
        'model': 'claude-sonnet-4-5',
        'scheduler': scheduler_info
    }
```

---

## API Reference

### FastAPI Endpoints

**Base URL**: `http://localhost:8000`

#### POST /mentor/generate-digest

Generate daily digest manually (no auth required).

**Response**:
```json
{
  "success": true,
  "insights_created": 3,
  "insights": [
    {"type": "Delta Watch", "id": "uuid-1"},
    {"type": "Connection", "id": "uuid-2"},
    {"type": "Prompt", "id": "uuid-3"}
  ]
}
```

#### POST /mentor/trigger-daily-digest

Trigger digest generation with API key authentication.

**Headers**:
- `X-API-Key`: Your configured API key

**Response**: Same as /generate-digest

#### GET /mentor/status

Get Mentor status.

**Response**:
```json
{
  "status": "running",
  "model": "claude-sonnet-4-5",
  "scheduler": {
    "enabled": true,
    "running": true,
    "next_run": "2025-10-09T07:00:00Z"
  }
}
```

#### POST /feedback/acknowledge

Process acknowledge feedback.

**Body**:
```json
{
  "insight_id": "uuid-123"
}
```

**Response**:
```json
{
  "success": true,
  "insight_id": "uuid-123",
  "entities_adjusted": 3,
  "changes": [
    {
      "entity_id": "uuid-entity-1",
      "importance": {"old": 0.8, "new": 0.9},
      "recency": {"old": 0.5, "new": 1.0}
    }
  ]
}
```

#### POST /feedback/dismiss

Process dismiss feedback.

**Body**:
```json
{
  "insight_id": "uuid-123"
}
```

**Response**:
```json
{
  "success": true,
  "insight_id": "uuid-123",
  "entities_adjusted": 2,
  "pattern_recorded": true,
  "changes": [...],
  "pattern": {
    "insight_type": "Connection",
    "driver_entity_types": ["feature", "feature"],
    "pattern_signature": {...}
  }
}
```

### Next.js API Routes

**Base URL**: `http://localhost:3110/api`

#### GET /insights

Get open insights for display.

**Query Params**:
- `status` (optional): Filter by status (default: 'open')

**Response**:
```json
[
  {
    "id": "uuid-1",
    "title": "Goal Drift Detected",
    "body": "Your Q4 goal was Water OS...",
    "drivers": {
      "entity_ids": ["uuid-goal", "uuid-feed-1"],
      "insight_type": "Delta Watch"
    },
    "status": "open",
    "created_at": "2025-10-08T07:00:00Z"
  }
]
```

#### POST /feedback/acknowledge/[id]

Acknowledge insight (proxy to AI Core).

**Response**:
```json
{
  "success": true,
  "message": "Feedback processed"
}
```

#### POST /feedback/dismiss/[id]

Dismiss insight (proxy to AI Core).

**Response**:
```json
{
  "success": true,
  "message": "Feedback processed"
}
```

---

## Prompt Engineering

### Delta Watch Prompt Template

```python
def _build_delta_watch_prompt(self, goals, actual_work, dismissed_patterns):
    # Format dismissed patterns
    dismissed_str = ""
    delta_watch_patterns = [p for p in dismissed_patterns if p['insight_type'] == 'Delta Watch']

    if delta_watch_patterns:
        dismissed_str = "\n\nIMPORTANT - Avoid these dismissed patterns:\n"
        for pattern in delta_watch_patterns:
            keywords = pattern['pattern_signature'].get('title_keywords', [])
            dismissed_str += f"- Pattern with keywords: {', '.join(keywords[:5])}\n"

    prompt = f"""You are a strategic thinking partner analyzing work patterns.

User's Stated Goals:
{self._format_entities(goals)}

User's Actual Work (high recency entities):
{self._format_entities(actual_work)}

TASK:
Generate a "Delta Watch" insight that detects goal alignment or drift.

Compare stated goals with actual work. Identify:
1. Alignment: Are they working on their stated goals?
2. Drift: Are they spending time on other priorities?
3. Strategic question: Is this drift intentional (pivot) or accidental (distraction)?

CRITICAL RULES:
1. Be specific: Reference actual entity titles, not generic descriptions
2. Be challenging: Don't just observe, ask hard questions
3. Be concise: Title = 5-8 words, Body = 2-3 sentences max
4. If goals and work align perfectly, say so and ask about progress/blockers
5. Avoid generic advice - ground everything in their actual entities
{dismissed_str}

Return ONLY valid JSON (no markdown):
{{
  "title": "...",
  "body": "...",
  "alignment_score": 0.0 to 1.0 (1.0 = perfect alignment, 0.0 = total drift)
}}
"""
    return prompt
```

### Connection Prompt Template

```python
def _build_connection_prompt(self, current_entity, historical_entity, dismissed_patterns):
    # Format dismissed patterns
    dismissed_str = ""
    connection_patterns = [p for p in dismissed_patterns if p['insight_type'] == 'Connection']

    if connection_patterns:
        dismissed_str = "\n\nIMPORTANT - Avoid these dismissed patterns:\n"
        for pattern in connection_patterns:
            keywords = pattern['pattern_signature'].get('title_keywords', [])
            dismissed_str += f"- Pattern with keywords: {', '.join(keywords[:5])}\n"

    time_gap = (datetime.now() - historical_entity['created_at']).days

    prompt = f"""You are a strategic thinking partner finding valuable connections across time.

Current Work:
- Title: {current_entity['title']}
- Type: {current_entity['type']}
- Summary: {current_entity.get('summary', 'N/A')}

Historical Work ({time_gap} days ago):
- Title: {historical_entity['title']}
- Type: {historical_entity['type']}
- Summary: {historical_entity.get('summary', 'N/A')}

TASK:
Generate a "Connection" insight that surfaces valuable lessons from the historical work that apply to current work.

What can the user learn from the past that's relevant now?
- Similar patterns or approaches?
- Lessons learned (what worked, what didn't)?
- Mistakes to avoid?
- Insights to apply?

CRITICAL RULES:
1. Only surface connections if there's REAL value (not just "these are similar")
2. Focus on actionable lessons, not just observations
3. Be specific: What exactly should they remember/apply?
4. Be concise: Title = 5-8 words, Body = 2-3 sentences max
5. If no valuable connection exists, return NULL (do not force it)
{dismissed_str}

Return ONLY valid JSON (no markdown):
{{
  "title": "...",
  "body": "...",
  "relevance_score": 0.0 to 1.0 (how relevant is this connection?)
}}

Or return NULL if no valuable connection exists.
"""
    return prompt
```

### Prompt Insight Prompt Template

```python
def _build_prompt_prompt(self, recent_work, goals, dismissed_patterns):
    # Format dismissed patterns
    dismissed_str = ""
    prompt_patterns = [p for p in dismissed_patterns if p['insight_type'] == 'Prompt']

    if prompt_patterns:
        dismissed_str = "\n\nIMPORTANT - Avoid these dismissed patterns:\n"
        for pattern in prompt_patterns:
            keywords = pattern['pattern_signature'].get('title_keywords', [])
            dismissed_str += f"- Pattern with keywords: {', '.join(keywords[:5])}\n"

    prompt = f"""You are a strategic thinking partner who challenges assumptions.

Recent Work Patterns:
{self._format_entities(recent_work[:5])}

User's Goals:
{self._format_entities(goals)}

TASK:
Generate a "Prompt" insight - a thought-provoking question that challenges assumptions and pushes strategic thinking.

Analyze the recent work and ask ONE powerful question that:
1. Challenges an assumption they might not know they're making
2. Exposes a potential blindspot
3. Reframes the problem from a different angle
4. Pushes beyond tactical execution toward strategic thinking
5. Is uncomfortable but valuable (not confrontational, but challenging)

CRITICAL RULES:
1. Ask ONE specific question (not multiple)
2. Ground the question in their actual work (reference specific entities)
3. Make it strategic, not tactical ("Why?" not "How?")
4. Be concise: Title = question itself (5-10 words), Body = 1-2 sentence context
5. Avoid generic questions - make it specific to their situation
{dismissed_str}

Return ONLY valid JSON (no markdown):
{{
  "title": "The question itself",
  "body": "Brief context explaining why this question matters now"
}}
"""
    return prompt
```

---

## Signal System

Signals are the foundation of insight personalization. The Mentor uses three signal dimensions to determine what's relevant:

### Signal Dimensions

1. **Importance (0.0 to 1.0)**: Static value based on entity type
   - `core_identity`: 1.0
   - `project`: 0.85
   - `feature`: 0.8
   - `decision`: 0.75
   - `person`: 0.7
   - `reflection`: 0.65
   - `task`: 0.6
   - `meeting_note`: 0.5

2. **Recency (0.0 to 1.0)**: Dynamic value that decays over time
   - Formula: `recency = e^(-λt)` where λ = ln(2)/30 (30-day half-life)
   - New entity: 1.0
   - 30 days old: 0.5
   - 60 days old: 0.25

3. **Novelty (0.0 to 1.0)**: Based on connection count and age
   - Formula: `novelty = (1/(1 + edges * 0.1) + 1/(1 + age * 0.05)) / 2`
   - Few connections + recent = novel (0.8-1.0)
   - Many connections + old = established (0.1-0.3)

### Signal Adjustments (Feedback Loop)

**Acknowledge** (+0.1 importance, recency → 1.0):
```python
new_importance = min(1.0, old_importance + 0.1)
new_recency = 1.0
```

**Dismiss** (-0.1 importance):
```python
new_importance = max(0.0, old_importance - 0.1)
```

### Signal Usage in Context Gathering

```python
# High priority entities (importance >= 0.7)
high_priority = db.get_entities_by_signal_threshold(
    signal_type='importance',
    threshold=0.7,
    limit=20
)

# Active work (recency >= 0.8)
active_work = db.get_entities_by_signal_threshold(
    signal_type='recency',
    threshold=0.8,
    limit=20
)
```

---

## Pattern Detection & Avoidance

### Pattern Structure

```json
{
  "insight_type": "Connection",
  "driver_entity_types": ["feature", "feature"],
  "pattern_signature": {
    "insight_type": "Connection",
    "driver_types": ["feature", "feature"],
    "title_keywords": ["similar", "notification", "pattern"],
    "body_keywords": ["4 months ago", "engagement", "timing"],
    "entity_ids": ["uuid-1", "uuid-2"],
    "dismissed_at": "2025-10-08T09:06:00Z"
  }
}
```

### Pattern Matching

When generating insights, the Mentor checks if the new insight matches any dismissed patterns:

```python
def matches_dismissed_pattern(self, insight_data: Dict, dismissed_patterns: List[Dict]) -> bool:
    """
    Check if insight matches any dismissed patterns.

    Matching criteria:
    1. Same insight_type
    2. Similar driver_entity_types
    3. Overlapping keywords (> 50% overlap)
    """
    for pattern in dismissed_patterns:
        # Check type
        if insight_data['insight_type'] != pattern['insight_type']:
            continue

        # Check driver types
        pattern_types = set(pattern['driver_entity_types'])
        insight_types = set([e['type'] for e in insight_data['driver_entities']])

        type_overlap = len(pattern_types & insight_types) / max(len(pattern_types), len(insight_types))

        if type_overlap < 0.5:
            continue

        # Check keyword overlap
        pattern_keywords = set(pattern['pattern_signature']['title_keywords'])
        insight_keywords = set(self.extract_keywords(insight_data['title']))

        keyword_overlap = len(pattern_keywords & insight_keywords) / max(len(pattern_keywords), len(insight_keywords))

        if keyword_overlap > 0.5:
            return True  # Match found

    return False
```

### Pattern Avoidance in Prompts

Dismissed patterns are included in Claude prompts:

```python
dismissed_str = "\n\nIMPORTANT - Avoid these dismissed patterns:\n"
for pattern in delta_watch_patterns:
    keywords = pattern['pattern_signature'].get('title_keywords', [])
    dismissed_str += f"- Pattern with keywords: {', '.join(keywords[:5])}\n"
```

This instructs Claude to avoid generating similar insights.

---

## UI Components

### Daily Digest Page

**File**: `apps/web/app/digest/page.tsx`

```typescript
import { createClient } from '@/utils/supabase/server';
import InsightCard from '@/components/InsightCard';

export default async function DigestPage() {
  const supabase = createClient();

  // Fetch open insights (server-side)
  const { data: insights } = await supabase
    .from('insight')
    .select('*')
    .eq('status', 'open')
    .order('created_at', { ascending: false })
    .limit(3);

  if (!insights || insights.length === 0) {
    return (
      <div className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Daily Digest</h1>
        <p className="text-gray-600">
          No insights available. Check back tomorrow at 7 AM!
        </p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">Daily Digest</h1>
      <p className="text-gray-600 mb-8">
        {new Date().toLocaleDateString('en-US', {
          weekday: 'long',
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        })}
      </p>

      <div className="space-y-6">
        {insights.map((insight) => (
          <InsightCard key={insight.id} insight={insight} />
        ))}
      </div>
    </div>
  );
}
```

### Insight Card Component

**File**: `apps/web/components/InsightCard.tsx`

```typescript
'use client';

import { useState } from 'react';

interface InsightCardProps {
  insight: {
    id: string;
    title: string;
    body: string;
    drivers: {
      insight_type: string;
      entity_ids: string[];
    };
    created_at: string;
  };
}

export default function InsightCard({ insight }: InsightCardProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [isHidden, setIsHidden] = useState(false);

  const insightType = insight.drivers.insight_type;

  // Color coding by type
  const cardColors = {
    'Delta Watch': 'bg-blue-50 border-blue-200',
    'Connection': 'bg-purple-50 border-purple-200',
    'Prompt': 'bg-green-50 border-green-200'
  };

  const iconEmojis = {
    'Delta Watch': '📊',
    'Connection': '🔗',
    'Prompt': '❓'
  };

  const handleAcknowledge = async () => {
    setIsProcessing(true);

    try {
      const response = await fetch(`/api/feedback/acknowledge/${insight.id}`, {
        method: 'POST'
      });

      if (response.ok) {
        setIsHidden(true);
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
        setIsHidden(true);
      }
    } catch (error) {
      console.error('Error dismissing insight:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  if (isHidden) {
    return null;
  }

  return (
    <div className={`border-2 rounded-lg p-6 ${cardColors[insightType] || 'bg-gray-50 border-gray-200'}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{iconEmojis[insightType] || '💡'}</span>
          <span className="text-sm font-medium text-gray-600">{insightType}</span>
        </div>
      </div>

      <h3 className="text-xl font-bold mb-2">{insight.title}</h3>
      <p className="text-gray-700 mb-6">{insight.body}</p>

      <div className="flex gap-3">
        <button
          onClick={handleAcknowledge}
          disabled={isProcessing}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          👍 Acknowledge
        </button>
        <button
          onClick={handleDismiss}
          disabled={isProcessing}
          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
        >
          👎 Dismiss
        </button>
      </div>
    </div>
  );
}
```

---

## Testing

### Test Coverage

**File**: `apps/ai-core/tests/test_mentor.py` (600+ lines, 23 tests)

**Test Classes**:
1. `TestMentorInitialization` - 3 tests
2. `TestContextGathering` - 3 tests
3. `TestInsightGeneration` - 4 tests
4. `TestFeedbackProcessor` - 7 tests
5. `TestMentorIntegration` - 3 tests
6. `TestErrorHandling` - 3 tests

### Running Tests

```bash
# All tests
cd apps/ai-core
source venv/bin/activate
pytest tests/test_mentor.py -v

# Specific test class
pytest tests/test_mentor.py::TestFeedbackProcessor -v

# Integration tests only
pytest tests/test_mentor.py -v -m integration

# With coverage
pytest tests/test_mentor.py -v --cov=agents --cov-report=html
```

### E2E Manual Test

```bash
# Start server
cd apps/ai-core
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Run E2E test
python tests/test_feedback_loop.py
```

**Test Flow**:
1. Health check
2. Seed 14 test entities
3. Generate 3 insights
4. Test acknowledge feedback
5. Test dismiss feedback
6. Verify adaptation

---

## Configuration

### Environment Variables

**File**: `apps/ai-core/.env`

```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key

# AI
ANTHROPIC_API_KEY=sk-ant-api03-...

# Scheduler
ENABLE_SCHEDULER=true
ENABLE_DAILY_DIGEST=true
DAILY_DIGEST_HOUR=7
DAILY_DIGEST_MINUTE=0

# Security
CRON_API_KEY=your-secure-key  # For manual triggers

# App
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Configuration Class

**File**: `apps/ai-core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # AI
    ANTHROPIC_API_KEY: str

    # Scheduler
    ENABLE_SCHEDULER: bool = True
    ENABLE_DAILY_DIGEST: bool = True
    DAILY_DIGEST_HOUR: int = 7
    DAILY_DIGEST_MINUTE: int = 0

    # Security
    CRON_API_KEY: str = "change-me-in-production"

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Deployment

### Production Checklist

- [ ] Database migrations run in Supabase
- [ ] Environment variables configured (especially `CRON_API_KEY`)
- [ ] Scheduler enabled (`ENABLE_SCHEDULER=true`)
- [ ] Logs configured (file or service like Sentry)
- [ ] API key secure (not default value)
- [ ] SSL/HTTPS enabled
- [ ] Health check endpoint working
- [ ] Test digest generation manually
- [ ] Verify scheduler next run time
- [ ] Monitor first scheduled run

### Railway Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Set environment variables
railway variables set ENABLE_SCHEDULER=true
railway variables set DAILY_DIGEST_HOUR=7
railway variables set CRON_API_KEY=$(openssl rand -base64 32)

# Deploy
railway up
```

### Vercel + Railway Setup

**Frontend (Vercel)**:
- Deploy Next.js app to Vercel
- Set `AI_CORE_URL` to Railway backend URL
- Set `NEXT_PUBLIC_SUPABASE_URL` and anon key

**Backend (Railway)**:
- Deploy FastAPI app to Railway
- Set all environment variables
- Ensure scheduler runs 24/7 (not serverless)

### Monitoring

**Key Metrics**:
- Digest generation success rate
- Average insight quality (user feedback %)
- Scheduler uptime
- API response times
- Claude API costs

**Logging**:
```python
import logging

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ai-core.log'),
        logging.StreamHandler()
    ]
)
```

---

## Troubleshooting

### Common Issues

#### 1. No Insights Generated

**Symptoms**:
- `/digest` page shows "No insights available"
- Manual generation returns empty result

**Causes**:
- No core identity entities
- No recent work entities
- Claude API errors

**Debug**:
```bash
# Check database
curl http://localhost:8000/mentor/status

# Generate manually with logs
curl -X POST http://localhost:8000/mentor/generate-digest

# Check logs
tail -f logs/ai-core.log
```

#### 2. Scheduler Not Running

**Symptoms**:
- Status endpoint shows `running: false`
- No insights at 7 AM

**Causes**:
- `ENABLE_SCHEDULER=false`
- Server crashed
- APScheduler not installed

**Fix**:
```bash
# Check config
echo $ENABLE_SCHEDULER

# Reinstall dependencies
pip install -r requirements.txt

# Restart server
uvicorn main:app --reload --port 8000
```

#### 3. Feedback Not Working

**Symptoms**:
- Button click does nothing
- Signals not updating

**Causes**:
- API route errors
- Database connection issues
- Missing insight ID

**Debug**:
```bash
# Test acknowledge directly
curl -X POST http://localhost:8000/feedback/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"insight_id": "your-insight-id"}'

# Check browser console
# Check network tab
```

#### 4. Patterns Not Avoiding

**Symptoms**:
- Similar insights after dismiss
- Pattern not recorded

**Causes**:
- Pattern extraction failed
- Keyword matching too strict
- Pattern matching logic issue

**Debug**:
```python
# Check dismissed patterns in database
SELECT * FROM dismissed_patterns ORDER BY last_dismissed_at DESC;

# Check pattern signature
```

---

**Last Updated**: 2025-10-08
**Status**: Production-ready
**Version**: 1.0
**Test Coverage**: 85%
