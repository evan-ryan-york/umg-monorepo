# AI Agent Quickstart Guide

**READ THIS FIRST** before starting any work on the UMG project.

---

## Project Overview

UMG (Unified Memory Graph) is a bespoke personal AI system designed to function as a persistent mentor, coach, and thought partner. It captures, connects, and reasons over all aspects of the user's life—from daily reflections and meeting notes to code commits and long-term goals—to accelerate personal and professional growth aligned with core values.

The system operates on a **Pipes → Brain → Mentor** model:
- **Pipes**: Frictionless capture of data (text, voice, webhooks)
- **Brain**: AI agents process raw data into a structured memory graph
- **Mentor**: Proactive intelligence that surfaces insights and challenges assumptions

---

## Tech Stack Overview

**Monorepo**: Turborepo with pnpm workspaces

**Frontend**:
- `apps/web` - Next.js 15 (App Router) with React 19 and Tailwind CSS v4
- `apps/mobile` - React Native with Expo (not yet implemented)
- `apps/desktop` - Tauri (not yet implemented)

**Backend**:
- Supabase (PostgreSQL + pgvector for embeddings)
- Node.js API (Next.js API routes in `apps/web`)
- Python AI Core with FastAPI (not yet implemented)

**Shared Packages**:
- `packages/db` - Supabase client and TypeScript types
- `packages/ui` - Shared React components
- `packages/config` - Shared configs (ESLint, TypeScript)

---

## Critical Rules

### Development Workflow

❌ **NEVER** start or stop dev servers (e.g., `pnpm run dev`, `pnpm dev`)
- The user manages all local services
- If you need the server running, ask the user
- Exception: Background processes explicitly requested by the user

✅ **ALWAYS** run `pnpm run build` when your task is complete
- This ensures no TypeScript errors were introduced
- Run from the monorepo root to check all packages
- Report any build errors before marking task complete

✅ **ALWAYS** read `@docs/project-wide-resources/ai-memory.md` first
- This is the source of truth for what's been done
- Update it when you complete significant work
- Prevents duplicate work and maintains context

### Code Quality Standards

❌ **NO TypeScript shortcuts**
- Never use `:any` type
- Never use `@ts-ignore` or `@ts-expect-error` without explanation
- All types must be properly defined
- Use `unknown` if type is truly unknown, then narrow it

✅ **Prefer existing patterns**
- Check existing code before creating new patterns
- Use shared types from `packages/db`
- Follow existing file structure conventions

✅ **Database operations**
- Always use the Supabase client from `@repo/db`
- Never bypass RLS policies
- All types should match the database schema

### Documentation Standards

✅ **Update documentation as you work**
- Update `ai-memory.md` when completing features
- Create/update implementation plans in `docs/` as needed
- Mark tasks complete in plans when done

❌ **Don't create unnecessary documentation**
- No README files unless explicitly requested
- No verbose code comments for self-explanatory code
- Focus on "why" not "what" in comments

---

## Key Files to Read

**Start here** (in order):
1. `docs/ai-quickstart.md` (this file)
2. `docs/project-wide-resources/ai-memory.md` - What's been built and current state
3. `docs/project-wide-resources/project-overview.md` - Mission and vision
4. `docs/project-wide-resources/technical-guide.md` - Detailed architecture
5. `docs/project-wide-resources/database-structure.md` - Complete schema

**Implementation plans** (when relevant):
- `docs/raw-input-text-implementation-plan.md` - Example of completed feature

---

## Common Commands

```bash
# Install dependencies (from monorepo root)
pnpm install

# Build all packages (ALWAYS run before marking task complete)
pnpm run build

# Run linting
pnpm run lint

# Type checking (without emitting files)
pnpm run check-types

# Run builds for specific package
pnpm --filter web build
pnpm --filter @repo/db build
```

---

## Project Structure

```
umg-monorepo/
├── apps/
│   ├── web/          # Next.js web app (primary interface)
│   ├── mobile/       # React Native app (not yet implemented)
│   └── desktop/      # Tauri desktop app (not yet implemented)
├── packages/
│   ├── db/           # Supabase client + types
│   ├── ui/           # Shared React components
│   ├── config/       # Shared configurations
│   ├── eslint-config/
│   └── typescript-config/
└── docs/
    ├── ai-quickstart.md (this file)
    ├── ai-memory.md (development history)
    └── project-wide-resources/
```

---

## Current State

**What's Built**:
- ✅ Supabase database with 7 core tables
- ✅ `packages/db` with client and types
- ✅ Raw text input system in `apps/web`
- ✅ API route for submitting events
- ✅ Basic capture UI

**What's NOT Built**:
- ❌ Python AI Core (Archivist and Mentor agents)
- ❌ Voice input
- ❌ Mobile and desktop apps
- ❌ Triage UI
- ❌ Graph visualization
- ❌ RAG system for semantic search

See `docs/project-wide-resources/ai-memory.md` for detailed status.

---

## When Starting a Task

1. **Read this file** (you're doing it!)
2. **Read `ai-memory.md`** to understand current state
3. **Ask clarifying questions** before making assumptions
4. **Create/update implementation plans** for non-trivial features
5. **Use TodoWrite tool** to track progress on multi-step tasks
6. **Update `ai-memory.md`** when completing significant work
7. **Run `pnpm run build`** before marking task complete

---

## Environment Variables

Located in `apps/web/.env.local` (already configured):
```
NEXT_PUBLIC_SUPABASE_URL=https://mdcarckygvbcjgexvdqw.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[redacted]
SUPABASE_SERVICE_ROLE_KEY=[redacted]
```

---

## User Preferences

- **Concise communication**: Be direct and to the point
- **No preamble/postamble**: Skip "Here's what I'll do" and "I've completed" - just do it
- **Proactive but not presumptuous**: Take initiative on tasks, but ask about ambiguity
- **Value alignment**: This project serves a mission to tackle the global water crisis via WaterOS

---

*Last Updated: 2025-10-03*
