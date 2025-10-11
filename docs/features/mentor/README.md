# The Mentor Agent

## Overview

The Mentor is an AI-powered thinking partner that analyzes your work patterns and generates personalized daily insights to help you stay aligned with your goals, learn from past experiences, and challenge your assumptions. It's like having a coach who knows your entire work history and helps you stay on track by surfacing the right context at the right time.

**The Mentor is not a passive assistant—it's a proactive guardian against the quiet misallocation of your life's energy.**

---

## What Problem Does It Solve?

You've built systems to capture your work (Quick Capture), organize it (Archivist), and store it (knowledge graph). But without the Mentor, that data is static.

**The Mentor brings your knowledge graph to life** by:
- Detecting when your actions drift from your stated goals
- Surfacing forgotten lessons from your past work
- Asking powerful questions that challenge your assumptions
- Learning from your feedback to adapt future insights

**Example**: You said your Q4 goal was to launch Water OS in Ghana, but you've spent 80% of this week polishing Willow's Feed feature UI. The Mentor notices this misalignment and asks: "Is this a strategic pivot or a distraction?"

---

## Core Concept: The Daily Digest

**Every morning at 7 AM**, the Mentor:
1. Analyzes your knowledge graph
2. Generates **3 insight cards** tailored to your current work
3. You provide feedback (👍 Acknowledge or 👎 Dismiss)
4. The system **learns** from your feedback and adapts future insights

---

## The Three Insight Types

### 📊 Delta Watch - "Are you on track?"

**Purpose**: Detects goal alignment or drift

Compares what you *said* you'd work on (your stated goals) with what you're *actually* working on (recent activity).

**Example**:
> "Your Q4 goal was to launch Water OS in Ghana, but you've spent 80% of this week on Willow's Feed feature. Is this a strategic pivot or a distraction?"

**When it helps**:
- Catches goal drift before weeks pass
- Validates intentional pivots
- Surfaces conflicts between stated priorities and actual work

---

### 🔗 Connection - "What can you learn from the past?"

**Purpose**: Surfaces relevant historical context

Finds past work that relates to your current challenges and reminds you of lessons learned.

**Example**:
> "The Feed feature you're building now is similar to the Parent Notification System you built 4 months ago. The engagement patterns you discovered about timing and content preferences might apply here."

**When it helps**:
- Prevents repeating past mistakes
- Surfaces forgotten solutions
- Connects disparate experiences across time and projects

---

### ❓ Prompt - "What should you be asking?"

**Purpose**: Generates forward-looking challenge questions

Creates thought-provoking questions based on your recent work to challenge assumptions and expose blindspots.

**Example**:
> "You've been focused on the Feed feature's UI polish. But what problem is this feature actually solving for students and teachers? Is polish the highest leverage work right now?"

**When it helps**:
- Challenges assumptions you didn't know you had
- Reframes problems from different angles
- Pushes strategic thinking beyond tactical execution

---

## How It Works: The Feedback Loop

### Step 1: Context Gathering (Every morning at 7 AM)

The Mentor gathers a complete picture of your work:

**What you care about**:
- Core identity entities (goals, values, mission)
- High-importance entities (importance ≥ 0.7)

**What you've been doing**:
- Recent work from last 24 hours
- Active entities (recency ≥ 0.8)

**What to avoid**:
- Dismissed patterns from last 30 days

### Step 2: Insight Generation

For each insight type, the Mentor:
1. Uses Claude Sonnet 4.5 to analyze your work patterns
2. Generates personalized insights tied to specific entities
3. Stores insights in database with `status='open'`

**Delta Watch Generation**:
```
Goals: "Launch Water OS in Ghana" (from core identity)
Recent Work: 3 Willow Feed entities (high recency)
→ Detects misalignment
→ Generates Delta Watch insight
```

**Connection Generation**:
```
Current Work: "Feed Feature" (recent)
Historical Work: "Parent Notification System" (4 months ago)
→ Finds similarity
→ Generates Connection insight
```

