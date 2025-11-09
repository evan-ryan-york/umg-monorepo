from anthropic import Anthropic
from datetime import datetime, timedelta
from services.database import DatabaseService
from config import settings
from models.chat import ChatMessage, ChatResponse
from prompts.prompt_manager import prompt_manager
from typing import List, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)


class Mentor:
    """
    The Mentor agent generates insights from the knowledge graph
    by analyzing patterns, connections, and user priorities.

    It produces 3 daily insight cards:
    - Delta Watch: Goal alignment check
    - Connection: Historical context
    - Prompt: Forward-looking question
    """

    def __init__(self, db: DatabaseService = None):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-5"
        self.db = db or DatabaseService()

    def generate_daily_digest(self) -> dict:
        """
        Generate 3 insight cards for daily digest

        Returns:
            {
                'delta_watch': insight_dict or None,
                'connection': insight_dict or None,
                'prompt': insight_dict or None,
                'insights_created': int
            }
        """
        logger.info("Generating daily digest...")

        try:
            # Gather context from knowledge graph
            context = self._gather_context()

            # Generate each card type
            delta_watch = self._generate_delta_watch(context)
            connection = self._generate_connection(context)
            prompt = self._generate_prompt(context)

            insights_created = sum(
                1 for insight in [delta_watch, connection, prompt] if insight is not None
            )

            logger.info(f"Daily digest generated: {insights_created} insights created")

            return {
                "delta_watch": delta_watch,
                "connection": connection,
                "prompt": prompt,
                "insights_created": insights_created,
            }

        except Exception as e:
            logger.error(f"Error generating daily digest: {e}", exc_info=True)
            raise

    def chat(
        self,
        message: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        user_entity_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Conversational chat with Mentor.

        Provides context-aware responses using the knowledge graph.
        Saves both user message and assistant response to raw_events for Archivist processing.

        Args:
            message: User's message
            conversation_history: Previous messages in conversation
            user_entity_id: UUID of user's entity

        Returns:
            ChatResponse with assistant reply and event IDs
        """
        logger.info(f"Processing chat message: {message[:50]}...")

        try:
            conversation_history = conversation_history or []

            # Step 1: Gather relevant context from knowledge graph
            context = self._gather_chat_context(message)

            # Step 2: Build conversational prompt
            prompt = self._build_chat_prompt(
                message,
                conversation_history,
                context
            )

            # Step 3: Call Claude
            response = self._call_claude(prompt, "chat")

            # Step 4: Extract entity mentions from user message
            entities_mentioned = self._extract_entity_mentions(message, context)

            # Step 5: Save user message to raw_events
            user_event_id = self.db.create_raw_event({
                "payload": {
                    "type": "text",
                    "content": message,
                    "metadata": {
                        "source_type": "mentor_chat",
                        "role": "user"
                    },
                    "user_id": "default_user",
                    "user_entity_id": user_entity_id
                },
                "source": "mentor_chat",
                "status": "pending_processing"
            })

            # Step 6: Save assistant response to raw_events
            assistant_event_id = self.db.create_raw_event({
                "payload": {
                    "type": "text",
                    "content": response,
                    "metadata": {
                        "source_type": "mentor_chat",
                        "role": "assistant",
                        "user_message_event_id": user_event_id
                    },
                    "user_id": "default_user",
                    "user_entity_id": user_entity_id
                },
                "source": "mentor_chat",
                "status": "pending_processing"
            })

            logger.info(f"Chat response generated. Events: {user_event_id}, {assistant_event_id}")

            return ChatResponse(
                response=response,
                user_event_id=user_event_id,
                assistant_event_id=assistant_event_id,
                entities_mentioned=entities_mentioned,
                context_used={
                    "core_identity_count": len(context.get("core_identity", [])),
                    "high_priority_count": len(context.get("high_priority", [])),
                    "active_work_count": len(context.get("active_work", [])),
                    "relevant_entities_count": len(context.get("relevant_entities", [])),
                    "relationships_count": len(context.get("relationships", []))
                }
            )

        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            raise

    def _gather_chat_context(self, message: str, is_first_message: bool = False) -> dict:
        """
        Gather relevant context for chat based on message content

        Strategy:
        - First message: Load core identity + highest importance + recent work
        - Subsequent messages: Extract entities mentioned + expand via relationships

        Args:
            message: User's message
            is_first_message: Whether this is the first message in conversation

        Returns:
            Context dict with core_identity, high_priority, active_work, relevant_entities, relationships
        """

        # Always get user's core identity (goals, values, mission)
        core_identity = self.db.get_entities_by_type("core_identity")

        # Get current active work (high recency)
        active_work = self.db.get_entities_by_signal_threshold(recency_min=0.8, limit=10)

        # Get highest importance entities (what matters most)
        high_priority = self.db.get_entities_by_importance(min_importance=0.7, limit=10)

        # Extract entities mentioned in message
        relevant_entities = []
        relationships = []

        # Extract keywords and search for matching entities
        entity_keywords = self._extract_keywords_from_message(message)
        logger.info(f"Extracted keywords from message: {entity_keywords}")

        for keyword in entity_keywords:
            matches = self.db.search_entities_by_title(keyword, limit=3)

            for entity in matches:
                # Add the matched entity
                relevant_entities.append(entity)

                # Expand: get all entities connected via edges
                related = self.db.get_entity_relationships(entity.id, limit=5)

                # Add outgoing relationships (this entity -> other entities)
                for rel in related.outgoing:
                    relationships.append({
                        "from": entity,
                        "to": rel.entity,
                        "edge": rel.edge
                    })
                    # Add connected entity to context
                    relevant_entities.append(rel.entity)

                # Add incoming relationships (other entities -> this entity)
                for rel in related.incoming:
                    relationships.append({
                        "from": rel.entity,
                        "to": entity,
                        "edge": rel.edge
                    })
                    # Add connected entity to context
                    relevant_entities.append(rel.entity)

        # Remove duplicates
        seen_ids = set()
        unique_relevant = []
        for entity in relevant_entities:
            if entity.id not in seen_ids:
                seen_ids.add(entity.id)
                unique_relevant.append(entity)

        logger.info(
            f"Context gathered: {len(core_identity)} core identity, "
            f"{len(active_work)} active work, {len(high_priority)} high priority, "
            f"{len(unique_relevant)} relevant entities, {len(relationships)} relationships"
        )

        return {
            "core_identity": core_identity,
            "active_work": active_work,
            "high_priority": high_priority,
            "relevant_entities": unique_relevant[:15],  # Top 15 most relevant
            "relationships": relationships[:10]  # Top 10 relationships
        }

    def _build_chat_prompt(
        self,
        message: str,
        conversation_history: List[ChatMessage],
        context: dict
    ) -> str:
        """Build context-aware chat prompt using PromptManager"""
        return prompt_manager.build_mentor_chat_prompt(
            message=message,
            conversation_history=conversation_history,
            context=context
        )

    def _extract_keywords_from_message(self, message: str) -> List[str]:
        """Extract potential entity keywords from message"""

        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                      'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                      'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                      'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
                      'these', 'those', 'i', 'you', 'we', 'they', 'my', 'your', 'our'}

        # Simple word extraction
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|\b[a-z]+\b', message)

        # Filter and clean
        keywords = []
        for word in words:
            clean_word = word.lower().strip()
            if clean_word not in stop_words and len(clean_word) > 2:
                keywords.append(clean_word)

        return keywords

    def _extract_entity_mentions(self, message: str, context: dict) -> List[str]:
        """Extract entity titles mentioned in message"""

        mentioned = []

        # Check against relevant entities
        for entity in context.get("relevant_entities", []):
            title = entity.title.lower()
            if title in message.lower():
                mentioned.append(entity.title)

        # Check against active work
        for entity in context.get("active_work", []):
            title = entity.title.lower()
            if title in message.lower():
                if entity.title not in mentioned:
                    mentioned.append(entity.title)

        return mentioned

    def _gather_context(self) -> dict:
        """Gather relevant context from knowledge graph"""

        logger.info("Gathering context from knowledge graph...")

        # Get user's core identity (values, goals, mission)
        core_identity = self.db.get_entities_by_type("core_identity")

        # Get recent activity (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_entities = self.db.get_entities_created_since(yesterday)

        # Get high-importance entities
        high_priority = self.db.get_entities_by_signal_threshold(
            importance_min=0.7, limit=20
        )

        # Get recent high-recency entities (active work)
        recent_work = self.db.get_entities_by_signal_threshold(recency_min=0.8, limit=20)

        # Get dismissed patterns (to avoid)
        dismissed = self.db.get_dismissed_patterns(days_back=30)

        context = {
            "core_identity": core_identity,
            "recent_entities": recent_entities,
            "high_priority": high_priority,
            "recent_work": recent_work,
            "dismissed_patterns": dismissed,
        }

        logger.info(
            f"Context gathered: {len(core_identity)} core identity, "
            f"{len(recent_entities)} recent entities, "
            f"{len(high_priority)} high priority, "
            f"{len(recent_work)} recent work, "
            f"{len(dismissed)} dismissed patterns"
        )

        return context

    def _generate_delta_watch(self, context: dict) -> dict:
        """Generate Delta Watch insight (goal alignment check)"""

        logger.info("Generating Delta Watch insight...")

        try:
            # Extract stated goals from core identity
            goals = [
                e
                for e in context["core_identity"]
                if "goal" in e.metadata.get("tags", [])
            ]

            # Get what user actually worked on
            actual_work = context["recent_work"]

            # If no goals or no work, return None
            if not goals and not actual_work:
                logger.info("No goals or recent work - skipping Delta Watch")
                return None

            # Build prompt for Claude
            prompt = self._build_delta_watch_prompt(
                goals, actual_work, context["dismissed_patterns"]
            )

            # Call Claude
            response = self._call_claude(prompt, "delta_watch")

            # Parse and store insight
            insight_data = json.loads(response)

            insight_id = self.db.create_insight(
                {
                    "title": f"Delta Watch: {insight_data['title']}",
                    "body": insight_data["body"],
                    "drivers": {
                        "entity_ids": insight_data.get("driver_entity_ids", []),
                        "edge_ids": [],
                    },
                    "status": "open",
                }
            )

            logger.info(f"Delta Watch insight created: {insight_id}")

            return {"id": insight_id, **insight_data}

        except Exception as e:
            logger.error(f"Error generating Delta Watch: {e}", exc_info=True)
            # Return fallback insight
            return self._create_fallback_insight("delta_watch")

    def _generate_connection(self, context: dict) -> dict:
        """Generate Connection insight (historical patterns)"""

        logger.info("Generating Connection insight...")

        try:
            # Get recent work and search for similar past work
            recent = context["recent_entities"][:5]  # Last 5 entities

            if not recent:
                logger.info("No recent entities - skipping Connection")
                return None

            # For each recent entity, find semantically similar historical entities
            historical_connections = []
            for entity in recent:
                similar = self.db.get_similar_entities(
                    entity_id=entity.id, limit=3, exclude_recent_days=30  # Historical only
                )
                if similar:
                    historical_connections.append(
                        {"current": entity, "historical": similar}
                    )

            if not historical_connections:
                logger.info("No historical connections found - skipping Connection")
                return None

            # Build prompt
            prompt = self._build_connection_prompt(
                historical_connections, context["dismissed_patterns"]
            )

            # Call Claude
            response = self._call_claude(prompt, "connection")

            # Parse and store
            insight_data = json.loads(response)

            insight_id = self.db.create_insight(
                {
                    "title": f"Connection: {insight_data['title']}",
                    "body": insight_data["body"],
                    "drivers": {
                        "entity_ids": insight_data.get("driver_entity_ids", []),
                        "edge_ids": insight_data.get("driver_edge_ids", []),
                    },
                    "status": "open",
                }
            )

            logger.info(f"Connection insight created: {insight_id}")

            return {"id": insight_id, **insight_data}

        except Exception as e:
            logger.error(f"Error generating Connection: {e}", exc_info=True)
            return self._create_fallback_insight("connection")

    def _generate_prompt(self, context: dict) -> dict:
        """Generate Prompt insight (forward-looking question)"""

        logger.info("Generating Prompt insight...")

        try:
            # Use recent work to generate a challenging question
            recent_work = context["recent_work"]
            goals = [
                e
                for e in context["core_identity"]
                if "goal" in e.metadata.get("tags", [])
            ]

            if not recent_work and not goals:
                logger.info("No recent work or goals - skipping Prompt")
                return None

            # Build prompt
            prompt = self._build_prompt_card_prompt(
                recent_work, goals, context["dismissed_patterns"]
            )

            # Call Claude
            response = self._call_claude(prompt, "prompt")

            # Parse and store
            insight_data = json.loads(response)

            insight_id = self.db.create_insight(
                {
                    "title": f"Prompt: {insight_data['title']}",
                    "body": insight_data["body"],
                    "drivers": {
                        "entity_ids": insight_data.get("driver_entity_ids", []),
                        "edge_ids": [],
                    },
                    "status": "open",
                }
            )

            logger.info(f"Prompt insight created: {insight_id}")

            return {"id": insight_id, **insight_data}

        except Exception as e:
            logger.error(f"Error generating Prompt: {e}", exc_info=True)
            return self._create_fallback_insight("prompt")

    def _call_claude(self, prompt: str, insight_type: str) -> str:
        """Make API call to Claude"""

        try:
            logger.info(f"Calling Claude for {insight_type}...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.7,  # Higher for creative insights
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text.strip()

            # Strip markdown if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            logger.info(f"Claude response received for {insight_type}")

            return content

        except Exception as e:
            logger.error(f"Error calling Claude for {insight_type}: {e}")
            raise

    def _create_fallback_insight(self, insight_type: str) -> dict:
        """Create fallback insight when Claude fails"""

        fallback_data = {
            "delta_watch": {
                "title": "Daily Check-In",
                "body": "How does today's work align with your stated goals?",
                "driver_entity_ids": [],
            },
            "connection": {
                "title": "Past Learning",
                "body": "What past experiences might inform today's challenges?",
                "driver_entity_ids": [],
            },
            "prompt": {
                "title": "Key Question",
                "body": "What's the most important question you should ask today?",
                "driver_entity_ids": [],
            },
        }

        data = fallback_data.get(insight_type, {})

        try:
            insight_id = self.db.create_insight(
                {
                    "title": f"{insight_type.replace('_', ' ').title()}: {data['title']}",
                    "body": data["body"],
                    "drivers": {"entity_ids": [], "edge_ids": []},
                    "status": "open",
                }
            )

            return {"id": insight_id, **data}
        except Exception as e:
            logger.error(f"Error creating fallback insight: {e}")
            return None

    def _build_delta_watch_prompt(
        self, goals, actual_work, dismissed_patterns
    ) -> str:
        """Build prompt for Delta Watch card"""

        # Build entity lists with IDs explicitly mapped
        goal_list = []
        goal_id_map = {}
        for g in goals:
            entity_id = g.id
            goal_list.append(f"- [{entity_id}] {g.title}: {g.summary or 'No summary'}")
            goal_id_map[g.title] = entity_id

        work_list = []
        work_id_map = {}
        for w in actual_work:
            entity_id = w.id
            work_list.append(f"- [{entity_id}] {w.title} ({w.type}): {w.summary or 'No summary'}")
            work_id_map[w.title] = entity_id

        # Build dismissed pattern context
        dismissed_context = ""
        delta_dismissed = [
            p for p in dismissed_patterns if p["insight_type"] == "Delta Watch"
        ]
        if delta_dismissed:
            dismissed_context = "\n\nIMPORTANT: The user previously dismissed these Delta Watch patterns - avoid similar insights:\n"
            for p in delta_dismissed[:3]:
                sig = p.get("pattern_signature", {})
                dismissed_context += f"- Pattern: {sig}\n"

        prompt = f"""You are analyzing a user's stated goals versus their actual work to detect potential misalignment.

User's Stated Goals (from core identity):
{chr(10).join(goal_list) if goal_list else "- No explicit goals stated"}

Actual Work (last 24 hours):
{chr(10).join(work_list) if work_list else "- No recent activity"}
{dismissed_context}

Task: Generate a "Delta Watch" insight that either:
1. Celebrates alignment (goals and work match)
2. Highlights drift (working on things not in goals - ask if pivot or distraction)
3. Suggests missing focus (goals stated but no work toward them)

Guidelines:
- Be specific and actionable
- Reference actual entity names from the data
- Don't moralize - be curious and supportive
- Keep it under 3 sentences
- If alignment is good, celebrate it briefly

Return ONLY a JSON object (no markdown, no code blocks):
{{
    "title": "Brief headline (5-8 words)",
    "body": "2-3 sentence insight with specific examples",
    "driver_entity_ids": ["uuid-from-brackets-above", "another-uuid"],
    "alignment_score": 0.85
}}

IMPORTANT:
- Use the actual UUIDs from the brackets [uuid] in the lists above
- driver_entity_ids must contain the UUIDs of the entities you reference
- Return ONLY the JSON object, nothing else."""

        return prompt

    def _build_connection_prompt(self, connections, dismissed_patterns) -> str:
        """Build prompt for Connection card"""

        connection_list = []
        for conn in connections[:3]:  # Max 3 connections
            current = conn["current"]
            historical = conn["historical"][0]  # Best match
            created_date = str(historical.created_at)[:10] if historical.created_at else ""

            current_id = current.id
            historical_id = historical.id

            connection_list.append(
                f"Current: [{current_id}] {current.title} ({current.type})\n"
                f"  → Historical: [{historical_id}] {historical.title} from {created_date}"
            )

        dismissed_context = ""
        conn_dismissed = [
            p for p in dismissed_patterns if p["insight_type"] == "Connection"
        ]
        if conn_dismissed:
            dismissed_context = "\n\nIMPORTANT: User dismissed these Connection patterns - avoid:\n"
            for p in conn_dismissed[:3]:
                sig = p.get("pattern_signature", {})
                dismissed_context += f"- Pattern: {sig}\n"

        prompt = f"""You are finding valuable connections between current work and historical context.

Potential Connections:
{chr(10).join(connection_list)}
{dismissed_context}

Task: Create a "Connection" insight that shows how historical work informs current challenges.

Guidelines:
- Focus on actionable insights from the past
- Be specific about what was learned and how it applies
- Keep it under 3 sentences
- Make the connection clear and valuable

Return ONLY a JSON object (no markdown, no code blocks):
{{
    "title": "Brief headline (5-8 words)",
    "body": "2-3 sentence insight connecting past to present",
    "driver_entity_ids": ["current-uuid-from-brackets", "historical-uuid-from-brackets"],
    "driver_edge_ids": [],
    "relevance_score": 0.75
}}

IMPORTANT:
- Use the actual UUIDs from the brackets [uuid] in the connections above
- driver_entity_ids should include both current and historical entity UUIDs
- Return ONLY the JSON object, nothing else."""

        return prompt

    def _build_prompt_card_prompt(
        self, recent_work, goals, dismissed_patterns
    ) -> str:
        """Build prompt for Prompt card"""

        work_summary = []
        for w in recent_work[:5]:
            entity_id = w.id
            work_summary.append(f"- [{entity_id}] {w.title}: {w.summary or 'No summary'}")

        goal_summary = []
        for g in goals:
            entity_id = g.id
            goal_summary.append(f"- [{entity_id}] {g.title}")

        dismissed_context = ""
        prompt_dismissed = [
            p for p in dismissed_patterns if p["insight_type"] == "Prompt"
        ]
        if prompt_dismissed:
            dismissed_context = "\n\nIMPORTANT: User dismissed these Prompt types - avoid:\n"
            for p in prompt_dismissed[:3]:
                sig = p.get("pattern_signature", {})
                dismissed_context += f"- Pattern: {sig}\n"

        prompt = f"""You are a thought partner helping the user think critically about their work.

Recent Work:
{chr(10).join(work_summary)}

Goals:
{chr(10).join(goal_summary) if goal_summary else "- No explicit goals"}
{dismissed_context}

Task: Generate a challenging, forward-looking question that:
1. Pushes the user to think deeper about their current work
2. Challenges assumptions or exposes blindspots
3. Connects to their larger goals and values
4. Is specific and actionable

Guidelines:
- Ask ONE powerful question
- Make it open-ended (not yes/no)
- Ground it in their actual work
- Be challenging but supportive

Return ONLY a JSON object (no markdown, no code blocks):
{{
    "title": "The Question (as headline)",
    "body": "1-2 sentence setup explaining why this question matters now",
    "driver_entity_ids": ["uuid-from-brackets-above", "another-uuid"]
}}

IMPORTANT:
- Use the actual UUIDs from the brackets [uuid] in the lists above
- driver_entity_ids should include the UUIDs of work/goals you reference
- Return ONLY the JSON object, nothing else."""

        return prompt


# Singleton instance
mentor = Mentor()
