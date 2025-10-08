from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class EntityResolver:
    """Resolves references in text (pronouns, contextual references) to existing entity IDs"""

    def __init__(self):
        # First-person pronouns that refer to the user
        self.first_person_pronouns = [
            'i', 'me', 'my', 'mine', 'myself',
            "i'm", "i've", "i'll", "i'd"
        ]

    def resolve_pronouns(
        self,
        text: str,
        user_entity_id: Optional[str]
    ) -> Dict[str, str]:
        """
        Map first-person pronouns to user entity ID

        Args:
            text: The text to analyze
            user_entity_id: The entity ID of the current user/author

        Returns:
            Dictionary mapping pronouns to entity IDs
            Example: {"i": "uuid-123", "me": "uuid-123", "my": "uuid-123"}
        """
        logger.info(f"\n🔍 [DEBUG] resolve_pronouns() called")
        logger.info(f"🔍 [DEBUG] user_entity_id: {user_entity_id}")
        logger.info(f"🔍 [DEBUG] text preview: {text[:100]}...")

        resolutions = {}

        if not user_entity_id:
            logger.warning("⚠️  [DEBUG] No user_entity_id provided, skipping pronoun resolution")
            return resolutions

        text_lower = text.lower()

        # Check if any first-person pronouns appear in text
        for pronoun in self.first_person_pronouns:
            # Use word boundary checking to avoid partial matches
            # e.g., don't match "i" in "India"
            if f' {pronoun} ' in f' {text_lower} ' or text_lower.startswith(f'{pronoun} '):
                resolutions[pronoun] = user_entity_id
                logger.info(f"✅ [DEBUG] Resolved '{pronoun}' to user entity {user_entity_id[:8]}...")

        if resolutions:
            logger.info(f"✅ [DEBUG] Resolved {len(resolutions)} pronoun references: {list(resolutions.keys())}")
        else:
            logger.warning(f"⚠️  [DEBUG] No pronouns found in text")

        return resolutions

    def resolve_references(
        self,
        text: str,
        user_entity_id: Optional[str],
        existing_entities: List[Dict] = []
    ) -> Dict[str, str]:
        """
        Main resolution method - combines all resolution strategies

        Args:
            text: The text to analyze
            user_entity_id: The entity ID of the current user
            existing_entities: List of existing entities from knowledge graph

        Returns:
            Dictionary mapping references to entity IDs
        """
        # For Phase 1, only pronoun resolution
        # Future phases will add contextual and LLM-based resolution
        return self.resolve_pronouns(text, user_entity_id)
