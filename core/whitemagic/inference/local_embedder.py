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
        return list(vecs)


class LlamaCppEmbedder:
    """Embedding provider using llama-server's /v1/embeddings endpoint.

    Requires llama-server started with --embeddings flag.
    Dimension depends on the loaded GGUF model (e.g. 384 for bge-small,
    768 for bge-base, 1024 for bge-large).

    No model download needed — uses the already-running llama-server.
    """

    def __init__(self, model_name: str = "llama-server") -> None:
        self.model_name = model_name
        self._available = False
        self._dim: int | None = None
        self._embed_url: str = ""
        self._try_connect()

    def _try_connect(self) -> None:
        """Check if llama-server supports embeddings.

        Checks the foreground backend first (port 8080), then falls back
        to the background model (port 8081) which has --embeddings enabled.
        """
        try:
            import requests

            # 1. Try foreground backend (default port 8080)
            from whitemagic.inference.llama_cpp import get_llama_cpp_backend

            backend = get_llama_cpp_backend()
            if backend.is_available:
                vec = backend.embed("test")
                if vec and len(vec) > 0:
                    self._dim = len(vec)
                    self._available = True
                    self._embed_url = backend.base_url
                    logger.info(
                        "LlamaCppEmbedder connected (dim=%d) via %s",
                        self._dim,
                        self._embed_url,
                    )
                    return

            # 2. Try background model via DualModelManager (port 8081)
            from whitemagic.inference.llama_cpp import get_dual_model_manager

            dmm = get_dual_model_manager()
            if dmm is not None and dmm.background.is_available:
                bg_url = dmm.background.base_url
                resp = requests.post(
                    f"{bg_url}/v1/embeddings",
                    json={"input": "test", "model": "local"},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                vec = data.get("data", [{}])[0].get("embedding", [])
                if vec and len(vec) > 0:
                    self._dim = len(vec)
                    self._available = True
                    self._embed_url = bg_url
                    logger.info(
                        "LlamaCppEmbedder connected (dim=%d) via background %s",
                        self._dim,
                        bg_url,
                    )
                    return

            self._available = False
        except Exception as e:
            logger.debug("LlamaCppEmbedder connect failed: %s", e)
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def embedding_dim(self) -> int | None:
        return self._dim

    def embed(self, texts: str | list[str]) -> np.ndarray | None:
        """Generate embeddings. Returns numpy array of shape (N, D)."""
        if not self._available:
            return None

        import requests as _requests

        if isinstance(texts, str):
            texts = [texts]

        try:
            vecs = []
            for text in texts:
                resp = _requests.post(
                    f"{self._embed_url}/v1/embeddings",
                    json={"input": text, "model": "local"},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                v = data.get("data", [{}])[0].get("embedding", [])
                if v:
                    vecs.append(v)
                else:
                    return None
            return np.array(vecs, dtype=np.float32)
        except Exception as e:
            logger.error("LlamaCppEmbedder embed failed: %s", e, exc_info=True)
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
        """Match SentenceTransformer.encode() interface."""
        vecs = self.embed(sentences)
        if vecs is None:
            return []
        return list(vecs)
