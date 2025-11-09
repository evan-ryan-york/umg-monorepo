# Relationship Engine

## Overview

The **Relationship Engine** is a separate, asynchronous system responsible for discovering and creating connections (edges) between entities in the Universal Memory Graph. While the Archivist extracts and creates entity nodes from raw events, the Relationship Engine operates independently to find meaningful relationships across the entire knowledge graph.

## What It Does

The Relationship Engine scans the entity graph and creates weighted edges between entities that are meaningfully connected. It answers the fundamental question: **"What relates to what, and how?"**

### Core Functions

1. **Discovers Connections**: Identifies all meaningful relationships between entities, regardless of whether they were created in the same event or years apart.

2. **Creates Edges**: Generates typed, weighted edges in the graph database with metadata including:
   - `relationship_type`: The nature of the connection (e.g., "worked_at", "role_at", "relates_to")
   - `confidence`: How certain the engine is about this connection (0.0 to 1.0)
   - `importance`: How significant this relationship is (0.0 to 1.0)
   - `description`: Rich context about the relationship (e.g., "CTO", "Co-founder")
   - `start_date` / `end_date`: Temporal boundaries when applicable
   - `source_strategy`: Which detection strategy found this connection

3. **Updates Edge Weights**: Strengthens existing connections when they're reinforced by new evidence, weakens connections over time through pruning.

4. **Cross-Event Pattern Recognition**: Unlike the Archivist (which processes one event at a time), the Relationship Engine sees the **entire graph**, enabling it to find connections like:
   - A role entity from 2020 connecting to an organization entity from 2018
   - A skill mentioned in Event A relating to a project mentioned in Event B
   - A person's goal from last year relating to a decision made today

## Why It Exists (Separation from Archivist)

### The Problem with Integrated Relationship Detection

Originally, relationship detection was embedded within the Archivist pipeline:
```
Event → Extract Entities → Detect Relationships → Create Both → Done
```

This created several critical limitations:

1. **Tunnel Vision**: Relationships could only be found within the context of a single event. If a role was mentioned in one event and the organization in another, no connection would ever be made.

2. **Prescriptive Constraints**: The relationship detection relied on predefined templates ("person → organization", "person → skill"), meaning it could only find relationships that matched known patterns. Novel connection types were impossible.

3. **Real-World Example of Failure**:
   - Entity created: "Executive Director at Youth Empowerment Through Arts and Humanities" (type: role)
   - Entity created: "Youth Empowerment Through Arts and Humanities" (type: organization)
   - No edge created between them because the relationship detector had no "role → organization" template
   - Result: Obvious connections missing from the graph

4. **Performance Bottleneck**: Relationship detection is computationally expensive (requires LLM calls, semantic analysis). Forcing it to happen synchronously during event processing slowed down the entire pipeline.

### The Solution: Separation of Concerns

**Archivist**: Fast, focused, event-scoped entity extraction
- "What things are mentioned in this event?"
- Creates entity nodes
- Runs synchronously during event processing
- Optimized for speed and accuracy

**Relationship Engine**: Slow, comprehensive, graph-scoped connection discovery
- "What things relate to what other things across the entire graph?"
- Creates and updates edges
- Runs asynchronously (batch, scheduled, on-demand)
- Optimized for discovering ALL meaningful connections

This mirrors the separation in your brain between **encoding** (hippocampus) and **consolidation** (hippocampal-neocortical dialogue during sleep).

## Neuroscientific Foundation

The Relationship Engine is directly modeled on three core neuroscientific principles from the brain reference:

### 1. Hebbian Learning & Long-Term Potentiation (LTP)

**Brain Reference Section 2.4:**
> "The 'Archivist' must not naively link every concept that appears in the same note. This would create a 'fully-connected' and useless graph. It must use an 'LTP algorithm' to create weighted edges based on coincidence and salience."

**How the brain creates connections:**
- Neurons that "fire together, wire together"
- Connections form when two neurons are simultaneously active AND the activation crosses a salience threshold
- Weak connections naturally fade; strong, reinforced connections persist

**Relationship Engine Analog:**
```python
Strengthen_Edge(Entity_A, Entity_B):
  # Coincidence Detection
  IF entities_co_occur_in_context(A, B):
    # Salience Threshold
    IF context_salience > threshold:
      # Potentiation
      Edge(A, B).weight += 1
      Edge(A, B).confidence = calculate_confidence(context)
```

The engine doesn't need a predefined list of "allowed" relationships. It creates edges based on **co-occurrence + salience**, just like neurons.

### 2. Systems Consolidation (Hippocampal-Neocortical Dialogue)

**Brain Reference Section 2.1:**
> "During 'offline' periods, particularly sleep, the hippocampus 'replays' the neural firing patterns of the recent memory. This replay is coordinated with corresponding replay events in the neocortex... This repeated, coordinated 'dialogue' acts as a 'teacher.'"