**Prompt Generation**:
```
Recent Work: 3 UI polish tasks
Goals: "Launch Water OS"
→ Detects tactical focus
→ Generates strategic question
```

### Step 3: UI Display

Visit `/digest` to see 3 color-coded insight cards:
- 🔵 **Blue card** - Delta Watch
- 🟣 **Purple card** - Connection
- 🟢 **Green card** - Prompt

Each card has two buttons:
- 👍 **Acknowledge** - "This is valuable"
- 👎 **Dismiss** - "This is noise"

### Step 4: Feedback Processing

**When you click Acknowledge**:
1. Boosts importance of related entities (+0.1)
2. Refreshes recency to 1.0 (marks as actively relevant)
3. Updates insight status to 'acknowledged'
4. Card disappears from UI

**When you click Dismiss**:
1. Lowers importance of related entities (-0.1)
2. Records pattern to avoid in future:
   ```json
   {
     "insight_type": "Connection",
     "driver_entity_types": ["feature", "feature"],
     "title_keywords": ["similar", "notification"],
     "dismissed_at": "2025-10-08T09:06:00Z"
   }
   ```
3. Updates insight status to 'dismissed'
4. Card disappears from UI

### Step 5: Adaptation (Next morning)

**The system learns**:
- Entities you acknowledged → higher importance scores → surface more often
- Patterns you dismissed → actively avoided in future insights
- Your preferences shape what you see over time

**Result**: After a week of feedback:
- More insights about topics you acknowledge
- Fewer insights matching dismissed patterns
- Higher relevance and lower noise

---

## The Self-Improving Loop

```
Day 1:
  Generate insight based on current signals
  ↓
  User acknowledges Delta Watch, dismisses Connection
  ↓
  Signals updated (+0.1/-0.1)
  ↓
  Pattern recorded

Day 2:
  Generate insight using updated signals
  ↓
  Delta Watch gets priority (acknowledged yesterday)
  ↓
  Connection pattern avoided (dismissed yesterday)
  ↓
  New insights more aligned with user preferences

Week Later:
  System has learned:
  - Which topics you care about (high importance)
  - Which insight types you prefer (Delta Watch > Connection)
  - Which patterns to avoid (5 dismissed patterns)
  → Highly personalized, low-noise insights
```

---

## Real Example: One Week of Adaptation

### Monday Morning (First Digest)

**Generated Insights**:
1. 📊 Delta Watch: "Goal drift - Water OS vs Willow"
2. 🔗 Connection: "Feed similar to Notifications from 4mo ago"
3. ❓ Prompt: "Is UI polish the right focus?"

**User Feedback**:
- ✅ Acknowledge Delta Watch (valuable!)
- ❌ Dismiss Connection (not helpful)
- ✅ Acknowledge Prompt (good question!)

**Signal Changes**:
- Water OS entity: importance remains 1.0 (already max)
- Willow Feed entities: importance 0.8 → 0.9 (acknowledged)
- Notification entity: importance 0.7 → 0.6 (dismissed)

**Pattern Recorded**:
- Don't show Connection insights about notification patterns

### Tuesday Morning (Second Digest)

**Generated Insights**:
1. 📊 Delta Watch: "Water OS vs Willow" (same pattern, higher confidence because acknowledged)
2. 🔗 Connection: "Feed similar to Dashboard from 2mo ago" (avoided notification pattern)
3. ❓ Prompt: "What's the core problem this feature solves?"

**Result**: Already adapting! Avoided dismissed pattern, surfaced Delta Watch again (you care about this).

### Friday Morning (End of Week)

**Generated Insights**:
1. 📊 Delta Watch: "Strategic focus: Water OS needs attention"
2. 🔗 Connection: "Water OS Ghana launch similar to Willow rollout"
3. ❓ Prompt: "What's blocking Water OS progress?"

