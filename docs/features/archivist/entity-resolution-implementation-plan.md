# Entity Resolution & Cross-Event Relationship Implementation Plan

## Overview

**Goal**: Enable the Archivist to recognize references to existing entities across events and create relationships between them.

**Current Limitation**: The Archivist processes each event in isolation. When you mention "I am starting Water OS", it doesn't connect "I" back to "Ryan York" from a previous event.

**Desired Behavior**:
- Event 1: "My name is Ryan York..."
- Event 2: "I am starting Water OS..."
- Result: Create relationship "Ryan York --[founded]--> Water OS"

---

## Architecture Components

### 1. Entity Resolution Service
**Purpose**: Match pronouns and references in new text to existing entities in the graph.

**Location**: `apps/ai-core/services/entity_resolver.py`

**Key Methods**:
```python
class EntityResolver:
    def resolve_references(
        self,
        text: str,
        extracted_entities: List[Dict],
        existing_entities: List[Dict],
        context: Dict
    ) -> Dict[str, str]:
        """
        Map pronouns/references to existing entity IDs

        Returns:
            {
                "I": "entity_id_for_ryan_york",
                "the company": "entity_id_for_willow_ed",
                "my business": "entity_id_for_water_os"
            }
        """
```

**Resolution Strategies**:
1. **Pronoun Resolution** (I, me, my, we, our)
   - Use event metadata to determine speaker/author
   - Map to person entities associated with that user

2. **Contextual References** (the company, this project, the feature)
   - Use recency signals + type matching
   - "the company" → most recent company entity with high importance

3. **Fuzzy Name Matching** (Water, WaterOS, water-os)
   - Use existing fuzzy matcher utility
   - Match partial names to full entity titles

4. **LLM-Powered Resolution** (complex cases)
   - Pass text + list of existing entities to Claude
   - Ask: "Which existing entities are referenced in this text?"

---

## Implementation Phases

### Phase 1: Basic Pronoun Resolution (1-2 days)

**Goal**: Map "I/me/my" to the primary user entity.

**Changes**:

1. **Add User Context to Events**
   ```python
   # apps/ai-core/models/raw_event.py
   class RawEventPayload(BaseModel):
       content: str
       metadata: Optional[Dict[str, Any]] = {}
       user_id: Optional[str] = None  # NEW
       user_entity_id: Optional[str] = None  # NEW - link to person entity
   ```

2. **Update Quick Capture API**
   ```typescript
   // apps/web/app/api/events/route.ts
   const payload = {
       type: 'quick_capture',
       content: text,
       metadata: {},
       user_id: 'default_user',  // NEW - later from auth
       user_entity_id: await getUserEntityId('default_user')  // NEW
   };
   ```

3. **Create Entity Resolver Service**
   ```python
   # apps/ai-core/services/entity_resolver.py
   class EntityResolver:
       def __init__(self):
           self.pronoun_patterns = ['i', 'me', 'my', 'mine', 'myself']

       def resolve_pronouns(
           self,
           text: str,
           user_entity_id: Optional[str]
       ) -> Dict[str, str]:
           """Basic pronoun → entity mapping"""
           text_lower = text.lower()
           resolutions = {}

           # If user_entity_id exists, map first-person pronouns
           if user_entity_id:
               for pronoun in self.pronoun_patterns:
                   if pronoun in text_lower:
                       resolutions[pronoun] = user_entity_id

           return resolutions
   ```

4. **Update Archivist to Use Resolver**
   ```python
   # apps/ai-core/agents/archivist.py (in process_event)

   # After entity extraction (line ~73)
   extracted_entities = self.entity_extractor.extract_entities(cleaned_text)

   # NEW: Resolve references to existing entities
   user_entity_id = event.payload.user_entity_id
   reference_map = self.entity_resolver.resolve_pronouns(
       cleaned_text,
       user_entity_id
   )

   # NEW: Fetch relevant existing entities
   existing_entities = self.db.get_recent_entities(limit=20)

   # Step 6: Relationship Mapping (UPDATE - line ~146)
   relationships = self.relationship_mapper.detect_relationships(
       cleaned_text,
       extracted_entities,
       existing_entities=existing_entities,  # PASS existing entities
       reference_map=reference_map  # PASS pronoun resolutions
   )
   ```

