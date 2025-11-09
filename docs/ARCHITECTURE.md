# Universal Memory Graph - System Architecture

Complete architecture overview of the UMG system, including all agents, engines, and data flow.

**Version**: 2.0
**Last Updated**: 2025-11-08

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [Deployment](#deployment)

---

## System Overview

Universal Memory Graph (UMG) is a neuroscience-inspired knowledge management system that captures, structures, and surfaces information from user interactions.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Quick Capture│  │ Voice Debrief│  │   Webhooks   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                             ▼
          ┌─────────────────────────────────────┐
          │         raw_events (inbox)          │
          │    status: pending_processing       │
          └──────────────────┬──────────────────┘
                             │
                             ▼
          ┌─────────────────────────────────────┐
          │        Archivist Agent              │
          │  • Entity extraction (Claude)       │
          │  • Cross-event resolution           │
          │  • Entity creation                  │
          │  • Hub-and-spoke pattern            │
          └──────────────────┬──────────────────┘
                             │
                             ▼
          ┌─────────────────────────────────────┐
          │    RelationshipEngine (NEW!)        │
          │  • Pattern-based detection          │
          │  • Semantic LLM detection           │
          │  • Embedding similarity (nightly)   │
          │  • Temporal analysis (nightly)      │
          │  • Graph topology (nightly)         │
          │  • Hebbian learning (LTP)           │
          │  • Synaptic homeostasis (decay)     │
          └──────────────────┬──────────────────┘
                             │
                             ▼
          ┌─────────────────────────────────────┐
          │         Knowledge Graph             │
          │  ┌──────────┐        ┌───────────┐ │
          │  │ Entities │───────▶│   Edges   │ │
          │  │ (nodes)  │        │ (w/ weight)│ │
          │  └──────────┘        └───────────┘ │
          │  ┌──────────┐        ┌───────────┐ │
          │  │  Chunks  │        │  Signals  │ │
          │  └──────────┘        └───────────┘ │
          └──────────────────┬──────────────────┘
                             │
                             ▼
          ┌─────────────────────────────────────┐
          │          Mentor Agent               │
          │  • Context retrieval                │
          │  • Insight generation               │
          │  • Proactive surfacing              │
          └─────────────────────────────────────┘
```

---

## Architecture Diagram

### Component Interaction

```
┌────────────────────────────────────────────────────────────────┐
│                          Frontend (Next.js)                    │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │ Quick Capture │  │ Entity Graph  │  │  Mentor Chat     │  │
│  └───────┬───────┘  └───────┬───────┘  └────────┬─────────┘  │
│          │                  │                    │             │
└──────────┼──────────────────┼────────────────────┼─────────────┘
           │                  │                    │
           │  HTTP POST       │  HTTP GET          │  HTTP POST
           │                  │                    │
┌──────────▼──────────────────▼────────────────────▼─────────────┐
│                    Next.js API Routes                           │
│  /api/events  │  /api/entities  │  /api/mentor-chat            │
└──────────┬──────────────────┬────────────────────┬─────────────┘
           │                  │                    │
           │                  │                    │
┌──────────▼──────────────────▼────────────────────▼─────────────┐
│                      Supabase (PostgreSQL)                      │
│  ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  raw_events  │  │  entity  │  │   edge   │  │  signal  │  │
│  └──────────────┘  └──────────┘  └──────────┘  └──────────┘  │
└──────────┬──────────────────┬────────────────────┬─────────────┘
           │                  │                    │
           │                  │                    │
┌──────────▼──────────────────▼────────────────────▼─────────────┐
│                      AI Core (FastAPI)                          │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    Archivist Agent                        │ │
│  │  ┌────────────────┐  ┌─────────────────┐                │ │
│  │  │ EntityExtractor│  │ EntityResolver  │                │ │
│  │  │   (Claude)     │  │  (Pronouns)     │                │ │
│  │  └────────────────┘  └─────────────────┘                │ │
│  │  ┌────────────────┐  ┌─────────────────┐                │ │
│  │  │ MentionTracker │  │  SignalScorer   │                │ │
│  │  └────────────────┘  └─────────────────┘                │ │
│  └──────────────┬───────────────────────────────────────────┘ │
│                 │ Triggers                                     │
│                 ▼                                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              RelationshipEngine (NEW!)                    │ │
│  │  ┌──────────────────────────────────────────────────────┐│ │
│  │  │ Detection Strategies:                                 ││ │
│  │  │  1. Pattern-based (regex)                             ││ │
│  │  │  2. Semantic LLM (Claude)                             ││ │
│  │  │  3. Embedding similarity (cosine)                     ││ │
│  │  │  4. Temporal overlap (dates)                          ││ │
│  │  │  5. Graph topology (transitive)                       ││ │
│  │  └──────────────────────────────────────────────────────┘│ │
│  │  ┌──────────────────────────────────────────────────────┐│ │
│  │  │ Hebbian Learning:                                     ││ │
│  │  │  • Edge reinforcement (weight += 1.0)                 ││ │
│  │  │  • Global decay (weight *= 0.99)                      ││ │
│  │  │  • Pruning (delete if weight < 0.1)                   ││ │
│  │  └──────────────────────────────────────────────────────┘│ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    Mentor Agent                           │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │ │
│  │  │ Graph Query │  │ LLM Synthesis│  │ Insight Cache  │  │ │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Archivist Agent

**Responsibility**: Transform raw events into structured knowledge (entities)

**Location**: `apps/ai-core/agents/archivist.py`

**Pipeline** (10 steps):
1. Fetch event from `raw_events`
2. Parse and clean text
3. Extract entities using Claude Sonnet 4.5
4. Cross-event entity resolution (pronoun → entity mapping)
5. Mention tracking and entity promotion
6. Self-introduction detection (user entity bootstrapping)
7. Entity creation (hub-and-spoke pattern)
8. Trigger RelationshipEngine (incremental mode)
9. Chunking and embeddings
10. Signal scoring (importance, recency, novelty)
11. Update event status to `processed`

**Key Features**:
- Claude-powered entity extraction
- Pronoun resolution (`"I"` → Ryan York)
- Hub-and-spoke for complex concepts
- Mention-based entity promotion
- Signal scoring for relevance

**Documentation**: `docs/features/archivist/feature-details.md`

---

### 2. RelationshipEngine ⭐ NEW

**Responsibility**: Create and maintain edges between entities

**Location**: `apps/ai-core/engines/relationship_engine.py`

**Operating Modes**:
- **Incremental** - Called by Archivist after each event (fast, 2 strategies)
- **Nightly** - Scheduled at 3 AM daily (comprehensive, all 5 strategies + decay/pruning)
- **On-demand** - User-triggered manual analysis (debugging, custom)

**Detection Strategies**:

| Strategy | Type | When | Example |
|----------|------|------|---------|
| Pattern-based | Regex | Incremental + Nightly | `"CTO at Company"` → `role_at` edge |
| Semantic LLM | Claude API | Incremental + Nightly | `"learned from mentor"` → `mentored_by` |
| Embedding similarity | Cosine distance | Nightly only | Similar entities → `semantically_related` |
| Temporal analysis | Date overlap | Nightly only | Co-occurring entities → `temporal_overlap` |
| Graph topology | Transitive | Nightly only | `A→B→C` infers `A→C` |

**Hebbian Learning** (LTP analog):
```python
# New edge
edge.weight = 1.0

# Repeated detection
edge.weight += 1.0  # Long-term potentiation

# Nightly decay (synaptic homeostasis)
edge.weight *= 0.99  # 1% decay per night

# Pruning
if edge.weight < 0.1:
    delete(edge)  # "Use it or lose it"
```

**Why Separate from Archivist?**:
- ✅ Cross-event relationship detection (Archivist is event-scoped)
- ✅ Multiple detection strategies (pattern + LLM + embeddings + temporal + topology)
- ✅ Edge reinforcement and decay (neuroscience-inspired)
- ✅ Separation of concerns (Archivist = nodes, RelationshipEngine = edges)

**Documentation**:
- Feature details: `docs/features/relationship-engine/feature-details.md`
- API reference: `docs/features/relationship-engine/api-reference.md`
- Troubleshooting: `docs/features/relationship-engine/troubleshooting.md`

---

### 3. Mentor Agent

**Responsibility**: Surface relevant insights from knowledge graph

**Location**: `apps/ai-core/agents/mentor.py`

**Capabilities**:
- Graph querying (entity + edge traversal)
- Context retrieval (signal-based ranking)
- LLM synthesis (Claude generates insights)
- Proactive surfacing (based on recency + importance + novelty)

**Documentation**: `docs/features/mentor/`

---

### 4. Database (Supabase)

**Technology**: PostgreSQL with pgvector extension

**Schema** (7 tables):

```sql
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  raw_events  │────▶│    entity    │────▶│     edge     │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                     │
                            │                     │
                            ▼                     ▼
                     ┌──────────────┐     ┌──────────────┐
                     │    chunk     │     │    signal    │
                     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  embedding   │
                     └──────────────┘
```

**Key Tables**:

**raw_events** - Universal inbox
```sql
CREATE TABLE raw_events (
  id UUID PRIMARY KEY,
  payload JSONB,              -- {type, content, metadata, user_id, user_entity_id}
  source TEXT,                -- 'quick_capture', 'voice_debrief', 'webhook_granola'
  status TEXT,                -- 'pending_processing', 'processed', 'error'
  created_at TIMESTAMPTZ
);
```

**entity** - Nodes in knowledge graph
```sql
CREATE TABLE entity (
  id UUID PRIMARY KEY,
  source_event_id UUID,
  type TEXT,                  -- 'person', 'project', 'role', 'organization', etc.
  title TEXT,
  summary TEXT,
  metadata JSONB,             -- {is_hub, is_spoke, is_user_entity, aliases, ...}
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

**edge** - Relationships between entities (with Hebbian learning)
```sql
CREATE TABLE edge (
  id UUID PRIMARY KEY,
  from_id UUID REFERENCES entity(id),
  to_id UUID REFERENCES entity(id),
  kind TEXT,                  -- 'role_at', 'founded', 'mentored_by', etc.

  -- Hebbian Learning (added 2025-11-08)
  weight FLOAT DEFAULT 1.0,           -- Synaptic strength
  last_reinforced_at TIMESTAMPTZ,     -- Last reinforcement timestamp

  -- Scoring
  confidence FLOAT DEFAULT 1.0,
  importance FLOAT,

  -- Context
  description TEXT,
  start_date DATE,
  end_date DATE,
  metadata JSONB,
  source_event_id UUID,

  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);

CREATE INDEX idx_edge_from_to ON edge(from_id, to_id);
CREATE INDEX idx_edge_weight ON edge(weight);
```

**signal** - Relevance scores
```sql
CREATE TABLE signal (
  id UUID PRIMARY KEY,
  entity_id UUID REFERENCES entity(id),
  importance FLOAT,           -- Entity type-based
  recency FLOAT,              -- Exponential decay (30-day half-life)
  novelty FLOAT,              -- Based on connections + age
  last_surfaced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

**Documentation**: `docs/features/archivist/feature-details.md#database-schema`

---

## Data Flow

### Event Processing Flow

```
1. USER ACTION
   │ User types: "I'm CTO at Willow Education"
   │
   ▼
2. CAPTURE
   │ POST /api/events
   │ Creates raw_event with status='pending_processing'
   │
   ▼
3. ARCHIVIST (10-step pipeline)
   │ a. Fetch event
   │ b. Parse text: "I'm CTO at Willow Education"
   │ c. Extract entities via Claude:
   │    → Entity 1: "CTO at Willow Education" (type: role)
   │    → Entity 2: "Willow Education" (type: organization)
   │ d. Resolve "I" → Ryan York (user entity)
   │ e. Check mention tracker (should promote?)
   │ f. Self-introduction check (is this user?)
   │ g. Create entities in database
   │    → role-1: "CTO at Willow Education"
   │    → org-1: "Willow Education"
   │ h. Trigger RelationshipEngine.run_incremental(event_id)
   │ i. Chunk text + generate embeddings
   │ j. Score signals (importance, recency, novelty)
   │ k. Update event status → 'processed'
   │
   ▼
4. RELATIONSHIPENGINE (Incremental mode)
   │ a. Fetch entities for event:
   │    → role-1: "CTO at Willow Education"
   │    → org-1: "Willow Education"
   │ b. Run pattern-based strategy:
   │    → Regex match: "CTO at Willow Education"
   │    → Extract: "Willow Education"
   │    → Find matching org entity: org-1
   │    → Create relationship:
   │       {from: role-1, to: org-1, kind: 'role_at', confidence: 0.95}
   │ c. Run semantic LLM strategy:
   │    → Send to Claude: "Identify relationships in this text..."
   │    → LLM response: [possibly additional relationships]
   │ d. Filter by confidence (>= 0.3)
   │ e. For each relationship:
   │    → Check if edge exists (same from_id, to_id, kind)
   │    → If exists: weight += 1.0 (reinforcement)
   │    → If new: create with weight=1.0
   │ f. Return:
   │    {edges_created: 1, edges_updated: 0, entities_analyzed: 2}
   │
   ▼
5. KNOWLEDGE GRAPH UPDATED
   │ Entities:
   │   role-1: "CTO at Willow Education"
   │   org-1: "Willow Education"
   │   person-1: "Ryan York"
   │
   │ Edges:
   │   role-1 ──[role_at, weight=1.0]──▶ org-1
   │
   ▼
6. MENTOR READY
   │ User asks: "What roles do I have?"
   │ Mentor queries graph → finds role-1 → returns "CTO at Willow Education"
```

---

### Nightly Consolidation Flow

```
SCHEDULED: 3:00 AM Daily
   │
   ▼
1. TRIGGER
   │ Scheduler: nightly_consolidation.py
   │ Calls: RelationshipEngine.run_nightly(full_scan=False)
   │
   ▼
2. FETCH ENTITIES
   │ Get entities created/updated in last 24 hours
   │ Example: 150 entities
   │
   ▼
3. RUN ALL 5 STRATEGIES
   │ a. Pattern-based → 8 role_at edges
   │ b. Semantic LLM → 12 complex relationships
   │ c. Embedding similarity → 5 semantically_related edges
   │ d. Temporal overlap → 3 temporal_overlap edges
   │ e. Graph topology → 7 inferred_connection edges
   │
   │ Total potential edges: 35
   │
   ▼
4. FILTER & CREATE/UPDATE
   │ Filter by confidence >= 0.3 → 30 edges remain
   │ For each edge:
   │   → If exists: weight += 1.0 (reinforcement)
   │   → If new: create with weight = 1.0
   │
   │ Result: 15 created, 15 updated
   │
   ▼
5. GLOBAL DECAY (Synaptic homeostasis)
   │ For ALL edges in database (not just new):
   │   edge.weight = edge.weight * 0.99
   │
   │ Example:
   │   Edge A: 2.0 → 1.98
   │   Edge B: 1.0 → 0.99
   │   Edge C: 0.15 → 0.1485
   │
   │ Result: 236 edges decayed
   │
   ▼
6. PRUNING (Remove weak edges)
   │ Delete edges where weight < 0.1
   │
   │ Example:
   │   Edge X: weight=0.08 → DELETED
   │   Edge Y: weight=0.12 → KEPT
   │
   │ Result: 12 edges pruned
   │
   ▼
7. COMPLETE
   │ Return: {
   │   edges_created: 15,
   │   edges_updated: 15,
   │   edges_decayed: 236,
   │   edges_pruned: 12,
   │   entities_analyzed: 150,
   │   processing_time: 45.2s
   │ }
```

---

## Technology Stack

### Frontend

**Framework**: Next.js 14 (App Router)
**Language**: TypeScript
**UI Library**: React 18
**Styling**: Tailwind CSS
**State Management**: React Context
**Data Fetching**: Native fetch with async/await
**Deployment**: Vercel

**Key Pages**:
- `/` - Quick Capture (text input)
- `/entities` - Entity Graph Visualization
- `/mentor` - Mentor Chat Interface
- `/archivist-log` - Processing Activity Log

---

### Backend (AI Core)

**Framework**: FastAPI (Python 3.11)
**Language**: Python
**LLM**: Claude Sonnet 4.5 (Anthropic)
**Database Client**: Supabase Python SDK
**Validation**: Pydantic v2
**Scheduling**: APScheduler (nightly consolidation)
**Logging**: Python logging module

**Endpoints**:
- `POST /process` - Trigger batch processing
- `POST /process/event/{id}` - Process specific event
- `GET /health` - Health check
- `POST /reset-cache` - Clear in-memory cache

---

### Database

**Provider**: Supabase
**Engine**: PostgreSQL 15
**Extensions**:
- pgvector (vector similarity search)
- uuid-ossp (UUID generation)

**Features**:
- Row-level security (RLS)
- Real-time subscriptions
- REST API auto-generation
- Database webhooks

---

### External Services

**Anthropic Claude**:
- Model: claude-sonnet-4-5-20250929
- Usage:
  - Entity extraction
  - Relationship detection (LLM strategy)
  - Mentor responses
- Cost: ~$0.02 per event

**Supabase**:
- Database hosting
- Authentication (future)
- Storage (future)
- Real-time (future)

---

## Deployment

### Development

```bash
# Terminal 1: Frontend (Next.js)
cd apps/web
pnpm run dev
# → http://localhost:3110

# Terminal 2: Backend (FastAPI)
cd apps/ai-core
python -m uvicorn main:app --reload --port 8000
# → http://localhost:8000

# Terminal 3: Scheduler (nightly consolidation)
cd apps/ai-core
python schedulers/nightly_consolidation.py
# Runs at 3:00 AM daily
```

---

### Production

**Frontend** (Vercel):
- Auto-deploy on push to `main`
- Environment variables via Vercel dashboard
- CDN distribution
- SSR + ISR rendering

**Backend** (TBD):
- Options:
  - Railway (Python support, easy deployment)
  - Fly.io (containerized, global edge)
  - Google Cloud Run (serverless, auto-scaling)
- Requirements:
  - Python 3.11
  - uvicorn ASGI server
  - Persistent storage for logs
  - Cron job or scheduler support (nightly consolidation)

**Database** (Supabase):
- Managed PostgreSQL
- Automatic backups
- Connection pooling
- Point-in-time recovery

---

## Key Design Decisions

### 1. Separation of Entity and Edge Creation

**Decision**: Archivist creates entities, RelationshipEngine creates edges

**Rationale**:
- **Single Responsibility**: Each component has one job
- **Cross-Event Relationships**: Engine can detect relationships across events (Archivist is event-scoped)
- **Multiple Strategies**: Engine uses 5 different detection methods (pattern, LLM, embeddings, temporal, topology)
- **Hebbian Learning**: Engine maintains edge weights over time

**Trade-off**: Adds complexity (2 components instead of 1), but enables more sophisticated relationship detection

---

### 2. Neuroscience-Inspired Edge Management

**Decision**: Implement Hebbian learning (LTP) and synaptic homeostasis

**Rationale**:
- **Reinforcement**: Repeated detection strengthens edges (weight += 1.0)
- **Decay**: Unused edges decay over time (weight *= 0.99)
- **Pruning**: Very weak edges deleted (weight < 0.1)
- **Biological Plausibility**: Mimics how human memory works

**Trade-off**: More complex than simple boolean edges, but provides dynamic graph that adapts over time

---

### 3. Incremental + Nightly Hybrid

**Decision**: Run 2 strategies incrementally, all 5 strategies nightly

**Rationale**:
- **Incremental** (fast, post-event): Pattern-based + Semantic LLM (2-5 seconds)
- **Nightly** (comprehensive, slow): All 5 strategies + decay + pruning (30-60 seconds for 24h window)

**Trade-off**: Some relationships only detected during nightly consolidation, but keeps per-event processing fast

---

### 4. Weight-Based Edge Quality

**Decision**: Store weight instead of just confidence

**Rationale**:
- **Confidence**: How sure we are of the relationship (set at creation)
- **Weight**: How strong the relationship is (increases with reinforcement)
- **Use Case**: Weight reflects evidence accumulation over time

**Example**:
```
Detection 1: "Ryan founded Water OS" → confidence=0.85, weight=1.0
Detection 2: "Ryan started Water OS" → confidence=0.80, weight=2.0 (reinforced)
Detection 3: "Ryan created Water OS" → confidence=0.90, weight=3.0 (reinforced)
```

---

## Future Enhancements

### Phase 11: Real-World Validation
- Process test events through full pipeline
- Verify role→org edges created correctly
- Test nightly consolidation with real data
- Validate edge reinforcement in production

### Phase 12: Performance Optimization
- Batch LLM API calls (10 entity pairs per call)
- Cache recent entities in Redis
- Parallel strategy execution
- Database query optimization

### Phase 13: Advanced Detection Strategies
- Contextual reference resolution ("the company" → most recent company)
- Temporal state tracking (entity versioning)
- Conflict detection (contradictory edges)
- Causality inference (event X caused event Y)

### Phase 14: User Features
- Manual edge creation/deletion (UI)
- Edge weight visualization (graph thickness)
- Relationship type customization
- Export/import graph data

---

## Documentation Index

### Core Documentation
- **This file**: System architecture overview
- `docs/features/archivist/feature-details.md` - Archivist implementation
- `docs/features/relationship-engine/feature-details.md` - RelationshipEngine implementation
- `docs/features/mentor/` - Mentor agent

### API Documentation
- `docs/features/archivist/feature-details.md#api-reference` - Archivist API
- `docs/features/relationship-engine/api-reference.md` - RelationshipEngine API

### Operational Documentation
- `docs/features/relationship-engine/troubleshooting.md` - Troubleshooting guide
- `docs/migrations/README.md` - Database migrations
- `apps/ai-core/tests/README.md` - Test suite documentation

### Planning Documentation
- `docs/features/relationship-engine/plan-status-update.md` - Implementation status
- `docs/features/relationship-engine/implementation-plan.md` - Original plan

---

**Version History**:
- **v1.0** (2025-10-26) - Initial architecture with Archivist
- **v2.0** (2025-11-08) - Added RelationshipEngine, Hebbian learning, nightly consolidation

**Maintained by**: Ryan York
**Status**: Production-ready (Phase 0-9 complete, Phase 10 in progress)
