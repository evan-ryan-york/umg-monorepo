# Mentor Chat Implementation: AI Agent Handoff

**Created**: 2025-10-08
**Updated**: 2025-10-09
**Status**: ✅ COMPLETE - Chat interface working end-to-end!
**Completion**: 100% (Backend + Frontend both working)
**Next Steps**: Test the full feedback loop and iterate on UX

---

## Executive Summary

**What We're Doing**: Creating a conversational chat interface where users can talk with their Mentor agent. All conversations automatically feed into the Archivist for processing, completing the feedback loop.

**Current Status**: Backend is fully implemented and working. The FastAPI endpoint at `/mentor/chat` accepts messages, provides context-aware responses using the knowledge graph, and saves conversations to `raw_events` for Archivist processing.

**Critical Context**: This completes the core feedback loop:
```
Chat with Mentor → Saved to raw_events → Archivist processes → Knowledge graph updated
→ Mentor uses updated context → Better insights → Feedback loop continues
```

---

## What's Working ✅

### Backend Infrastructure (Phase 1 - COMPLETE)

**1. Chat Models** (`apps/ai-core/models/chat.py`)
- ✅ `ChatMessage` - Single message model (role, content)
- ✅ `ChatRequest` - Request model (message, history, user_entity_id)
- ✅ `ChatResponse` - Response model (response, event IDs, entities mentioned)

**2. Mentor Chat Method** (`apps/ai-core/agents/mentor.py`)
- ✅ `chat()` - Main conversational interface (lines 70-160)
  - Gathers relevant context from knowledge graph
  - Builds context-aware prompts
  - Calls Claude for responses
  - Saves both user and assistant messages to raw_events
  - Returns response with metadata

- ✅ `_gather_chat_context()` - Context gathering (lines 162-192)
  - Pulls core identity (goals/values)
  - Gets active work (high recency entities)
  - Finds relevant entities via keyword matching
  - Returns structured context dict

- ✅ `_build_chat_prompt()` - Prompt engineering (lines 194-257)
  - Formats knowledge graph context
  - Includes conversation history (last 5 messages)
  - Creates context-aware Claude prompt
  - Instructs Mentor to be strategic and grounded

- ✅ `_extract_keywords_from_message()` - Keyword extraction (lines 259-279)
  - Simple word extraction with stop word filtering
  - Used for finding relevant entities

- ✅ `_extract_entity_mentions()` - Entity detection (lines 281-299)
  - Identifies which entities were mentioned in message
  - Returns list of entity titles

**3. FastAPI Endpoint** (`apps/ai-core/main.py`)
- ✅ `POST /mentor/chat` (lines 315-378)
  - Accepts: message, conversation_history, user_entity_id
  - Parses request and calls mentor.chat()
  - Returns: response, event IDs, entities mentioned, context used
  - Error handling with proper HTTP status codes

**4. Integration with Archivist**
- ✅ Chat messages automatically saved to `raw_events` table
- ✅ Source: `mentor_chat`
- ✅ Status: `pending_processing` (Archivist will process)
- ✅ Both user and assistant messages saved
- ✅ Metadata includes role, timestamps, linked message IDs

**5. Knowledge Graph Context**
- ✅ Queries core identity entities
- ✅ Queries active work (recency >= 0.8)
- ✅ Searches for relevant entities via keywords
- ✅ Context included in Claude prompts

---

## What's Next: Phase 2 (Frontend)

### Files to Create (5 new files)

**1. Chat Page Component**
- **File**: `apps/web/app/mentor/chat/page.tsx` (NEW)
- **What it does**: Main chat page with message list and input
- **Features needed**:
  - Server component that renders initial empty state
  - Client components for interactive chat
  - Conversation history display
  - Input field with send button
  - Loading states
  - Auto-scroll to latest message

**2. Chat Message Component**
- **File**: `apps/web/components/ChatMessage.tsx` (NEW)
- **What it does**: Renders individual messages
- **Features needed**:
  - Different styling for user vs assistant messages
  - Entity mention badges/pills
  - Timestamp display
  - Markdown support (optional)
  - Copy message functionality (optional)

