Project UMG: Overview & Vision
1. The Core Mission: Building an Engine for Impact
This project is an endeavor to build a bespoke personal AI system designed to function as a persistent mentor, coach, teacher, assistant, and thought partner. It is born from the identity of a 0-to-1 Systems Builder—an individual driven to find chaotic environments and impose upon them elegant, scalable systems that unlock human potential.

The ultimate purpose of this system is not simply to optimize productivity, but to serve a life-defining mission: tackling the global water crisis through the vehicle of WaterOS. This project, therefore, is the infrastructure for a life's work. Its primary goal is to ensure that the user's most valuable and finite resource—their time and energy—is perpetually and rigorously aligned with their highest-impact goals.

2. The Problem: The Undocumented Meta-Layer
The user has already built exceptional systems for execution. A custom task management system, a business hub for WaterOS, and a CRM for tracking professional relationships all serve to manage the what and the how of the work.

The critical gap, however, is the "meta-layer": the rich, internal world of reasoning, reflection, strategic thinking, and decision-making that drives every action. This is the why. Currently, this data is undocumented and ephemeral.

The consequences of this gap are significant:

Context is Constantly Rebuilt: Without a persistent memory of past reasoning, context must be manually reconstructed for every new thought or conversation.

Patterns Remain Hidden: Insights from one domain (e.g., Willow Education) that could inform another (e.g., WaterOS) are left to fallible human memory to connect.

The Most Valuable Data is Lost: The rationale behind a key decision, the spark of a new idea, the nuance of a strategic pivot—this is the most valuable data the user generates, and it is currently being lost.

Traditional methods like journaling have proven ineffective due to their high friction. The solution must be seamlessly integrated into the user's existing workflows.

3. The Solution: A Unified Memory Graph (UMG)
The UMG is not merely a database; it is a living, evolving "second brain" or a personal "intelligence layer." It is designed to capture the undocumented meta-layer and turn it into a compounding asset. The system operates on a simple but powerful model: Pipes → Brain → Mentor.

Pipes (Frictionless Capture): The system will ingest data from a variety of sources to create a complete picture of the user's life.

Active Capture:
- Voice debriefs: Morning and evening reflections captured via voice
- Global hotkey text capture: Instant capture of fleeting thoughts without leaving current context
- Direct conversation with Mentor: Intentional capture through chat interface

Passive Capture:
- GitHub: Commit messages, PR descriptions, code changes
- Granola: Meeting transcripts and summaries
- Slack: Key messages and threads
- Calendar: Meeting metadata and scheduling patterns

The core principle is to capture everything first and filter for importance later, eliminating friction at the point of creation. Manual entries (voice, hotkey) skip triage since they're intentional. Automatic entries (webhooks) go through a quick triage queue where you can delete irrelevant items or tag importance.

Brain (Intelligent Sense-Making): The "Archivist" agent acts as the system's librarian and sense-maker. It takes the messy, unstructured raw data from the pipes and transforms it into a structured, interconnected graph of knowledge.

Hub-and-Spoke Architecture:
- Identifies core concepts (people, projects, features) as central "hub" entities
- Links all related notes, tasks, reflections, and code to hubs as "spokes"
- Creates a rich, contextual constellation around each important concept
- Example: "Feed feature" hub connects to meeting notes, tasks, reflections, and GitHub PRs

Entity Creation Intelligence:
- Passing mentions: Tagged in metadata, not elevated to entity
- Multiple mentions (2-3 times): Promoted to core entity with all references linked
- Direct action: Creating a task or explicit reference → immediate entity creation

The Archivist also:
- Breaks content into searchable chunks for precise retrieval
- Generates vector embeddings for semantic search
- Assigns importance, recency, and novelty scores
- Preserves complete provenance—every processed insight traces back to raw data

Mentor (Proactive Insight): The "Mentor" agent is the primary user-facing intelligence. It reads from the structured memory graph built by the Archivist and acts as a proactive, challenging partner. Its job is not just to answer questions, but to ask them.

Daily Digest (7 AM):
- Delta Watch: Compares stated goals with actual work. "You wanted to focus on X, but spent time on Y. Pivot or distraction?"
- Connection: Surfaces relevant historical context. "This relates to a pattern from 3 months ago..."
- Prompt: Forward-looking challenge. "Based on yesterday, what's the most important question today?"