**Database Changes**:
```sql
-- Add user_entity_id to raw_events payload
-- No schema changes needed - already stored in JSONB payload
```

**Testing**:
- Event 1: "My name is Ryan York"
- Event 2: "I am starting Water OS"
- Expected: Creates "Ryan York --[founded]--> Water OS" relationship

---

### Phase 2: Contextual Reference Resolution (2-3 days)

**Goal**: Resolve "the company", "this project", etc. to specific entities.

**Changes**:

1. **Add Contextual Resolution Method**
   ```python
   # apps/ai-core/services/entity_resolver.py

   def resolve_contextual_references(
       self,
       text: str,
       existing_entities: List[Dict]
   ) -> Dict[str, str]:
       """
       Resolve contextual references like:
       - "the company" → most recent company entity
       - "this project" → most recent project entity
       - "the feature" → most recent feature entity
       """
       resolutions = {}
       text_lower = text.lower()

       # Pattern: "the [entity_type]"
       reference_patterns = {
           'the company': 'company',
           'the business': 'company',
           'this project': 'project',
           'the project': 'project',
           'the feature': 'feature',
           'this feature': 'feature',
       }

       for pattern, entity_type in reference_patterns.items():
           if pattern in text_lower:
               # Find most recent entity of this type
               matching_entities = [
                   e for e in existing_entities
                   if e['type'] == entity_type
               ]

               if matching_entities:
                   # Sort by recency + importance
                   best_match = max(
                       matching_entities,
                       key=lambda e: e.get('signal', {}).get('recency', 0)
                   )
                   resolutions[pattern] = best_match['id']

       return resolutions
   ```

2. **Update Database Service to Include Signals**
   ```python
   # apps/ai-core/services/database.py

   def get_recent_entities(
       self,
       limit: int = 20,
       include_signals: bool = True
   ) -> List[Dict]:
       """Fetch recent entities with optional signal data"""
       query = self.supabase.table('entity').select(
           'id, title, type, created_at, updated_at, metadata'
       )

       if include_signals:
           query = query.select(
               'id, title, type, created_at, updated_at, metadata, '
               'signal(importance, recency, novelty)'
           )

       result = query.order('created_at', desc=True).limit(limit).execute()
       return result.data
   ```

**Testing**:
- Event 1: "Starting Water OS, a water infrastructure company"
- Event 2: "The company will focus on NRW reduction"
- Expected: "the company" resolves to Water OS entity

---

### Phase 3: LLM-Powered Entity Resolution (3-4 days)

**Goal**: Use Claude to intelligently match complex references.

**Changes**:

