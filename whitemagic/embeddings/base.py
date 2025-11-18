"""
Base embedding provider interface.

Defines the abstract interface that all embedding providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If text is empty or invalid
            RuntimeError: If embedding generation fails
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors, one per input text

        Raises:
            ValueError: If texts list is empty or contains invalid entries
            RuntimeError: If batch embedding generation fails
        """
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """
        Number of dimensions in the embedding vector.

        Returns:
            Integer dimension count (e.g., 1536 for OpenAI, 384 for MiniLM)
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Identifier for the embedding model.

        Returns:
            String model identifier (e.g., "text-embedding-3-small")
        """
        pass

    @property
    def provider_name(self) -> str:
        """
        Name of the embedding provider.

        Returns:
            String provider name (e.g., "openai", "local")
        """
        return self.__class__.__name__.lower().replace("embeddings", "")

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get provider metadata for logging and tracking.

        Returns:
            Dictionary with provider information
        """
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "dimensions": self.dimensions,
        }