**3. Chat Hook**
- **File**: `apps/web/hooks/useMentorChat.ts` (NEW)
- **What it does**: Manages chat state and API calls
- **Features needed**:
  - State: messages array, loading state, error state
  - sendMessage function (calls API)
  - Message history management
  - Local storage persistence (optional but recommended)
  - Error handling

**4. Next.js API Route**
- **File**: `apps/web/app/api/mentor/chat/route.ts` (NEW)
- **What it does**: Proxies chat requests to AI Core
- **Features needed**:
  - POST handler
  - Get user_entity_id (like other API routes)
  - Call AI Core `/mentor/chat` endpoint
  - Return response to frontend
  - Error handling

**5. Navigation Update**
- **File**: `apps/web/components/NavBar.tsx` (MODIFY)
- **What it does**: Add link to chat page
- **Changes needed**:
  - Add "Chat with Mentor" link
  - Active state styling
  - Icon (optional)

---

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                 │
└────────────┬────────────────────────────────────────────────┘
             │
             │ Types message in chat UI
             │
┌────────────▼────────────────────────────────────────────────┐
│   /mentor/chat (Next.js Page)                               │
│   - Message list (conversation history)                     │
│   - Input field + Send button                               │
│   - useMentorChat() hook manages state                      │
└────────────┬────────────────────────────────────────────────┘
             │
             │ onClick Send → sendMessage()
             │
┌────────────▼────────────────────────────────────────────────┐
│   POST /api/mentor/chat (Next.js API Route)                 │
│   - Gets user_entity_id from database                       │
│   - Adds message to conversation_history                    │
│   - Proxies to AI Core                                      │
└────────────┬────────────────────────────────────────────────┘
             │
             │ Proxies request
             │
┌────────────▼────────────────────────────────────────────────┐
│   POST http://localhost:8000/mentor/chat (AI Core)          │
│   - mentor.chat() method processes                          │
│   - Gathers context from knowledge graph                    │
│   - Calls Claude with context-aware prompt                  │
│   - Saves messages to raw_events                            │
│   - Returns response                                        │
└────────────┬────────────────────────────────────────────────┘
             │
             │ Returns response
             │
┌────────────▼────────────────────────────────────────────────┐
│   Frontend Updates                                          │
│   - Adds user message to UI                                 │
│   - Adds assistant response to UI                           │
│   - Shows entity mentions as badges                         │
│   - Auto-scrolls to bottom                                  │
└─────────────────────────────────────────────────────────────┘

                    MEANWHILE...

┌─────────────────────────────────────────────────────────────┐
│   Archivist Background Processing                           │
│   - Polls raw_events every 60s                              │
│   - Finds messages with source='mentor_chat'                │
│   - Extracts entities (people, projects, features, etc.)    │
│   - Creates/updates entities in knowledge graph             │
│   - Creates relationships between entities                  │
│   - Updates signal scores (importance, recency, novelty)    │
└────────────┬────────────────────────────────────────────────┘
             │
             │ Knowledge graph updated
             │
┌────────────▼────────────────────────────────────────────────┐
│   Next Chat Message                                         │
│   - Mentor has updated context                              │
│   - Can reference entities from previous chat               │
│   - Better, more informed responses                         │
└─────────────────────────────────────────────────────────────┘

                    AND ALSO...

┌─────────────────────────────────────────────────────────────┐
│   Next Day's Digest (7 AM)                                  │
│   - Delta Watch may reference chat topics                   │
│   - Connection may link chat to past work                   │
│   - Prompt may ask about chat discussions                   │
│   - Complete feedback loop! 🎉                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan for Next Agent

### Step 1: Read Required Documentation

**Critical docs to read first** (in order):
1. **`docs/features/mentor/chat-implementation-plan.md`** - Full implementation plan (you are here!)
2. **`apps/web/app/digest/page.tsx`** - Example of existing Mentor UI (see patterns)
3. **`apps/web/components/InsightCard.tsx`** - Component structure reference
4. **`apps/web/app/api/events/route.ts`** - Pattern for Next.js API routes
5. **`apps/web/components/NavBar.tsx`** - Navigation component to update

