# UMG 30-Day Implementation Roadmap

This roadmap outlines a phased approach to building the Unified Memory Graph system, prioritizing rapid feedback loops and immediate value delivery.

---

## Week 1: Foundation & Quick Capture
**Goal**: Get your first data flowing into the system.

### Tasks

**Day 1-2: Database & API Foundation**
- ✅ Deploy schema in Supabase (all 7 tables)
- ✅ Set up Row Level Security policies
- ✅ Build basic API endpoint (`/api/events`) for writing events
- ✅ Configure Google OAuth authentication

**Day 3-4: Quick Capture Interface**
- Build global hotkey text capture app (Tauri desktop)
  - Configurable hotkey (e.g., Cmd+Shift+Space)
  - Minimal UI: text input → submit → fade away
  - Writes to `raw_events` with source='quick_capture', status='pending_processing'
- Or: Add quick capture to web app as interim solution

**Day 5-7: Archivist v1 (Basic Processing)**
- Set up Python AI Core project structure (FastAPI)
- Implement basic Archivist agent:
  - Polls `raw_events` for status='pending_processing'
  - Simple entity extraction (people, projects mentioned)
  - Basic chunking (split on paragraphs, ~500 tokens each)
  - Generate embeddings via OpenAI API
  - Write to `entity`, `chunk`, `embedding` tables
  - Update `raw_events` status to 'processed'

### Success Metric
✅ You can capture thoughts via hotkey (or web form) and see them:
- Saved in `raw_events` table
- Processed into `entity` and `chunk` tables
- Searchable via basic SQL queries

### What You'll Learn
- Is the capture friction actually zero?
- What entity types are most common in your data?
- Are the chunks the right size for semantic search?

---

## Weeks 2-3: Voice Capture & Daily Digest
**Goal**: Complete the capture-to-coaching loop.

### Week 2: Voice Debrief App

**Day 8-10: Voice Recording & Transcription**
- Build voice debrief interface (web or mobile)
  - "Start Morning Debrief" / "Start Evening Debrief" buttons
  - Record audio via browser/device mic
  - Transcribe via Whisper API or Deepgram
  - Write to `raw_events` with source='voice_debrief', status='pending_processing'

**Day 11-14: Enhanced Archivist Processing**
- Improve entity recognition:
  - Add NER (Named Entity Recognition) for people, companies
  - Implement hub-and-spoke model for features/projects
  - Create edges between entities ('belongs_to', 'mentions', 'modifies')
- Add signal scoring:
  - Calculate importance based on type and user actions
  - Set recency to 1.0 for new entities
  - Initialize novelty based on connection count

### Week 3: Mentor Agent & Daily Digest

**Day 15-17: Mentor v1 Agent**
- Implement Mentor agent in Python AI Core:
  - Query entities from last 24 hours (high recency)
  - Vector search for 3 most relevant historical entries
  - Use LLM to generate insights based on:
    - Recent activity vs stated goals
    - Connections to past patterns
    - Forward-looking questions

**Day 18-21: Daily Digest Generation**
- Build 3-card digest structure:
  - **Delta Watch**: Compare goals (type='goal' entities) with actual work
  - **Connection**: Find semantic similarities between recent and historical
  - **Prompt**: Generate forward-looking reflection question
- Write insights to `insight` table with:
  - Appropriate title prefix ("Delta Watch:", "Connection:", "Prompt:")
  - Full body text from LLM
  - drivers JSONB with entity_ids and edge_ids used
  - status='open'
- Schedule digest generation for 7 AM daily (cron job or Supabase function)

**Day 22: Digest UI in Web App**
- Render 3 insight cards on dashboard
- Add Accept/Dismiss buttons
- Wire up buttons to update insight.status
- Implement feedback loop:
  - Acknowledged → raise importance of driver entities
  - Dismissed → lower importance of driver entities

### Success Metric
✅ Every morning at 7 AM you see personalized insights based on yesterday's work:
- Delta Watch notices if you drifted from stated goals
- Connection surfaces relevant context from your history
- Prompt challenges you with a forward-looking question
- Your feedback (Accept/Dismiss) trains the system

### What You'll Learn
- Are the insights actually valuable, or just noise?
- Which insight type (Delta/Connection/Prompt) is most helpful?
- Is 7 AM the right time, or should it be configurable?

---

## Week 4: Review & Refine
**Goal**: Measure value and close feedback loop.

### Day 23-25: Data Review & Analysis