**Signal State**:
- Water OS: importance 1.0, recency 1.0 (multiple acknowledges)
- Willow Feed: importance 0.7 (initial boost, then normal decay)
- Notification pattern: permanently on "avoid" list

**System Learned**:
- You care deeply about goal alignment (Delta Watch always acknowledged)
- You don't find historical feature comparisons useful (Connection often dismissed)
- You value strategic questions (Prompt often acknowledged)

---

## Key Features

### 1. Personalized Learning
- Every user gets different insights based on **their** work
- System adapts to **their** feedback preferences
- No two users see identical insights

### 2. Continuous Adaptation
- Signals update with every feedback action
- Patterns accumulate over time
- System gets smarter the more you use it

### 3. Prevents Noise
- Dismissed patterns are actively avoided
- Low-importance entities surface less often
- You train it to your preferences

### 4. Leverages Full Context
- Uses entire knowledge graph (years of work)
- Connects disparate time periods
- Surfaces forgotten knowledge

### 5. Actionable Insights
- Always tied to specific entities (driver_entity_ids)
- Grounded in your actual work
- Not generic advice

---

## Technical Architecture (High-Level)

### Components

```
┌─────────────────────────────┐
│      Daily Digest UI        │
│      (Next.js /digest)      │
│  3 insight cards with       │
│  Acknowledge/Dismiss btns   │
└──────────┬──────────────────┘
           │
           │ Fetch/Feedback
           │
┌──────────▼──────────────────┐
│    Next.js API Routes       │
│  /api/insights (GET)        │
│  /api/feedback/* (POST)     │
└──────────┬──────────────────┘
           │
           │ Proxy to AI Core
           │
┌──────────▼──────────────────┐
│      Supabase Database      │
│  Tables: entity, signal,    │
│  insight, dismissed_patterns│
└──────────┬──────────────────┘
           │
           │ Read/Write
           │
┌──────────▼──────────────────┐
│    AI Core (FastAPI)        │
│                             │
│  ┌─────────────────────┐   │
│  │    APScheduler      │   │
│  │   (7 AM daily)      │   │
│  └──────┬──────────────┘   │
│         │                   │
│  ┌──────▼──────────────┐   │
│  │   Mentor Agent      │   │
│  │ - Context gathering │   │
│  │ - Insight generation│   │
│  │ - Claude API calls  │   │
│  └─────────────────────┘   │
│                             │
│  ┌─────────────────────┐   │
│  │ Feedback Processor  │   │
│  │ - Signal adjustments│   │
│  │ - Pattern recording │   │
│  └─────────────────────┘   │
└─────────────┬───────────────┘
              │
              │ API Calls
              │
┌─────────────▼───────────────┐
│    Anthropic Claude API     │
│    (claude-sonnet-4-5)      │
└─────────────────────────────┘
```

### Data Flow

1. **Scheduled Generation** (7 AM daily)
   - APScheduler triggers job
   - Mentor gathers context from database
   - Generates 3 insights via Claude
   - Stores insights with status='open'

2. **User Views Digest**
   - Next.js page fetches open insights
   - Displays 3 cards in UI
   - User reads and decides

3. **User Provides Feedback**
   - Click Acknowledge or Dismiss
   - Frontend calls API route
   - API proxies to AI Core
   - Feedback Processor updates signals and patterns
   - Insight marked acknowledged/dismissed

4. **Next Morning**
   - Mentor reads updated signals
   - Reads dismissed patterns
   - Generates adapted insights
   - Cycle repeats

---

## Configuration

### Environment Variables

