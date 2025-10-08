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

        prompt = f"""Extract all entities from this text. For each entity, identify:
- The entity name/title
- The type (person, company, project, feature, task, decision, reflection)
- A brief summary (1 sentence)
- Whether it's the primary subject (is_primary_subject: true/false)

IMPORTANT RULES:
1. DO NOT extract pronouns (I, me, my, you, we, etc.) as entities
2. Only extract actual names, titles, and concrete things
3. If someone says "My name is X", extract "X" as the primary subject (is_primary_subject: true)
4. If someone says "I am starting Company Y", extract "Company Y" but NOT "I"

Text: {text}

Return ONLY a valid JSON object (no markdown, no explanation) in this exact format:
{{
  "entities": [
    {{"title": "...", "type": "...", "summary": "...", "confidence": 0.95, "is_primary_subject": false}}
  ]
}}
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response from Claude
            content = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if content.startswith("```"):
                # Extract JSON from markdown code block
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace("```json", "").replace("```", "").strip()

            result = json.loads(content)
            entities = result.get("entities", [])

            for entity in entities:
                entity["source"] = "llm"

            return entities
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