**How the brain builds connections:**
- Initial encoding creates episodic traces in the hippocampus (fast, event-driven)
- Later, during sleep, these traces are "replayed"
- This replay strengthens connections in the neocortex (slow, offline)
- The result: permanent semantic connections in the cortical graph

**Relationship Engine Analog:**
- **Archivist** = Hippocampus (fast encoding, creates entity nodes from events)
- **Relationship Engine** = Hippocampal-Neocortical Dialogue (offline replay, creates edges by analyzing entities)
- The engine "replays" entities and finds patterns across them, building the permanent semantic graph

### 3. Offline Processing (NREM Sleep)

**Brain Reference Section 2.5:**
> "Phase 1 (NREM-analog): Consolidate_and_Prune(): 'Replay' all new episodic nodes from the 'daily log'... running the Strengthen_Edge (LTP) function to build and reinforce their connections in the permanent 'Semantic Graph'."

**How the brain maintains the graph:**
- Consolidation happens during sleep, not during waking experience
- New connections are formed
- Weak, unused connections are pruned ("synaptic homeostasis")
- The graph is optimized for efficiency and relevance

**Relationship Engine Analog:**
- Runs asynchronously, during "idle time" (like sleep)
- Creates new edges (consolidation)
- Weakens/removes edges that haven't been reinforced (pruning)
- Maintains graph health through a "use-it-or-lose-it" mechanism

## How It Works

### Operating Modes

The Relationship Engine supports three distinct modes of operation:

#### 1. Incremental Mode (Real-Time Consolidation)
- **Trigger**: Runs after each event is processed by the Archivist
- **Scope**: Analyzes only the newly created entities and their potential connections to existing entities
- **Purpose**: Creates immediate, local connections (e.g., entities mentioned in the same event)
- **Analogy**: Early-stage memory consolidation (first few hours after encoding)

#### 2. Nightly Mode (Deep Consolidation)
- **Trigger**: Runs on a schedule during user idle time (e.g., 3 AM daily)
- **Scope**: Full graph scan, analyzes all entities
- **Purpose**: Finds distant, cross-event connections that weren't obvious locally
- **Analogy**: NREM sleep consolidation (the "hippocampal replay" phase)

#### 3. On-Demand Mode (Manual Analysis)
- **Trigger**: User explicitly requests "re-analyze my graph"
- **Scope**: Configurable (full graph or specific subgraph)
- **Purpose**: Allows manual refinement, testing new strategies, or fixing gaps
- **Analogy**: Deliberate recall and reflection

### Detection Strategies

The engine uses multiple complementary strategies to find relationships, each optimized for different types of connections:

