# Archivist Agent: Implementation Plan

## Overview

This document outlines the step-by-step implementation plan for building the Archivist agent—the intelligent processing engine that transforms raw events into a structured memory graph.

## Tech Stack

**Language**: Python 3.11+
**Framework**: FastAPI (async REST API)
**AI/ML Libraries**:
- `langchain` - LLM orchestration
- `openai` - GPT-4 and embedding API access
- `spacy` - Named Entity Recognition (NER)
- `tiktoken` - Token counting

**Database**:
- `supabase-py` - Python client for Supabase
- Direct SQL via `psycopg2` for complex queries

**Infrastructure**:
- Background processing via `celery` or simple async workers
- Scheduled tasks via `apscheduler`

## Project Structure

```
apps/
└── ai-core/
    ├── pyproject.toml           # Poetry/pip dependencies
    ├── main.py                  # FastAPI app entry point
    ├── config.py                # Environment variables and settings
    ├── requirements.txt         # Python dependencies
    │
    ├── agents/
    │   ├── __init__.py
    │   ├── archivist.py         # Main Archivist orchestrator
    │   ├── feedback_processor.py # User feedback processing
    │   └── mentor.py            # Mentor agent (future)
    │
    ├── services/
    │   ├── __init__.py
    │   ├── database.py          # Supabase client wrapper
    │   ├── embeddings.py        # OpenAI embeddings API
    │   ├── llm.py               # LLM calls (GPT-4)
    │   └── chunker.py           # Text chunking logic
    │
    ├── processors/
    │   ├── __init__.py
    │   ├── entity_extractor.py  # Entity recognition
    │   ├── relationship_mapper.py # Edge creation
    │   ├── signal_scorer.py     # Importance/recency/novelty scoring
    │   └── mention_tracker.py   # Entity mention tracking & promotion
    │
    ├── models/
    │   ├── __init__.py
    │   ├── raw_event.py         # Pydantic models matching DB schema
    │   ├── entity.py
    │   ├── edge.py
    │   └── chunk.py
    │
    ├── utils/
    │   ├── __init__.py
    │   ├── text_cleaner.py      # Text normalization
    │   └── fuzzy_matcher.py     # Entity deduplication
    │
    └── tests/
        ├── __init__.py
        ├── test_archivist.py
        ├── test_entity_extractor.py
        └── fixtures/
            └── sample_events.json
```

## Implementation Phases

### Phase 0: Project Setup (Day 1)

**Goal**: Get the Python project scaffolded and connected to Supabase.

#### Tasks

1. **Create `apps/ai-core` directory**
   ```bash
   mkdir -p apps/ai-core
   cd apps/ai-core
   ```

