"""
Local embeddings provider (stub).

TODO: Implement when sentence-transformers dependency conflicts are resolved.
"""

import asyncio
from typing import List
import logging
from .base import EmbeddingProvider

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)


class LocalEmbeddings(EmbeddingProvider):
    """
    Local embeddings provider using sentence-transformers.
    
    Provides privacy-first semantic search without external APIs.
    Models are downloaded and cached locally on first use.
    
    Recommended models:
    - all-MiniLM-L6-v2: Fast, 90MB, 384 dimensions (default)
    - all-mpnet-base-v2: Better quality, 420MB, 768 dimensions
    """
    
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        """
        Initialize local embeddings provider.
        
        Args:
            model: SentenceTransformer model name
            
        Raises:
            ImportError: If sentence-transformers not installed
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        logger.info(f"Loading local embedding model: {model}")
        self._model_name = model
        self._model = SentenceTransformer(model)
        self._dimensions = self._model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded: {model} ({self._dimensions} dimensions)")
    
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for single text.
        
        Runs in background thread to avoid blocking event loop during CPU-intensive encoding.
        """
        embedding = await asyncio.to_thread(
            self._model.encode, text, convert_to_numpy=True
        )
        return embedding.tolist()
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batched for efficiency).
        
        Runs in background thread to avoid blocking event loop during CPU-intensive encoding.
        """
        embeddings = await asyncio.to_thread(
            self._model.encode, 
            texts, 
            convert_to_numpy=True, 
            show_progress_bar=len(texts) > 10
        )
        return embeddings.tolist()
    
    @property
    def dimensions(self) -> int:
        """Embedding dimensions for this model."""
        return self._dimensions
    
    @property
    def model_name(self) -> str:
        """Name of the loaded model."""
        return self._model_name
