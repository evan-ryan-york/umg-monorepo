# UMG Monorepo - Setup Complete ✅

## Project Structure

```
umg-monorepo/
├── apps/
│   ├── web/           # Next.js web dashboard (Triage UI, visualization)
│   ├── mobile/        # React Native (Expo) mobile app (voice & text capture)
│   ├── desktop/       # Tauri desktop app (global hotkey text capture)
│   └── api/           # Python/FastAPI service for AI Core
├── packages/
│   ├── ui/            # Shared React components
│   ├── config/        # Shared ESLint, Prettier, TSConfig
│   ├── typescript-config/  # TypeScript configurations
│   ├── eslint-config/ # ESLint configurations
│   └── db/            # Shared Supabase client & database types
├── .env.local         # Environment variables (configured)
├── package.json       # Root package.json with pnpm
├── pnpm-workspace.yaml
└── turbo.json         # Turborepo configuration

```

## ✅ Completed Setup Steps

### 1. Monorepo Initialization
- ✅ Turborepo initialized with **pnpm** as package manager
- ✅ Workspace configured for all apps and packages

### 2. Supabase Configuration
- ✅ Project ID: `mdcarckygvbcjgexvdqw`
- ✅ Environment variables configured in `.env.local`
- ✅ **pgvector extension enabled**
- ✅ **7 database tables created:**
  - `raw_events` - Stores all incoming data
  - `entity` - Core knowledge graph nodes
  - `edge` - Relationships between entities
  - `chunk` - Text chunks for embedding
  - `embedding` - Vector embeddings (1536 dimensions)
  - `signal` - Importance/recency/novelty scores
  - `insight` - AI-generated insights

### 3. Frontend Applications Scaffolded
- ✅ **Web** (Next.js 15 + TypeScript + Tailwind)
- ✅ **Mobile** (React Native + Expo + TypeScript)
- ✅ **Desktop** (Tauri 2 + React + TypeScript + Vite)

### 4. Python AI Core Setup
- ✅ Virtual environment created at `apps/api/venv`
- ✅ Dependencies installed:
  - FastAPI 0.115.6
  - Uvicorn 0.34.0
  - LangChain 0.3.16
  - LangChain-OpenAI 0.3.2
  - Supabase 2.14.0
- ✅ Basic FastAPI server created with CORS

### 5. Shared Packages Initialized
- ✅ `@repo/ui` - Shared React components
- ✅ `@repo/db` - Supabase client + TypeScript types
- ✅ `@repo/typescript-config` - Shared TS configs
- ✅ `@repo/eslint-config` - Shared linting rules

## 🚀 Next Steps: Phase 1 Development

### 1. Capture Interfaces
Build basic UI for Mobile and Desktop apps to send text/voice data to `/api/events` endpoint.

**Tasks:**
- [ ] Create mobile capture screen with text input
- [ ] Add voice recording capability (React Native Audio)
- [ ] Build desktop global hotkey listener (Tauri)
- [ ] Implement quick capture form

### 2. Backend Event Endpoint
Create `/api/events` endpoint that writes to `raw_events` table.

**Tasks:**
- [ ] Add route in Next.js: `app/api/events/route.ts`
- [ ] Validate incoming payload
- [ ] Insert into `raw_events` with status='pending_triage'
- [ ] Return success response

### 3. Archivist v1 (Python Agent)
Background task that processes `raw_events` → creates entities, chunks, embeddings.

**Tasks:**
- [ ] Create `apps/api/agents/archivist.py`
- [ ] Poll `raw_events` where status='pending_triage'
- [ ] Extract entities using LLM
- [ ] Generate chunks and embeddings (OpenAI)
- [ ] Write to `entity`, `chunk`, `embedding` tables
- [ ] Update event status to 'processed'

### 4. Mentor v1 - Daily Digest
Simple view in web app showing generated insights.

**Tasks:**
- [ ] Create `app/insights/page.tsx` in web app
- [ ] Query `insight` table for recent insights
- [ ] Display in card-based UI
- [ ] Add basic filtering by status

## 🔧 Development Commands

### Run All Apps (Turborepo)
```bash
pnpm dev          # Run all apps in dev mode
pnpm build        # Build all apps
pnpm lint         # Lint all apps
```

### Individual Apps
```bash
# Web Dashboard
cd apps/web
pnpm dev          # Runs on http://localhost:3000

# Mobile App
cd apps/mobile
pnpm start        # Start Expo dev server

# Desktop App
cd apps/desktop
pnpm dev          # Launches Tauri app

# Python AI Core
cd apps/api
source venv/bin/activate
python main.py    # Runs on http://localhost:8000
# or
uvicorn main:app --reload
```

## 📝 Environment Variables

Remember to update `.env.local` with your API keys:
- `OPENAI_API_KEY` - For embeddings and LLM calls
- `ANTHROPIC_API_KEY` - Alternative LLM provider

## 🗄️ Database Access

**Supabase Dashboard:** https://supabase.com/dashboard/project/mdcarckygvbcjgexvdqw

**Connection via code:**
```typescript
import { supabase } from '@repo/db';

// Example: Insert raw event
await supabase.from('raw_events').insert({
  payload: { text: "My reflection..." },
  source: "mobile",
  status: "pending_triage"
});
```

## 📚 Key Technologies

| Layer | Tech | Purpose |
|-------|------|---------|
| Monorepo | Turborepo + pnpm | Unified workspace management |
| Web | Next.js 15 | Dashboard & triage UI |
| Mobile | React Native + Expo | Native iOS/Android capture |
| Desktop | Tauri 2 | Lightweight native desktop app |
| AI Core | Python + FastAPI | LLM orchestration & agents |
| Database | Supabase (Postgres + pgvector) | Unified data & vectors |
| AI/ML | LangChain + OpenAI | Embeddings & LLM agents |

---

**Setup completed on:** October 2, 2025
**All 6 setup steps completed successfully!** 🎉
