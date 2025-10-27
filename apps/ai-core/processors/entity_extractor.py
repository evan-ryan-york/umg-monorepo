from typing import List, Dict
from config import settings
import json
import logging

logger = logging.getLogger(__name__)


class EntityExtractor:
    def __init__(self):
        # Will be initialized with Anthropic client when available
        self.client = None
        try:
            from anthropic import Anthropic

            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        except Exception as e:
            logger.warning(f"Anthropic client not available: {e}")

    def extract_entities(
        self, text: str, use_llm: bool = True
    ) -> List[Dict]:
        """Main extraction method - uses LLM for extraction"""
        if use_llm and self.client:
            return self.extract_with_llm(text)
        else:
            # Fallback: return empty list if no LLM available
            return []

    def extract_with_llm(self, text: str) -> List[Dict]:
        """Use Claude for advanced extraction"""
        if not self.client:
            return []

        prompt = f"""Extract all salient entities from this text. Extract EVERY organization, role, skill, milestone, and location mentioned.

ENTITY TYPES:
- person: People (e.g., "Ryan York")
- organization: Companies, schools, nonprofits (e.g., "Willow Education", "RePublic Schools")
- role: Job titles with organization (e.g., "CTO at Willow Education", "Principal at Nashville Academy")
- skill: Technical abilities (e.g., "JavaScript", "React", "Product Design")
- milestone: Major achievements (e.g., "Won Sally Ride award", "Secured $3M funding")
- project: Initiatives (e.g., "Computer science curriculum")
- product: Things built (e.g., "AI college advisory", "Learning platform")
- location: Places (e.g., "San Antonio, TX", "Nashville, TN")
- core_identity: Values and mission (e.g., "Equity", "Innovation")
- goal: Objectives (e.g., "Scale to 10,000 students")
- decision: Important choices made
- event: Significant happenings
- concept: Ideas or frameworks
- task: Action items
- source: Books, articles, research

CRITICAL RULES FOR RESUME TEXT:
1. Extract EVERY organization mentioned
2. Extract EVERY role (format: "Title at Organization")
3. Extract EVERY technical skill listed
4. Extract major achievements as milestones
5. Extract all locations where work happened
6. DO NOT create "reflection" entities for resume text

For biographical text:
- Extract all stated values and mission
- Extract goals and decisions

Text:
{text}

Return ONLY valid JSON (no markdown):
{{
  "entities": [
    {{"title": "Entity name", "type": "organization|role|skill|...", "summary": "Brief description", "confidence": 0.95, "is_primary_subject": false}}
  ]
}}

RESUME EXAMPLE:
Input: "Willow Education - Remote, Jan 2024-Current. CTO. Skills: JavaScript, React, SQL."

Output:
{{
  "entities": [
    {{"title": "Willow Education", "type": "organization", "summary": "Education technology company", "confidence": 0.95, "is_primary_subject": false}},
    {{"title": "Chief Technology Officer at Willow Education", "type": "role", "summary": "CTO role from Jan 2024 to present", "confidence": 0.95, "is_primary_subject": false}},
    {{"title": "JavaScript", "type": "skill", "summary": "Programming language", "confidence": 0.95, "is_primary_subject": false}},
    {{"title": "React", "type": "skill", "summary": "JavaScript framework", "confidence": 0.95, "is_primary_subject": false}},
    {{"title": "SQL", "type": "skill", "summary": "Database query language", "confidence": 0.95, "is_primary_subject": false}}
  ]
}}
"""

        try:
            logger.info(f"🔍 [DEBUG] Sending extraction request to Claude (text length: {len(text)} chars, prompt length: {len(prompt)} chars)")

            response = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,  # Increased from 2048 to handle larger responses
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response from Claude
            content = response.content[0].text.strip()
            logger.info(f"🔍 [DEBUG] Claude response length: {len(content)} chars")
            logger.info(f"🔍 [DEBUG] Claude response preview: {content[:500]}...")

            # Remove markdown code blocks if present
            if content.startswith("```"):
                # Extract JSON from markdown code block
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            result = json.loads(content)
            entities = result.get("entities", [])

            logger.info(f"✅ [DEBUG] Successfully extracted {len(entities)} entities from Claude response")

            for entity in entities:
                entity["source"] = "llm"

            return entities
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Raw content that failed to parse: {content[:1000]}")
            return []
        except Exception as e:
            logger.error(f"Error extracting entities with LLM: {e}", exc_info=True)
            return []

    def _map_spacy_type(self, spacy_label: str) -> str:
        """Map spaCy entity types to our schema"""
        mapping = {
            "PERSON": "person",
            "ORG": "company",
            "PRODUCT": "feature",
            "EVENT": "meeting_note",
        }
        return mapping.get(spacy_label, "reference_document")
