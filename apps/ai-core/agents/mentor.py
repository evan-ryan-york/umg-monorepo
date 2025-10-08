from anthropic import Anthropic
from datetime import datetime, timedelta
from services.database import DatabaseService
from config import settings
import logging
import json

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
                if "goal" in e.get("metadata", {}).get("tags", [])
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
                    entity_id=entity["id"], limit=3, exclude_recent_days=30  # Historical only
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
                if "goal" in e.get("metadata", {}).get("tags", [])
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

        goal_list = [f"- {g['title']}: {g.get('summary', 'No summary')}" for g in goals]
        work_list = [
            f"- {w['title']} ({w['type']}): {w.get('summary', 'No summary')}"
            for w in actual_work
        ]

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
    "driver_entity_ids": ["uuid1", "uuid2"],
    "alignment_score": 0.85
}}

IMPORTANT: Return ONLY the JSON object, nothing else."""

        return prompt

    def _build_connection_prompt(self, connections, dismissed_patterns) -> str:
        """Build prompt for Connection card"""

        connection_list = []
        for conn in connections[:3]:  # Max 3 connections
            current = conn["current"]
            historical = conn["historical"][0]  # Best match
            created_date = historical.get("created_at", "")[:10]
            connection_list.append(
                f"Current: {current['title']} ({current['type']})\n"
                f"  → Historical: {historical['title']} from {created_date}"
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
    "driver_entity_ids": ["current_uuid", "historical_uuid"],
    "driver_edge_ids": [],
    "relevance_score": 0.75
}}

IMPORTANT: Return ONLY the JSON object, nothing else."""

        return prompt

    def _build_prompt_card_prompt(
        self, recent_work, goals, dismissed_patterns
    ) -> str:
        """Build prompt for Prompt card"""

        work_summary = [
            f"- {w['title']}: {w.get('summary', 'No summary')}" for w in recent_work[:5]
        ]
        goal_summary = [f"- {g['title']}" for g in goals]

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
    "driver_entity_ids": ["uuid1", "uuid2"]
}}

IMPORTANT: Return ONLY the JSON object, nothing else."""

        return prompt


# Singleton instance
mentor = Mentor()
