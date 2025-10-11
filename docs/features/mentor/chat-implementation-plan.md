# Mentor Chat Implementation Plan

## Goal

Create a conversational chat interface where you can talk with your Mentor agent, with all conversations automatically feeding into the Archivist for processing. This completes the feedback loop:

```
Chat with Mentor → Saved to raw_events → Archivist processes → Knowledge graph updated
→ Mentor uses updated context → Better insights → Feedback loop continues
```

---

## Phase 1: Backend - Mentor Chat Endpoint (AI Core)

**Time**: 30 minutes

### 1.1 Create Chat Message Model

**File**: `apps/ai-core/models/chat.py` (NEW)

```python
from pydantic import BaseModel
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    response: str
    event_id: str  # ID of saved raw_event
    entities_found: List[str]  # Quick preview of entities mentioned
```

### 1.2 Enhance Mentor Agent with Chat Method

**File**: `apps/ai-core/agents/mentor.py` (MODIFY)

Add new method:
```python
async def chat(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
    """
    Conversational chat with Mentor.

    Features:
    1. Queries knowledge graph for relevant context
    2. Uses conversation history for continuity
    3. Saves conversation to raw_events
    4. Returns response + metadata
    """
```

**Steps**:
1. Query knowledge graph for relevant entities based on message
2. Build context-aware prompt with:
   - Recent conversation history (last 5 messages)
   - Relevant entities from knowledge graph
   - User's goals/values (core identity)
   - Current active work (high recency)
3. Call Claude for response
4. Save both user message and assistant response to raw_events
5. Return response with metadata

### 1.3 Create Chat Endpoint

**File**: `apps/ai-core/main.py` (MODIFY)

Add endpoint:
```python
@app.post("/mentor/chat")
async def mentor_chat(request: ChatRequest):
    """
    Chat with Mentor agent.

    - Provides context-aware responses
    - Saves conversation to raw_events
    - Returns assistant response
    """
    mentor = Mentor()
    result = await mentor.chat(
        message=request.message,
        conversation_history=request.conversation_history
    )
    return result
```

---

## Phase 2: Frontend - Chat UI (Next.js)

**Time**: 45 minutes

### 2.1 Create Chat Page Component

**File**: `apps/web/app/mentor/chat/page.tsx` (NEW)

**Features**:
- Message list (conversation history)
- Input field with send button
- Loading state while waiting for response
- Auto-scroll to latest message
- Show typing indicator
- Display entity mentions as badges/chips

**UI Layout**:
```
┌─────────────────────────────────────────┐
│  Chat with Mentor                       │
├─────────────────────────────────────────┤
│                                         │
│  [User]: Had a great meeting with      │
│  Sarah about the Feed feature           │
│                                         │
│  [Mentor]: That's excellent! The Feed  │
│  feature is a hub entity in your graph.│
│  What decisions did you make?           │
│  Entities: Sarah (person), Feed (feat) │
│                                         │
│  [User]: We decided to rename it...    │
│                                         │
├─────────────────────────────────────────┤
│  [Input field________________] [Send]   │
└─────────────────────────────────────────┘
```

### 2.2 Create Message Component

**File**: `apps/web/components/ChatMessage.tsx` (NEW)

```typescript
interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  entities?: string[];
  timestamp: string;
}
```

**Styling**:
- User messages: Right-aligned, blue background
- Assistant messages: Left-aligned, gray background
- Entity badges: Small pills showing extracted entities
- Timestamp: Subtle, below message

### 2.3 Create Chat Hook

**File**: `apps/web/hooks/useMentorChat.ts` (NEW)

```typescript
export function useMentorChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (content: string) => {
    // Add user message to UI
    // Call API
    // Add assistant response to UI
    // Handle errors
  };

  return { messages, sendMessage, isLoading };
}
```

---

## Phase 3: Integration - Chat → raw_events → Archivist

**Time**: 30 minutes

### 3.1 Create Next.js API Route