**Reference for patterns**:
- **`apps/web/hooks/`** - See existing hooks (if any) for patterns
- **`apps/web/app/api/feedback/acknowledge/[id]/route.ts`** - API proxy pattern

### Step 2: Create the Files (in order)

**Order matters** - build from inside out:

1. **Create useMentorChat hook** (`apps/web/hooks/useMentorChat.ts`)
   - This is the core state management
   - Test it can call API and manage state

2. **Create ChatMessage component** (`apps/web/components/ChatMessage.tsx`)
   - Just the visual component
   - User message: right-aligned, blue
   - Assistant message: left-aligned, gray
   - Entity badges below messages

3. **Create Next.js API route** (`apps/web/app/api/mentor/chat/route.ts`)
   - Follow pattern from `/api/events/route.ts`
   - Get user_entity_id
   - Proxy to AI Core
   - Return response

4. **Create chat page** (`apps/web/app/mentor/chat/page.tsx`)
   - Use the hook and component
   - Message list
   - Input + send button
   - Loading states

5. **Update NavBar** (`apps/web/components/NavBar.tsx`)
   - Add "Chat with Mentor" link
   - Active styling

### Step 3: Test the Complete Loop

**End-to-end test flow**:

1. **Start both servers**:
   ```bash
   # Terminal 1: AI Core
   cd apps/ai-core
   source venv/bin/activate
   uvicorn main:app --reload --port 8000

   # Terminal 2: Web
   cd apps/web
   pnpm run dev
   ```

2. **Open chat**: `http://localhost:3110/mentor/chat`

3. **Send test message**: "I had a productive meeting with Sarah about the Feed feature"

4. **Verify response**: Should get context-aware response from Mentor

5. **Check raw_events**:
   ```sql
   SELECT * FROM raw_events
   WHERE source = 'mentor_chat'
   ORDER BY created_at DESC
   LIMIT 2;
   ```
   Should show 2 events (user + assistant) with status='pending_processing'

6. **Trigger Archivist** (or wait 60s):
   ```bash
   curl -X POST http://localhost:8000/process
   ```

7. **Verify entities created**:
   ```sql
   SELECT e.title, e.type, s.importance, s.recency
   FROM entity e
   JOIN signal s ON e.id = s.entity_id
   WHERE e.source_event_id IN (
     SELECT id FROM raw_events WHERE source = 'mentor_chat'
   );
   ```
   Should show: Sarah (person), Feed (feature)

8. **Continue conversation**: "What should we focus on next for the Feed?"
   - Mentor should reference Feed feature from knowledge graph
   - Response should be context-aware

9. **Generate digest tomorrow**:
   ```bash
   curl -X POST http://localhost:8000/mentor/generate-digest
   ```
   - Should see insights referencing Feed and Sarah
   - **Loop complete!** 🎉

---

## Critical Design Decisions

### 1. Conversation Persistence

**Decision**: Start with localStorage, upgrade to database later

**Rationale**:
- localStorage is simple and fast
- Doesn't require new database tables
- Good enough for MVP
- Can always upgrade to DB-backed persistence

**Implementation**:
```typescript
// In useMentorChat hook
useEffect(() => {
  // Load from localStorage on mount
  const saved = localStorage.getItem('mentor_chat_history');
  if (saved) {
    setMessages(JSON.parse(saved));
  }
}, []);

useEffect(() => {
  // Save to localStorage on change
  localStorage.setItem('mentor_chat_history', JSON.stringify(messages));
}, [messages]);
```

### 2. Message Format

**Decision**: Use simple array of messages, not threaded

**Rationale**:
- Chat is conversational, not threaded
- Simple linear history is easier to manage
- Matches Claude API message format

**Format**:
```typescript
interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  entities?: string[];
}
```

### 3. Streaming vs Complete Response

**Decision**: Complete response (not streaming)

**Rationale**:
- Simpler to implement
- Claude call is fast enough (<3s)
- Can add streaming later if needed
- Loading spinner sufficient for now

### 4. Entity Highlighting

**Decision**: Show entities as badges below message, not inline

