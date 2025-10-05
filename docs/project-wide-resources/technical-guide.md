UMG Technical Guide for AI Agents
Objective: This document provides a comprehensive technical overview of the Unified Memory Graph (UMG) project. Its purpose is to onboard any developer or AI agent, ensuring a deep understanding of the project's goals, architecture, and technology stack.

1. Project Vision & Goals
Project UMG (Unified Memory Graph) is a bespoke personal AI system designed to function as a persistent mentor, coach, and thought partner.

The primary goal is to accelerate the user's personal and professional growth by building a deep, interconnected memory of their work, thoughts, and values. The system will capture, connect, and reason over all aspects of their life—from daily reflections and meeting notes to code commits and long-term goals.

By identifying patterns, challenging assumptions, and surfacing hidden connections, the UMG's "Mentor" agent will help ensure the user's daily actions remain aligned with their core values and life's mission.

2. Core Architecture & Philosophy
The architecture is a system of connected applications that share a common backend and database, all managed within a monorepo. The core philosophy is to use the right tool for each job:

TypeScript & React Ecosystem: For all frontend applications and the Node.js backend API to maximize code sharing.

Python: For the dedicated AI Core, leveraging its superior AI/ML ecosystem.

Supabase (Postgres): As the all-in-one backend for database, authentication, and serverless functions.

### Technology Decisions & Rationale

**Why Turborepo + pnpm?**
- Single repository containing all apps and shared code
- Share components, logic, and TypeScript types across all three frontend apps
- pnpm is faster and more efficient than npm/yarn for workspace management
- Simplifies dependency management—no version conflicts between apps

**Why TypeScript for Frontend & API?**
- Same language reduces cognitive load
- Share types between frontend and backend—database types defined once, used everywhere
- Modern, well-supported ecosystem with excellent AI assistance
- Strong type safety catches errors at compile time

**Why Node.js for API Server?**
- Same language as frontend = shared types and code
- Excellent async I/O performance for webhooks and API endpoints
- Tight integration with Supabase
- Fast development cycle—no context switching between languages

**Why Python for AI Core?**
- Best AI/ML ecosystem (LangChain, LlamaIndex, transformers)
- Access to cutting-edge tools as they're released
- Superior libraries for NER, embeddings, and LLM orchestration
- Future-proof for new AI capabilities
- Runs as separate microservice, communicates with Node.js API via HTTP

**Why Supabase (Postgres + pgvector)?**
- Built-in vector search with pgvector extension (semantic search out of the box)
- Includes authentication, storage, and serverless functions
- Can host Node.js backend via Edge Functions
- Full SQL power for complex graph queries
- Real-time subscriptions for live updates
- Open source—can self-host if needed

3. The Tech Stack & Components
A. The Monorepo (Turborepo with pnpm)
The entire project lives in a single repository to simplify dependency management and code sharing. pnpm is used for its speed and efficiency in managing workspace packages.

B. Frontend Applications (apps/)
These are the user-facing interfaces for capturing data and viewing insights.

apps/web (Next.js): The main web dashboard.

Purpose: Provides browser-based access for viewing insights from the Mentor agent, visualizing the memory graph, and handling the Triage UI where the user classifies incoming raw data from automated sources.

apps/mobile (React Native with Expo): The primary on-the-go capture tool.

Purpose: Optimized for quick, frictionless capture of voice memos and text-based thoughts. It also serves as a convenient way to review daily insights.

apps/desktop (Tauri): A lightweight, native macOS application.

Purpose: Provides a globally accessible hotkey for instant text capture. This allows the user to log "aha moments" or quick notes without leaving their current application context.

C. Backend & AI Services
These are the headless systems that perform the data processing and sense-making.

Node.js API Server (Next.js API Routes):

Purpose: Acts as the "front door" for all incoming data. It provides a secure API endpoint (/api/events) that the frontend apps and external webhooks call to submit data. Its sole job is to write this information into the raw_events table.

apps/api (Python, FastAPI, LangChain): The AI Core, the brain of the operation.

Purpose: This standalone Python service hosts the intelligent agents responsible for processing data and generating insights. It runs independently from the Node.js server.

D. Intelligent Agents (within the AI Core)
The "Archivist" Agent: The sense-maker.

Function: Runs as a continuous background process. It monitors the raw_events table, pulls new data, and uses LLMs to process it. It identifies and creates entity nodes, establishes edge relationships, and generates chunks and embeddings to build the UMG.

The "Mentor" Agent: The insight generator.

Function: Runs on a schedule (e.g., daily). It queries the fully processed UMG, looks for patterns, and generates actionable suggestions or challenges, which it writes to the insight table for the user to see in the web app.

E. Database (Supabase with pgvector)
The single source of truth for all data, both raw and processed. The schema is designed to support both relational queries (e.g., finding all tasks for a project) and semantic search (e.g., finding all thoughts related to a concept).

F. Shared Packages (packages/)
These are internal libraries shared across the different applications in the monorepo.

packages/ui: A library of shared React components (buttons, cards, etc.) used by the web, mobile, and desktop apps.