**File**: `apps/web/app/api/mentor/chat/route.ts` (NEW)

```typescript
export async function POST(request: Request) {
  const { message, conversationHistory } = await request.json();

  // Get user entity ID
  const userEntityId = await getUserEntityId();

  // Call AI Core chat endpoint
  const response = await fetch(`${AI_CORE_URL}/mentor/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory,
      user_entity_id: userEntityId
    })
  });

  const result = await response.json();
  return Response.json(result);
}
```

### 3.2 Modify Mentor Chat Method to Save Events

**File**: `apps/ai-core/agents/mentor.py` (MODIFY)

After generating response:
```python
# Save user message to raw_events
user_event_id = self.db.create_raw_event({
    'payload': {
        'type': 'text',
        'content': message,
        'metadata': {
            'source_type': 'mentor_chat',
            'role': 'user'
        },
        'user_id': 'default_user',
        'user_entity_id': user_entity_id
    },
    'source': 'mentor_chat',
    'status': 'pending_processing'  # Archivist will process
})

# Save assistant response to raw_events
assistant_event_id = self.db.create_raw_event({
    'payload': {
        'type': 'text',
        'content': response_text,
        'metadata': {
            'source_type': 'mentor_chat',
            'role': 'assistant',
            'user_message_event_id': user_event_id
        },
        'user_id': 'default_user',
        'user_entity_id': user_entity_id
    },
    'source': 'mentor_chat',
    'status': 'pending_processing'  # Archivist will process
})
```

### 3.3 Archivist Already Handles This! ✅

**No changes needed** - Archivist already:
- Polls `raw_events` for `status='pending_processing'`
- Processes text from any source
- Extracts entities
- Creates relationships
- Updates signals

The chat messages will automatically flow through the existing pipeline!

---

## Phase 4: Context-Aware Responses

**Time**: 30 minutes

### 4.1 Knowledge Graph Query in Chat

**File**: `apps/ai-core/agents/mentor.py` (MODIFY)

Before calling Claude:
```python
# Extract potential entities from user message
message_entities = await self._extract_entity_mentions(message)

# Query knowledge graph for context
context_entities = []
for entity_mention in message_entities:
    # Find matching entities
    matches = self.db.search_entities_by_title(entity_mention)
    context_entities.extend(matches)

# Get user's goals and active work
core_identity = self.db.get_entities_by_type('core_identity')
active_work = self.db.get_entities_by_signal_threshold('recency', 0.8, limit=10)

# Build context-aware prompt
```

### 4.2 Enhanced Chat Prompt

```python
def _build_chat_prompt(self, message, conversation_history, context_entities, core_identity, active_work):
    prompt = f"""You are the Mentor - a strategic thinking partner with access to the user's complete knowledge graph.

User's Core Identity (Goals & Values):
{self._format_entities(core_identity)}

User's Active Work (High Recency):
{self._format_entities(active_work)}

Relevant Context from Knowledge Graph:
{self._format_entities(context_entities)}

Recent Conversation:
{self._format_conversation(conversation_history)}

User's Message:
{message}

INSTRUCTIONS:
1. Respond conversationally and helpfully
2. Reference specific entities from their knowledge graph when relevant
3. Ask strategic questions that push their thinking
4. Be concise but insightful
5. Challenge assumptions when appropriate
6. Connect current topic to their goals and past work

CRITICAL:
- Ground responses in their actual work (reference entity titles)
- Don't just answer - ask follow-up questions
- Be direct and actionable
- Avoid generic advice

Respond naturally:
"""
    return prompt