**Rationale**:
- Simpler to implement (no text parsing)
- Backend already returns entities_mentioned array
- Badges are visual and clickable (future: link to entity page)

**Implementation**:
```tsx
{message.entities && message.entities.length > 0 && (
  <div className="mt-2 flex flex-wrap gap-1">
    {message.entities.map(entity => (
      <span key={entity} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
        {entity}
      </span>
    ))}
  </div>
)}
```

---

## API Reference for Frontend

### POST /api/mentor/chat

**Request**:
```typescript
{
  message: string;
  conversation_history: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
}
```

**Response**:
```typescript
{
  response: string;
  user_event_id: string;
  assistant_event_id: string;
  entities_mentioned: string[];
  context_used: {
    core_identity_count: number;
    active_work_count: number;
    relevant_entities_count: number;
  };
}
```

**Error Response**:
```typescript
{
  detail: string;
}
```

---

## UI/UX Specifications

### Chat Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Chat with Mentor                                    [NavBar]│
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [User - Right aligned, blue background]             │  │
│  │ I had a meeting with Sarah about the Feed feature   │  │
│  │ Entities: [Sarah] [Feed]                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [Mentor - Left aligned, gray background]            │  │
│  │ Excellent! The Feed feature is a hub entity in      │  │
│  │ your graph. What decisions did you make?            │  │
│  │ Entities: [Feed]                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [User]                                              │  │
│  │ We decided to rename it from "school-update"        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  [Scroll area - auto-scroll to bottom on new message]       │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐  ┌──────────┐   │
│  │ Type your message...                 │  │  Send    │   │
│  └──────────────────────────────────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Color Palette

**User Messages**:
- Background: `bg-blue-50`
- Border: `border-blue-200`
- Text: `text-gray-900`
- Alignment: Right (`ml-auto`)

**Assistant Messages**:
- Background: `bg-gray-50`
- Border: `border-gray-200`
- Text: `text-gray-900`
- Alignment: Left (`mr-auto`)

**Entity Badges**:
- Background: `bg-purple-100`
- Text: `text-purple-800`
- Size: `text-xs`
- Padding: `px-2 py-1`
- Border radius: `rounded`

**Loading State**:
- Show typing indicator: "Mentor is thinking..."
- Or simple spinner

---

## Code Templates for Next Agent

### Template: useMentorChat Hook

```typescript
// apps/web/hooks/useMentorChat.ts
'use client';

import { useState, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  entities?: string[];
}

export function useMentorChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('mentor_chat_history');
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse saved chat history', e);
      }
    }
  }, []);

  // Save to localStorage on change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('mentor_chat_history', JSON.stringify(messages));
    }
  }, [messages]);

  const sendMessage = async (content: string) => {
    if (!content.trim()) return;

    // Add user message immediately
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      // Call API
      const response = await fetch('/api/mentor/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          conversation_history: messages.slice(-10).map(m => ({
            role: m.role,
            content: m.content
          }))
        })
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const data = await response.json();

      // Add assistant message
      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        entities: data.entities_mentioned
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      // Remove user message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const clearHistory = () => {
    setMessages([]);
    localStorage.removeItem('mentor_chat_history');
  };

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearHistory
  };
}
```

### Template: API Route