1. **Add LLM Resolution Method**
   ```python
   # apps/ai-core/services/entity_resolver.py

   from anthropic import Anthropic
   from config import settings

   class EntityResolver:
       def __init__(self):
           self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
           # ... other init

       def resolve_with_llm(
           self,
           text: str,
           extracted_entities: List[Dict],
           existing_entities: List[Dict]
       ) -> Dict[str, str]:
           """
           Use LLM to map references in text to existing entities

           Returns:
               {
                   "reference_text": "entity_id",
                   "I": "uuid-for-ryan-york",
                   "Water OS": "uuid-for-water-os"
               }
           """

           # Build entity list for prompt
           entity_list = [
               f"{e['id'][:8]}: {e['title']} ({e['type']})"
               for e in existing_entities
           ]

           prompt = f"""You are analyzing a new text to identify which existing entities are referenced.

New Text:
{text}

Existing Entities in Knowledge Graph:
{chr(10).join(entity_list)}

Task: Identify ALL references in the new text that map to existing entities.

Examples:
- "I" or "me" → person entity of the author
- "my company" → company entity the author works at
- Partial names → full entity names (e.g., "Water" → "Water OS")

Return ONLY a JSON object mapping references to entity IDs:
{{
  "I": "entity_id_short_form",
  "my company": "entity_id_short_form",
  "Water": "entity_id_short_form"
}}

If no references found, return {{}}.
"""

           try:
               response = self.client.messages.create(
                   model="claude-sonnet-4-5",
                   max_tokens=1024,
                   temperature=0.2,  # Lower temperature for consistency
                   messages=[{"role": "user", "content": prompt}]
               )

               content = response.content[0].text.strip()

               # Strip markdown if present
               if content.startswith("```"):
                   lines = content.split("\n")
                   content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                   content = content.replace("```json", "").replace("```", "").strip()

               resolutions = json.loads(content)

               # Map short IDs back to full UUIDs
               id_map = {e['id'][:8]: e['id'] for e in existing_entities}
               full_resolutions = {
                   ref: id_map.get(short_id, short_id)
                   for ref, short_id in resolutions.items()
               }

               logger.info(f"LLM resolved {len(full_resolutions)} entity references")
               return full_resolutions

           except Exception as e:
               logger.error(f"Error in LLM entity resolution: {e}")
               return {}
   ```

2. **Update Relationship Mapper to Use Resolutions**
   ```python
   # apps/ai-core/processors/relationship_mapper.py

   def detect_relationships(
       self,
       text: str,
       entities: List[Dict],
       existing_entities: List[Dict] = [],
       reference_map: Dict[str, str] = {}  # NEW parameter
   ) -> List[Dict]:
       """
       Detect relationships between entities using GPT-4

       Args:
           text: Source text
           entities: Newly extracted entities
           existing_entities: Entities from knowledge graph
           reference_map: Mapping of references to entity IDs
       """

       # Combine new + existing entities
       all_entities = entities + existing_entities

       if len(all_entities) < 2:
           return []

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

       # Updated prompt with reference awareness
       prompt = f"""Given this text and list of entities, identify relationships between them.

Text: {text}

Entities (new and existing from knowledge graph):
{chr(10).join(entity_list)}

IMPORTANT: Consider that pronouns and references in the text may refer to existing entities.
For example, "I am starting Water OS" means the person entity relates to Water OS.

For each relationship, specify:
- from_entity: The source entity title (must match exactly from the list above)
- to_entity: The destination entity title (must match exactly from the list above)
- relationship_type: One of [belongs_to, modifies, mentions, informs, blocks, contradicts, relates_to, founded, works_at]
- metadata: Any relevant context as a JSON object

Return ONLY a JSON object with a "relationships" array.
If no relationships exist, return {{"relationships": []}}"""

       # ... rest of method (LLM call, parsing, etc.)
   ```

**Testing**:
- Event 1: "My name is Ryan York. I work at Willow Ed."
- Event 2: "I am starting a new company called Water OS."
- Event 3: "Water will launch in Ghana first."
- Expected relationships:
  - "Ryan York --[works_at]--> Willow Ed"
  - "Ryan York --[founded]--> Water OS"
  - "Water" resolves to "Water OS" entity

---

### Phase 4: Relationship Type Enhancement (1 day)

**Goal**: Add more specific relationship types for richer context.

**New Relationship Types**:
```python
# apps/ai-core/processors/relationship_mapper.py