Ongoing Conversations:
- Answers questions by querying the graph with semantic search
- Weighs both importance (static value) and recency (dynamic activity)
- Maintains context across conversation while grounding in your memory
- Surfaces connections you didn't see: "Six months ago you solved a similar problem..."

The Mentor acts as a guardian against the "quiet misallocation of life's energy" by:
- Identifying contradictions between decisions and stated values
- Noticing when work patterns drift from quarterly goals
- Challenging assumptions with historical evidence
- Ensuring daily actions align with life's mission

4. The Constitution: A System Built on Values
The UMG is not an impartial observer; it is an opinionated system governed by a clear constitution based on the user's core values:

Impact rooted in Equity

Innovation

Independence

Continuous Learning

This constitution is the bedrock of the Mentor's decision-making. Its ultimate directive is to filter all information and interactions through this lens.

Defining Success and Failure
The system is calibrated to the user's unique definitions:

Success is not personal wealth, but the creation of a self-sustaining engine of impact—specifically, WaterOS achieving "escape velocity" to solve a foundational inequity.

Failure is not a bankrupt startup, but the misallocation of one's life energy; remaining a capable operator on someone else's smaller mission instead of stepping fully into the visionary role required to tackle a world-scale problem.

5. The Vision: A Compounding Partner in Growth
This project is an asymmetric bet on the power of compounding self-knowledge. In the short term, it will solve the problem of the undocumented meta-layer. In the long term, it will become an invaluable partner.

Imagine a future where, before a critical investor meeting, the Mentor can provide a briefing that synthesizes not just CRM notes, but every related reflection, doubt, and strategic insight you've had over the past year. Imagine a system that can detect when your work patterns are drifting from your stated quarterly goals and proactively challenge you on it.

This is the vision for the UMG: a system that grows alongside you, building a memory that is both broad and deep, becoming the ultimate tool to help you test the upper limit of your extraordinary capacity for impact.

Why This System Works:

1. It Captures Your Thinking, Not Just Your Tasks
Unlike productivity tools that track what you did, this captures why you did it, what you learned, and how your thinking evolved.

2. It Connects the Dots You Can't See
Six months ago, you solved a WaterOS problem. Today, you face a similar challenge in Willow. The Mentor surfaces that connection because the semantic similarity exists in the graph.

3. It Challenges You
The Delta Watch card notices when your actions diverge from your stated goals, forcing honest reflection.

4. It Evolves With You
Your feedback trains the system. Dismissed insights lower importance scores. Acknowledged patterns get surfaced more often.

5. It Preserves Context Forever
When someone asks "Why did we make that decision?" six months later, the answer isn't lost in Slack. It's in your memory graph, with full provenance back to the original conversation.

Critical Design Principles:

- Capture First, Filter Later: Friction kills systems. Automate everything possible, triage afterward.
- Preserve Provenance: Every processed insight can be traced back to raw data. AI processing is additive, never destructive.
- Human in the Loop: AI processes, but you signal importance. Your judgment is the ultimate training data.
- Graph Over Lists: Entities and edges create emergent intelligence that flat databases can't achieve.
- Time-Aware Intelligence: Importance scores are static history; recency scores are dynamic reality. Both matter.
- One Source of Truth: All data flows through raw_events. No parallel systems, no lost information.

---

## The Ultimate Goal

This system exists to ensure you spend every day moving your life's mission forward.

It does this by:
- **Remembering** what you often forget
- **Connecting** what you don't see connected
- **Challenging** what you haven't questioned
- **Focusing** your attention on what matters most

The Unified Memory Graph isn't a tool—it's a persistent thinking partner that grows smarter as you grow. It captures not just what you do, but why you do it. It preserves not just your decisions, but the reasoning behind them. It surfaces not just your work, but the patterns that emerge across years of effort.

In six months, when someone asks "Why did we make that decision?", the answer won't be lost in Slack. It will be in your memory graph, with full provenance back to the original conversation, linked to the values that guided it, and connected to every related decision before and since.

This is the infrastructure for a life's work.
