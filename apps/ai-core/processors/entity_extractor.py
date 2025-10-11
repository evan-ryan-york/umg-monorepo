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

        prompt = f"""Extract all meaningful entities from this text. An "entity" is any person, project, company, goal, value, decision, task, or concept worth remembering.

ENTITY TYPES:
1. **person** - People mentioned by name (e.g., "Sarah", "Ryan York")
2. **company** - Organizations (e.g., "WaterOS", "Willow Education")
3. **project** - Projects or initiatives (e.g., "Ghana water pilot", "Feed feature redesign")
4. **feature** - Product features (e.g., "Parent notification system")
5. **task** - Action items (e.g., "Update documentation", "Call Sarah")
6. **decision** - Important decisions made (e.g., "Chose to expose company failure")
7. **reflection** - Personal reflections or lessons (e.g., "Failure is misallocation of energy")
8. **core_identity** - Goals, values, mission statements, defining principles (e.g., "Impact rooted in Equity", "Build WaterOS to escape velocity")
9. **meeting_note** - Meeting summaries or discussion records
10. **reference_document** - External docs, articles, research

EXTRACTION STRATEGY:

**For biographical/philosophical text** (like "about me" statements):
- Extract the person entity
- Extract 3-5 CORE VALUES as separate core_identity entities (not every value mentioned, focus on the fundamental ones)
- Extract 1-3 PRIMARY GOALS as separate core_identity entities (not sub-goals or means to an end)
- Extract the ONE overarching mission/purpose as a core_identity entity (if clearly stated)
- Extract any pivotal decisions as decision entities
- Extract any defining projects/companies
- AVOID redundancy: if two concepts overlap significantly, choose the more fundamental one

**For conversational text** (like "I met with Sarah about Feed"):
- Extract people mentioned
- Extract projects/features discussed
- Extract any tasks or decisions made
- Extract any reflections or lessons learned

**For work logs** (like "Built the login flow today"):
- Extract the feature/task
- Extract any decisions or technical learnings
- Extract related projects

IMPORTANT RULES:
1. DO NOT extract pronouns (I, me, my, you, we) as entities
2. DO extract what the pronouns REFER TO (e.g., "my mission to solve water crisis" → extract "Solve water crisis" as core_identity)
3. Extract 3-5 core values maximum - focus on the MOST FUNDAMENTAL ones
4. Extract 1-3 primary goals maximum - avoid sub-goals that are means to an end
5. Prefer consolidation over granularity - if two goals/values overlap, pick ONE
6. Mark is_primary_subject: true for the main focus (e.g., if "My name is X", then X is primary)
7. Quality over quantity - better to have 6 highly relevant entities than 15 redundant ones

Text:
{text}

Return ONLY a valid JSON object (no markdown, no explanation) in this exact format:
{{
  "entities": [
    {{"title": "Brief entity name", "type": "core_identity|person|company|...", "summary": "1-2 sentence description", "confidence": 0.95, "is_primary_subject": false}}
  ]
}}

EXAMPLE INPUT:
"My name is Jane. My mission is to build sustainable housing to solve homelessness. I value equity, innovation, and sustainability. I want to launch GreenHomes, grow it to 1000 homes, and eventually fund other housing projects. Success means creating a self-sustaining system."

EXAMPLE OUTPUT (showing consolidation):
{{
  "entities": [
    {{"title": "Jane", "type": "person", "summary": "The user describing their mission and work.", "confidence": 1.0, "is_primary_subject": true}},
    {{"title": "Build sustainable housing to solve homelessness", "type": "core_identity", "summary": "Primary mission combining sustainable housing with addressing homelessness.", "confidence": 0.95, "is_primary_subject": false}},
    {{"title": "Equity and Innovation", "type": "core_identity", "summary": "Core values focused on fairness and creating new solutions.", "confidence": 0.9, "is_primary_subject": false}},
    {{"title": "GreenHomes", "type": "company", "summary": "Primary project/company focused on sustainable housing.", "confidence": 0.95, "is_primary_subject": false}},
    {{"title": "Create self-sustaining system of impact", "type": "core_identity", "summary": "Success definition focused on building systems that generate ongoing impact beyond initial projects.", "confidence": 0.9, "is_primary_subject": false}}
  ]
}}

Note: "grow to 1000 homes" was NOT extracted (it's a sub-goal/metric, not the primary goal). "sustainability" was merged with equity/innovation (overlapping values). Result: 5 entities instead of 10+.
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
