from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)


class SignalScorer:
    """Calculates importance, recency, and novelty scores for entities"""

    def __init__(self, recency_half_life_days: int = 30):
        """Initialize signal scorer

        Args:
            recency_half_life_days: Number of days for recency to decay to 0.5
        """
        self.recency_half_life_days = recency_half_life_days

    def calculate_importance(self, entity_type: str, metadata: dict = None) -> float:
        """Calculate importance score based on entity type and metadata

        Args:
            entity_type: The type of entity (e.g., 'project', 'task', 'person')
            metadata: Optional metadata dict that may contain user_importance

        Returns:
            Float between 0.0 and 1.0 representing importance

        Importance Map:
        - core_identity: 1.0 (always reference)
        - project: 0.85 (high priority)
        - feature: 0.8
        - decision: 0.75
        - person: 0.7
        - reflection: 0.65
        - task: 0.6
        - meeting_note: 0.5
        - reference_document: 0.4
        """
        if metadata is None:
            metadata = {}

        # Base importance by entity type
        importance_map = {
            'core_identity': 1.0,
            'project': 0.85,
            'feature': 0.8,
            'decision': 0.75,
            'person': 0.7,
            'reflection': 0.65,
            'task': 0.6,
            'meeting_note': 0.5,
            'company': 0.5,
            'reference_document': 0.4,
        }

        base_score = importance_map.get(entity_type, 0.5)

        # Adjust based on user-provided importance in metadata
        user_importance = metadata.get('user_importance')

        if user_importance == 'high':
            base_score = min(1.0, base_score + 0.2)
            logger.debug(f"Boosted importance for user_importance=high: {base_score}")
        elif user_importance == 'low':
            base_score = max(0.1, base_score - 0.2)
            logger.debug(f"Reduced importance for user_importance=low: {base_score}")

        # Ensure score is within bounds
        return max(0.0, min(1.0, base_score))

    def calculate_recency(self, created_at: datetime, updated_at: datetime = None) -> float:
        """Calculate recency score with exponential decay

        Args:
            created_at: When the entity was created
            updated_at: When the entity was last updated (optional)

        Returns:
            Float between 0.0 and 1.0 representing recency

        Formula: recency = e^(-decay_rate * age_days)
        where decay_rate = ln(2) / half_life_days

        Examples with 30-day half-life:
        - 0 days old: 1.0
        - 30 days old: 0.5
        - 60 days old: 0.25
        - 90 days old: 0.125
        """
        # Use the most recent timestamp
        if updated_at is not None:
            reference_time = max(created_at, updated_at)
        else:
            reference_time = created_at

        # Calculate age in days
        now = datetime.now()
        if reference_time.tzinfo is not None:
            # Make now timezone-aware to match
            from datetime import timezone
            now = datetime.now(timezone.utc)

        age = now - reference_time
        age_days = age.total_seconds() / 86400  # Convert to days

        # Exponential decay formula
        decay_rate = math.log(2) / self.recency_half_life_days
        recency = math.exp(-decay_rate * age_days)

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, recency))

    def calculate_novelty(self, edge_count: int, entity_age_days: int) -> float:
        """Calculate novelty based on connections and age

        Args:
            edge_count: Number of edges connected to this entity
            entity_age_days: Age of entity in days

        Returns:
            Float between 0.0 and 1.0 representing novelty

        Logic:
        - New entities with few connections are novel (high score)
        - Well-connected, old entities are not novel (low score)

        Formula:
        - connection_score = 1.0 / (1.0 + edge_count * 0.1)
        - age_score = 1.0 / (1.0 + entity_age_days * 0.05)
        - novelty = (connection_score + age_score) / 2.0

        Examples:
        - New entity (0 days, 0 edges): 1.0
        - Young entity (10 days, 5 edges): ~0.57
        - Old entity (100 days, 20 edges): ~0.22
        """
        # Connection score: decreases as edge count increases
        connection_score = 1.0 / (1.0 + edge_count * 0.1)

        # Age score: decreases as age increases
        age_score = 1.0 / (1.0 + entity_age_days * 0.05)

        # Average the two scores
        novelty = (connection_score + age_score) / 2.0

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, novelty))

    def calculate_all_signals(
        self,
        entity_type: str,
        created_at: datetime,
        updated_at: datetime = None,
        edge_count: int = 0,
        metadata: dict = None
    ) -> dict:
        """Calculate all three signal scores at once

        Args:
            entity_type: Type of entity
            created_at: Creation timestamp
            updated_at: Last update timestamp (optional)
            edge_count: Number of edges (default 0)
            metadata: Entity metadata (optional)

        Returns:
            Dictionary with importance, recency, and novelty scores
        """
        now = datetime.now()
        if created_at.tzinfo is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)

        age = now - created_at
        age_days = int(age.total_seconds() / 86400)

        return {
            'importance': self.calculate_importance(entity_type, metadata),
            'recency': self.calculate_recency(created_at, updated_at),
            'novelty': self.calculate_novelty(edge_count, age_days)
        }

    def calculate_composite_score(
        self,
        importance: float,
        recency: float,
        novelty: float,
        weights: dict = None
    ) -> float:
        """Calculate a weighted composite score from the three signals

        Args:
            importance: Importance score (0.0 to 1.0)
            recency: Recency score (0.0 to 1.0)
            novelty: Novelty score (0.0 to 1.0)
            weights: Optional dict with 'importance', 'recency', 'novelty' weights
                    Defaults to {'importance': 0.5, 'recency': 0.3, 'novelty': 0.2}

        Returns:
            Float between 0.0 and 1.0 representing composite relevance score
        """
        if weights is None:
            weights = {
                'importance': 0.5,
                'recency': 0.3,
                'novelty': 0.2
            }

        composite = (
            importance * weights.get('importance', 0.5) +
            recency * weights.get('recency', 0.3) +
            novelty * weights.get('novelty', 0.2)
        )

        return max(0.0, min(1.0, composite))