2. **Initialize Python project**
   ```bash
   # Using Poetry (recommended)
   poetry init

   # Or using pip + requirements.txt
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Install core dependencies**
   ```bash
   poetry add fastapi uvicorn supabase openai langchain spacy tiktoken python-dotenv pydantic
   poetry add --group dev pytest black ruff

   # Download spaCy English model
   python -m spacy download en_core_web_sm
   ```

4. **Create `.env` file**
   ```
   SUPABASE_URL=https://mdcarckygvbcjgexvdqw.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   OPENAI_API_KEY=your-openai-key
   ENVIRONMENT=development
   LOG_LEVEL=INFO
   ```

5. **Create basic FastAPI app** (`main.py`)
   ```python
   from fastapi import FastAPI
   from config import settings

   app = FastAPI(title="UMG AI Core", version="0.1.0")

   @app.get("/health")
   async def health_check():
       return {"status": "healthy", "environment": settings.ENVIRONMENT}

   @app.post("/process")
   async def trigger_processing():
       """Manually trigger Archivist processing"""
       # TODO: Implement
       return {"message": "Processing started"}

   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)
   ```

6. **Create config.py**
   ```python
   from pydantic_settings import BaseSettings

   class Settings(BaseSettings):
       SUPABASE_URL: str
       SUPABASE_SERVICE_ROLE_KEY: str
       OPENAI_API_KEY: str
       ENVIRONMENT: str = "development"
       LOG_LEVEL: str = "INFO"

       class Config:
           env_file = ".env"

   settings = Settings()
   ```

7. **Test the setup**
   ```bash
   python main.py
   # Visit http://localhost:8000/docs to see FastAPI docs
   ```

**Success Criteria**: FastAPI server runs, `/health` endpoint responds, Supabase connection works.

---

### Phase 1: Database Layer (Day 1-2)

**Goal**: Create Python models matching the database schema and basic CRUD operations.

#### Tasks

1. **Create Pydantic models** (`models/raw_event.py`)
   ```python
   from pydantic import BaseModel
   from typing import Optional, Dict, Any
   from datetime import datetime

   class RawEventPayload(BaseModel):
       type: str  # 'text', 'voice', 'webhook'
       content: str
       metadata: Dict[str, Any] = {}

   class RawEvent(BaseModel):
       id: str
       payload: RawEventPayload
       source: str
       status: str
       created_at: datetime

       class Config:
           from_attributes = True
   ```

2. **Create models for entity, edge, chunk, embedding, signal**
   - `models/entity.py`
   - `models/edge.py`
   - `models/chunk.py`
   - etc.

3. **Create database service** (`services/database.py`)
   ```python
   from supabase import create_client, Client
   from config import settings
   from typing import List, Optional
   from models.raw_event import RawEvent

   class DatabaseService:
       def __init__(self):
           self.client: Client = create_client(
               settings.SUPABASE_URL,
               settings.SUPABASE_SERVICE_ROLE_KEY
           )

       def get_pending_events(self, limit: int = 10) -> List[RawEvent]:
           """Fetch events with status='pending_processing' (excludes triage and ignored)"""
           response = self.client.table('raw_events') \
               .select('*') \
               .eq('status', 'pending_processing') \
               .order('created_at', desc=False) \
               .limit(limit) \
               .execute()

           return [RawEvent(**event) for event in response.data]

       def update_event_status(self, event_id: str, status: str):
           """Update event status after processing"""
           self.client.table('raw_events') \
               .update({'status': status}) \
               .eq('id', event_id) \
               .execute()

       def create_entity(self, entity_data: dict) -> str:
           """Create new entity, return ID"""
           response = self.client.table('entity') \
               .insert(entity_data) \
               .execute()
           return response.data[0]['id']

       def get_entity_metadata(self, entity_id: str) -> dict:
           """Get entity metadata"""
           response = self.client.table('entity') \
               .select('metadata') \
               .eq('id', entity_id) \
               .single() \
               .execute()
           return response.data.get('metadata', {})

       def update_entity_metadata(self, entity_id: str, metadata: dict):
           """Update entity metadata (for aliases, etc.)"""
           self.client.table('entity') \
               .update({'metadata': metadata}) \
               .eq('id', entity_id) \
               .execute()

       def create_hub_entity(self, entity_data: dict) -> str:
           """Create hub entity for complex concepts (e.g., 'Feed feature')"""
           # Mark as hub in metadata
           entity_data['metadata'] = entity_data.get('metadata', {})
           entity_data['metadata']['is_hub'] = True
           return self.create_entity(entity_data)

       def create_spoke_entity(self, hub_entity_id: str, spoke_data: dict) -> str:
           """Create spoke entity linked to hub (e.g., meeting_note about Feed)"""
           spoke_id = self.create_entity(spoke_data)

           # Create edge from spoke to hub
           self.create_edge({
               'from_id': spoke_id,
               'to_id': hub_entity_id,
               'kind': 'relates_to',
               'metadata': {'relationship': 'spoke_to_hub'}
           })

           return spoke_id

       def create_edge(self, edge_data: dict) -> str:
           """Create new edge, return ID"""
           response = self.client.table('edge') \
               .insert(edge_data) \
               .execute()
           return response.data[0]['id']

       def create_chunk(self, chunk_data: dict) -> str:
           """Create chunk, return ID"""
           response = self.client.table('chunk') \
               .insert(chunk_data) \
               .execute()
           return response.data[0]['id']

       def create_embedding(self, embedding_data: dict):
           """Create embedding for chunk"""
           self.client.table('embedding') \
               .insert(embedding_data) \
               .execute()

       def create_signal(self, signal_data: dict):
           """Create signal for entity"""
           self.client.table('signal') \
               .insert(signal_data) \
               .execute()

   db = DatabaseService()
   ```

4. **Test database operations**
   ```python
   # In tests/test_database.py
   def test_fetch_pending_events():
       events = db.get_pending_events(limit=5)
       assert isinstance(events, list)
   ```

**Success Criteria**: Can fetch pending events, create entities/edges/chunks in database from Python.

---

### Phase 2: Text Processing Pipeline (Day 2-3)

**Goal**: Build the core text processing utilities (cleaning, chunking, token counting).

#### Tasks

1. **Create text cleaner** (`utils/text_cleaner.py`)
   ```python
   import re

   class TextCleaner:
       @staticmethod
       def clean(text: str) -> str:
           """Clean and normalize text"""
           # Remove excessive whitespace
           text = re.sub(r'\s+', ' ', text)

           # Remove markdown artifacts
           text = re.sub(r'\*\*', '', text)
           text = re.sub(r'__', '', text)

           # Normalize quotes
           text = text.replace('"', '"').replace('"', '"')

           # Strip leading/trailing whitespace
           text = text.strip()

           return text
   ```

2. **Create chunker** (`services/chunker.py`)
   ```python
   import tiktoken
   from typing import List, Dict
   import hashlib

   class Chunker:
       def __init__(self, target_tokens: int = 500, overlap_tokens: int = 50):
           self.target_tokens = target_tokens
           self.overlap_tokens = overlap_tokens
           self.encoding = tiktoken.get_encoding("cl100k_base")

       def chunk_text(self, text: str) -> List[Dict]:
           """Split text into chunks with overlap"""
           # Split on paragraphs first
           paragraphs = text.split('\n\n')

           chunks = []
           current_chunk = []
           current_tokens = 0

           for para in paragraphs:
               para_tokens = len(self.encoding.encode(para))

               if current_tokens + para_tokens > self.target_tokens and current_chunk:
                   # Save current chunk
                   chunk_text = '\n\n'.join(current_chunk)
                   chunks.append({
                       'text': chunk_text,
                       'token_count': current_tokens,
                       'hash': hashlib.sha256(chunk_text.encode()).hexdigest()
                   })

                   # Start new chunk with overlap
                   current_chunk = current_chunk[-1:]  # Keep last paragraph for overlap
                   current_tokens = len(self.encoding.encode(current_chunk[0])) if current_chunk else 0

               current_chunk.append(para)
               current_tokens += para_tokens

           # Add final chunk
           if current_chunk:
               chunk_text = '\n\n'.join(current_chunk)
               chunks.append({
                   'text': chunk_text,
                   'token_count': current_tokens,
                   'hash': hashlib.sha256(chunk_text.encode()).hexdigest()
               })

           return chunks
   ```

3. **Test chunking**
   ```python
   def test_chunker():
       chunker = Chunker(target_tokens=100, overlap_tokens=20)
       text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
       chunks = chunker.chunk_text(text)
       assert len(chunks) > 0
       assert all('hash' in c for c in chunks)
   ```

**Success Criteria**: Text is properly cleaned, chunked into ~500 token pieces with overlap, hashed for deduplication.

---

### Phase 3: Entity Extraction (Day 3-5)

**Goal**: Implement entity recognition using NER + LLM, including mention tracking and promotion logic.

#### Tasks

1. **Create mention tracker** (`processors/mention_tracker.py`)
   ```python
   from typing import Dict, Optional, List
   from datetime import datetime, timedelta

   class MentionTracker:
       """Tracks entity mentions across events to determine promotion to full entity"""

       def __init__(self):
           # In production, this would be database-backed
           # For now, maintain in-memory cache
           self.mention_cache: Dict[str, Dict] = {}

       def record_mention(
           self,
           entity_text: str,
           entity_type: str,
           event_id: str,
           is_primary_subject: bool = False
       ) -> Dict:
           """Record a mention of an entity"""
           normalized_key = self._normalize_entity_name(entity_text)

           if normalized_key not in self.mention_cache:
               self.mention_cache[normalized_key] = {
                   'text': entity_text,
                   'type': entity_type,
                   'mention_count': 0,
                   'events': [],
                   'first_seen': datetime.now(),
                   'last_seen': datetime.now(),
                   'is_promoted': False
               }

           mention = self.mention_cache[normalized_key]
           mention['mention_count'] += 1
           mention['last_seen'] = datetime.now()

           if event_id not in mention['events']:
               mention['events'].append(event_id)

           return mention

       def should_promote(
           self,
           entity_text: str,
           is_primary_subject: bool = False
       ) -> bool:
           """Determine if entity should be promoted to full entity node"""
           # Rule 1: Immediate promotion if entity is primary subject
           if is_primary_subject:
               return True

           normalized_key = self._normalize_entity_name(entity_text)

           if normalized_key not in self.mention_cache:
               return False

           mention = self.mention_cache[normalized_key]

           # Rule 2: Promote after 2-3 mentions across different events
           if mention['mention_count'] >= 2 and len(mention['events']) >= 2:
               return True

           # Rule 3: Don't promote if already promoted
           if mention['is_promoted']:
               return False

           return False

       def mark_promoted(self, entity_text: str, entity_id: str):
           """Mark entity as promoted to avoid duplicate creation"""
           normalized_key = self._normalize_entity_name(entity_text)

           if normalized_key in self.mention_cache:
               self.mention_cache[normalized_key]['is_promoted'] = True
               self.mention_cache[normalized_key]['entity_id'] = entity_id

       def get_existing_entity_id(self, entity_text: str) -> Optional[str]:
           """Get entity ID if already promoted"""
           normalized_key = self._normalize_entity_name(entity_text)
           mention = self.mention_cache.get(normalized_key)

           if mention and mention.get('is_promoted'):
               return mention.get('entity_id')

           return None

       def _normalize_entity_name(self, name: str) -> str:
           """Normalize entity name for comparison"""
           return name.lower().strip().replace('  ', ' ')
   ```

2. **Create entity extractor** (`processors/entity_extractor.py`)
   ```python
   import spacy
   from openai import OpenAI
   from typing import List, Dict
   from config import settings

   class EntityExtractor:
       def __init__(self):
           self.nlp = spacy.load("en_core_web_sm")
           self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

       def extract_with_ner(self, text: str) -> List[Dict]:
           """Use spaCy NER for basic extraction"""
           doc = self.nlp(text)
           entities = []

           for ent in doc.ents:
               entities.append({
                   'text': ent.text,
                   'type': self._map_spacy_type(ent.label_),
                   'confidence': 0.85,  # spaCy doesn't provide confidence
                   'source': 'ner'
               })

           return entities

       def extract_with_llm(self, text: str) -> List[Dict]:
           """Use GPT-4 for advanced extraction"""
           prompt = f"""
           Extract all entities from this text. For each entity, identify:
           - The entity name/title
           - The type (person, company, project, feature, task, decision, reflection)
           - A brief summary (1 sentence)

           Text: {text}

           Return as JSON array:
           [
             {{"title": "...", "type": "...", "summary": "...", "confidence": 0.95}}
           ]
           """

           response = self.client.chat.completions.create(
               model="gpt-4",
               messages=[{"role": "user", "content": prompt}],
               response_format={"type": "json_object"}
           )

           # Parse JSON response
           import json
           entities = json.loads(response.choices[0].message.content)

           for entity in entities:
               entity['source'] = 'llm'

           return entities

       def extract_entities(self, text: str, use_llm: bool = True) -> List[Dict]:
           """Main extraction method - combines NER + LLM"""
           ner_entities = self.extract_with_ner(text)

           if use_llm:
               llm_entities = self.extract_with_llm(text)
               # Merge and deduplicate
               return self._merge_entities(ner_entities, llm_entities)

           return ner_entities

       def _map_spacy_type(self, spacy_label: str) -> str:
           """Map spaCy entity types to our schema"""
           mapping = {
               'PERSON': 'person',
               'ORG': 'company',
               'PRODUCT': 'feature',
               'EVENT': 'meeting_note',
           }
           return mapping.get(spacy_label, 'reference_document')

       def _merge_entities(self, ner: List[Dict], llm: List[Dict]) -> List[Dict]:
           """Merge and deduplicate entities from both sources"""
           # Prefer LLM entities (more detailed), but include unique NER finds
           # TODO: Implement fuzzy matching for deduplication
           return llm + [e for e in ner if not self._in_llm_results(e, llm)]
   ```

2. **Create fuzzy matcher** (`utils/fuzzy_matcher.py`)
   ```python
   from difflib import SequenceMatcher

   class FuzzyMatcher:
       @staticmethod
       def similarity(str1: str, str2: str) -> float:
           """Return similarity score between 0 and 1"""
           return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

       @staticmethod
       def is_match(str1: str, str2: str, threshold: float = 0.85) -> bool:
           """Check if two strings are fuzzy matches"""
           return FuzzyMatcher.similarity(str1, str2) >= threshold
   ```

3. **Test entity extraction**
   ```python
   def test_entity_extraction():
       extractor = EntityExtractor()
       text = "Had a meeting with Sarah about the Feed feature for WaterOS."
       entities = extractor.extract_entities(text, use_llm=False)

       # Should find: Sarah (person), Feed feature (feature), WaterOS (project)
       assert len(entities) >= 3
   ```

**Success Criteria**: Can extract people, projects, features, tasks from text using both NER and LLM.

---

### Phase 4: Relationship Mapping (Day 5-6)

**Goal**: Identify relationships between entities and create edges.

#### Tasks

1. **Create relationship mapper** (`processors/relationship_mapper.py`)
   ```python
   from typing import List, Dict, Tuple
   from openai import OpenAI
   from config import settings

   class RelationshipMapper:
       def __init__(self):
           self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

       def detect_relationships(
           self,
           text: str,
           entities: List[Dict],
           existing_entities: List[Dict] = []
       ) -> List[Dict]:
           """Detect relationships between entities"""

           # Build entity list for LLM
           entity_list = [f"{e['title']} ({e['type']})" for e in entities]

           prompt = f"""
           Given this text and list of entities, identify relationships between them.

           Text: {text}

           Entities:
           {chr(10).join(entity_list)}

           For each relationship, specify:
           - from_entity: The source entity
           - to_entity: The destination entity
           - relationship_type: One of [belongs_to, modifies, mentions, informs, blocks, contradicts]
           - metadata: Any relevant context

           Return as JSON array:
           [
             {{
               "from_entity": "...",
               "to_entity": "...",
               "relationship_type": "...",
               "metadata": {{}}
             }}
           ]
           """

           response = self.client.chat.completions.create(
               model="gpt-4",
               messages=[{"role": "user", "content": prompt}],
               response_format={"type": "json_object"}
           )

           import json
           relationships = json.loads(response.choices[0].message.content)

           return relationships.get('relationships', [])

       def detect_explicit_relationships(self, text: str) -> List[Dict]:
           """Detect explicit relationships from keywords"""
           relationships = []

           # Pattern matching for explicit signals
           if "renamed" in text.lower() or "now called" in text.lower():
               # Suggests a 'modifies' relationship
               relationships.append({
                   'type': 'modifies',
                   'signal': 'rename',
                   'confidence': 0.9
               })

           if "belongs to" in text.lower() or "part of" in text.lower():
               relationships.append({
                   'type': 'belongs_to',
                   'signal': 'explicit_mention',
                   'confidence': 0.95
               })

           # Add more patterns as needed

           return relationships

       def detect_alias_and_update(
           self,
           text: str,
           entities: List[Dict],
           db
       ) -> List[Dict]:
           """Detect entity renames/aliases and update entity metadata"""
           alias_updates = []

           # Pattern: "renamed from X to Y" or "now called Y instead of X"
           rename_patterns = [
               r'renamed?\s+(?:from\s+)?["\']?(.+?)["\']?\s+to\s+["\']?(.+?)["\']?',
               r'now\s+called\s+["\']?(.+?)["\']?\s+instead\s+of\s+["\']?(.+?)["\']?',
               r'changing\s+["\']?(.+?)["\']?\s+to\s+["\']?(.+?)["\']?'
           ]

           import re
           for pattern in rename_patterns:
               matches = re.finditer(pattern, text, re.IGNORECASE)
               for match in matches:
                   old_name = match.group(1).strip()
                   new_name = match.group(2).strip()

                   # Find matching entity
                   for entity in entities:
                       if new_name.lower() in entity['title'].lower():
                           # Update entity metadata to include alias
                           entity_id = entity.get('entity_id')
                           if entity_id:
                               current_metadata = db.get_entity_metadata(entity_id)
                               aliases = current_metadata.get('aliases', [])

                               if old_name not in aliases:
                                   aliases.append(old_name)

                               db.update_entity_metadata(entity_id, {
                                   **current_metadata,
                                   'aliases': aliases,
                                   'previous_names': aliases  # Duplicate for clarity
                               })

                               alias_updates.append({
                                   'entity_id': entity_id,
                                   'old_name': old_name,
                                   'new_name': new_name,
                                   'type': 'rename'
                               })

           return alias_updates
   ```

2. **Test relationship detection**
   ```python
   def test_relationship_detection():
       mapper = RelationshipMapper()
       text = "The Feed feature belongs to the Willow project."
       entities = [
           {'title': 'Feed', 'type': 'feature'},
           {'title': 'Willow', 'type': 'project'}
       ]

       relationships = mapper.detect_relationships(text, entities)
       assert len(relationships) > 0
       assert any(r['relationship_type'] == 'belongs_to' for r in relationships)
   ```

**Success Criteria**: Can detect belongs_to, modifies, mentions, informs, blocks, contradicts relationships.

---

### Phase 5: Embeddings Service (Day 6-7)

**Goal**: Generate vector embeddings for chunks using OpenAI API.

#### Tasks

1. **Create embeddings service** (`services/embeddings.py`)
   ```python
   from openai import OpenAI
   from typing import List
   from config import settings

   class EmbeddingsService:
       def __init__(self):
           self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
           self.model = "text-embedding-3-small"
           self.dimensions = 1536

       def generate_embedding(self, text: str) -> List[float]:
           """Generate embedding for a single text"""
           response = self.client.embeddings.create(
               model=self.model,
               input=text
           )
           return response.data[0].embedding

       def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
           """Generate embeddings for multiple texts (more efficient)"""
           response = self.client.embeddings.create(
               model=self.model,
               input=texts
           )
           return [item.embedding for item in response.data]
   ```

2. **Test embeddings**
   ```python
   def test_embeddings():
       service = EmbeddingsService()
       text = "This is a test sentence."
       embedding = service.generate_embedding(text)

       assert len(embedding) == 1536
       assert all(isinstance(x, float) for x in embedding)
   ```

**Success Criteria**: Can generate 1,536-dimension embeddings via OpenAI API, batch processing works.

---

### Phase 6: Signal Scoring (Day 7-8)

**Goal**: Assign importance, recency, novelty scores to entities.

#### Tasks

1. **Create signal scorer** (`processors/signal_scorer.py`)
   ```python
   from datetime import datetime, timedelta
   import math

   class SignalScorer:
       def calculate_importance(self, entity_type: str, metadata: dict) -> float:
           """Calculate importance score based on entity type"""
           importance_map = {
               'core_identity': 1.0,
               'project': 0.85,
               'feature': 0.8,
               'task': 0.6,
               'decision': 0.75,
               'person': 0.7,
               'meeting_note': 0.5,
               'reflection': 0.65,
               'reference_document': 0.4,
           }

           base_score = importance_map.get(entity_type, 0.5)

           # Adjust based on metadata (e.g., user marked as important)
           if metadata.get('user_importance') == 'high':
               base_score = min(1.0, base_score + 0.2)
           elif metadata.get('user_importance') == 'low':
               base_score = max(0.1, base_score - 0.2)

           return base_score

       def calculate_recency(self, created_at: datetime, updated_at: datetime) -> float:
           """Calculate recency score with exponential decay"""
           # Use most recent timestamp
           reference_time = max(created_at, updated_at)
           age_days = (datetime.now() - reference_time).days

           # Exponential decay with 30-day half-life
           half_life_days = 30
           decay_rate = math.log(2) / half_life_days
           recency = math.exp(-decay_rate * age_days)

           return max(0.0, min(1.0, recency))

       def calculate_novelty(self, edge_count: int, entity_age_days: int) -> float:
           """Calculate novelty based on connections and age"""
           # New entities with few connections are novel
           # Well-connected, old entities are not novel

           connection_score = 1.0 / (1.0 + edge_count * 0.1)
           age_score = 1.0 / (1.0 + entity_age_days * 0.05)

           novelty = (connection_score + age_score) / 2.0

           return max(0.0, min(1.0, novelty))
   ```

**Success Criteria**: Entities get appropriate importance/recency/novelty scores.

---

### Phase 7: Orchestrator (Day 8-10)

**Goal**: Build the main Archivist class that orchestrates the full pipeline.

#### Tasks

1. **Create Archivist orchestrator** (`agents/archivist.py`)
   ```python
   from services.database import db
   from utils.text_cleaner import TextCleaner
   from services.chunker import Chunker
   from processors.entity_extractor import EntityExtractor
   from processors.relationship_mapper import RelationshipMapper
   from services.embeddings import EmbeddingsService
   from processors.signal_scorer import SignalScorer
   from typing import List
   import logging

   logger = logging.getLogger(__name__)

   class Archivist:
       def __init__(self):
           self.text_cleaner = TextCleaner()
           self.chunker = Chunker()
           self.entity_extractor = EntityExtractor()
           self.relationship_mapper = RelationshipMapper()
           self.embeddings_service = EmbeddingsService()
           self.signal_scorer = SignalScorer()
           self.mention_tracker = MentionTracker()

       def process_event(self, event_id: str):
           """Process a single raw event through the full pipeline"""
           try:
               # 1. Fetch event
               event = db.get_event_by_id(event_id)
               logger.info(f"Processing event {event_id}")

               # 2. Parse & Clean
               text = event.payload.content
               cleaned_text = self.text_cleaner.clean(text)

               # 3. Entity Recognition
               entities = self.entity_extractor.extract_entities(cleaned_text)
               logger.info(f"Extracted {len(entities)} entities")

               # 4. Entity Creation/Update (with mention tracking)
               entity_ids = []
               hub_entity_id = None

               for entity_data in entities:
                   # Record mention
                   is_primary = entity_data.get('is_primary_subject', False)
                   self.mention_tracker.record_mention(
                       entity_data['title'],
                       entity_data['type'],
                       event_id,
                       is_primary
                   )

                   # Check if should promote
                   if self.mention_tracker.should_promote(entity_data['title'], is_primary):
                       # Check if already exists
                       existing_id = self.mention_tracker.get_existing_entity_id(entity_data['title'])

                       if existing_id:
                           entity_ids.append(existing_id)
                       else:
                           # Determine if this should be a hub entity
                           is_hub = entity_data['type'] in ['project', 'feature', 'decision']

                           if is_hub:
                               entity_id = db.create_hub_entity({
                                   'source_event_id': event_id,
                                   'type': entity_data['type'],
                                   'title': entity_data['title'],
                                   'summary': entity_data.get('summary', ''),
                                   'metadata': entity_data.get('metadata', {}),
                               })
                               hub_entity_id = entity_id
                           else:
                               entity_id = db.create_entity({
                                   'source_event_id': event_id,
                                   'type': entity_data['type'],
                                   'title': entity_data['title'],
                                   'summary': entity_data.get('summary', ''),
                                   'metadata': entity_data.get('metadata', {}),
                               })

                           self.mention_tracker.mark_promoted(entity_data['title'], entity_id)
                           entity_ids.append(entity_id)
                   else:
                       # Entity not promoted yet - just tag in metadata
                       logger.debug(f"Entity '{entity_data['title']}' not promoted yet (mention count too low)")

               # Create meeting_note/reflection as spoke if hub exists
               if hub_entity_id and event.source in ['quick_capture', 'voice_debrief', 'webhook_granola']:
                   spoke_id = db.create_spoke_entity(hub_entity_id, {
                       'source_event_id': event_id,
                       'type': 'meeting_note' if 'meeting' in text.lower() else 'reflection',
                       'title': f"Note about {text[:50]}...",
                       'summary': text[:200],
                       'metadata': {'is_spoke': True}
                   })
                   entity_ids.append(spoke_id)

               # 5. Relationship Mapping (including alias detection)
               relationships = self.relationship_mapper.detect_relationships(
                   cleaned_text,
                   entities
               )

               for rel in relationships:
                   db.create_edge({
                       'from_id': rel['from_entity_id'],
                       'to_id': rel['to_entity_id'],
                       'kind': rel['relationship_type'],
                       'metadata': rel.get('metadata', {})
                   })

               # Detect and process aliases/renames
               alias_updates = self.relationship_mapper.detect_alias_and_update(
                   cleaned_text,
                   entities,
                   db
               )

               if alias_updates:
                   logger.info(f"Updated {len(alias_updates)} entity aliases")

               # 6. Chunking
               chunks = self.chunker.chunk_text(cleaned_text)
               logger.info(f"Created {len(chunks)} chunks")

               # 7. Embedding Generation
               chunk_texts = [c['text'] for c in chunks]
               embeddings = self.embeddings_service.generate_embeddings_batch(chunk_texts)

               # 8. Store Chunks & Embeddings
               for i, chunk in enumerate(chunks):
                   # Assume entity_id is the first entity (or create a meeting_note entity)
                   entity_id = entity_ids[0] if entity_ids else None

                   chunk_id = db.create_chunk({
                       'entity_id': entity_id,
                       'text': chunk['text'],
                       'token_count': chunk['token_count'],
                       'hash': chunk['hash']
                   })

                   db.create_embedding({
                       'chunk_id': chunk_id,
                       'vec': embeddings[i],
                       'model': 'text-embedding-3-small'
                   })

               # 9. Signal Assignment
               for entity_id in entity_ids:
                   entity = db.get_entity_by_id(entity_id)

                   importance = self.signal_scorer.calculate_importance(
                       entity.type,
                       entity.metadata
                   )
                   recency = self.signal_scorer.calculate_recency(
                       entity.created_at,
                       entity.updated_at
                   )
                   novelty = self.signal_scorer.calculate_novelty(
                       edge_count=0,  # TODO: Calculate actual edge count
                       entity_age_days=0
                   )

                   db.create_signal({
                       'entity_id': entity_id,
                       'importance': importance,
                       'recency': recency,
                       'novelty': novelty,
                       'last_surfaced_at': None
                   })

               # 10. Update Status
               db.update_event_status(event_id, 'processed')
               logger.info(f"Successfully processed event {event_id}")

           except Exception as e:
               logger.error(f"Error processing event {event_id}: {str(e)}")
               db.update_event_status(event_id, 'error')
               raise

       def process_pending_events(self, batch_size: int = 10):
           """Process all pending events in batches"""
           events = db.get_pending_events(limit=batch_size)

           logger.info(f"Processing {len(events)} pending events")

           for event in events:
               self.process_event(event.id)

       def run_continuous(self, interval_seconds: int = 60):
           """Run Archivist in continuous mode (check for new events every N seconds)"""
           import time

           logger.info("Starting Archivist in continuous mode")

           while True:
               try:
                   self.process_pending_events()
               except Exception as e:
                   logger.error(f"Error in continuous processing: {str(e)}")

               time.sleep(interval_seconds)
   ```

2. **Add processing endpoint to FastAPI** (`main.py`)
   ```python
   from agents.archivist import Archivist

   archivist = Archivist()

   @app.post("/process")
   async def trigger_processing():
       """Manually trigger Archivist processing"""
       archivist.process_pending_events()
       return {"message": "Processing complete"}

   @app.on_event("startup")
   async def startup_event():
       """Start background processing on server startup"""
       import threading

       def run_archivist():
           archivist.run_continuous(interval_seconds=60)

       thread = threading.Thread(target=run_archivist, daemon=True)
       thread.start()
   ```

**Success Criteria**: Full pipeline processes raw event → entities, edges, chunks, embeddings, signals.

---

### Phase 8: Testing & Refinement (Day 10-12)

**Goal**: Test end-to-end flow, fix bugs, optimize performance.

#### Tasks

1. **Create test fixtures** (`tests/fixtures/sample_events.json`)
   ```json
   [
     {
       "payload": {
         "type": "text",
         "content": "Had a great meeting with Sarah about the Feed feature. We decided to rename it from 'school-update' to just 'feed' for clarity. Need to update docs and tell the team.",
         "metadata": {}
       },
       "source": "quick_capture",
       "status": "pending_processing"
     }
   ]
   ```

2. **Write integration tests**
   ```python
   # tests/test_archivist.py
   def test_full_pipeline():
       # Insert test event into DB
       event_id = db.create_raw_event({
           "payload": {...},
           "source": "quick_capture",
           "status": "pending_processing"
       })

       # Process it
       archivist = Archivist()
       archivist.process_event(event_id)

       # Verify entities created
       entities = db.get_entities_by_source_event(event_id)
       assert len(entities) > 0

       # Verify chunks created
       chunks = db.get_chunks_by_entity_id(entities[0].id)
       assert len(chunks) > 0

       # Verify embeddings created
       embeddings = db.get_embeddings_by_chunk_id(chunks[0].id)
       assert len(embeddings) > 0

       # Verify event status updated
       event = db.get_event_by_id(event_id)
       assert event.status == 'processed'
   ```

3. **Performance optimization**
   - Batch API calls where possible
   - Cache frequently accessed entities
   - Add database indexes for common queries
   - Profile slow operations

4. **Error handling improvements**
   - Retry failed API calls with exponential backoff
   - Log detailed error context
   - Alert on repeated failures

**Success Criteria**: 90%+ test coverage, processes events in < 5 seconds, handles errors gracefully.

---

### Phase 9: User Feedback Processing (Day 12-13)

**Goal**: Implement feedback loop for user interactions (Acknowledge/Dismiss) to adjust signal scores.

#### Tasks

1. **Add feedback endpoints to FastAPI** (`main.py`)
   ```python
   from agents.feedback_processor import FeedbackProcessor

   feedback_processor = FeedbackProcessor()

   @app.post("/feedback/acknowledge/{insight_id}")
   async def acknowledge_insight(insight_id: str):
       """User acknowledged an insight as valuable"""
       feedback_processor.process_acknowledge(insight_id)
       return {"message": "Feedback recorded", "action": "acknowledge"}

   @app.post("/feedback/dismiss/{insight_id}")
   async def dismiss_insight(insight_id: str):
       """User dismissed an insight as not valuable"""
       feedback_processor.process_dismiss(insight_id)
       return {"message": "Feedback recorded", "action": "dismiss"}
   ```

2. **Create feedback processor** (`agents/feedback_processor.py`)
   ```python
   from services.database import db
   from processors.signal_scorer import SignalScorer
   from typing import List
   import logging

   logger = logging.getLogger(__name__)

   class FeedbackProcessor:
       def __init__(self):
           self.signal_scorer = SignalScorer()

       def process_acknowledge(self, insight_id: str):
           """Process user acknowledgment of insight"""
           try:
               # Get insight and its driver entities/edges
               insight = db.get_insight_by_id(insight_id)
               driver_entity_ids = insight.get('metadata', {}).get('driver_entity_ids', [])
               driver_edge_ids = insight.get('metadata', {}).get('driver_edge_ids', [])

               logger.info(f"Processing acknowledge for insight {insight_id}")

               # Boost importance scores for driver entities
               for entity_id in driver_entity_ids:
                   self._adjust_entity_signals(
                       entity_id,
                       importance_delta=0.1,
                       recency_boost=True
                   )

               # Update insight interaction metadata
               db.update_insight_metadata(insight_id, {
                   'user_feedback': 'acknowledged',
                   'feedback_timestamp': db.now()
               })

               logger.info(f"Boosted {len(driver_entity_ids)} entity signals")

           except Exception as e:
               logger.error(f"Error processing acknowledge: {str(e)}")
               raise

       def process_dismiss(self, insight_id: str):
           """Process user dismissal of insight"""
           try:
               # Get insight and its driver entities/edges
               insight = db.get_insight_by_id(insight_id)
               driver_entity_ids = insight.get('metadata', {}).get('driver_entity_ids', [])

               logger.info(f"Processing dismiss for insight {insight_id}")

               # Lower importance scores for driver entities
               for entity_id in driver_entity_ids:
                   self._adjust_entity_signals(
                       entity_id,
                       importance_delta=-0.1,
                       recency_boost=False
                   )

               # Update insight interaction metadata
               db.update_insight_metadata(insight_id, {
                   'user_feedback': 'dismissed',
                   'feedback_timestamp': db.now()
               })

               # Record pattern to avoid similar insights
               self._record_dismissed_pattern(insight)

               logger.info(f"Lowered {len(driver_entity_ids)} entity signals")

           except Exception as e:
               logger.error(f"Error processing dismiss: {str(e)}")
               raise

       def _adjust_entity_signals(
           self,
           entity_id: str,
           importance_delta: float,
           recency_boost: bool
       ):
           """Adjust signal scores for an entity"""
           signal = db.get_signal_by_entity_id(entity_id)

           if not signal:
               logger.warning(f"No signal found for entity {entity_id}")
               return

           # Adjust importance (clamp to [0.0, 1.0])
           new_importance = max(0.0, min(1.0, signal['importance'] + importance_delta))

           # Boost recency if acknowledged
           updates = {'importance': new_importance}

           if recency_boost:
               # Set last_surfaced_at to now (resets recency decay)
               entity = db.get_entity_by_id(entity_id)
               new_recency = self.signal_scorer.calculate_recency(
                   entity.created_at,
                   db.now()  # Updated timestamp
               )
               updates['recency'] = new_recency
               updates['last_surfaced_at'] = db.now()

           db.update_signal(entity_id, updates)

       def _record_dismissed_pattern(self, insight: dict):
           """Record dismissed insight pattern to avoid similar future insights"""
           # Store in a dismissed_patterns table or metadata
           pattern = {
               'type': insight.get('type'),
               'driver_entity_types': [
                   db.get_entity_by_id(eid).type
                   for eid in insight.get('metadata', {}).get('driver_entity_ids', [])
               ],
               'timestamp': db.now()
           }

           # In production, store this for Mentor agent to check
           db.record_dismissed_pattern(pattern)
   ```

3. **Add database methods** (extend `services/database.py`)
   ```python
   def get_insight_by_id(self, insight_id: str) -> dict:
       """Get insight by ID"""
       response = self.client.table('insight') \
           .select('*') \
           .eq('id', insight_id) \
           .single() \
           .execute()
       return response.data

   def update_insight_metadata(self, insight_id: str, metadata: dict):
       """Update insight metadata"""
       self.client.table('insight') \
           .update({'metadata': metadata}) \
           .eq('id', insight_id) \
           .execute()

   def get_signal_by_entity_id(self, entity_id: str) -> dict:
       """Get signal for entity"""
       response = self.client.table('signal') \
           .select('*') \
           .eq('entity_id', entity_id) \
           .maybe_single() \
           .execute()
       return response.data

   def update_signal(self, entity_id: str, updates: dict):
       """Update signal scores"""
       self.client.table('signal') \
           .update(updates) \
           .eq('entity_id', entity_id) \
           .execute()

   def record_dismissed_pattern(self, pattern: dict):
       """Record dismissed insight pattern"""
       self.client.table('dismissed_patterns') \
           .insert(pattern) \
           .execute()

   @staticmethod
   def now():
       """Return current timestamp"""
       from datetime import datetime
       return datetime.now()
   ```

4. **Test feedback processing**
   ```python
   # tests/test_feedback.py
   def test_acknowledge_feedback():
       # Create test insight with driver entities
       entity_id = db.create_entity({...})
       insight_id = db.create_insight({
           'metadata': {'driver_entity_ids': [entity_id]}
       })

       # Record initial signal
       db.create_signal({
           'entity_id': entity_id,
           'importance': 0.5,
           'recency': 0.5,
           'novelty': 0.5
       })

       # Process acknowledge
       processor = FeedbackProcessor()
       processor.process_acknowledge(insight_id)

       # Verify signal boosted
       signal = db.get_signal_by_entity_id(entity_id)
       assert signal['importance'] > 0.5
   ```

**Success Criteria**: User feedback adjusts entity signals, dismissed patterns recorded, system learns preferences.

---

### Phase 10: Deployment (Day 13-14)

**Goal**: Deploy the AI Core as a background service.

#### Tasks

1. **Containerize with Docker**
   ```dockerfile
   # Dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   RUN python -m spacy download en_core_web_sm

   COPY . .

   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Deploy options**
   - **Local**: Run with `docker-compose` alongside web app
   - **Cloud**: Deploy to Railway, Render, or AWS ECS
   - **Supabase Edge Functions**: For lighter processing (may need to split into functions)

