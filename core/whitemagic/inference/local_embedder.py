# ruff: noqa: BLE001
"""
Local Embedding Engine
======================
Provides high-performance local text embeddings using FastEmbed (OnnxRuntime).
No GPU required. Lightweight, fast, and private.

Usage:
    from whitemagic.inference.local_embedder import LocalEmbedder
    embedder = LocalEmbedder()
    vectors = embedder.embed(["hello world", "local ai is fast"])
"""

import logging
import time

import numpy as np

logger = logging.getLogger(__name__)


class LocalEmbedder:
    """
    Local embedding provider using FastEmbed (BGE-Small-EN-V1.5 or similar).
    Target throughput: >500 docs/sec on CPU.
    """

    def __init__(
        self, model_name: str = "BAAI/bge-small-en-v1.5", max_length: int = 512
    ):
        self.model_name = model_name
        self.max_length = max_length
        self._model = None
        self._available = False
        self._try_load()

    def _try_load(self):
        """Try to load FastEmbed model."""
        try:
            from fastembed import TextEmbedding

            logger.info("Loading local embedding model: %s", self.model_name)
            start = time.time()
            self._model = TextEmbedding(
                model_name=self.model_name, max_length=self.max_length
            )
            self._available = True
            elapsed = time.time() - start
            logger.info("Local embedding model loaded in %ss", elapsed)
        except ImportError:
            logger.warning(
                "fastembed not installed. Install with: pip install fastembed"
            )
            self._available = False
        except (ImportError, ModuleNotFoundError) as e:
            logger.error("Failed to load local embedding model: %s", e, exc_info=True)
            self._available = False

    @property
    def is_available(self) -> bool:
        """
        Check whether the available condition holds.

        Returns:
            bool
        """
        return self._available

    def embed(self, texts: str | list[str], batch_size: int = 256) -> np.ndarray | None:
        """
        Generate embeddings for texts.
        Returns numpy array of shape (N, D) or None if unavailable.
        """
        if not self._available or not self._model:
            return None

        if isinstance(texts, str):
            texts = [texts]

        try:
            # FastEmbed returns a generator of numpy arrays (one per query, or batched? It returns iterable of embeddings)
            # actually list(model.embed(texts)) returns list of numpy arrays
            embeddings = list(self._model.embed(texts, batch_size=batch_size))
            if not embeddings:
                return np.array([])
            return np.array(embeddings)
        except Exception as e:
            logger.error("Embedding failed: %s", e, exc_info=True)
            return None

    def embed_query(self, query: str) -> np.ndarray | None:
        """Embed a single query string."""
        res = self.embed([query])
        if res is not None and len(res) > 0:
            return res[0]
        return None

    def encode(
        self, sentences: str | list[str], batch_size: int = 256, **kwargs
    ) -> list[np.ndarray]:
        """
        Alias for embed() to match SentenceTransformer API.
        Returns a list of numpy arrays (or single numpy array if input is string?
        SentenceTransformer.encode returns ndarray or list of ndarrays).
        """
        # Ignore extra kwargs like show_progress_bar
        vecs = self.embed(sentences, batch_size=batch_size)
        if vecs is None:
            return []
        # Return as list of arrays to match what EmbeddingEngine expects from encode_batch (list of vectors)
        return list(vecs)