**Review 30 Days of Captured Data**
- How many events captured? (Target: 50-100 for meaningful patterns)
- What entity types emerged? (Projects, people, features, decisions?)
- Which entities have highest importance scores? (Align with your actual priorities?)

**Analyze Insight Effectiveness**
- How many insights generated? (Target: ~21 daily digests = 63 cards)
- Acknowledge rate: What % were valuable?
- Dismiss rate: What % were noise?
- Pattern analysis: Which driver combinations yielded good insights?

**User Behavior Patterns**
- Capture frequency: Are you using hotkey/voice regularly?
- Triage behavior: What % of webhook events did you mark important?
- Engagement: Are you reading the daily digest every day?

### Day 26-28: Tune the System

**Based on Review, Adjust:**

Signal Scoring:
- Recency decay rate (too fast? too slow?)
- Importance thresholds for different entity types
- Novelty calculation (over/under-valuing new entities?)

Entity Creation Rules:
- Are passing mentions being elevated to entities too aggressively?
- Should hub-and-spoke kick in sooner/later?
- Which entity types should auto-create vs. require multiple mentions?

Insight Generation:
- Adjust Delta Watch sensitivity (catching real drift vs false positives?)
- Tune Connection relevance threshold (too obscure? too obvious?)
- Refine Prompt generation (too vague? too specific?)

### Day 29-30: Implement Full Feedback System

**Close the Loop**
- Implement insight table fully:
  - Store all drivers (entity_ids, edge_ids) with each insight
  - Track which combinations yield acknowledged insights
  - Weight future insights toward successful patterns
- Add importance score updates:
  - Acknowledged insight → +0.1 importance for all driver entities
  - Dismissed insight → -0.05 importance for all driver entities
- Build basic analytics dashboard:
  - Entity count by type
  - Insight acknowledge/dismiss rates over time
  - Top 10 entities by importance

### Success Metric
✅ You can answer: **"Did the Mentor's nudges lead to better decisions?"**

Not "Is the tech perfect?" but "Did this change behavior?"

Examples of success:
- You caught yourself drifting from a goal before wasting a week
- You applied a lesson from 6 months ago to a current problem
- You asked yourself a hard question you'd been avoiding

### What You'll Learn
- Is this system worth continuing to build?
- What's the highest-leverage next feature?
- Should you focus on more capture tools, better processing, or richer insights?

---

## Post-30-Day: Future Enhancements

Based on your findings, prioritize next:

### More Capture Tools (if capture is working well)
- Mobile app for voice capture on-the-go
- Webhook integrations (GitHub, Granola, Slack)
- Triage UI for automatic entries

### Better Processing (if insights are shallow)
- More sophisticated entity extraction
- Better edge detection (contradictions, blocks, informs)
- Improved chunking strategies

### Richer Insights (if daily digest is valuable)
- Conversational Mentor (chat interface)
- Memory graph visualization
- "Briefing mode" for meetings (synthesize all related context)

### Scale & Polish (if you're using it daily)
- Multi-device sync
- Offline capture
- Performance optimization
- Better UI/UX

---

## Key Success Factors

### 1. Ship Fast, Learn Faster
Don't wait for perfection. Week 1 goal is just to get data flowing. You'll learn more from using a basic system than planning a perfect one.

### 2. Focus on the Feedback Loop
The system's value compounds when your actions train it. Prioritize the acknowledge/dismiss mechanism over fancier features.

### 3. Measure Behavior Change, Not Tech Metrics
Success is "I caught goal drift early" not "98% entity extraction accuracy."

### 4. One Source of Truth
Everything flows through `raw_events`. If something breaks, you can always reprocess. This gives you freedom to experiment with processing logic.

### 5. Start with Morning Debrief
Voice capture is powerful because it's conversational. You'll naturally reflect on yesterday and plan today, giving the system rich intentional data.

---

## Critical Questions to Answer

By Day 30, you should be able to answer:

1. **Capture**: Is the friction actually zero? Am I capturing daily?
2. **Processing**: Are entities meaningful? Are edges useful?
3. **Insights**: Did any Mentor nudge change my behavior?
4. **Value**: Is this worth continuing, or pivot to different approach?

If the answer to #3 is "Yes, at least once" — you've validated the core hypothesis. Keep building.

If the answer is "No, never" — dig into why:
- Not enough data yet? (Capture working?)
- Bad insights? (Processing working?)
- Right insights, ignored? (Trust/engagement issue?)

---

*This roadmap assumes ~2-3 hours per day of focused development. Adjust timeline based on your capacity and priorities.*