**AI Core** (`apps/ai-core/.env`):
```bash
# Scheduler
ENABLE_SCHEDULER=true
ENABLE_DAILY_DIGEST=true
DAILY_DIGEST_HOUR=7
DAILY_DIGEST_MINUTE=0

# API Key for external triggers
CRON_API_KEY=your-secure-key

# Database & AI
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

### Manual Trigger

Instead of waiting for 7 AM:
```bash
curl -X POST http://localhost:8000/mentor/generate-digest
```

### Check Status

```bash
curl http://localhost:8000/mentor/status | jq .scheduler
```

Expected:
```json
{
  "enabled": true,
  "running": true,
  "next_run": "2025-10-09T07:00:00Z"
}
```

---

## Current Status

**✅ Fully Operational** (as of 2025-10-08)

**Completed Phases**:
- ✅ Phase 1: Database Setup
- ✅ Phase 2: Mentor Agent Core
- ✅ Phase 3: Prompt Engineering
- ✅ Phase 4: Feedback Processor
- ✅ Phase 5: Daily Digest UI
- ✅ Phase 6: Scheduled Generation
- ✅ Phase 7: Testing & Refinement

**Test Coverage**:
- 23 automated tests (unit + integration)
- ~85% code coverage
- End-to-end manual testing verified
- Error handling comprehensive

**Production Ready**: Yes! 🎉

---

## Usage Guide

### Daily Workflow

**Morning (7 AM)**:
1. Mentor generates digest automatically
2. You receive 3 fresh insights

**Anytime**:
1. Visit `http://localhost:3110/digest`
2. Read 3 insight cards (blue, purple, green)
3. For each card:
   - Click 👍 if valuable → boosts related topics
   - Click 👎 if noise → avoids similar patterns
4. Cards disappear after feedback
5. Come back tomorrow for adapted insights

### First Week Strategy

**Days 1-3**: Explore
- Acknowledge insights that resonate
- Dismiss insights that feel noisy
- Train the system to your preferences

**Days 4-7**: Observe
- Notice how insights adapt to your feedback
- Fewer dismissed patterns appear
- More acknowledged topics surface

**Week 2+**: Trust
- Insights become highly personalized
- Low noise, high signal
- Valuable coaching every morning

### Tips for Maximum Value

1. **Be honest with feedback**
   - Don't acknowledge just to be nice
   - Dismiss freely if not helpful
   - System learns from your truth

2. **Acknowledge strategic insights**
   - Goal alignment checks (Delta Watch)
   - Challenging questions (Prompt)
   - Actionable connections (Connection)

3. **Dismiss tactical noise**
   - Obvious observations
   - Irrelevant historical connections
   - Questions you've already answered

4. **Check daily**
   - Insights are most relevant on generation day
   - Recency matters for context
   - Consistent feedback improves adaptation

---

## Why This Design Works

### 1. Self-Improving System
Every feedback action teaches the Mentor what you value. After a week, insights are dramatically more relevant than day one.

### 2. Grounded in Your Reality
All insights reference specific entities from your knowledge graph. Not generic advice—personalized coaching based on your actual work.

### 3. Prevents Quiet Drift
Delta Watch catches misalignment before weeks pass. It's easy to drift from goals day by day. The Mentor notices.

### 4. Leverages Forgotten Knowledge
Connection insights surface lessons from months or years ago that you've forgotten but are relevant now.

### 5. Challenges Assumptions
Prompt insights ask questions you didn't know to ask. They push beyond tactical execution toward strategic thinking.

### 6. Low Friction
3 cards, 2 buttons, 30 seconds. High value, low time investment. Works in your flow, not against it.

---

## Scheduler Usage

For detailed scheduler configuration, external triggers, troubleshooting, and production deployment, see [scheduler-usage-guide.md](./scheduler-usage-guide.md).

**Quick Reference**:
- Default: 7 AM daily (configurable via `DAILY_DIGEST_HOUR`)
- Manual trigger: `POST /mentor/generate-digest`
- Status check: `GET /mentor/status`
- Disable: Set `ENABLE_SCHEDULER=false`

---

## Future Enhancements

### Phase 8+

**Notification Delivery**:
- Email digest delivery
- Slack/Discord notifications
- Mobile push notifications

**Advanced Insight Types**:
- **Contradiction**: Detect conflicting decisions over time
- **Milestone**: Celebrate progress toward goals
- **Warning**: Flag potential blockers or risks

