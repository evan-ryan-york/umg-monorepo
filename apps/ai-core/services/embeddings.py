from typing import List
from config import settings
import logging

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating vector embeddings - DISABLED (Anthropic doesn't provide embeddings)"""

    def __init__(self):
        self.client = None  # Embeddings disabled
        self.model = "none"
        self.dimensions = 1536
        logger.warning("Embeddings service disabled - Anthropic doesn't provide embeddings")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text - DISABLED

        Args:
            text: The text to embed

        Returns:
            Zero vector (embeddings disabled)
        """
        logger.debug("Embeddings disabled - returning zero vector")
        return [0.0] * self.dimensions

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts - DISABLED

        Args:
            texts: List of texts to embed

        Returns:
            List of zero vectors (embeddings disabled)
        """
        logger.debug(f"Embeddings disabled - returning {len(texts)} zero vectors")
        return [[0.0] * self.dimensions] * len(texts)

    def get_model_info(self) -> dict:
        """Get information about the embedding model being used

        Returns:
            Dictionary with model name and dimensions
        """
        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "provider": "Disabled (Anthropic doesn't provide embeddings)"
        }