```

---

## Phase 5: Polish & Enhancement

**Time**: 30 minutes

### 5.1 Navigation

**File**: `apps/web/components/NavBar.tsx` (MODIFY)

Add link:
```tsx
<Link href="/mentor/chat">Chat with Mentor</Link>
```

### 5.2 Conversation Persistence

**Option A**: Client-side (localStorage)
- Store conversation in browser
- Simple, fast
- Doesn't persist across devices

**Option B**: Database
- Create `conversation` table
- Store messages with timestamps
- Persist across devices
- More complex

**Recommendation**: Start with Option A, upgrade to B later

### 5.3 Entity Highlighting

**File**: `apps/web/components/ChatMessage.tsx` (ENHANCE)

```typescript
// Detect entity mentions in text and highlight them
function highlightEntities(text: string, entities: string[]) {
  // Simple: Show badges below message
  // Advanced: Inline highlighting with tooltips
}
```

### 5.4 Quick Actions

Add buttons to chat:
- "Summarize my week" → Triggers specific query
- "What should I focus on today?" → Mentor generates prioritized list
- "Show my goals" → Displays core identity entities

---

## Phase 6: Testing the Complete Loop

**Time**: 20 minutes

### 6.1 End-to-End Test Flow

1. **Chat**: Type message in chat interface
   - "Had a productive meeting with Sarah about the Feed feature. We decided to rename it from 'school-update' to just 'feed' for clarity."

2. **Verify raw_events**:
   ```sql
   SELECT * FROM raw_events
   WHERE source = 'mentor_chat'
   ORDER BY created_at DESC
   LIMIT 2;
   ```
   - Should show 2 events (user message + assistant response)
   - Status should be 'pending_processing'

3. **Wait for Archivist** (60 seconds or manual trigger):
   ```bash
   curl -X POST http://localhost:8000/process
   ```

4. **Verify Processing**:
   ```sql
   -- Check entities created
   SELECT * FROM entity
   WHERE source_event_id IN (
     SELECT id FROM raw_events WHERE source = 'mentor_chat'
   );

   -- Should show: Sarah (person), Feed (feature)

   -- Check signals
   SELECT e.title, s.importance, s.recency
   FROM entity e
   JOIN signal s ON e.id = s.entity_id
   WHERE e.title IN ('Sarah', 'Feed');
   ```

5. **Continue Chat**:
   - "What else should we discuss about the Feed feature?"
   - Mentor should reference Feed feature from knowledge graph

6. **Check Signals Update**:
   - Feed feature recency should refresh to 1.0 (mentioned again)

7. **Next Day Digest**:
   ```bash
   curl -X POST http://localhost:8000/mentor/generate-digest
   ```
   - Should see insights referencing Feed feature and Sarah
   - Delta Watch might mention work on Feed
   - Connection might link to past similar features

### 6.2 Success Criteria

✅ Chat messages saved to raw_events
✅ Archivist processes chat messages
✅ Entities extracted (Sarah, Feed)
✅ Signals created/updated
✅ Mentor uses knowledge graph context in responses
✅ Next digest references entities from chat
✅ Feedback loop complete!

---

## Implementation Order

### Day 1: Backend Foundation (2 hours)
1. ✅ Phase 1.1: Chat models
2. ✅ Phase 1.2: Mentor chat method
3. ✅ Phase 1.3: Chat endpoint
4. ✅ Phase 3.2: Save to raw_events

**Deliverable**: Working API endpoint at `/mentor/chat`

### Day 2: Frontend UI (2 hours)
5. ✅ Phase 2.1: Chat page
6. ✅ Phase 2.2: Message component
7. ✅ Phase 2.3: Chat hook
8. ✅ Phase 3.1: Next.js API route

**Deliverable**: Working chat UI at `/mentor/chat`

### Day 3: Context & Polish (2 hours)
9. ✅ Phase 4: Knowledge graph integration
10. ✅ Phase 5: Navigation & enhancements
11. ✅ Phase 6: End-to-end testing

**Deliverable**: Complete feedback loop working!

---

## Total Time Estimate: 6 hours

- Backend: 2 hours
- Frontend: 2 hours
- Integration & Testing: 2 hours

---

## Files to Create/Modify

### New Files (6)
1. `apps/ai-core/models/chat.py` - Chat models
2. `apps/web/app/mentor/chat/page.tsx` - Chat page
3. `apps/web/components/ChatMessage.tsx` - Message component
4. `apps/web/hooks/useMentorChat.ts` - Chat hook
5. `apps/web/app/api/mentor/chat/route.ts` - API route
6. `docs/features/mentor/chat-implementation-plan.md` - This document

### Modified Files (2)
1. `apps/ai-core/agents/mentor.py` - Add chat() method
2. `apps/web/components/NavBar.tsx` - Add chat link

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                 │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
             │ 1. View Insights           │ 2. Chat
             │                            │
┌────────────▼──────────┐    ┌───────────▼────────────────┐
│   /digest              │    │   /mentor/chat             │
│   (Daily Digest)       │    │   (Chat Interface)         │
│                        │    │                            │
│ - 3 insight cards      │    │ - Conversation history     │
│ - Acknowledge/Dismiss  │    │ - Send messages            │
└────────────┬───────────┘    └───────────┬────────────────┘
             │                            │
             │ 3. Feedback                │ 4. Chat messages
             │                            │
┌────────────▼────────────────────────────▼────────────────┐
│              Next.js API Routes                           │
│   /api/feedback/*          /api/mentor/chat              │
└────────────┬────────────────────────────┬─────────────────┘
             │                            │
             │ Proxy                      │ Proxy
             │                            │
┌────────────▼────────────────────────────▼─────────────────┐
│                    AI Core (FastAPI)                       │
│                                                            │
│  ┌──────────────────┐      ┌──────────────────┐          │
│  │ Feedback         │      │ Mentor Chat      │          │
│  │ Processor        │      │ - Query graph    │          │
│  │ - Adjust signals │      │ - Call Claude    │          │
│  │ - Record patterns│      │ - Save to events │          │
│  └──────────────────┘      └─────────┬────────┘          │
│                                       │                    │
│  ┌──────────────────┐                │                    │
│  │ Mentor Agent     │                │ 5. Save            │
│  │ - Generate digest│                │                    │
│  │ - Use graph      │                │                    │
│  └────────┬─────────┘                │                    │
│           │                          │                    │
└───────────┼──────────────────────────┼────────────────────┘
            │                          │
            │ 6. Read                  │ 7. Write
            │                          │
┌───────────▼──────────────────────────▼────────────────────┐
│                    Supabase Database                       │
│                                                            │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────┐   │
│  │ raw_events  │   │ entity      │   │ signal       │   │
│  │ (inbox)     │   │ (nodes)     │   │ (scores)     │   │
│  └─────────────┘   └─────────────┘   └──────────────┘   │
│                                                            │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────┐   │
│  │ insight     │   │ edge        │   │ dismissed_   │   │
│  │ (cards)     │   │ (relations) │   │ patterns     │   │
│  └─────────────┘   └─────────────┘   └──────────────┘   │
└───────────────────────┬────────────────────────────────────┘
                        │
                        │ 8. Poll & Process
                        │
                ┌───────▼──────────┐
                │   Archivist      │
                │   (Background)   │
                │                  │
                │ - Extract entities│
                │ - Create edges   │
                │ - Update signals │
                └──────────────────┘
```

**The Complete Loop**:
1. User views digest → 2. Provides feedback → 3. Signals updated
4. User chats with Mentor → 5. Messages saved to raw_events
6. Archivist processes → 7. Entities/signals updated
8. Mentor uses updated graph → 9. Better digest tomorrow → Repeat!

---

## Success Metrics

After implementing, you should be able to:

✅ **Chat with Mentor** about your work
✅ **See chat messages** appear in raw_events
✅ **Watch Archivist** extract entities from chat
✅ **Observe signals** update based on chat topics
✅ **Receive insights** that reference chat discussions
✅ **Provide feedback** that improves future chat responses

**The loop is complete when**: A topic discussed in chat shows up in tomorrow's digest, and your feedback on that insight improves the next chat conversation.

---

Ready to implement! Starting with Phase 1 (Backend Foundation).
