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
Capture: The user creates data via a frontend app (e.g., a voice note on mobile) or an external service sends a webhook (e.g., a meeting summary from Granola).

Ingestion: The data is sent to the Node.js API Server, which writes it as a single entry in the raw_events table with a pending status.

Sense-Making: The Python "Archivist" agent detects the new event, processes its content, and populates the entity, edge, chunk, and embedding tables, effectively building the memory graph.

Insight Generation: The Python "Mentor" agent periodically queries the graph, finds a valuable insight, and writes it to the insight table.

Presentation: The user opens the apps/web dashboard, which reads from the insight table and displays the Mentor's latest suggestions.