#### Strategy 1: Semantic Co-Occurrence (LLM-Based)
**What it does:**
- Uses an LLM to analyze the text context where entities appear
- Asks: "Given this text, what meaningful relationships exist between these entities?"
- NOT prescriptive (doesn't limit to predefined types)
- Generates relationship_type, confidence, and description from the semantic content

**When it's used:**
- Entities that appear in the same chunk of text
- Entities from the same source event

**Example:**
- Text: "I was Executive Director at Youth Empowerment Through Arts and Humanities"
- Entities detected: ["Executive Director at..." (role), "Youth Empowerment..." (organization)]
- Engine asks LLM: "How do these relate?"
- LLM response: `{from: role, to: org, type: "role_at", confidence: 0.95, description: "Leadership position"}`

#### Strategy 2: Pattern-Based Inference
**What it does:**
- Uses regex and structural analysis to infer obvious connections
- No LLM needed (fast, cheap, deterministic)

**Examples:**
- Entity title matches pattern `"{Title} at {Organization}"` → automatically creates edge from role → organization
- Entity type "skill" + appears in same event as entity type "person" → creates "manages" edge
- Temporal co-occurrence (two entities created within same hour) → potential connection

#### Strategy 3: Embedding Similarity
**What it does:**
- Compares entity embeddings to find semantically similar or related concepts
- Useful for finding distant connections that weren't explicitly mentioned together

**When it's used:**
- Nightly Mode (expensive, so run during idle time)
- Finding abstract relationships

**Example:**
- Entity A: "AI safety research" (concept, 2023)
- Entity B: "Anthropic alignment work" (project, 2025)
- High embedding similarity → creates "relates_to" edge with moderate confidence

#### Strategy 4: Temporal Analysis
**What it does:**
- Analyzes entities with temporal metadata (start_date, end_date)
- Finds overlapping time periods, sequences, causality

**Example:**
- Role A: "CTO at Willow" (2024-01 to present)
- Project B: "EdTech platform rebuild" (2024-06 to 2024-12)
- Temporal overlap → infers "led" or "contributed_to" relationship

#### Strategy 5: Graph Topology
**What it does:**
- Analyzes the structure of the existing graph
- Finds missing transitive connections

**Example:**
- Person A → worked_at → Organization B
- Organization B → part_of → Parent Company C
- Missing edge: Person A → affiliated_with → Parent Company C
- Engine creates the inferred connection

### Edge Weighting & Reinforcement

The Relationship Engine implements the brain's Hebbian "fire together, wire together" principle:

**Initial Creation:**
- When a connection is first detected, it's created with a base weight (e.g., `weight = 1.0`)
- Confidence and importance scores are set based on the detection strategy

**Reinforcement (Potentiation):**
- If the same connection is detected again in a different context, the edge weight increases
- Example: Person → Organization edge found in Event A (weight = 1.0), then reinforced in Event B (weight = 2.0)
- This is the LTP analog: repeated co-activation strengthens the synapse

**Decay (Pruning):**
- During Nightly Mode, all edge weights are globally scaled down (e.g., `weight *= 0.99`)
- Edges that haven't been reinforced gradually weaken
- Edges below a minimum threshold are deleted
- This is the NREM pruning analog: "use it or lose it" synaptic homeostasis

## What Problems This Solves

### 1. Missing Obvious Connections
**Problem**: Role entity "Executive Director at Org X" and organization entity "Org X" exist in the graph but aren't connected.

**Solution**: The Relationship Engine's pattern-based strategy automatically parses the role title, extracts "Org X", and creates the edge.

### 2. Cross-Event Relationships
**Problem**: A skill is mentioned in one event, a project in another event six months later. The Archivist, processing events independently, never connects them.

**Solution**: Nightly Mode scans the entire graph, finds the skill and project, and uses semantic analysis to infer a "used_in" or "required_for" relationship.

### 3. Prescriptive Relationship Types
**Problem**: The old relationship mapper only created edges for predefined types like "worked_at" or "founded". Novel relationships (e.g., "inspired_by", "contradicts") were impossible.

**Solution**: The LLM-based strategy generates relationship types from the semantic content. If the LLM determines two entities have a "mentored_by" relationship, it creates that type, even if it's never been seen before.

### 4. Graph Bloat (Too Many Weak Connections)
**Problem**: Creating edges for every co-occurrence creates a dense, useless graph where everything connects to everything.

**Solution**:
- Salience threshold prevents low-confidence connections from being created
- Decay/pruning removes weak connections that aren't reinforced over time
- The graph stays sparse and meaningful

### 5. Static, Never-Improving Graph
**Problem**: Once edges are created, they never change. The graph doesn't learn or adapt.

**Solution**:
- Edge weights dynamically increase with reinforcement
- Edges are pruned if they become irrelevant
- On-demand mode allows testing new strategies and re-analyzing the graph
- The graph is a living, learning structure

## Output: What the Engine Creates

For each relationship discovered, the engine creates or updates an edge in the database with:

```javascript
{
  id: UUID,
  from_id: UUID,                    // Source entity
  to_id: UUID,                      // Target entity
  kind: string,                     // "worked_at", "role_at", "relates_to", etc.
  confidence: float,                // 0.0 to 1.0 (how certain is this connection?)
  importance: float,                // 0.0 to 1.0 (how significant is this?)
  description: string,              // Rich context (e.g., "CTO", "2 years")
  start_date: date | null,          // When did this relationship begin?
  end_date: date | null,            // When did it end? (null = ongoing)
  weight: float,                    // Synaptic strength (for retrieval ranking)
  metadata: {
    source_strategy: string,        // Which strategy found this?
    reinforcement_count: int,       // How many times has this been reinforced?
    last_reinforced_at: timestamp,  // When was this last strengthened?
    detected_in_events: [UUIDs]     // Which events contributed to this edge?
  },
  created_at: timestamp,
  updated_at: timestamp
}
```

## Why This Matters

The Relationship Engine transforms the UMG from a **collection of facts** into a **semantic knowledge graph**.

Without it:
- You have entities (people, projects, skills, organizations)
- But they exist in isolation
- Queries like "Show me everything related to Project X" are impossible
- The graph can't answer "how" or "why" questions

With it:
- Entities are woven into a web of meaning
- The graph captures not just "what exists" but "how things relate"
- Retrieval becomes powerful: spreading activation can traverse the graph to find related concepts
- The Mentor can reason about your work, goals, and decisions by following the edges

**The edges ARE the intelligence.** They're what make the graph "universal" and "semantic". They're what enable the system to think, not just remember.

This is exactly how your brain works: neurons (entities) are meaningless without synapses (edges). The Relationship Engine is the system that builds and maintains those synapses.