**Multi-Timeframe Analysis**:
- Weekly digest (broader patterns)
- Monthly reflection (strategic review)
- Quarterly alignment check

**Team Insights** (future):
- Multi-user support
- Shared goals and patterns
- Team alignment checks

**Enhanced Adaptation**:
- Machine learning on feedback patterns
- Predictive insight relevance scoring
- Automatic insight type preference learning

---

## Key Files Reference

### Backend (AI Core)
- `apps/ai-core/agents/mentor.py` - Mentor agent (insight generation)
- `apps/ai-core/agents/feedback_processor.py` - Feedback processing
- `apps/ai-core/main.py` - FastAPI endpoints, scheduler setup
- `apps/ai-core/services/database.py` - Database queries
- `apps/ai-core/config.py` - Configuration settings

### Frontend (Web)
- `apps/web/app/digest/page.tsx` - Daily Digest UI page
- `apps/web/components/InsightCard.tsx` - Insight card component
- `apps/web/app/api/insights/route.ts` - Insights API route
- `apps/web/app/api/feedback/acknowledge/[id]/route.ts` - Acknowledge endpoint
- `apps/web/app/api/feedback/dismiss/[id]/route.ts` - Dismiss endpoint

### Tests
- `apps/ai-core/tests/test_mentor.py` - Unit & integration tests (23 tests)
- `apps/ai-core/tests/test_feedback_loop.py` - End-to-end test
- `apps/ai-core/tests/fixtures/mentor_fixtures.py` - Test data

### Database
- `entity` table - All captured work/ideas
- `signal` table - Importance/recency/novelty scores
- `insight` table - Generated insights
- `dismissed_patterns` table - Patterns to avoid

---

## Mentor Chat: Conversational Memory Building

### How Chat Conversations Become Long-Term Memories

Beyond the daily digest, you can **chat conversationally with your Mentor** at `/mentor/chat`. Every message you send (and every response the Mentor gives) becomes a permanent memory in your knowledge graph.

**The critical insight**: There are **no milestones or thresholds**. Every single chat message is processed immediately.

### The Complete Chat-to-Memory Flow

```
You: "I had a meeting with Sarah about the Feed feature"
  ↓
  Creates 2 raw events instantly (user message + assistant response)
  ↓
  Both marked status='pending_processing', source='mentor_chat'
  ↓
  Archivist processes within 60 seconds
  ↓
  Extracts entities: Sarah (person), Feed feature (feature)
  ↓
  Creates/updates relationships: Sarah --[mentions]--> Feed
  ↓
  Refreshes signal scores: recency → 1.0 for both
  ↓
  Next chat (even weeks later) can reference Sarah and Feed
  ↓
  Long-term memory achieved! 🎉
```

### What Gets Saved From Each Chat Message

**Every chat exchange creates**:

1. **2 Raw Events**:
   - Your message → `raw_events` (role: user)
   - Mentor's response → `raw_events` (role: assistant)
   - Both get full Archivist processing

2. **0-N Entities** (extracted by Claude):
   - New entities created if first mention
   - Existing entities get `mention_count` incremented
   - `referenced_by_event_ids` array updated

3. **1-N Edges** (relationships detected):
   - Person mentions Project
   - Feature belongs_to Company
   - User founded Company
   - All tracked with `source_event_id`

4. **Signal Updates**:
   - Recency refreshed to 1.0 (mentioned just now)
   - Importance adjusted by feedback over time
   - Novelty updated based on new connections

### Example: Multi-Turn Conversation Memory

**Chat Session 1** (Monday):
```
You: "My name is Ryan York. I'm starting Water OS."

Memory Created:
- Entity: Ryan York (person, is_user_entity: true)
- Entity: Water OS (company)
- Edge: Ryan York --[founded]--> Water OS
- Signals: Both at recency 1.0, importance based on type
```

