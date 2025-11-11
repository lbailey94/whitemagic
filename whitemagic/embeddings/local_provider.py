"""
Local embeddings provider (stub).

TODO: Implement when sentence-transformers dependency conflicts are resolved.
"""

from typing import List
from .base import EmbeddingProvider


class LocalEmbeddings(EmbeddingProvider):
    """
    Local embeddings provider using sentence-transformers.
    
    NOTE: Currently not implemented due to transformers dependency conflicts.
    Will be added once dependencies are resolved.
    """
    
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        """
        Initialize local embeddings provider.
        
        Args:
            model: SentenceTransformer model name
            
        Raises:
            NotImplementedError: Always, until dependencies are resolved
        """
        raise NotImplementedError(
            "Local embeddings not yet implemented. "
            "Use 'openai' provider or help resolve sentence-transformers dependency conflicts."
        )
    
    async def embed(self, text: str) -> List[float]:
        """Not implemented."""
        raise NotImplementedError("Local embeddings not available")
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Not implemented."""
        raise NotImplementedError("Local embeddings not available")
    
    @property
    def dimensions(self) -> int:
        """Not implemented."""
        return 384  # Standard for MiniLM
    
    @property
    def model_name(self) -> str:
        """Not implemented."""
        return "all-MiniLM-L6-v2"