RELATIONSHIP_TYPES = {
    # Existing
    'belongs_to': 'Hierarchical ownership',
    'modifies': 'Changes or updates',
    'mentions': 'Simple reference',
    'informs': 'Knowledge transfer',
    'blocks': 'Dependencies',
    'contradicts': 'Tensions',
    'relates_to': 'General connection',

    # NEW - Professional
    'works_at': 'Employment relationship',
    'founded': 'Founder/creator relationship',
    'manages': 'Management relationship',
    'reports_to': 'Organizational hierarchy',

    # NEW - Project
    'owns': 'Ownership/responsibility',
    'contributes_to': 'Contributing to project/feature',
    'uses': 'Tool/resource usage',

    # NEW - Knowledge
    'learned_from': 'Learning/insight source',
    'inspired_by': 'Inspiration source',
    'supersedes': 'Replaces/deprecates',
}
```

**Update Prompt**:
```python
prompt = f"""...
- relationship_type: One of [
    belongs_to, modifies, mentions, informs, blocks, contradicts, relates_to,
    founded, works_at, manages, reports_to, owns, contributes_to, uses,
    learned_from, inspired_by, supersedes
]

Relationship type meanings:
- works_at: Person works at a company
- founded: Person founded/started a company or project
- manages: Person manages a project or team
- owns: Person/entity owns or is responsible for something
- contributes_to: Person contributes to a project
- uses: Entity uses a tool/resource
...
"""
```

---

### Phase 5: Entity Update & Augmentation (2 days)

**Goal**: Update existing entities with new information from subsequent mentions.

**Example**:
- Event 1: "My name is Ryan York"
- Event 2: "I live in Texas"
- Result: Update Ryan York entity's metadata with location

**Changes**:

1. **Add Entity Augmentation Method**
   ```python
   # apps/ai-core/services/entity_augmenter.py

   class EntityAugmenter:
       def __init__(self, db):
           self.db = db
           self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

       def augment_entity(
           self,
           entity_id: str,
           new_text: str,
           reference: str
       ) -> Dict:
           """
           Extract new information about an entity from text

           Args:
               entity_id: Existing entity to augment
               new_text: New text mentioning the entity
               reference: How entity was referenced ("I", "Ryan", etc.)

           Returns:
               Dict of metadata updates to apply
           """

           # Fetch current entity
           entity = self.db.get_entity_by_id(entity_id)

           prompt = f"""You are analyzing new text that mentions an existing entity.

Existing Entity:
- Title: {entity.title}
- Type: {entity.type}
- Current Summary: {entity.summary}
- Current Metadata: {json.dumps(entity.metadata, indent=2)}

New Text:
{new_text}

Reference in text: "{reference}"

Task: Extract any NEW information about this entity from the text.

Return a JSON object with:
{{
  "summary_update": "Updated one-sentence summary (or null if no change)",
  "metadata_additions": {{
    "new_field": "new_value",
    "location": "Texas",
    "role": "CTO"
  }},
  "has_changes": true/false
}}

Only include information explicitly stated in the new text.
If no new information, return {{"has_changes": false}}.
"""

           # ... LLM call and processing

       def should_augment(
           self,
           entity: Dict,
           text: str
       ) -> bool:
           """Determine if entity likely has new info in text"""
           # Simple heuristic: if entity mentioned in detail
           return len(text) > 50 and entity['title'].lower() in text.lower()
   ```

2. **Integrate into Archivist Pipeline**
   ```python
   # apps/ai-core/agents/archivist.py (in process_event)

   # After entity resolution (new step after line ~73)
   for reference, entity_id in reference_map.items():
       entity = self.db.get_entity_by_id(entity_id)

       if self.entity_augmenter.should_augment(entity, cleaned_text):
           updates = self.entity_augmenter.augment_entity(
               entity_id,
               cleaned_text,
               reference
           )

           if updates.get('has_changes'):
               self.db.update_entity(entity_id, updates)
               logger.info(f"Augmented entity {entity.title} with new info")
   ```

---

## Testing Strategy

### Unit Tests
```python
# apps/ai-core/tests/test_entity_resolver.py

def test_pronoun_resolution():
    resolver = EntityResolver()
    user_entity_id = "uuid-123"

    text = "I am starting a company"
    resolutions = resolver.resolve_pronouns(text, user_entity_id)

    assert resolutions['i'] == user_entity_id

