from services.database import DatabaseService
from processors.signal_scorer import SignalScorer
from typing import List, Dict, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class FeedbackProcessor:
    """
    Processes user feedback (Acknowledge/Dismiss) and adjusts
    the knowledge graph accordingly.

    Acknowledge: Boosts importance scores, refreshes recency
    Dismiss: Lowers importance scores, records pattern to avoid
    """

    def __init__(self):
        self.db = DatabaseService()
        self.signal_scorer = SignalScorer()

    def process_acknowledge(self, insight_id: str) -> Dict:
        """
        User acknowledged an insight as valuable

        Actions:
        1. Boost importance scores for driver entities
        2. Refresh recency scores
        3. Update insight status

        Args:
            insight_id: UUID of the insight

        Returns:
            Dict with status, action, entities_updated, signal_changes
        """
        try:
            # Get insight and its drivers
            insight = self.db.get_insight_by_id(insight_id)

            if not insight:
                logger.error(f"Insight not found: {insight_id}")
                return {
                    'status': 'error',
                    'message': 'Insight not found'
                }

            driver_entity_ids = insight.get('drivers', {}).get('entity_ids', [])

            logger.info(f"Processing acknowledge for insight {insight_id} with {len(driver_entity_ids)} drivers")

            # Boost signals for each driver entity
            entities_updated = []
            for entity_id in driver_entity_ids:
                # Try to resolve entity_id if it's a title instead of UUID
                resolved_id = self._resolve_entity_id(entity_id)
                if not resolved_id:
                    logger.warning(f"Could not resolve entity: {entity_id}")
                    continue

                updated = self._adjust_entity_signals(
                    resolved_id,
                    importance_delta=0.1,
                    recency_boost=True
                )
                if updated.get('error'):
                    logger.warning(f"Failed to update entity {resolved_id}: {updated.get('error')}")
                else:
                    entities_updated.append(updated)

            # Update insight status
            self.db.update_insight_status(insight_id, 'acknowledged')

            logger.info(f"Acknowledged: Boosted {len(entities_updated)} entity signals")

            return {
                'status': 'success',
                'action': 'acknowledge',
                'entities_updated': len(entities_updated),
                'signal_changes': entities_updated
            }

        except Exception as e:
            logger.error(f"Error processing acknowledge: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }

    def process_dismiss(self, insight_id: str) -> Dict:
        """
        User dismissed an insight as not valuable

        Actions:
        1. Lower importance scores for driver entities
        2. Record pattern to avoid in future
        3. Update insight status

        Args:
            insight_id: UUID of the insight

        Returns:
            Dict with status, action, entities_updated, pattern_recorded
        """
        try:
            # Get insight and its drivers
            insight = self.db.get_insight_by_id(insight_id)

            if not insight:
                logger.error(f"Insight not found: {insight_id}")
                return {
                    'status': 'error',
                    'message': 'Insight not found'
                }

            driver_entity_ids = insight.get('drivers', {}).get('entity_ids', [])

            logger.info(f"Processing dismiss for insight {insight_id} with {len(driver_entity_ids)} drivers")

            # Lower signals for each driver entity
            entities_updated = []
            for entity_id in driver_entity_ids:
                # Try to resolve entity_id if it's a title instead of UUID
                resolved_id = self._resolve_entity_id(entity_id)
                if not resolved_id:
                    logger.warning(f"Could not resolve entity: {entity_id}")
                    continue

                updated = self._adjust_entity_signals(
                    resolved_id,
                    importance_delta=-0.1,
                    recency_boost=False
                )
                if updated.get('error'):
                    logger.warning(f"Failed to update entity {resolved_id}: {updated.get('error')}")
                else:
                    entities_updated.append(updated)

            # Record dismissed pattern
            pattern = self._extract_pattern(insight)
            self.db.record_dismissed_pattern(pattern)

            # Update insight status
            self.db.update_insight_status(insight_id, 'dismissed')

            logger.info(f"Dismissed: Lowered {len(entities_updated)} entity signals, recorded pattern")

            return {
                'status': 'success',
                'action': 'dismiss',
                'entities_updated': len(entities_updated),
                'pattern_recorded': pattern,
                'signal_changes': entities_updated
            }

        except Exception as e:
            logger.error(f"Error processing dismiss: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }

    def _resolve_entity_id(self, entity_id: str) -> Optional[str]:
        """
        Resolve entity_id - if it's a UUID, return as-is.
        If it's a title, look up the actual UUID.

        This handles the issue where Claude returns entity titles
        instead of UUIDs in driver_entity_ids.
        """
        # Check if it looks like a UUID (contains hyphens and hex chars)
        if '-' in entity_id and len(entity_id) >= 32:
            return entity_id

        # Otherwise, try to look up by title
        try:
            entity = self.db.get_entity_by_title(entity_id)
            if entity:
                return entity['id']
        except Exception as e:
            logger.warning(f"Error looking up entity by title '{entity_id}': {e}")

        return None

    def _adjust_entity_signals(
        self,
        entity_id: str,
        importance_delta: float,
        recency_boost: bool
    ) -> Dict:
        """
        Adjust signal scores for an entity

        Args:
            entity_id: UUID of entity
            importance_delta: Amount to change importance (+0.1 or -0.1)
            recency_boost: Whether to refresh recency to 1.0

        Returns:
            Dict with entity_id, importance changes, recency_boosted
        """
        try:
            signal = self.db.get_signal_by_entity_id(entity_id)

            if not signal:
                logger.warning(f"No signal found for entity {entity_id}")
                return {'entity_id': entity_id, 'error': 'no_signal'}

            # Calculate new importance (clamped to [0.0, 1.0])
            old_importance = signal.get('importance', 0.5)
            new_importance = max(0.0, min(1.0, old_importance + importance_delta))

            updates = {'importance': new_importance}

            # Boost recency if acknowledged
            if recency_boost:
                entity = self.db.get_entity_by_id(entity_id)
                if entity:
                    # Refresh recency to 1.0 (as if just created)
                    new_recency = self.signal_scorer.calculate_recency(
                        entity['created_at'],
                        datetime.now().isoformat()
                    )
                    updates['recency'] = new_recency
                    updates['last_surfaced_at'] = datetime.now().isoformat()

            # Apply updates
            self.db.update_signal(entity_id, updates)

            logger.info(f"Updated entity {entity_id}: importance {old_importance:.2f} -> {new_importance:.2f}")

            return {
                'entity_id': entity_id,
                'importance': {'old': old_importance, 'new': new_importance},
                'recency_boosted': recency_boost
            }

        except Exception as e:
            logger.error(f"Error adjusting signals for entity {entity_id}: {e}", exc_info=True)
            return {'entity_id': entity_id, 'error': str(e)}

    def _extract_pattern(self, insight: Dict) -> Dict:
        """
        Extract dismissal pattern from insight

        Builds a pattern signature that includes:
        - Insight type (Delta Watch, Connection, Prompt)
        - Driver entity types
        - Title keywords

        This allows the Mentor to avoid generating similar insights.
        """
        # Get entity types of drivers
        driver_ids = insight.get('drivers', {}).get('entity_ids', [])
        driver_types = []

        for entity_id in driver_ids:
            # Resolve entity ID if needed
            resolved_id = self._resolve_entity_id(entity_id)
            if not resolved_id:
                continue

            entity = self.db.get_entity_by_id(resolved_id)
            if entity:
                driver_types.append(entity.get('type', 'unknown'))

        # Extract insight type from title
        title = insight.get('title', '')
        insight_type = 'Unknown'
        if 'Delta Watch' in title:
            insight_type = 'Delta Watch'
        elif 'Connection' in title:
            insight_type = 'Connection'
        elif 'Prompt' in title:
            insight_type = 'Prompt'

        # Build pattern signature
        pattern_signature = {
            'insight_type': insight_type,
            'driver_types': list(set(driver_types)),
            'title_keywords': self._extract_keywords(title),
            'body_keywords': self._extract_keywords(insight.get('body', '')),
            'dismissed_at': datetime.now().isoformat()
        }

        return {
            'insight_type': insight_type,
            'driver_entity_types': driver_types,
            'pattern_signature': pattern_signature
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract key terms from text

        Simple keyword extraction - removes stop words and short words.
        """
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'is', 'was', 'are', 'were', 'been', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
            'when', 'where', 'why', 'how', 'your', 'their', 'our'
        }

        # Clean and split text
        words = text.lower().replace(':', ' ').replace(',', ' ').replace('.', ' ').split()

        # Filter out stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 3]

        # Return top 5 keywords
        return keywords[:5]


# Singleton instance
feedback_processor = FeedbackProcessor()
