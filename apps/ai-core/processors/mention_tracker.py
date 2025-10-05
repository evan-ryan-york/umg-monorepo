from typing import Dict, Optional, List
from datetime import datetime


class MentionTracker:
    """Tracks entity mentions across events to determine promotion to full entity"""

    def __init__(self):
        # In production, this would be database-backed
        # For now, maintain in-memory cache
        self.mention_cache: Dict[str, Dict] = {}

    def record_mention(
        self,
        entity_text: str,
        entity_type: str,
        event_id: str,
        is_primary_subject: bool = False,
    ) -> Dict:
        """Record a mention of an entity"""
        normalized_key = self._normalize_entity_name(entity_text)

        if normalized_key not in self.mention_cache:
            self.mention_cache[normalized_key] = {
                "text": entity_text,
                "type": entity_type,
                "mention_count": 0,
                "events": [],
                "first_seen": datetime.now(),
                "last_seen": datetime.now(),
                "is_promoted": False,
            }

        mention = self.mention_cache[normalized_key]
        mention["mention_count"] += 1
        mention["last_seen"] = datetime.now()

        if event_id not in mention["events"]:
            mention["events"].append(event_id)

        return mention

    def should_promote(
        self, entity_text: str, is_primary_subject: bool = False
    ) -> bool:
        """Determine if entity should be promoted to full entity node"""
        # Rule 1: Immediate promotion if entity is primary subject
        if is_primary_subject:
            return True

        normalized_key = self._normalize_entity_name(entity_text)

        if normalized_key not in self.mention_cache:
            return False

        mention = self.mention_cache[normalized_key]

        # Rule 2: Promote after 2-3 mentions across different events
        if mention["mention_count"] >= 2 and len(mention["events"]) >= 2:
            return True

        # Rule 3: Don't promote if already promoted
        if mention["is_promoted"]:
            return False

        return False

    def mark_promoted(self, entity_text: str, entity_id: str):
        """Mark entity as promoted to avoid duplicate creation"""
        normalized_key = self._normalize_entity_name(entity_text)

        if normalized_key in self.mention_cache:
            self.mention_cache[normalized_key]["is_promoted"] = True
            self.mention_cache[normalized_key]["entity_id"] = entity_id

    def get_existing_entity_id(self, entity_text: str) -> Optional[str]:
        """Get entity ID if already promoted"""
        normalized_key = self._normalize_entity_name(entity_text)
        mention = self.mention_cache.get(normalized_key)

        if mention and mention.get("is_promoted"):
            return mention.get("entity_id")

        return None

    def _normalize_entity_name(self, name: str) -> str:
        """Normalize entity name for comparison"""
        return name.lower().strip().replace("  ", " ")