def test_contextual_resolution():
    resolver = EntityResolver()

    existing_entities = [
        {'id': 'uuid-water', 'title': 'Water OS', 'type': 'company',
         'signal': {'recency': 1.0}}
    ]

    text = "The company will launch in Ghana"
    resolutions = resolver.resolve_contextual_references(text, existing_entities)

    assert resolutions['the company'] == 'uuid-water'

def test_llm_resolution():
    resolver = EntityResolver()

    existing_entities = [
        {'id': 'uuid-ryan', 'title': 'Ryan York', 'type': 'person'},
        {'id': 'uuid-water', 'title': 'Water OS', 'type': 'company'}
    ]

    text = "I am the founder of Water"
    resolutions = resolver.resolve_with_llm(text, [], existing_entities)

    assert 'I' in resolutions
    assert 'Water' in resolutions
```

### Integration Tests
```python
# apps/ai-core/tests/test_cross_event_relationships.py

def test_cross_event_relationship_creation():
    archivist = Archivist()

    # Event 1: Create Ryan York
    event1_id = create_test_event({
        'content': 'My name is Ryan York',
        'user_entity_id': None
    })
    result1 = archivist.process_event(event1_id)
    ryan_id = result1['entity_ids'][0]

    # Event 2: Create Water OS with relationship to Ryan
    event2_id = create_test_event({
        'content': 'I am starting Water OS',
        'user_entity_id': ryan_id
    })
    result2 = archivist.process_event(event2_id)

    # Assert relationship was created
    assert result2['edges_created'] >= 1

    # Verify relationship exists
    edges = db.get_edges_for_entity(ryan_id)
    assert any(
        edge['kind'] == 'founded' and
        edge['to_entity']['title'] == 'Water OS'
        for edge in edges
    )
```

### End-to-End Tests
```python
def test_full_user_story():
    """Test realistic user journey"""

    # Day 1: User intro
    submit_event("My name is Ryan York. I'm CTO at Willow Ed.")

    # Day 2: New project
    submit_event("I'm starting a new company called Water OS")

    # Day 3: Project update
    submit_event("Water OS will focus on leak detection in Ghana")

    # Verify knowledge graph
    ryan = get_entity_by_title("Ryan York")
    willow = get_entity_by_title("Willow Ed")
    water = get_entity_by_title("Water OS")

    assert ryan is not None
    assert willow is not None
    assert water is not None

    # Verify relationships
    assert has_relationship(ryan, 'works_at', willow)
    assert has_relationship(ryan, 'founded', water)

    # Verify entity updates
    assert 'CTO' in ryan.metadata.get('role', '')
    assert 'Ghana' in water.metadata.get('target_markets', [])
```

---

## Migration & Deployment

### Database Migrations
```sql
-- No schema changes needed
-- All new data stored in existing JSONB fields

-- Optional: Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_entity_title_search
ON entity USING gin(to_tsvector('english', title));

CREATE INDEX IF NOT EXISTS idx_entity_metadata
ON entity USING gin(metadata);
```

### Configuration
```python
# apps/ai-core/config.py

class Settings(BaseSettings):
    # ... existing settings

    # Entity Resolution Settings
    ENABLE_ENTITY_RESOLUTION: bool = True
    ENABLE_LLM_RESOLUTION: bool = True
    ENABLE_ENTITY_AUGMENTATION: bool = True

    # Performance Settings
    MAX_EXISTING_ENTITIES_FOR_RESOLUTION: int = 50
    ENTITY_RESOLUTION_TIMEOUT_SECONDS: int = 10