```typescript
// apps/web/app/api/mentor/chat/route.ts
import { createClient } from '@/utils/supabase/server';

const AI_CORE_URL = process.env.AI_CORE_URL || 'http://localhost:8000';

async function getUserEntityId(): Promise<string | null> {
  const supabase = createClient();
  const RYAN_YORK = 'Ryan York';

  const { data } = await supabase
    .from('entity')
    .select('id, title, metadata')
    .eq('type', 'person')
    .ilike('title', `%${RYAN_YORK}%`);

  if (!data || data.length === 0) {
    return null;
  }

  const userEntity = data.find(e => e.metadata?.is_user_entity === true);
  return userEntity?.id || data[0].id;
}

export async function POST(request: Request) {
  try {
    const { message, conversation_history } = await request.json();

    if (!message) {
      return Response.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Get user entity ID
    const user_entity_id = await getUserEntityId();

    // Call AI Core
    const response = await fetch(`${AI_CORE_URL}/mentor/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_history: conversation_history || [],
        user_entity_id
      })
    });

    if (!response.ok) {
      throw new Error(`AI Core error: ${response.statusText}`);
    }

    const data = await response.json();
    return Response.json(data);

  } catch (error) {
    console.error('Chat API error:', error);
    return Response.json(
      { error: 'Failed to process chat message' },
      { status: 500 }
    );
  }
}
```

---

## Success Criteria for Phase 2

When Phase 2 is complete, you should be able to:

✅ **Open chat page** at `/mentor/chat`
✅ **See empty chat** with input field
✅ **Type and send message** "Tell me about my work"
✅ **See user message** appear in chat (right-aligned, blue)
✅ **See loading indicator** while waiting
✅ **See Mentor response** appear (left-aligned, gray)
✅ **See entity badges** if entities mentioned
✅ **Continue conversation** with context maintained
✅ **Refresh page** and see history preserved (localStorage)
✅ **Check raw_events** and see messages saved
✅ **Trigger Archivist** and see entities extracted
✅ **Send another message** and see updated context used

**The loop is complete when**: You discuss a topic in chat, it gets processed by Archivist, appears in next digest, and your feedback on that insight improves future chat responses.

---

## Known Limitations & Future Enhancements

### Current Limitations

1. **No streaming responses** - Wait for complete response (2-4s)
2. **localStorage only** - History doesn't sync across devices
3. **Simple keyword matching** - Entity detection could be smarter
4. **No edit/delete** - Can't edit or delete messages
5. **No conversation sessions** - All messages in one continuous thread

### Future Enhancements

**Phase 3** (Optional):
- Streaming responses (SSE or WebSockets)
- Database-backed conversation persistence
- Multiple conversation threads/sessions
- Edit/delete messages
- Export conversation
- Voice input (Whisper API integration)

**Phase 4** (Polish):
- Better entity detection (semantic search)
- Inline entity highlighting (not just badges)
- Entity clickthrough to entity detail page
- Conversation search
- Keyboard shortcuts (Enter to send, Cmd+K for quick actions)
- Mobile responsive layout

---

## Files Created So Far

### Backend Files (Phase 1 - Complete)
1. ✅ `apps/ai-core/models/chat.py` (NEW) - 30 lines
2. ✅ `apps/ai-core/agents/mentor.py` (MODIFIED) - Added 240 lines (chat method + helpers)
3. ✅ `apps/ai-core/main.py` (MODIFIED) - Added 65 lines (POST /mentor/chat endpoint)

### Documentation Files
4. ✅ `docs/features/mentor/chat-implementation-plan.md` (NEW) - Full implementation plan
5. ✅ `docs/features/mentor/ai-handoff.md` (NEW) - This document

### Frontend Files (Phase 2 - Complete)
6. ✅ `apps/web/hooks/useMentorChat.ts` (NEW) - Chat state management with localStorage
7. ✅ `apps/web/components/ChatMessage.tsx` (NEW) - Message component with entity badges
8. ✅ `apps/web/app/api/mentor/chat/route.ts` (NEW) - API proxy route with auth
9. ✅ `apps/web/app/mentor/chat/page.tsx` (NEW) - Chat page with auto-scroll
10. ✅ `apps/web/components/NavBar.tsx` (MODIFIED) - Added chat link

### Infrastructure Files
11. ✅ `apps/ai-core/start.sh` (NEW) - Shell script to start AI Core with venv
12. ✅ `package.json` (MODIFIED) - Added concurrently to run both servers
13. ✅ `apps/ai-core/services/database.py` (MODIFIED) - Added search_entities_by_title method

---

## Dependencies & Environment

### Backend Dependencies (Already installed)
- `anthropic==0.18.1` - Claude API
- `fastapi==0.109.0` - Web framework
- `supabase==2.3.4` - Database client

### Frontend Dependencies (Already installed)
- `next@15` - Framework
- `react@19` - UI library
- `@supabase/supabase-js` - Database client

### Environment Variables (Already configured)
```bash
# AI Core (.env)
ANTHROPIC_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...