3. **Monitoring & Logging**
   - Add structured logging
   - Set up error tracking (Sentry)
   - Monitor processing queue depth
   - Track API usage and costs

4. **Configure environment**
   - Production `.env` with real API keys
   - Set up secrets management
   - Configure rate limits for OpenAI API

**Success Criteria**: AI Core runs continuously, processes events automatically, logs visible, errors tracked.

---

## Success Metrics

The Archivist implementation is successful when:

1. **Processing Speed**: Events processed within 5 seconds on average
2. **Extraction Accuracy**: 90%+ of important entities captured
3. **Mention Tracking**: Entities promoted after 2-3 mentions, not immediately
4. **Alias Detection**: Entity renames detected and metadata updated correctly
5. **Hub-Spoke Pattern**: Complex entities (features, projects) have proper spoke relationships
6. **Relationship Quality**: Edges connect related concepts meaningfully
7. **Feedback Loop**: User actions (acknowledge/dismiss) adjust signal scores appropriately
8. **Uptime**: 99%+ uptime for background processing
9. **Cost Efficiency**: OpenAI API costs < $10/month for typical usage
10. **User Trust**: Minimal "why did the system miss this?" moments

## Future Enhancements

**Post-MVP**:
- Multi-model entity extraction (combine multiple approaches)
- Smarter chunking (topic segmentation, semantic boundaries)
- Entity merging and deduplication UI
- Relationship inference beyond explicit mentions
- Custom embedding fine-tuning for user's domain
- **Temporal reasoning** (detect goal drift, track entity lifecycle) - **NOTE**: This is mentioned in the technical guide as important for Delta Watch insights. Consider prioritizing this feature.
- Database-backed mention tracker (currently in-memory)
- Rate limiting and retry logic for OpenAI API calls
- Dead letter queue for repeatedly failed events