```

### Rollout Plan

**Week 1: Phase 1** (Basic Pronoun Resolution)
- Implement EntityResolver with pronoun mapping
- Add user_entity_id to event payload
- Update Archivist to pass user context
- Deploy to staging
- Test with 10-20 events
- Monitor for errors

**Week 2: Phase 2** (Contextual References)
- Add contextual resolution methods
- Update database queries to include signals
- Test "the company", "this project" patterns
- Deploy to staging

**Week 3: Phase 3** (LLM Resolution)
- Implement LLM-powered resolution
- Update relationship mapper
- Extensive testing with complex references
- Monitor API costs (Claude calls)
- Deploy to production with feature flag

**Week 4: Phases 4-5** (Enhancements)
- Add new relationship types
- Implement entity augmentation
- Performance optimization
- Documentation updates

---

## Performance Considerations

### API Costs
- **Current**: ~2 Claude API calls per event (entity extraction + relationship mapping)
- **After Implementation**: ~3 calls per event (+ entity resolution)
- **Cost Impact**: +50% API usage
- **Mitigation**: Cache entity resolutions, use smaller models for simple resolution

### Latency
- **Current**: ~10-15 seconds per event
- **After Implementation**: ~15-20 seconds per event
- **Mitigation**:
  - Run resolution in parallel with entity extraction
  - Limit existing entities passed to resolver (max 50)
  - Add timeout to LLM resolution (10s max)

### Database Load
- **New Queries**: Fetch recent entities per event
- **Mitigation**:
  - Cache recent entities (TTL: 60s)
  - Add database indexes on commonly queried fields
  - Limit to 20-50 most recent entities

---

## Success Metrics

### Functional Metrics
- **Cross-Event Relationship Detection Rate**: Target 80%+
  - Measure: # of events with cross-event relationships / # of events with pronoun references

- **Entity Resolution Accuracy**: Target 90%+
  - Measure: Manual review of 100 resolved references

- **Entity Augmentation Rate**: Target 30%+
  - Measure: # of entities updated with new info / # of entity re-mentions

### Performance Metrics
- **Processing Time**: < 20 seconds per event (P95)
- **API Cost**: < $0.05 per event processed
- **Error Rate**: < 5% of events fail resolution

### User Experience Metrics
- **Knowledge Graph Completeness**: Measure relationship density
  - Target: Average 3+ edges per entity

- **Duplicate Entity Rate**: Target < 5%
  - Measure: Entities that should have been resolved to existing entities

---

## Future Enhancements

### Phase 6: Temporal Understanding
- Track entity state changes over time
- "I used to work at X, now I work at Y"
- Create versioned entity snapshots

### Phase 7: Multi-User Support
- Resolve "we" and "us" to team entities
- Handle conversations between multiple users
- Attribute statements to correct person

### Phase 8: Conflict Resolution
- Handle contradictory information
- "Actually, the launch is in Uganda, not Ghana"
- Update or version conflicting facts

### Phase 9: Smart Prompting
- Proactively ask clarifying questions
- "You mentioned 'the company' - did you mean Water OS or Willow Ed?"
- Interactive entity resolution

---

## Open Questions

1. **User Entity Bootstrapping**: How do we create the initial user entity?
   - Option A: Explicit onboarding flow
   - Option B: First event auto-creates user entity
   - Option C: Infer from auth/profile data

2. **Confidence Scoring**: Should we add confidence scores to resolutions?
   - Track how certain we are about each resolution
   - Allow manual correction in UI

3. **Cross-User Privacy**: If multi-user, how do we handle entity visibility?
   - User A mentions User B - should User B see this?
   - Team vs. personal knowledge graphs

4. **Disambiguation UI**: When resolution is uncertain, should we ask the user?
   - "Did 'the company' refer to Water OS or Willow Ed?"
   - Trade-off: accuracy vs. friction

---

## Conclusion

This implementation plan adds critical "memory" capabilities to the Archivist, enabling it to build a truly connected knowledge graph across events. The phased approach allows for incremental development and testing, with clear success metrics at each stage.

**Recommended Start**: Begin with Phase 1 (Basic Pronoun Resolution) as it provides immediate value with minimal complexity. This can be implemented in 1-2 days and will handle the most common case (first-person references).

**Estimated Total Timeline**: 2-3 weeks for Phases 1-3, with Phases 4-5 as follow-on enhancements.
