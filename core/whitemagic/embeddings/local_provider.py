import logging
"""
Local Embeddings Provider - No API Calls Required!

Uses sentence-transformers for local semantic embeddings.
Updated Ganapati Day: Now fully implemented!
"""
from typing import List, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class LocalEmbeddingProvider:
    """
    Local embedding generation using sentence-transformers.
    
    Benefits:
    - No API calls = no cost
    - Works offline
    - Fast for small batches
    - Privacy (data never leaves machine)
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._available = self._check_available()
    
    def _check_available(self) -> bool:
        """Check if sentence-transformers is available"""
        try:
            from sentence_transformers import SentenceTransformer
            return True
        except ImportError:
            return False
    
    def _load_model(self):
        """Lazy load the model"""
        if self._model is None and self._available:
            from sentence_transformers import SentenceTransformer
            logger.info(f"🧠 Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("✅ Model loaded!")
        return self._model
    
    @property
    def is_available(self) -> bool:
        """Check if local embeddings are available"""
        return self._available
    
    def embed(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text"""
        if not self._available:
            return None
        
        model = self._load_model()
        if model is None:
            return None
        
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> Optional[List[List[float]]]:
        """Generate embeddings for multiple texts"""
        if not self._available:
            return None
        
        model = self._load_model()
        if model is None:
            return None
        
        embeddings = model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
        return embeddings.tolist()
    
    def similarity(self, text1: str, text2: str) -> Optional[float]:
        """Compute cosine similarity between two texts"""
        if not self._available:
            return None
        
        embeddings = self.embed_batch([text1, text2])
        if embeddings is None:
            return None
        
        vec1 = np.array(embeddings[0])
        vec2 = np.array(embeddings[1])
        
        # Cosine similarity
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot / (norm1 * norm2))
    
    def find_similar(self, query: str, candidates: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """Find most similar texts to query"""
        if not self._available or not candidates:
            return []
        
        # Embed query and all candidates
        all_texts = [query] + candidates
        embeddings = self.embed_batch(all_texts)
        
        if embeddings is None:
            return []
        
        query_vec = np.array(embeddings[0])
        candidate_vecs = np.array(embeddings[1:])
        
        # Compute similarities
        similarities = []
        for i, vec in enumerate(candidate_vecs):
            dot = np.dot(query_vec, vec)
            norm1 = np.linalg.norm(query_vec)
            norm2 = np.linalg.norm(vec)
            sim = dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
            similarities.append((i, float(sim)))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k results
        results = []
        for idx, sim in similarities[:top_k]:
            results.append({
                "text": candidates[idx],
                "index": idx,
                "similarity": sim
            })
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model"""
        info = {
            "model_name": self.model_name,
            "available": self._available,
            "loaded": self._model is not None
        }
        
        if self._model is not None:
            info["embedding_dimension"] = self._model.get_sentence_embedding_dimension()
        
        return info


# Convenience functions
_default_provider: Optional[LocalEmbeddingProvider] = None


def get_provider() -> LocalEmbeddingProvider:
    """Get or create default provider"""
    global _default_provider
    if _default_provider is None:
        _default_provider = LocalEmbeddingProvider()
    return _default_provider


def embed(text: str) -> Optional[List[float]]:
    """Quick embedding of single text"""
    return get_provider().embed(text)


def similarity(text1: str, text2: str) -> Optional[float]:
    """Quick similarity between two texts"""
    return get_provider().similarity(text1, text2)


def find_similar(query: str, candidates: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
    """Quick semantic search"""
    return get_provider().find_similar(query, candidates, top_k)


__all__ = [
    "LocalEmbeddingProvider",
    "get_provider",
    "embed",
    "similarity", 
    "find_similar"
]

# Backward compatibility alias
LocalEmbeddings = LocalEmbeddingProvider