**Chat Session 2** (Same day):
```
You: "I want to focus on the Feed feature first."

Memory Created:
- Entity: Feed feature (feature)
- Edge: Feed --[belongs_to]--> Water OS
- Edge: Ryan York --[owns]--> Feed
- Signals: Feed at recency 1.0, Water OS refreshed to 1.0
```

**Chat Session 3** (Next day, new session):
```
You: "Had a meeting about the Feed with Sarah."

Context Gathering:
- Mentor queries graph: finds Feed (recency 0.97), Water OS (0.96)
- Includes in context even though conversation_history is empty
- This is long-term memory in action!

Mentor Response:
"Great! The Feed feature for Water OS is showing high activity.
What did you and Sarah decide?"

Memory Created:
- Entity: Sarah (person)
- Edge: Sarah --[mentions]--> Feed
- Updates: Feed mention_count++, recency → 1.0
```

### Why Both User AND Assistant Messages Are Saved

**User Messages**:
- Primary source of new information
- Extract entities, relationships, decisions
- Build knowledge graph from your thoughts

**Assistant Messages**:
- Tracks which entities Mentor referenced
- Shows which topics are "top of mind"
- Captures Mentor's synthesis and insights
- Ensures conversation threads are preserved

**Example**:
```
User: "Tell me about Water OS"
Assistant: "Water OS is your new company founded last month.
            It's related to your experience at Willow Education..."
```

Processing the assistant's message ensures:
- "Water OS" and "Willow Education" get recency bumps
- The connection between them gets reinforced
- Future queries surface these relationships

### Chat Context: Short-Term vs Long-Term Memory

**Short-Term Memory** (conversation_history):
- Frontend sends last 10 messages with each request
- Used for conversational continuity ("it", "that project", etc.)
- Lasts only for current chat session
- Cleared when you refresh the page

**Long-Term Memory** (knowledge graph):
- Every message processed by Archivist → entities extracted
- Entities persist forever in database
- Next chat (even weeks later) queries graph via keywords
- You get persistent memory across all conversations

**This is why chat works even without conversation_history:**
```
New chat session (no history):
You: "What should I work on for the Feed?"

Mentor still knows about Feed because:
1. Context gathering extracts keywords: "work", "Feed"
2. Queries database: finds Feed entity (from previous chats)
3. Includes in prompt to Claude
4. Response: "The Feed feature for Water OS is showing..."
```

### Database Queries to View Chat Memories

**See all your chat messages**:
```sql
SELECT
  payload->>'role' as role,
  payload->>'content' as content,
  status,
  created_at
FROM raw_events
WHERE source = 'mentor_chat'
ORDER BY created_at DESC
LIMIT 20;
```

**See entities extracted from chat**:
```sql
SELECT
  e.title,
  e.type,
  e.metadata->>'mention_count' as mentions,
  e.created_at
FROM entity e
WHERE e.source_event_id IN (
  SELECT id FROM raw_events WHERE source = 'mentor_chat'
)
ORDER BY e.created_at DESC;
```

**See which entities are "hot" from recent chats**:
```sql
SELECT
  e.title,
  e.type,
  s.recency,
  s.importance,
  array_length(
    (e.metadata->'referenced_by_event_ids')::jsonb::text[]::text[], 1
  ) as total_references
FROM entity e
JOIN signal s ON e.id = s.entity_id
WHERE s.recency > 0.8  -- Recently mentioned
ORDER BY s.recency DESC, s.importance DESC
LIMIT 20;
```

### Comparison: Quick Capture vs Mentor Chat

Both work the same way under the hood:

| Feature | Quick Capture | Mentor Chat |
|---------|--------------|-------------|
| Creates raw events? | ✅ Yes (1 per submit) | ✅ Yes (2 per message) |
| Status | `pending_processing` | `pending_processing` |
| Source | `quick_capture` | `mentor_chat` |
| Processed by Archivist? | ✅ Yes | ✅ Yes |
| Entity extraction? | ✅ Yes (Claude) | ✅ Yes (Claude) |
| Signals updated? | ✅ Yes | ✅ Yes |
| Long-term memory? | ✅ Yes | ✅ Yes |

