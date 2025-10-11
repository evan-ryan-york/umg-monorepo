# Archivist Agent: Technical Implementation Details

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Processing Pipeline](#processing-pipeline)
3. [Entity Recognition & Mention Tracking](#entity-recognition--mention-tracking)
4. [Cross-Event Entity Resolution](#cross-event-entity-resolution)
5. [Relationship Mapping](#relationship-mapping)
6. [Hub-and-Spoke Pattern](#hub-and-spoke-pattern)
7. [Signal Scoring](#signal-scoring)
8. [Database Schema](#database-schema)
9. [API Reference](#api-reference)
10. [Configuration](#configuration)
11. [Testing](#testing)
12. [Performance & Optimization](#performance--optimization)

---

## Architecture Overview

### Tech Stack

**Backend**:
- Python 3.11
- FastAPI (async REST API)
- Claude Sonnet 4.5 (Anthropic)
- Supabase Python client
- tiktoken (token counting)

**Database**:
- Supabase (PostgreSQL + pgvector)
- 7 tables: `raw_events`, `entity`, `edge`, `chunk`, `embedding`, `signal`, `insight`

**Deployment**:
- Runs alongside Next.js web app via `pnpm run dev:web`
- Continuous background processing (60-second intervals)
- Manual trigger via `/process` endpoint

### Project Structure

```
apps/ai-core/
├── main.py                  # FastAPI app entry point
├── config.py                # Environment variables
├── requirements.txt         # Python dependencies
│
├── agents/
│   ├── archivist.py         # Main orchestrator (11-step pipeline)
│   └── feedback_processor.py
│
├── services/
│   ├── database.py          # Supabase client wrapper
│   ├── embeddings.py        # OpenAI embeddings (disabled)
│   ├── chunker.py           # Text chunking logic
│   └── entity_resolver.py   # Cross-event pronoun resolution
│
├── processors/
│   ├── entity_extractor.py  # Entity recognition (Claude)
│   ├── relationship_mapper.py # Edge creation (Claude)
│   ├── mention_tracker.py   # Entity promotion logic
│   └── signal_scorer.py     # Importance/recency/novelty
│
├── models/
│   ├── raw_event.py         # Pydantic models
│   ├── entity.py
│   ├── edge.py
│   └── ...
│
└── tests/
    ├── test_archivist.py
    └── fixtures/
```

---

## Processing Pipeline

The Archivist processes events through an 11-step pipeline:

### Step 1: Fetch Event
```python
# Fetch from database
event = db.get_event_by_id(event_id)

# Event structure
{
  "id": "uuid-123",
  "payload": {
    "type": "text",
    "content": "Had a meeting with Sarah...",
    "metadata": {},
    "user_id": "default_user",
    "user_entity_id": "uuid-ryan-york"  # Set after first event
  },
  "source": "quick_capture",
  "status": "pending_processing",
  "created_at": "2025-10-06T10:00:00Z"
}
```

### Step 2: Parse & Clean
```python
# apps/ai-core/utils/text_cleaner.py
text = event.payload.content
cleaned_text = TextCleaner.clean(text)

# Removes:
# - Excessive whitespace → single space
# - Markdown artifacts (**, __, etc.)
# - Normalizes quotes (" " → " ")
```

### Step 3: Entity Extraction
```python
# apps/ai-core/processors/entity_extractor.py
entities = entity_extractor.extract_entities(cleaned_text)

# Uses Claude Sonnet 4.5 with structured prompt
# Returns:
[
  {
    "title": "Feed",
    "type": "feature",
    "summary": "Feature for displaying updates in Willow app",
    "confidence": 0.98,
    "is_primary_subject": True
  },
  {
    "title": "Sarah",
    "type": "person",
    "summary": "Team member",
    "confidence": 0.95,
    "is_primary_subject": False
  }
]
```

**Entity Types**:
- `person`, `company`, `project`, `feature`, `task`, `decision`, `reflection`, `meeting_note`, `core_identity`, `reference_document`

**Extraction Rules**:
- Does NOT extract pronouns ("I", "me", "my") as entities
- Identifies primary subject via explicit name statements ("My name is X")
- Extracts concrete names and things only

### Step 3.5: Cross-Event Entity Resolution
```python
# apps/ai-core/services/entity_resolver.py
user_entity_id = event.payload.user_entity_id
reference_map = entity_resolver.resolve_references(
    cleaned_text,
    user_entity_id,
    existing_entities
)

# Returns pronoun → entity_id mapping
{
  "i": "uuid-ryan-york",
  "me": "uuid-ryan-york",
  "my": "uuid-ryan-york"
}
```

**Resolution Strategies**:
1. **Pronoun Resolution**: Maps "I/me/my" to `user_entity_id`
2. **Future**: Contextual ("the company"), LLM-powered (complex references)

### Step 4: Mention Tracking & Entity Promotion
```python
# apps/ai-core/processors/mention_tracker.py
for entity_data in entities:
    # Record mention
    mention_tracker.record_mention(
        entity_data['title'],
        entity_data['type'],
        event_id,
        is_primary_subject=entity_data.get('is_primary_subject', False)
    )

    # Check promotion rules
    should_promote = mention_tracker.should_promote(
        entity_data['title'],
        is_primary_subject=entity_data.get('is_primary_subject', False)
    )
```

**Promotion Rules**:
1. **Immediate**: Entity is primary subject → promote
2. **After mentions**: 2-3 mentions across different events → promote
3. **Never**: Passing references (not promoted until threshold met)

**Note**: Mention tracker is in-memory (resets on restart). Database lookup prevents duplicates:
```python
# Check database before creating
existing = db.get_entity_by_title(entity_data['title'], entity_data['type'])
if existing:
    use existing.id
else:
    create new entity
```

### Step 4.5: Self-Introduction Detection
```python
# apps/ai-core/agents/archivist.py (lines 142-162)
if entity_type == 'person' and is_primary:
    # User is introducing themselves
    logger.info(f"Detected self-introduction: '{entity_data['title']}' is likely the user")

    # Mark as user entity
    entity_data['metadata']['is_user_entity'] = True
    entity_data['metadata']['user_id'] = 'default_user'

    # Create entity
    entity_id = db.create_entity(entity_data)

    # Update reference map to point to real person entity
    if not user_entity_id:
        reference_map['i'] = entity_id
        reference_map['me'] = entity_id
        reference_map['my'] = entity_id
```

### Step 5: Entity Creation (Hub-and-Spoke)
```python
# Determine if entity should be hub
is_hub = entity_type in ['project', 'feature', 'decision']

if is_hub:
    entity_id = db.create_hub_entity({
        'source_event_id': event_id,
        'type': entity_type,
        'title': entity_data['title'],
        'summary': entity_data.get('summary', ''),
        'metadata': {
            'is_hub': True,
            **entity_data.get('metadata', {})
        }
    })
else:
    entity_id = db.create_entity({...})

# Track for relationship mapping
entity_map[entity_data['title']] = entity_id
```

### Step 6: Create Spoke Entity (if hub exists)
```python
# If hub entity exists and event is meeting/reflection
if hub_entity_id and event.source in ['quick_capture', 'voice_debrief', 'webhook_granola']:
    spoke_type = 'meeting_note' if 'meeting' in text.lower() else 'reflection'

    spoke_id = db.create_spoke_entity(hub_entity_id, {
        'source_event_id': event_id,
        'type': spoke_type,
        'title': f"Note about {text[:50]}...",
        'summary': text[:200],
        'metadata': {'is_spoke': True}
    })

    # Creates edge: spoke --[relates_to]--> hub
```

### Step 7: Relationship Mapping
```python
# apps/ai-core/processors/relationship_mapper.py
relationships = relationship_mapper.detect_relationships(
    cleaned_text,
    entities,                 # Newly extracted entities
    existing_entities=[...],  # Recent 20 entities from DB
    reference_map={"i": "uuid-ryan-york", ...}
)

# Returns:
[
  {
    "from_entity": "Ryan York",
    "to_entity": "Water OS",
    "relationship_type": "founded",
    "metadata": {"context": "starting new business"}
  }
]
```

**Relationship Types**:
- `belongs_to`, `modifies`, `mentions`, `informs`, `blocks`, `contradicts`, `relates_to`
- `founded`, `works_at`, `manages`, `owns`, `contributes_to` (cross-event)

**Detection Methods**:
1. **Explicit keywords**: "renamed", "belongs to", "blocks", etc.
2. **LLM analysis**: Claude identifies relationships from context
3. **Reference hints**: Entity list includes `[also referred to as: i, me, my]`

### Step 8: Alias Detection
```python
# Detect renames/aliases
alias_updates = relationship_mapper.detect_alias_and_update(
    cleaned_text,
    entities,
    db
)

# Pattern matching for:
# - "renamed from X to Y"
# - "now called Y instead of X"
# - "changing X to Y"

# Updates entity metadata:
{
  "aliases": ["school-update", "school-update feature"],
  "previous_names": ["school-update"]
}
```

### Step 9: Chunking
```python
# apps/ai-core/services/chunker.py
chunks = chunker.chunk_text(cleaned_text)

# Strategy:
# - Target: ~500 tokens per chunk
# - Overlap: 50-100 tokens between chunks
# - Split on paragraph boundaries
# - Generate SHA-256 hash for deduplication

# Returns:
[
  {
    "text": "Meeting decision and renaming discussion...",
    "token_count": 450,
    "hash": "a3f2b9c8d7e6f5a4b3c2d1e0f9a8b7c6"
  },
  ...
]
```

### Step 10: Embedding Generation
```python
# apps/ai-core/services/embeddings.py
# NOTE: Currently disabled (Anthropic doesn't provide embeddings)

chunk_texts = [c['text'] for c in chunks]
embeddings = embeddings_service.generate_embeddings_batch(chunk_texts)

# Would return: 1536-dimension vectors
# Currently: Returns zero vectors as placeholders
```

### Step 11: Signal Assignment
```python
# apps/ai-core/processors/signal_scorer.py
for entity_id in entity_ids:
    entity = db.get_entity_by_id(entity_id)

    importance = signal_scorer.calculate_importance(
        entity.type,
        entity.metadata
    )
    recency = signal_scorer.calculate_recency(
        entity.created_at,
        entity.updated_at
    )
    novelty = signal_scorer.calculate_novelty(
        edge_count=db.get_edge_count_for_entity(entity_id),
        entity_age_days=(datetime.now() - entity.created_at).days
    )

    db.create_signal({
        'entity_id': entity_id,
        'importance': importance,
        'recency': recency,
        'novelty': novelty,
        'last_surfaced_at': None
    })
```

### Step 12: Update Event Status
```python
db.update_event_status(event_id, 'processed')
```

---

## Entity Recognition & Mention Tracking

### EntityExtractor Implementation

**File**: `apps/ai-core/processors/entity_extractor.py`

**LLM Prompt**:
```python
prompt = f"""You are an expert at extracting structured information from text.

Extract all meaningful entities from this text.

IMPORTANT RULES:
1. DO NOT extract pronouns (I, me, my, you, we, etc.) as entities
2. Only extract concrete names and things (people's names, companies, projects, etc.)
3. If the text contains "My name is X" or "I am X", extract X as a person entity and mark is_primary_subject: true
4. Extract tasks, decisions, reflections as entities when they are clearly stated

Text:
{text}

For each entity, provide:
- title: The entity name/title
- type: One of [person, company, project, feature, task, decision, reflection, meeting_note, core_identity, reference_document]
- summary: A brief 1-sentence description
- confidence: 0.0 to 1.0
- is_primary_subject: true/false (Is this the main focus of the text?)

Return ONLY valid JSON:
{{
  "entities": [
    {{"title": "...", "type": "...", "summary": "...", "confidence": 0.95, "is_primary_subject": true}}
  ]
}}
"""
```

**Response Parsing**:
- Uses Claude Sonnet 4.5
- Temperature: 0.3 (consistent results)
- Strips markdown code blocks before JSON parsing
- Fallback: Returns empty array on error

### MentionTracker Implementation

**File**: `apps/ai-core/processors/mention_tracker.py`

**Data Structure**:
```python
mention_cache = {
    "feed feature": {
        "text": "Feed feature",
        "type": "feature",
        "mention_count": 3,
        "events": ["uuid-1", "uuid-2", "uuid-3"],
        "first_seen": datetime(2025, 10, 1),
        "last_seen": datetime(2025, 10, 6),
        "is_promoted": True,
        "entity_id": "uuid-feed-entity"
    }
}
```

**Key Methods**:
```python
def record_mention(entity_text, entity_type, event_id, is_primary_subject):
    """Track entity mention"""
    normalized_key = entity_text.lower().strip()

    if normalized_key not in cache:
        cache[normalized_key] = {
            'mention_count': 0,
            'events': [],
            'is_promoted': False
        }

    cache[normalized_key]['mention_count'] += 1
    if event_id not in cache[normalized_key]['events']:
        cache[normalized_key]['events'].append(event_id)

def should_promote(entity_text, is_primary_subject):
    """Promotion logic"""
    # Rule 1: Immediate if primary subject
    if is_primary_subject:
        return True

    mention = cache.get(normalized(entity_text))

    # Rule 2: After 2-3 mentions across different events
    if mention and mention['mention_count'] >= 2 and len(mention['events']) >= 2:
        return True

    # Rule 3: Don't promote if already promoted
    if mention and mention['is_promoted']:
        return False

    return False
```

**Database Backup**:
```python
# Before creating entity, check database
existing = db.get_entity_by_title(title, type)
if existing:
    return existing.id
else:
    create_new_entity()
```

---

## Cross-Event Entity Resolution

### User Entity Bootstrapping

**File**: `apps/web/app/api/events/route.ts`

```typescript
async function getUserEntityId(): Promise<string | null> {
  const RYAN_YORK = 'Ryan York';

  // Query for person entity with title matching "Ryan York"
  const { data } = await supabase
    .from('entity')
    .select('id, title, metadata')
    .eq('type', 'person')
    .ilike('title', `%${RYAN_YORK}%`);

  if (!data || data.length === 0) {
    // First event - no user entity yet
    // Archivist will create via self-introduction detection
    return null;
  }

  // Find entity with is_user_entity: true
  const userEntity = data.find(e =>
    e.metadata?.is_user_entity === true
  );

  return userEntity?.id || data[0].id;
}
```

**Flow**:
1. **Event 1**: "My name is Ryan York"
   - `getUserEntityId()` returns `null` (no entities yet)
   - Event payload: `user_entity_id: null`
   - Archivist detects self-introduction → creates Ryan York entity with `is_user_entity: true`

2. **Event 2**: "I am starting Water OS"
   - `getUserEntityId()` finds Ryan York entity
   - Event payload: `user_entity_id: "uuid-ryan-york"`
   - Archivist resolves "I" → Ryan York

### EntityResolver Implementation

**File**: `apps/ai-core/services/entity_resolver.py`

```python
class EntityResolver:
    def __init__(self):
        self.pronoun_patterns = ['i', 'me', 'my', 'mine', 'myself']

    def resolve_pronouns(
        self,
        text: str,
        user_entity_id: Optional[str]
    ) -> Dict[str, str]:
        """Map pronouns to user entity ID"""
        text_lower = text.lower()
        resolutions = {}

        if user_entity_id:
            for pronoun in self.pronoun_patterns:
                if pronoun in text_lower:
                    resolutions[pronoun] = user_entity_id

        return resolutions

    def resolve_references(
        self,
        text: str,
        user_entity_id: Optional[str],
        existing_entities: List[Dict]
    ) -> Dict[str, str]:
        """Main entry point - Phase 1 only uses pronouns"""
        return self.resolve_pronouns(text, user_entity_id)
```

**Future Phases**:
- **Phase 2**: Contextual resolution ("the company" → most recent company entity)
- **Phase 3**: LLM-powered resolution (complex references)
- **Phase 4**: Entity augmentation (update existing entities with new info)

---

## Relationship Mapping

### RelationshipMapper Implementation

**File**: `apps/ai-core/processors/relationship_mapper.py`

**Enhanced Prompt with References**:
```python
def detect_relationships(
    text: str,
    entities: List[Dict],
    existing_entities: List[Dict] = [],
    reference_map: Dict[str, str] = {}
):
    # Combine new + existing entities
    all_entities = entities + existing_entities

    # Build entity list with reference hints
    entity_list = []
    for e in all_entities:
        entity_str = f"{e['title']} ({e['type']})"

        # Add reference hints
        matching_refs = [
            ref for ref, entity_id in reference_map.items()
            if entity_id == e.get('id', e.get('entity_id'))
        ]
        if matching_refs:
            entity_str += f" [also referred to as: {', '.join(matching_refs)}]"

        entity_list.append(entity_str)

    prompt = f"""Given this text and list of entities, identify relationships.

Text: {text}

Entities (new and existing from knowledge graph):
{chr(10).join(entity_list)}

IMPORTANT: Pronouns in text may refer to existing entities.
Example: "I am starting Water OS" means the person entity relates to Water OS.

For each relationship, specify:
- from_entity: Source entity title (exact match from list)
- to_entity: Destination entity title (exact match from list)
- relationship_type: One of [belongs_to, modifies, mentions, informs, blocks,
  contradicts, relates_to, founded, works_at, manages, owns, contributes_to]
- metadata: Relevant context as JSON

Return ONLY a JSON object with a "relationships" array.
If no relationships, return {{"relationships": []}}
"""
```

**Edge Creation**:
```python
for rel in relationships:
    # Map titles to entity IDs
    from_id = entity_map.get(rel['from_entity'])
    to_id = entity_map.get(rel['to_entity'])

    if from_id and to_id:
        db.create_edge({
            'from_id': from_id,
            'to_id': to_id,
            'kind': rel['relationship_type'],
            'metadata': rel.get('metadata', {}),
            'source_event_id': event_id  # Track which event created edge
        })
```

### Alias Detection Patterns

**Regex Patterns**:
```python
rename_patterns = [
    r'renamed?\s+(?:from\s+)?["\']?(.+?)["\']?\s+to\s+["\']?(.+?)["\']?',
    r'now\s+called\s+["\']?(.+?)["\']?\s+instead\s+of\s+["\']?(.+?)["\']?',
    r'changing\s+["\']?(.+?)["\']?\s+to\s+["\']?(.+?)["\']?'
]
```

**Metadata Update**:
```python
for match in matches:
    old_name = match.group(1).strip()
    new_name = match.group(2).strip()

    # Find entity with new_name
    entity = find_entity_by_title(new_name)

    # Update metadata
    current_metadata = db.get_entity_metadata(entity.id)
    aliases = current_metadata.get('aliases', [])

    if old_name not in aliases:
        aliases.append(old_name)

    db.update_entity_metadata(entity.id, {
        **current_metadata,
        'aliases': aliases,
        'previous_names': aliases
    })
```

---

## Hub-and-Spoke Pattern

### Hub Entity Creation

**When to Create Hub**:
```python
is_hub = entity_type in ['project', 'feature', 'decision']
```

**Hub Creation**:
```python
def create_hub_entity(entity_data: dict) -> str:
    """Create hub entity for complex concepts"""
    entity_data['metadata'] = entity_data.get('metadata', {})
    entity_data['metadata']['is_hub'] = True

    return create_entity(entity_data)
```

### Spoke Entity Creation

**When to Create Spoke**:
```python
# If hub exists and event is meeting/reflection
if hub_entity_id and event.source in ['quick_capture', 'voice_debrief', 'webhook_granola']:
    spoke_type = 'meeting_note' if 'meeting' in text.lower() else 'reflection'

    spoke_id = create_spoke_entity(hub_entity_id, {
        'source_event_id': event_id,
        'type': spoke_type,
        'title': f"Note about {text[:50]}...",
        'summary': text[:200],
        'metadata': {'is_spoke': True}
    })
```

**Spoke Creation (with Edge)**:
```python
def create_spoke_entity(hub_entity_id: str, spoke_data: dict) -> str:
    """Create spoke entity linked to hub"""
    spoke_id = create_entity(spoke_data)

    # Create edge from spoke to hub
    create_edge({
        'from_id': spoke_id,
        'to_id': hub_entity_id,
        'kind': 'relates_to',
        'metadata': {'relationship': 'spoke_to_hub'},
        'source_event_id': spoke_data['source_event_id']
    })

    return spoke_id
```

### Pattern Example

**Event**: "Had meeting about Feed feature. We renamed it from 'school-update'."

**Result**:
```
Hub: Feed (feature)
├── Spoke: Meeting note about Feed feature (relates_to)
├── Edge: Feed --[belongs_to]--> Willow Project
└── Edge: Meeting note --[modifies]--> Feed (because of rename)
```

---

## Signal Scoring

### Importance Calculation

**File**: `apps/ai-core/processors/signal_scorer.py`

```python
def calculate_importance(entity_type: str, metadata: dict) -> float:
    """Entity type-based importance with user adjustments"""
    importance_map = {
        'core_identity': 1.0,
        'project': 0.85,
        'feature': 0.8,
        'decision': 0.75,
        'person': 0.7,
        'reflection': 0.65,
        'task': 0.6,
        'meeting_note': 0.5,
        'reference_document': 0.4,
    }

    base_score = importance_map.get(entity_type, 0.5)

    # User adjustments
    if metadata.get('user_importance') == 'high':
        base_score = min(1.0, base_score + 0.2)
    elif metadata.get('user_importance') == 'low':
        base_score = max(0.1, base_score - 0.2)

    return base_score
```

### Recency Calculation

**Exponential Decay Formula**:
```python
def calculate_recency(created_at: datetime, updated_at: datetime) -> float:
    """Exponential decay with configurable half-life"""
    reference_time = max(created_at, updated_at)
    age_days = (datetime.now() - reference_time).days

    # Default: 30-day half-life
    half_life_days = 30
    decay_rate = math.log(2) / half_life_days
    recency = math.exp(-decay_rate * age_days)

    return max(0.0, min(1.0, recency))
```

**Examples**:
- 0 days old: 1.0
- 30 days old: 0.5 (half-life)
- 60 days old: 0.25
- 90 days old: 0.125

### Novelty Calculation

**Based on Connections & Age**:
```python
def calculate_novelty(edge_count: int, entity_age_days: int) -> float:
    """New entities with few connections are novel"""
    connection_score = 1.0 / (1.0 + edge_count * 0.1)
    age_score = 1.0 / (1.0 + entity_age_days * 0.05)

    novelty = (connection_score + age_score) / 2.0

    return max(0.0, min(1.0, novelty))
```

**Examples**:
- New entity (0 edges, 0 days): novelty ≈ 1.0
- Medium entity (10 edges, 30 days): novelty ≈ 0.35
- Well-established (50 edges, 180 days): novelty ≈ 0.1

### Composite Score

**Weighted Combination** (optional):
```python
def calculate_composite_score(
    importance: float,
    recency: float,
    novelty: float,
    weights: dict = {'importance': 0.5, 'recency': 0.3, 'novelty': 0.2}
) -> float:
    """Single relevance metric"""
    composite = (
        importance * weights['importance'] +
        recency * weights['recency'] +
        novelty * weights['novelty']
    )
    return max(0.0, min(1.0, composite))
```

---

## Database Schema

### Tables Overview

1. **raw_events**: Universal inbox for all captured data
2. **entity**: Nodes in the knowledge graph
3. **edge**: Relationships between entities
4. **chunk**: Text segments for retrieval
5. **embedding**: Vector representations (currently disabled)
6. **signal**: Relevance scores for entities
7. **insight**: Generated insights from Mentor

### raw_events Table

```sql
CREATE TABLE raw_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  payload JSONB NOT NULL,           -- { type, content, metadata, user_id, user_entity_id }
  source TEXT NOT NULL,              -- 'quick_capture', 'voice_debrief', 'webhook_granola', etc.
  status TEXT NOT NULL,              -- 'pending_triage', 'pending_processing', 'processed', 'ignored', 'error'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_raw_events_status_created_at ON raw_events(status, created_at DESC);
```

**Status Flow**:
- Manual entries → `pending_processing` (skip triage)
- Automatic webhooks → `pending_triage` → (user triages) → `pending_processing`
- After Archivist → `processed` or `error`
- User dismisses → `ignored`

### entity Table

```sql
CREATE TABLE entity (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_event_id UUID REFERENCES raw_events(id),
  type TEXT NOT NULL,                -- Entity type
  title TEXT NOT NULL,               -- Human-readable name
  summary TEXT,                      -- AI-generated description
  metadata JSONB DEFAULT '{}',       -- Flexible metadata (aliases, is_hub, is_spoke, is_user_entity, etc.)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entity_source_event_id ON entity(source_event_id);
CREATE INDEX idx_entity_type ON entity(type);
CREATE INDEX idx_entity_title_search ON entity USING gin(to_tsvector('english', title));
```

**Metadata Examples**:
```json
// Hub entity
{
  "is_hub": true,
  "aliases": ["school-update", "feed"],
  "status": "active"
}

// User entity
{
  "is_user_entity": true,
  "user_id": "default_user"
}

// Spoke entity
{
  "is_spoke": true
}
```

### edge Table

```sql
CREATE TABLE edge (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  from_id UUID REFERENCES entity(id) ON DELETE CASCADE,
  to_id UUID REFERENCES entity(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,                -- Relationship type
  metadata JSONB DEFAULT '{}',       -- Context about relationship
  source_event_id UUID REFERENCES raw_events(id),  -- Which event created this edge
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_edge_from_to ON edge(from_id, to_id);
CREATE INDEX idx_edge_source_event_id ON edge(source_event_id);
```

**Edge Kinds**:
- `belongs_to`, `modifies`, `mentions`, `informs`, `blocks`, `contradicts`, `relates_to`
- `founded`, `works_at`, `manages`, `owns`, `contributes_to`

### chunk Table

```sql
CREATE TABLE chunk (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_id UUID REFERENCES entity(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  token_count INTEGER NOT NULL,
  hash TEXT NOT NULL UNIQUE,         -- SHA-256 for deduplication
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunk_entity_id ON chunk(entity_id);
CREATE INDEX idx_chunk_hash ON chunk(hash);
```

### embedding Table

```sql
CREATE TABLE embedding (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chunk_id UUID REFERENCES chunk(id) ON DELETE CASCADE,
  vec VECTOR(1536),                  -- pgvector type (currently zero vectors)
  model TEXT DEFAULT 'text-embedding-3-small',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embedding_chunk_id ON embedding(chunk_id);
-- Vector similarity index (when embeddings enabled):
-- CREATE INDEX idx_embedding_vec ON embedding USING ivfflat (vec vector_cosine_ops);
```

### signal Table

```sql
CREATE TABLE signal (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_id UUID REFERENCES entity(id) ON DELETE CASCADE,
  importance FLOAT NOT NULL CHECK (importance >= 0 AND importance <= 1),
  recency FLOAT NOT NULL CHECK (recency >= 0 AND recency <= 1),
  novelty FLOAT NOT NULL CHECK (novelty >= 0 AND novelty <= 1),
  last_surfaced_at TIMESTAMPTZ,     -- When Mentor last showed this to user
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signal_entity_id ON signal(entity_id);
```

---

## API Reference

### FastAPI Endpoints

**Base URL**: `http://localhost:8000`

#### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "UMG AI Core - Archivist",
  "environment": "production"
}
```

#### POST /process
Manually trigger batch processing.

**Query Parameters**:
- `batch_size` (optional): Number of events to process (default: 10)

**Response**:
```json
{
  "message": "Processing complete",
  "results": {
    "succeeded": 8,
    "failed": 2,
    "total": 10
  }
}
```

#### POST /process/event/{event_id}
Process a specific event by ID.

**Path Parameters**:
- `event_id`: UUID of the event

**Response**:
```json
{
  "success": true,
  "event_id": "uuid-123",
  "entities_created": 3,
  "edges_created": 5,
  "chunks_created": 2,
  "processing_time_seconds": 12.4
}
```

#### GET /status
Get service status and configuration.

**Response**:
```json
{
  "status": "running",
  "model": "claude-sonnet-4-5",
  "environment": "production",
  "processing_mode": "continuous",
  "last_check": "2025-10-06T10:30:00Z"
}
```

### Next.js API Routes

**Base URL**: `http://localhost:3110/api`

#### POST /events
Create new raw event (Quick Capture).

**Request Body**:
```json
{
  "type": "text",
  "content": "Had a meeting with Sarah about the Feed feature",
  "source": "quick_capture"
}
```

**Response**:
```json
{
  "success": true,
  "eventId": "uuid-123"
}
```

#### GET /archivist-log
Get 10 most recent processed events with full details.

**Response**:
```json
[
  {
    "rawEvent": {
      "id": "uuid-123",
      "payload": {...},
      "source": "quick_capture",
      "status": "processed",
      "created_at": "2025-10-06T10:00:00Z"
    },
    "createdEntities": [...],
    "createdEdges": [...],
    "summary": {
      "chunkCount": 2,
      "embeddingCount": 2,
      "signalCount": 3
    },
    "signals": [...]
  }
]
```

#### POST /archivist-reset
Delete all Archivist data (for testing).

**Response**:
```json
{
  "success": true,
  "message": "All Archivist data has been reset"
}
```

---

## Configuration

### Environment Variables

**File**: `apps/ai-core/.env`

```bash
# Supabase
SUPABASE_URL=https://mdcarckygvbcjgexvdqw.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# AI
ANTHROPIC_API_KEY=sk-ant-api03-...

# App Settings
ENVIRONMENT=production           # 'development' or 'production'
LOG_LEVEL=INFO                   # 'DEBUG', 'INFO', 'WARNING', 'ERROR'

# Processing Settings (optional)
PROCESSING_INTERVAL_SECONDS=60   # How often to check for new events
BATCH_SIZE=10                    # Events per batch
```

### Configuration Class

**File**: `apps/ai-core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # AI
    ANTHROPIC_API_KEY: str

    # App Settings
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Processing Settings
    PROCESSING_INTERVAL_SECONDS: int = 60
    BATCH_SIZE: int = 10

    # Entity Resolution Settings
    ENABLE_ENTITY_RESOLUTION: bool = True
    MAX_EXISTING_ENTITIES_FOR_RESOLUTION: int = 20

    # Signal Scoring Settings
    RECENCY_HALF_LIFE_DAYS: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Testing

### Running Tests

```bash
# From apps/ai-core/
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific test file
pytest tests/test_archivist.py

# Specific test
pytest tests/test_archivist.py::test_process_event_basic_flow
```

### Test Structure

**File**: `apps/ai-core/tests/test_archivist.py`

**Test Fixtures**:
```python
@pytest.fixture
def mock_db():
    """Mock database service"""
    db = Mock(spec=DatabaseService)
    db.get_event_by_id.return_value = Mock(
        id="uuid-123",
        payload=Mock(
            content="Test event",
            user_entity_id=None
        ),
        source="quick_capture",
        status="pending_processing"
    )
    return db

@pytest.fixture
def archivist(mock_db):
    """Archivist instance with mocked dependencies"""
    archivist = Archivist()
    archivist.db = mock_db
    return archivist
```

**Example Test**:
```python
def test_process_event_with_cross_event_resolution(archivist, mock_db):
    """Test pronoun resolution creates correct relationships"""

    # Setup: User entity exists
    mock_db.get_recent_entities.return_value = [
        {"id": "uuid-ryan", "title": "Ryan York", "type": "person"}
    ]

    # Mock event with user_entity_id
    event = Mock(
        id="uuid-event-2",
        payload=Mock(
            content="I am starting Water OS",
            user_entity_id="uuid-ryan"
        )
    )
    mock_db.get_event_by_id.return_value = event

    # Process
    result = archivist.process_event("uuid-event-2")

    # Verify relationship created
    assert result['edges_created'] >= 1

    # Check create_edge was called with founded relationship
    edge_calls = mock_db.create_edge.call_args_list
    assert any(
        call[0][0]['kind'] == 'founded'
        for call in edge_calls
    )
```

### Integration Test Example

```python
def test_full_self_introduction_flow():
    """Test complete flow from self-introduction to cross-event resolution"""

    # Reset database
    reset_archivist_data()

    # Event 1: Self-introduction
    event1_id = create_raw_event({
        "content": "My name is Ryan York. I am CTO at Willow Education.",
        "source": "quick_capture"
    })

    archivist = Archivist()
    result1 = archivist.process_event(event1_id)

    # Verify Ryan York entity created
    ryan = db.get_entity_by_title("Ryan York", "person")
    assert ryan is not None
    assert ryan.metadata.get('is_user_entity') == True

    # Event 2: Reference to self
    event2_id = create_raw_event({
        "content": "I am starting a company called Water OS",
        "source": "quick_capture",
        "user_entity_id": ryan.id
    })

    result2 = archivist.process_event(event2_id)

    # Verify Water OS entity created
    water_os = db.get_entity_by_title("Water OS", "company")
    assert water_os is not None

    # Verify relationship created
    edges = db.get_edges_for_entity(ryan.id)
    founded_edge = next(
        (e for e in edges if e['kind'] == 'founded' and e['to_id'] == water_os.id),
        None
    )
    assert founded_edge is not None
```

---

## Performance & Optimization

### Current Performance

**Processing Time**:
- Average: 10-15 seconds per event
- Breakdown:
  - Entity extraction (Claude): 3-5 seconds
  - Relationship mapping (Claude): 3-5 seconds
  - Entity resolution (Claude): 2-3 seconds (when enabled)
  - Database operations: 1-2 seconds
  - Chunking + signals: < 1 second

**API Costs** (with Claude Sonnet 4.5):
- ~3 API calls per event (extraction, relationships, resolution)
- Average cost: ~$0.02 per event
- Monthly estimate (100 events): ~$2

### Optimization Strategies

#### 1. Batch Processing
```python
# Process multiple events in parallel
async def process_batch(event_ids: List[str]):
    tasks = [process_event(event_id) for event_id in event_ids]
    results = await asyncio.gather(*tasks)
    return results
```

#### 2. Caching Recent Entities
```python
@lru_cache(maxsize=100)
def get_recent_entities_cached(limit: int = 20) -> List[Dict]:
    """Cache recent entities for 60 seconds"""
    return db.get_recent_entities(limit)
```

#### 3. Database Indexes
```sql
-- Critical indexes already created
CREATE INDEX idx_entity_source_event_id ON entity(source_event_id);
CREATE INDEX idx_edge_from_to ON edge(from_id, to_id);
CREATE INDEX idx_chunk_entity_id ON chunk(entity_id);
CREATE INDEX idx_signal_entity_id ON signal(entity_id);
CREATE INDEX idx_raw_events_status_created_at ON raw_events(status, created_at DESC);
```

#### 4. Reduce LLM Calls
```python
# Combine entity extraction + relationship detection in single call
prompt = f"""
Extract entities AND relationships in one pass:

Text: {text}

Return:
{{
  "entities": [...],
  "relationships": [...]
}}
"""
```

#### 5. Embedding Optimization (when enabled)
```python
# Batch embed multiple chunks
texts = [chunk['text'] for chunk in chunks]
embeddings = embeddings_service.generate_embeddings_batch(texts)  # Single API call
```

### Monitoring

**Logging**:
```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)

# Log processing metrics
logger.info(f"Processed event {event_id} in {elapsed_time:.2f}s")
logger.info(f"Created {len(entity_ids)} entities, {len(relationships)} edges")
```

**Performance Tracking**:
```python
import time

start_time = time.time()
result = archivist.process_event(event_id)
elapsed = time.time() - start_time

# Store in database or metrics service
db.record_processing_metric({
    'event_id': event_id,
    'duration_seconds': elapsed,
    'entities_created': result['entities_created'],
    'edges_created': result['edges_created']
})
```

---

## Troubleshooting

### Common Issues

#### 1. Duplicate Entities Created
**Symptom**: Multiple entities with same title/type

**Cause**: Mention tracker is in-memory, resets on server restart

**Fix**: Database lookup implemented (lines 116-124 in archivist.py)
```python
# Check database before creating
existing = db.get_entity_by_title(title, type)
if existing:
    return existing.id
```

#### 2. No Cross-Event Relationships
**Symptom**: "I am starting X" doesn't link to user entity

**Causes**:
- `user_entity_id` not set in event payload
- Self-introduction detection not triggered
- Entity resolver not called

**Debug**:
```python
# Check event payload
logger.debug(f"Event payload: {event.payload}")
logger.debug(f"user_entity_id: {event.payload.user_entity_id}")

# Check reference map
logger.debug(f"Reference map: {reference_map}")

# Check existing entities
logger.debug(f"Existing entities: {existing_entities}")
```

#### 3. Chunks/Embeddings Fail
**Symptom**: Foreign key constraint violations

**Cause**: Entity creation failed but ID still used

**Fix**: Try-catch around chunk creation
```python
try:
    chunk_id = db.create_chunk({
        'entity_id': entity_id,
        'text': chunk['text'],
        'token_count': chunk['token_count'],
        'hash': chunk['hash']
    })
except Exception as e:
    logger.error(f"Failed to create chunk for entity {entity_id}: {e}")
    continue
```

#### 4. Activity Log Shows Wrong Relationships
**Symptom**: Event 1 shows relationships created by Event 2

**Cause**: Log query doesn't filter by `source_event_id`

**Fix**: Migration added `source_event_id` to edge table
```sql
ALTER TABLE edge ADD COLUMN source_event_id UUID REFERENCES raw_events(id);
```

Query with filter:
```typescript
.eq('source_event_id', event.id)
```

---

## Future Enhancements

### Phase 2: Contextual Reference Resolution
- Resolve "the company", "this project" to specific entities
- Use recency + importance signals to pick best match

### Phase 3: LLM-Powered Resolution
- Use Claude to match complex references
- Pass text + existing entities to LLM for mapping

### Phase 4: Entity Augmentation
- Update existing entities with new information
- "I live in Texas" → updates Ryan York entity metadata

### Phase 5: Temporal Understanding
- Track entity state changes over time
- "I used to work at X, now I work at Y"
- Create versioned entity snapshots

### Embeddings Re-enablement
- Switch to different provider (OpenAI, Cohere, or self-hosted)
- Enable semantic search over memories
- Vector similarity for cross-domain insights

### Performance Improvements
- Database-backed mention tracker
- Redis cache for recent entities
- Async/parallel processing where possible
- Rate limiting and retry logic for API calls

---

**Last Updated**: 2025-10-08
**Status**: Production-ready
**Version**: 1.0