# Web (.env.local)
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
AI_CORE_URL=http://localhost:8000
```

---

## Testing Checklist for Next Agent

After implementing Phase 2, test these scenarios:

### Happy Path
- [ ] Open `/mentor/chat` page
- [ ] Send message: "Tell me about my goals"
- [ ] Receive context-aware response referencing core identity
- [ ] Send follow-up: "What should I focus on today?"
- [ ] Receive response with active work context
- [ ] Refresh page - see history preserved

### Entity Context
- [ ] Send: "I had a meeting about the Feed feature"
- [ ] Check response mentions Feed from knowledge graph
- [ ] Check raw_events table shows saved messages
- [ ] Trigger Archivist processing
- [ ] Verify Feed entity updated with new mention

### Error Handling
- [ ] Disconnect AI Core server - see error message
- [ ] Send empty message - button should be disabled
- [ ] Send very long message (>10000 chars) - should handle gracefully

### UI/UX
- [ ] Messages render correctly (styling)
- [ ] Entity badges appear when entities mentioned
- [ ] Auto-scroll to bottom on new message
- [ ] Loading indicator appears while waiting
- [ ] Mobile responsive (test on phone)

### Complete Loop
- [ ] Chat about Water OS project
- [ ] Wait for Archivist (60s or manual trigger)
- [ ] Check entities created/updated
- [ ] Generate digest next day
- [ ] See Water OS referenced in insights
- [ ] Acknowledge insight
- [ ] Chat again about Water OS
- [ ] See improved context in Mentor response
- [ ] **Loop validated!** 🎉

---

## Notes for Next Agent

### Important Patterns to Follow

1. **Server Components by Default**: Next.js 15 uses server components by default. Use `'use client'` only when you need interactivity (hooks, state, event handlers).

2. **API Route Pattern**: Follow the same pattern as existing routes in `/api/events/route.ts` and `/api/feedback/*/route.ts`.

3. **Supabase Client**: Use `createClient()` from `@/utils/supabase/server` in server components and API routes. Use client version in client components.

4. **Error Handling**: Always wrap API calls in try-catch and return proper HTTP status codes (400 for bad request, 500 for server errors).

5. **TypeScript**: Prefer interfaces over types. Add proper type definitions for all functions and components.

### Where to Find Examples

- **Page Layout**: See `apps/web/app/digest/page.tsx`
- **Component Styling**: See `apps/web/components/InsightCard.tsx`
- **API Routes**: See `apps/web/app/api/events/route.ts`
- **Hooks**: Check `apps/web/hooks/` directory for patterns

### Common Pitfalls to Avoid

1. **Don't hardcode URLs**: Use environment variables for AI Core URL
2. **Don't forget user_entity_id**: Always get and pass it
3. **Don't skip error boundaries**: Add try-catch everywhere
4. **Don't forget auto-scroll**: Messages should scroll to bottom automatically
5. **Don't forget localStorage cleanup**: Clear on logout/clear button

---

## Summary for Quick Onboarding

**What's done**: Backend API endpoint that accepts chat messages, provides context-aware responses using knowledge graph, and saves everything to `raw_events` for Archivist processing.

**What's next**: Build React/Next.js chat UI with message list, input field, and conversation management.

**Time estimate**: 2-3 hours for experienced React dev, 4-5 hours for learning Next.js App Router.

**Key files to read**:
1. `docs/features/mentor/chat-implementation-plan.md` - Full plan
2. `apps/web/app/digest/page.tsx` - UI patterns
3. `apps/web/app/api/events/route.ts` - API route patterns

**Start here**: Create `apps/web/hooks/useMentorChat.ts` first. It's the core of the frontend.

**End goal**: Complete feedback loop where chat discussions automatically improve Mentor insights and vice versa.

---

**Phase 1 Status**: ✅ COMPLETE (Backend working)
**Phase 2 Status**: ✅ COMPLETE (Frontend working)

**Latest Commit**: Full chat interface working - users can have context-aware conversations with Mentor, all messages feed into knowledge graph via Archivist.

---

## Lessons Learned & Critical Setup Notes

### Python Environment Issues (CRITICAL)

**Problem**: Initial setup used Python 3.13, which caused package build failures for `tiktoken` and `pydantic-core`.

**Solution**:
```bash
# Recreate venv with Python 3.12
cd apps/ai-core
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Root Cause**: Python 3.13 is too new - many packages don't have pre-built wheels yet and require Rust compilation.

**Prevention**: Always use Python 3.12 (or 3.11) for this project until package ecosystem catches up.

---

### Package Version Conflicts (CRITICAL)

**Problem**: After installing dependencies, AI Core crashed on startup with:
- `TypeError: Client.__init__() got an unexpected keyword argument 'proxy'`
- `TypeError: Client.__init__() got an unexpected keyword argument 'proxies'`
- `ImportError: cannot import name 'AuthorizationError' from 'realtime'`
- `ModuleNotFoundError: No module named 'websockets.asyncio'`

**Root Cause**: The pinned versions in `requirements.txt` were outdated and incompatible with each other.

**Solution**: Upgrade key packages to compatible versions:
```bash
source venv/bin/activate

# Upgrade Supabase ecosystem (fixes proxy errors)
pip install --upgrade 'supabase>=2.22.0' 'realtime>=2.0.0' 'supafunc>=0.5.4'

# Upgrade websockets (fixes asyncio import)
pip install --upgrade 'websockets>=14.0'

# Upgrade Anthropic (fixes httpx compatibility)
pip install --upgrade 'anthropic>=0.42.0'
```

**Current Working Versions** (as of 2025-10-09):
- `supabase==2.22.0`
- `gotrue==2.12.4`
- `postgrest==2.22.0`
- `realtime==2.22.0`
- `storage3==2.22.0`
- `supafunc==0.10.2`
- `httpx==0.28.1`
- `websockets==15.0.1`
- `anthropic==0.69.0`

**Prevention**: Update `requirements.txt` with these versions to prevent future issues.

---

### Missing DatabaseService Method (CRITICAL)

**Problem**: Chat endpoint crashed with:
```
AttributeError: 'DatabaseService' object has no attribute 'search_entities_by_title'
```

**Root Cause**: The mentor chat code was calling `db.search_entities_by_title()` but this method didn't exist in `services/database.py`.

**Solution**: Added the missing method to `DatabaseService`:
```python
def search_entities_by_title(self, search_term: str, limit: int = 5) -> List[Dict]:
    """Search for entities by title (case-insensitive partial match)"""
    try:
        response = (
            self.client.table("entity")
            .select("*")
            .ilike("title", f"%{search_term}%")
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Error searching entities by title: {e}")
        return []
```

**Location**: `apps/ai-core/services/database.py` line 254

**Prevention**: Ensure all database methods called by agents are actually implemented.

---

### Development Server Setup (IMPORTANT)

**Problem**: Running only `pnpm run dev:web` didn't start the AI Core backend, causing connection refused errors.

**Solution**: Created automated startup with concurrently:

**1. Created startup script** (`apps/ai-core/start.sh`):
```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**2. Made executable**:
```bash
chmod +x apps/ai-core/start.sh
```

**3. Updated root `package.json`**:
```json
{
  "scripts": {
    "dev:web": "concurrently \"./apps/ai-core/start.sh\" \"turbo run dev --filter=web\""
  },
  "devDependencies": {
    "concurrently": "^9.2.1"
  }
}
```

**Now one command starts everything**:
```bash
pnpm run dev:web
```

This runs:
- AI Core backend (port 8000)
- Next.js web app (port 3110)

Both with color-coded output from concurrently.

---

### Authentication Integration (IMPORTANT)

**Problem**: Chat API calls returned 401 Unauthorized.

**Root Cause**: The `useMentorChat` hook wasn't sending authentication headers.

**Solution**: Get session token from Supabase and include in requests:
```typescript
// In useMentorChat.ts sendMessage()
const { data: { session } } = await supabase.auth.getSession();

if (!session) {
  throw new Error('Not authenticated. Please sign in again.');
}

const response = await fetch('/api/mentor/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.access_token}`, // Critical!
  },
  body: JSON.stringify({...})
});
```

**Pattern**: All API routes that call AI Core require this auth pattern.

---

### Next.js 15 Async Params (TypeScript Fix)

**Problem**: Build failed with type errors on dynamic route params:
```
Type "{ params: { id: string; }; }" is not a valid type for the function's second argument.
```

**Root Cause**: Next.js 15 changed params to be async Promises.

**Solution**: Update all dynamic routes:
```typescript
// OLD (Next.js 14)
export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  const insightId = params.id;
}

// NEW (Next.js 15)
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const insightId = id;
}
```

**Files Updated**:
- `apps/web/app/api/feedback/acknowledge/[id]/route.ts`
- `apps/web/app/api/feedback/dismiss/[id]/route.ts`

---

### TypeScript Strict Mode (Build Fix)

**Problem**: Build failed with:
```
The inferred type of 'ComponentName' cannot be named without a reference to '.pnpm/@types+react@19.1.17/...'
```

**Root Cause**: TypeScript strict mode in Next.js 15 requires explicit return types.

**Solution**: Add return type annotations:
```typescript
// For client components that can return null
export function InsightCard({ insight }: Props): React.JSX.Element | null {
  // ...
}

// For regular client components
export default function ChatMessage({ role, content }: Props): React.JSX.Element {
  // ...
}

// For async server components
export default async function DigestPage(): Promise<React.JSX.Element> {
  // ...
}
```

**Files Updated**:
- `apps/web/app/mentor/chat/page.tsx`
- `apps/web/components/ChatMessage.tsx`
- `apps/web/components/InsightCard.tsx`
- `apps/web/app/digest/page.tsx`

---

## How to Keep It Working

### Daily Development

**Start servers**:
```bash
pnpm run dev:web
```

Both AI Core and web app will start. Watch for errors in both `[0]` (AI Core) and `[1]` (web) output.

**Check if AI Core is healthy**:
```bash
curl http://localhost:8000/health
```

**Test chat endpoint**:
```bash
curl -X POST http://localhost:8000/mentor/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "conversation_history": [], "user_entity_id": null}'
```

---

### When Adding New Features

**If adding new database methods**:
1. Add method to `apps/ai-core/services/database.py`
2. Test it with a simple Python script before using in agents
3. Add type hints and error handling

**If updating Python packages**:
1. Always use Python 3.12 venv
2. Test that AI Core still starts after updates
3. Check for httpx/supabase version conflicts

**If updating Next.js code**:
1. Remember to add return types to all exported functions
2. Use `Promise<{ param: string }>` for dynamic route params
3. Test both dev and build (`pnpm run build`)

---

### Troubleshooting Guide

**AI Core won't start**:
```bash
# 1. Check Python version
source venv/bin/activate
python --version  # Should be 3.12.x

# 2. Try importing main.py
python -c "import main; print('OK')"

# 3. If it fails, reinstall packages
pip install --upgrade 'supabase>=2.22.0' 'anthropic>=0.69.0' 'websockets>=15.0'
```

**Chat returns connection refused**:
```bash
# Check if AI Core is running
ps aux | grep uvicorn

# Check if port 8000 is listening
lsof -i :8000

# Restart dev servers
pnpm run dev:web
```

**Chat returns 401 Unauthorized**:
- Make sure you're signed in to the web app
- Check that `useMentorChat.ts` is getting the session token
- Verify auth header is being sent in network tab

**Build fails with type errors**:
- Add explicit return types: `: React.JSX.Element`
- For async server components: `: Promise<React.JSX.Element>`
- For dynamic routes: `{ params: Promise<{ id: string }> }`

---

## Success Checklist

After any changes, verify:

- [ ] `pnpm run dev:web` starts both servers without errors
- [ ] Can visit `http://localhost:3110/mentor/chat`
- [ ] Can send a message and get a response
- [ ] Message appears in `raw_events` table with `source='mentor_chat'`
- [ ] Archivist processes the message (wait 60s or trigger manually)
- [ ] Entities are extracted from the conversation
- [ ] `pnpm run build` completes successfully
- [ ] No TypeScript errors in build output

---

**Status**: Everything working as of 2025-10-09 21:30 🎉