**The difference**:
- Quick Capture: Fire and forget (no response)
- Mentor Chat: Conversational (uses current graph state for context)

### How Context Gathering Works

Every chat message triggers context gathering before calling Claude:

**Step 1: Extract Keywords**
```python
message = "Had a meeting about the Feed with Sarah"
keywords = ["meeting", "feed", "sarah"]
```

**Step 2: Query Knowledge Graph**
```python
core_identity = db.get_entities_by_type("core_identity")  # Your goals
active_work = db.get_entities_by_signal_threshold(recency_min=0.8)  # Recent work
relevant = db.search_entities_by_title("feed")  # Keyword matches
relevant += db.search_entities_by_title("sarah")
```

**Step 3: Build Context Prompt**
```
You are the Mentor - a strategic thinking partner.

User's Goals & Values:
- Build Water OS
- Focus on core features

User's Active Work (High Recency):
- Feed feature (feature) - recency: 0.97
- Sarah (person) - recency: 0.85
- Water OS (company) - recency: 0.96

Relevant Context from Knowledge Graph:
- Feed feature: Main product feature for Water OS
- Sarah: Product manager at Water OS

Recent Conversation:
[Last 5 messages if in same session]

User's Current Message:
Had a meeting about the Feed with Sarah

INSTRUCTIONS:
- Reference specific entities from the knowledge graph
- Ask strategic questions
- Be direct and actionable
...
```

**Result**: Claude has full context even without conversation_history!

### The Complete Feedback Loop

```
Day 1: Chat about Water OS
  → Entities created (Water OS, Feed)
  → Signals: recency 1.0, importance 0.8

Day 2: Morning Digest
  → Delta Watch references Water OS (high recency)
  → You acknowledge → importance boosted to 0.9

Day 3: Chat mentions Water OS again
  → Context gathering finds Water OS (importance 0.9, recency 0.97)
  → Prioritized in context
  → Mentor gives more detailed response about Water OS
  → Recency refreshed to 1.0

Day 4: Morning Digest
  → Delta Watch about Water OS again (acknowledged before + high recency)
  → Connection surfaces related projects
  → Prompt asks strategic question about Water OS

Week Later: Chat "What should I prioritize?"
  → Mentor knows Water OS is top priority
  → Recommends next steps based on all previous context
  → Complete long-term memory achieved!
```

### Why This Design Works

1. **No Mental Overhead**: Just chat naturally, system captures everything
2. **Continuous Memory**: Every message builds the graph automatically
3. **Cross-Session Context**: Conversations weeks apart still have context
4. **Reinforcement Learning**: Frequently mentioned topics get higher priority
5. **Bidirectional Memory**: Chat improves digest, digest improves chat

### Key Insight: Conversations ARE Your Memories

You don't need to:
- Take separate notes after chatting
- Manually tag entities
- Worry about what to capture
- Remember to process conversations

**Just chat naturally. The system captures, processes, and remembers everything automatically.**

Every word you type builds the knowledge graph that makes the Mentor smarter over time.

---

## The Mentor's Philosophy

> **"Your most valuable and finite resource is your time and energy. The Mentor's job is to ensure you spend every day moving your life's mission forward by remembering what you forget, connecting what you don't see connected, and challenging what you haven't questioned."**

**It's not trying to replace your thinking. It's building the foundation that allows you to think more strategically, act more intentionally, and learn more systematically.**

The Mentor is your persistent thinking partner—one that never forgets, never judges, and always asks the important questions.

---

For detailed technical implementation, see [feature-details.md](./feature-details.md).

For chat implementation details, see [chat-implementation-plan.md](./chat-implementation-plan.md) and [ai-handoff.md](./ai-handoff.md).

For scheduler configuration and troubleshooting, see [scheduler-usage-guide.md](./scheduler-usage-guide.md).
