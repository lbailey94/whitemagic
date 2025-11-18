"""
OpenAI embeddings provider.

Uses OpenAI's text embedding models for cloud-based embedding generation.
"""

from typing import List

from openai import AsyncOpenAI, OpenAIError

from .base import EmbeddingProvider


class OpenAIEmbeddings(EmbeddingProvider):
    """OpenAI embeddings provider using text-embedding models."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """
        Initialize OpenAI embeddings provider.

        Args:
            api_key: OpenAI API key
            model: Model name (default: text-embedding-3-small)
            dimensions: Output dimensions (default: 1536)
            max_retries: Maximum retry attempts (default: 3)
            timeout: Request timeout in seconds (default: 30)
        """
        self.client = AsyncOpenAI(api_key=api_key, max_retries=max_retries, timeout=timeout)
        self.model = model
        self._dimensions = dimensions

    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If text is empty
            RuntimeError: If API request fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model,
                dimensions=self._dimensions if self.model == "text-embedding-3-small" else None,
            )
            return response.data[0].embedding
        except OpenAIError as e:
            raise RuntimeError(f"OpenAI embedding failed: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error during embedding: {str(e)}") from e

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If texts list is empty or contains invalid entries
            RuntimeError: If API request fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        # Filter out empty strings
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("All texts are empty")

        if len(valid_texts) != len(texts):
            raise ValueError(f"Texts contain {len(texts) - len(valid_texts)} empty entries")

        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model,
                dimensions=self._dimensions if self.model == "text-embedding-3-small" else None,
            )
            return [item.embedding for item in response.data]
        except OpenAIError as e:
            raise RuntimeError(f"OpenAI batch embedding failed: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error during batch embedding: {str(e)}") from e

    @property
    def dimensions(self) -> int:
        """Number of dimensions in embedding vectors."""
        return self._dimensions

    @property
    def model_name(self) -> str:
        """Model identifier."""
        return self.model

    async def close(self) -> None:
        """Close the OpenAI client connection."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