## Estimated Timeline

- **Phase 0**: 4 hours (setup)
- **Phase 1**: 6 hours (database layer with hub/spoke support)
- **Phase 2**: 4 hours (text processing)
- **Phase 3**: 10 hours (entity extraction + mention tracking)
- **Phase 4**: 8 hours (relationship mapping + alias detection)
- **Phase 5**: 4 hours (embeddings)
- **Phase 6**: 4 hours (signal scoring)
- **Phase 7**: 10 hours (orchestrator with full pipeline)
- **Phase 8**: 8 hours (testing)
- **Phase 9**: 6 hours (user feedback processing)
- **Phase 10**: 8 hours (deployment)

**Total**: ~72 hours (~2.5 weeks at 4-5 hours/day)

## Dependencies

**External Services**:
- OpenAI API (GPT-4 + embeddings)
- Supabase (database + auth)

**Python Libraries**:
- `fastapi` - Web framework
- `supabase-py` - Database client
- `openai` - LLM and embeddings API
- `langchain` - LLM orchestration
- `spacy` - NER
- `tiktoken` - Token counting

## Getting Started

```bash
# 1. Navigate to AI Core
cd apps/ai-core

# 2. Install dependencies
poetry install

# 3. Download spaCy model
python -m spacy download en_core_web_sm

# 4. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 5. Run the server
poetry run python main.py

# 6. Test the health endpoint
curl http://localhost:8000/health

# 7. Trigger processing manually
curl -X POST http://localhost:8000/process
```

## Questions & Decisions

**Before starting implementation, decide:**

1. **Deployment environment**: Local Docker, cloud service, or Supabase Edge Functions?
2. **LLM model**: GPT-4 (expensive, accurate) or GPT-3.5 (cheap, faster)?
3. **Processing mode**: Continuous background job or on-demand via API?
4. **Error strategy**: Retry failed events or move to error queue?
5. **Cost budget**: What's acceptable OpenAI API spend per month?

**Recommended choices for MVP:**
- Deploy locally with Docker for development
- Use GPT-4 for entity extraction (accuracy matters)
- Continuous background job checking every 60 seconds
- Retry failed events up to 3 times, then move to error queue
- Budget $20/month for OpenAI API (monitor closely)