packages/db: Contains the Supabase client and shared TypeScript types for the database schema, ensuring data consistency.

packages/config: Shared configurations for tools like ESLint and TypeScript.

4. High-Level Data Flow

Stage 1: Collection (Zero Friction)

Manual Entry:
- Voice debrief app: Morning/evening reflections with automatic transcription
- Global hotkey text capture (Tauri desktop app): Instant capture without context switching
- Direct conversation with Mentor agent in web app
- Status: Created with 'pending_processing' (skip triage—intentional capture)

Automatic Webhooks:
- Granola: Meeting transcripts and summaries
- GitHub: Commit messages, PR descriptions, code changes
- Slack: Key messages and threads
- Calendar: Meeting metadata and scheduling patterns
- Status: Created with 'pending_triage' (requires human classification)

All entries saved to raw_events table with immutable payload.

Stage 2: Triage (Human Signal) - Automatic Entries Only

For events with status='pending_triage':
1. User sees queue of unclassified events in Triage UI
2. Quick actions:
   - Delete → status='ignored' (irrelevant, won't be processed)
   - Tag importance (low/medium/high) → status='pending_processing'
3. Optional: Add brief notes about why it matters (stored in payload metadata)

Why Triage Matters:
- Prevents noise: Not every meeting is important
- Focuses AI processing power on what matters
- Your judgment trains the system over time

Manual entries skip triage since you intentionally captured them.

Stage 3: Sense-Making (The Archivist Agent)

The Archivist runs as a background process in the Python AI Core, triggered by new events with status='pending_processing'.

Processing Steps:

1. Parse & Clean: Extract structured data from raw payload
2. Entity Recognition: Use NER (Named Entity Recognition) to identify:
   - People, companies, projects
   - Features, tasks, decisions
   - Concepts mentioned multiple times
3. Entity Creation/Update:
   - Immediate creation: Concepts that are the main subject of action
   - After multiple mentions: Concepts mentioned 2-3 times promoted to entity
   - Passing mentions: Tagged in metadata only, not elevated to entity
   - Hub-and-spoke: Complex entities like "Feed feature" get spokes (meeting notes, tasks, reflections)
4. Relationship Mapping: Create edges between entities:
   - 'belongs_to': Feature belongs_to Project
   - 'modifies': Meeting note modifies Feature (e.g., renaming)
   - 'mentions': Reflection mentions Person
   - 'informs': Research informs Decision
   - 'blocks': Task blocks another Task
   - 'contradicts': New strategy contradicts Previous approach
5. Chunking: Break content into searchable pieces (optimized for token limits)
6. Embedding: Generate vector representations via embedding API
7. Signal Assignment: Set importance, recency, novelty scores
8. Provenance: Link everything back to source via source_event_id and edges
9. Update Status: raw_event status → 'processed'

Entity Creation Example - The Feed Feature:
- Week 1: "school-update feature" mentioned → entity created
- Week 2: Meeting note says "We're renaming it to 'feed'"
- Archivist recognizes this → adds "school-update feature" to aliases in metadata
- Creates 'modifies' edge from meeting_note to feature entity
- Future queries for "feed" OR "school-update" both find this entity

Stage 4: Coaching (The Mentor Agent)

Daily Digest Generation (scheduled for 7 AM):

1. Query Last 24 Hours: Pull all recent entities with high recency
2. Find Historical Context: Vector search for 3 most relevant past entries
3. Generate 3-Card Digest:
   - Delta Watch: "Your goal was X, but you focused on Y. Pivot or distraction?"
     - Compares stated intentions (entities with type='goal') with actual work
   - Connection: "This insight relates to a pattern from 3 months ago..."
     - Uses vector similarity to find relevant historical context
   - Prompt: "Based on yesterday, what's the most important question today?"
     - Challenges assumptions, proposes forward-looking reflection
4. Write to insight table with drivers (entity_ids and edge_ids that prompted each card)

Ongoing Conversations:

User asks: "What did I decide about the Texas school?"
1. Generate query embedding
2. Vector search finds top 5 semantically similar chunks
3. Traverse edges to gather full context (related entities, edges showing decision evolution)
4. Weigh recency and importance: Recent updates matter more, but history provides context
5. Synthesize answer grounded in your memory
6. Maintain conversation context while always linking back to graph

Feedback Loop:
- User clicks "Acknowledge" on Delta Watch insight
  → Raises importance scores for related entities
  → Updates recency (you just engaged with this)
  → Mentor surfaces similar patterns more frequently
- User clicks "Dismiss" on Connection insight
  → Lowers importance scores for those historical entities
  → Adjusts future Connection card algorithm to avoid similar patterns
  → System learns what's valuable to you

Stage 5: Presentation

Web Dashboard (apps/web):
- Daily Digest: 3 cards (Delta Watch, Connection, Prompt) with Accept/Dismiss buttons
- Triage Queue: Unclassified webhook events awaiting your signal
- Memory Graph Visualization: Interactive graph of entities and edges
- Conversational Interface: Chat with Mentor, grounded in your memory

The user's interactions (dismissing insights, acknowledging patterns, asking questions) continuously train the system's understanding of what's valuable.
