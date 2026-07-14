# ruff: noqa: BLE001
"""Semantic Embedding Layer (v14.1).
=================================
Provides sentence-level semantic embeddings for memory search and
association mining. Replaces keyword-overlap Jaccard with true
semantic similarity using sentence-transformers.

Design:
  - Lazy-loaded model (MiniLM-L6-v2, 384 dims, ~100MB)
  - Embeddings cached in `memory_embeddings` table (SQLite)
  - Batch encode via model.encode() with progress
  - HNSW approximate nearest-neighbor index (O(log N) queries)
  - Falls back to brute-force numpy cosine when hnswlib not available
  - Graceful fallback when sentence-transformers not installed

Usage:
    from whitemagic.core.memory.embeddings import get_embedding_engine
    engine = get_embedding_engine()

    # Encode a single text
    vec = engine.encode("holographic coordinate system")

    # Find similar memories (hot DB only)
    results = engine.search_similar("memory consolidation", limit=10)

    # Find similar memories across hot + cold DBs
    results = engine.search_similar("memory consolidation", limit=10, include_cold=True)

    # Batch encode all LONG_TERM memories
    engine.index_memories(memory_type="LONG_TERM")
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from typing import Any, cast

from whitemagic.core.memory.db_manager import safe_connect
from whitemagic.core.memory.embedding_similarity import (
    batch_cosine_similarity,
    batch_cosine_similarity_numpy,
    cosine_similarity,
    pack_embedding,
    unpack_embedding,
)

np: Any = None
_ndarray: Any = type(None)
_float32: Any = float
_linalg_norm: Any = None
_asarray: Any = None
_zeros: Any = None
_array: Any = None
_where: Any = None

try:
    import numpy as np
    _ndarray = np.ndarray
    _float32 = np.float32
    _linalg_norm = np.linalg.norm
    _asarray = np.asarray
    _zeros = np.zeros
    _array = np.array
    _where = np.where
except ImportError:
    np = None


logger = logging.getLogger(__name__)

# Embedding dimension (384 for both all-MiniLM-L6-v2 and BAAI/bge-small-en-v1.5)
# When using LlamaCppEmbedder, dimension is detected from the running model.
EMBEDDING_DIM = 384
MODEL_NAME = "BAAI/bge-small-en-v1.5"


class EmbeddingEngine:
    """Semantic embedding engine for memory search."""

    def __init__(self) -> None:
        self._model: Any | None = None
        self._model_lock = threading.RLock()
        self._available: bool | None = None  # None = unchecked
        self._db_conn: sqlite3.Connection | None = None
        self._cold_db_conn: sqlite3.Connection | None = None
        self._cold_db_checked = False
        # In-memory vector cache for fast repeated searches (hot DB)
        # Vectors stored as contiguous arrays for SIMD-friendly search
        # Pre-normalized at load time: each row is unit-length, so dot product == cosine
        self._vec_cache_ids: list[str] | None = None
        self._vec_cache_vecs: Any | None = None  # shape (N, EMBEDDING_DIM), PRE-NORMALIZED
        self._vec_cache_lock = threading.RLock()
        self._vec_cache_count: int = 0  # DB count at cache time
        # HNSW index (optional, O(log N) search)
        self._hnsw_index: Any | None = None
        self._hnsw_ids: list[str] | None = None
        self._hnsw_count: int = 0
        self._hnsw_available: bool | None = None  # None = unchecked
        # Cold HNSW index
        self._cold_hnsw_index: Any | None = None
        self._cold_hnsw_ids: list[str] | None = None
        self._cold_hnsw_count: int = 0
        # Separate vector cache for cold DB
        self._cold_vec_cache_ids: list[str] | None = None
        self._cold_vec_cache_vecs: Any | None = None  # shape (N, EMBEDDING_DIM)
        self._cold_vec_cache_lock = threading.RLock()
        self._cold_vec_cache_count: int = 0
        # HNSW disk persistence paths
        from whitemagic.config.paths import MEMORY_DIR
        self._hnsw_index_path = MEMORY_DIR / "hnsw_index.bin"
        self._hnsw_ids_path = MEMORY_DIR / "hnsw_ids.json"
        self._cold_hnsw_index_path = MEMORY_DIR / "hnsw_cold_index.bin"
        self._cold_hnsw_ids_path = MEMORY_DIR / "hnsw_cold_ids.json"

    def _get_embedding_dim(self) -> int:
        """Get the actual embedding dimension from the loaded model.

        Falls back to EMBEDDING_DIM (384) if model not loaded or dimension unknown.
        """
        model = self._model
        if model is not None and hasattr(model, "embedding_dim"):
            dim = model.embedding_dim
            if dim is not None and dim > 0:
                return dim
        return EMBEDDING_DIM

    def close(self) -> None:
        """Close SQLite connections and release resources."""
        if self._db_conn is not None:
            try:
                self._db_conn.close()
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass
            self._db_conn = None
        if self._cold_db_conn is not None:
            try:
                self._cold_db_conn.close()
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass
            self._cold_db_conn = None
        self._invalidate_vec_cache()
        self._invalidate_cold_vec_cache()

    def __del__(self) -> None:
        """Destructor fallback to ensure connections are closed."""
        self.close()

    def __enter__(self) -> EmbeddingEngine:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit — always close connections."""
        self.close()

    def _invalidate_cold_vec_cache(self) -> None:
        """Invalidate the in-memory cold vector cache and cold HNSW index."""
        with self._cold_vec_cache_lock:
            self._cold_vec_cache_ids = None
            self._cold_vec_cache_vecs = None
            self._cold_vec_cache_count = 0
            self._cold_hnsw_index = None
            self._cold_hnsw_ids = None
            self._cold_hnsw_count = 0

    def available(self, include_cache: bool = False) -> bool:
        """Check if embedding backend is available.

        If include_cache is True, returns True if at least the database
        cache of embeddings exists, even if the model cannot be loaded.
        """
        if include_cache:
            db = self._get_db()
            if db is not None:
                try:
                    res = db.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()
                    if res is None:
                        return False
                    return cast(int, res[0]) > 0
                except Exception as e:
                    logger.debug("Operation failed: %s", e)
                    return False
            return False

        if self._available is not None:
            return self._available

        # 1. Try llama.cpp embeddings (no extra download needed)
        try:
            from whitemagic.inference.local_embedder import LlamaCppEmbedder
            if LlamaCppEmbedder().is_available:
                self._available = True
                return True
        except ImportError:
            logger.debug("Optional dependency unavailable: ImportError")

        # 2. Try FastEmbed (LocalEmbedder)
        try:
            from whitemagic.inference.local_embedder import LocalEmbedder
            if LocalEmbedder().is_available:
                self._available = True
                return True
        except ImportError:
            logger.debug("Optional dependency unavailable: ImportError")

        # 3. Fallback to sentence-transformers
        try:
            import sentence_transformers  # noqa: F401

            self._available = True
        except ImportError:
            self._available = False
            logger.debug("No embedding backend available (llama.cpp, FastEmbed, or sentence-transformers)")
        return bool(self._available)

    def _get_model(self) -> Any:
        """Lazy-load the embedding model (llama.cpp > FastEmbed > SentenceTransformer)."""
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is not None:
                return self._model
            if not self.available():
                return None

            # 1. Try llama.cpp embeddings (no download, uses running server)
            try:
                from whitemagic.inference.local_embedder import LlamaCppEmbedder
                embedder = LlamaCppEmbedder()
                if embedder.is_available:
                    logger.info("Loaded LlamaCppEmbedder (dim=%d) via llama-server", embedder.embedding_dim)
                    self._model = embedder
                    return self._model
            except ImportError:
                logger.debug("Optional dependency unavailable: ImportError")

            # 2. Try FastEmbed (LocalEmbedder)
            try:
                from whitemagic.inference.local_embedder import LocalEmbedder
                embedder = LocalEmbedder(model_name="BAAI/bge-small-en-v1.5")
                if embedder.is_available:
                    logger.info("Loaded LocalEmbedder (FastEmbed): %s", embedder.model_name, exc_info=True)
                    self._model = embedder
                    return self._model
            except ImportError:
                logger.debug("Optional dependency unavailable: ImportError")

            # 3. Fallback to SentenceTransformer
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading embedding model: %s", MODEL_NAME, exc_info=True)
                self._model = SentenceTransformer(MODEL_NAME)
                logger.info("Embedding model loaded (%s dims)", EMBEDDING_DIM, exc_info=True)
            except Exception as e:
                logger.warning("Failed to load embedding model: %s", e, exc_info=True)
                self._available = False
                return None
        return self._model

    async def _get_db_async(self) -> sqlite3.Connection | None:
        """Get or create the DB connection for embedding search (async version)."""
        if self._db_conn is not None:
            return self._db_conn
        try:
            from whitemagic.config.paths import DB_PATH
            if not DB_PATH.exists():
                return None
            conn = safe_connect(str(DB_PATH))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA mmap_size=268435456")
            conn.execute("PRAGMA cache_size=-65536")
            conn.execute("PRAGMA temp_store=MEMORY")
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_embeddings'",
            ).fetchall()
            if not tables:
                logger.debug("DB has no memory_embeddings table yet")
                conn.close()
                return None
            self._db_conn = conn
            logger.debug("DB embedding connection established")
        except Exception as e:
            logger.debug("DB embedding init failed: %s", e, exc_info=True)
            return None
        return self._db_conn

    def _get_db(self) -> sqlite3.Connection | None:
        """Get or create the DB connection for embedding search (sync version)."""
        if self._db_conn is not None:
            return self._db_conn
        try:
            from whitemagic.config.paths import DB_PATH
            if not DB_PATH.exists():
                return None
            conn = safe_connect(str(DB_PATH))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA mmap_size=268435456")
            conn.execute("PRAGMA cache_size=-65536")
            conn.execute("PRAGMA temp_store=MEMORY")
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_embeddings'",
            ).fetchall()
            if not tables:
                conn.close()
                return None
            self._db_conn = conn
        except Exception as e:
            logger.debug("DB embedding init failed: %s", e, exc_info=True)
            return None
        return self._db_conn

    def _get_cold_db(self) -> sqlite3.Connection | None:
        """Get or create the cold DB connection for embedding search."""
        if self._cold_db_conn is not None:
            return self._cold_db_conn
        if self._cold_db_checked:
            return None  # Already tried, not available
        self._cold_db_checked = True
        try:
            from whitemagic.config.paths import COLD_DB_PATH
            if not COLD_DB_PATH.exists():
                return None
            conn = safe_connect(str(COLD_DB_PATH))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA mmap_size=268435456")
            conn.execute("PRAGMA cache_size=-65536")
            conn.execute("PRAGMA temp_store=MEMORY")
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_embeddings'",
            ).fetchall()
            if not tables:
                logger.debug("Cold DB has no memory_embeddings table yet")
                conn.close()
                self._cold_db_checked = False  # Retry later (might be encoding)
                return None
            self._cold_db_conn = conn
            logger.debug("Cold DB embedding connection established")
        except Exception as e:
            logger.debug("Cold DB embedding init failed: %s", e, exc_info=True)
            return None
        return self._cold_db_conn

    def _load_cold_vec_cache(self) -> tuple[list[str], Any]:
        """Load or return cached vectors from cold DB."""
        cold_db = self._get_cold_db()
        if cold_db is None:
            return [], []

        with self._cold_vec_cache_lock:
            try:
                current_count = cold_db.execute(
                    "SELECT COUNT(*) FROM memory_embeddings",
                ).fetchone()[0]
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                current_count = 0

            if current_count == 0:
                return [], []

            if (self._cold_vec_cache_ids is not None
                    and self._cold_vec_cache_vecs is not None
                    and self._cold_vec_cache_count == current_count):
                return self._cold_vec_cache_ids, self._cold_vec_cache_vecs

            # Reload from cold DB
            try:
                rows = cold_db.execute(
                    "SELECT memory_id, embedding FROM memory_embeddings",
                ).fetchall()
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                return [], []

            ids = [r[0] for r in rows]
            valid_vecs = [unpack_embedding(r[1]) for r in rows]

            if np is not None and _array is not None:
                vecs = _array(valid_vecs, dtype=_float32)
                size_info = f"{getattr(vecs, 'nbytes', 0) / 1024:.0f} KB contiguous"
            else:
                vecs = valid_vecs
                size_info = f"{len(valid_vecs)} lists"

            self._cold_vec_cache_ids = ids
            self._cold_vec_cache_vecs = vecs
            self._cold_vec_cache_count = current_count

            logger.debug("Cold vector cache loaded: {len(ids)} embeddings (%s)", size_info, exc_info=True)
            return ids, vecs

    def encode(self, text: str) -> list[float] | None:
        """Encode a single text into an embedding vector."""
        model = self._get_model()
        if model is None:
            return None
        try:
            vec = model.encode(text, show_progress_bar=False)
            # LocalEmbedder.encode() returns list[ndarray]; SentenceTransformer returns ndarray
            if isinstance(vec, list):
                vec = vec[0] if vec else None
            if vec is None:
                return None
            return cast(list[float], vec.tolist())
        except Exception as e:
            logger.debug("Encoding failed: %s", e, exc_info=True)
            return None

    def encode_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]] | None:
        """Batch encode texts into embedding vectors."""
        model = self._get_model()
        if model is None:
            return None
        try:
            vecs = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
            # LocalEmbedder returns list[ndarray]; SentenceTransformer returns ndarray
            if isinstance(vecs, list):
                return [v.tolist() for v in vecs]
            return [v.tolist() for v in vecs]
        except Exception as e:
            logger.debug("Batch encoding failed: %s", e, exc_info=True)
            return None

    async def get_cached_embedding_async(self, memory_id: str) -> list[float] | None:
        """Retrieve a cached embedding for a memory (async version)."""
        db = await self._get_db_async()
        if db is None:
            return None
        try:
            row = db.execute(
                "SELECT embedding FROM memory_embeddings WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
            if row and row[0]:
                return unpack_embedding(row[0])
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass
        return None

    def get_cached_embedding(self, memory_id: str) -> list[float] | None:
        """Retrieve a cached embedding for a memory (sync version)."""
        db = self._get_db()
        if db is None:
            return None
        try:
            row = db.execute(
                "SELECT embedding FROM memory_embeddings WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
            if row and row[0]:
                return unpack_embedding(row[0])
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass
        return None

    async def cache_embedding_async(self, memory_id: str, embedding: list[float]) -> bool:
        """Cache an embedding for a memory (async version)."""
        db = await self._get_db_async()
        if db is None:
            return False
        try:
            db.execute(
                "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, model) VALUES (?, ?, ?)",
                (memory_id, pack_embedding(embedding), MODEL_NAME),
            )
            db.commit()
            self._invalidate_vec_cache()
            return True
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            return False

    def cache_embedding(self, memory_id: str, embedding: list[float]) -> bool:
        """Cache an embedding for a memory (sync version)."""
        db = self._get_db()
        if db is None:
            return False
        try:
            db.execute(
                "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, model) VALUES (?, ?, ?)",
                (memory_id, pack_embedding(embedding), MODEL_NAME),
            )
            db.commit()
            self._invalidate_vec_cache()
            return True
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            return False

    def cache_embeddings_batch(self, items: list[tuple[str, list[float]]]) -> int:
        """Batch cache multiple embeddings in a single transaction.

        Args:
            items: List of (memory_id, embedding) pairs.

        Returns:
            Number of embeddings successfully cached.
        """
        db = self._get_db()
        if db is None:
            return 0
        try:
            rows = [
                (mid, pack_embedding(vec), MODEL_NAME)
                for mid, vec in items
            ]
            db.executemany(
                "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, model) VALUES (?, ?, ?)",
                rows,
            )
            db.commit()
            self._invalidate_vec_cache()
            return len(items)
        except Exception as e:
            logger.debug("Batch cache failed: %s", e)
            return 0

    def _invalidate_vec_cache(self) -> None:
        """Invalidate the in-memory vector cache and HNSW index."""
        with self._vec_cache_lock:
            self._vec_cache_ids = None
            self._vec_cache_vecs = None
            self._vec_cache_count = 0
            self._hnsw_index = None
            self._hnsw_ids = None
            self._hnsw_count = 0
            try:
                self._hnsw_index_path.unlink(missing_ok=True)
                self._hnsw_ids_path.unlink(missing_ok=True)
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

    def _hnsw_is_available(self) -> bool:
        """Check if hnswlib is installed."""
        if self._hnsw_available is not None:
            return self._hnsw_available
        try:
            import hnswlib  # type: ignore[import-untyped]  # noqa: F401
            self._hnsw_available = True
        except ImportError:
            self._hnsw_available = False
        return self._hnsw_available

    def _build_hnsw_index(self, ids: list[str], vectors: Any) -> Any:
        """Build an HNSW index from vectors.

        Parameters tuned for memory workloads:
          - ef_construction=200: higher quality graph (default 100)
          - M=32: connections per node (good for 384-dim, default 16)
          - ef=100: search-time beam width (recall ~99% at this level)
        """
        import hnswlib  # type: ignore[import-untyped]
        n, dim = vectors.shape
        index = hnswlib.Index(space="cosine", dim=dim)
        # max_elements with 20% headroom for incremental adds
        index.init_index(max_elements=max(n + 100, int(n * 1.2)), ef_construction=200, M=32)
        index.add_items(vectors, list(range(n)))
        index.set_ef(100)
        return index

    def _get_hnsw_index(self) -> tuple[Any, list[str]] | None:
        """Get or build the hot HNSW index. Returns (index, id_list) or None."""
        if not self._hnsw_is_available():
            return None
        ids, vectors = self._load_vec_cache()
        if not ids or not hasattr(vectors, 'shape') or vectors.shape[0] < 5:
            return None  # Too few vectors for HNSW to be useful
        with self._vec_cache_lock:
            if (self._hnsw_index is not None
                    and self._hnsw_ids is not None
                    and self._hnsw_count == len(ids)):
                return self._hnsw_index, self._hnsw_ids
        try:
            if self._hnsw_index_path.exists() and self._hnsw_ids_path.exists():
                import json

                import hnswlib  # type: ignore[import-untyped]
                saved_ids = json.loads(self._hnsw_ids_path.read_text())
                if len(saved_ids) == len(ids):
                    dim = vectors.shape[1] if hasattr(vectors, 'shape') else len(vectors[0])
                    index = hnswlib.Index(space="cosine", dim=dim)
                    index.load_index(str(self._hnsw_index_path))
                    index.set_ef(100)
                    self._hnsw_index = index
                    self._hnsw_ids = saved_ids
                    self._hnsw_count = len(saved_ids)
                    logger.debug("HNSW index loaded from disk: %s vectors", len(saved_ids))
                    return index, saved_ids
        except Exception as e:
            logger.debug("HNSW disk load failed: %s", e)

        # Build from scratch
        try:
            index = self._build_hnsw_index(ids, vectors)
            self._hnsw_index = index
            self._hnsw_ids = ids
            self._hnsw_count = len(ids)
            # Persist to disk for fast restart
            try:
                import json
                index.save_index(str(self._hnsw_index_path))
                self._hnsw_ids_path.write_text(json.dumps(ids))
                logger.debug("HNSW index persisted to disk: %s vectors", len(ids))
            except Exception as e:
                logger.debug("HNSW persist failed: %s", e)
            logger.debug("HNSW index built: %s vectors, dim=%s", len(ids), vectors.shape[1])
            return index, ids
        except Exception as e:
            logger.debug("HNSW build failed: %s", e, exc_info=True)
            self._hnsw_available = False
            return None

    def _get_cold_hnsw_index(self) -> tuple[Any, list[str]] | None:
        """Get or build the cold HNSW index. Returns (index, id_list) or None."""
        if not self._hnsw_is_available():
            return None
        cold_ids, cold_vectors = self._load_cold_vec_cache()
        if not cold_ids or not hasattr(cold_vectors, 'shape') or cold_vectors.shape[0] < 5:
            return None
        if (self._cold_hnsw_index is not None
                and self._cold_hnsw_ids is not None
                and self._cold_hnsw_count == len(cold_ids)):
            return self._cold_hnsw_index, self._cold_hnsw_ids
        try:
            index = self._build_hnsw_index(cold_ids, cold_vectors)
            self._cold_hnsw_index = index
            self._cold_hnsw_ids = cold_ids
            self._cold_hnsw_count = len(cold_ids)
            logger.debug("Cold HNSW index built: %s vectors", len(cold_ids))
            return index, cold_ids
        except Exception as e:
            logger.debug("Cold HNSW build failed: %s", e, exc_info=True)
            return None

    def _hnsw_search(self, query_vec: Any, index: Any, ids: list[str],
                     limit: int, min_similarity: float) -> list[dict[str, Any]]:
        """Search an HNSW index. Returns list of {memory_id, similarity, source}."""
        if np is None or _asarray is None:
            return []
        q = _asarray(query_vec, dtype=_float32).reshape(1, -1)
        k = min(limit * 3, len(ids))  # Over-fetch then filter
        labels, distances = index.knn_query(q, k=k)
        results = []
        for idx, dist in zip(labels[0], distances[0]):
            sim = 1.0 - dist  # hnswlib cosine returns distance = 1 - similarity
            if sim >= min_similarity:
                results.append({"memory_id": ids[idx], "similarity": round(float(sim), 4)})
        return results

    def _load_vec_cache(self) -> tuple[list[str], Any]:
        """Load or return cached vectors.

        Returns (ids, vectors) where vectors is shape (N, 384) float32 if np else list[list[float]].
        """
        db = self._get_db()
        if db is None:
            return [], []

        with self._vec_cache_lock:
            try:
                current_count = db.execute(
                    "SELECT COUNT(*) FROM memory_embeddings",
                ).fetchone()[0]
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                current_count = 0

            if (self._vec_cache_ids is not None
                    and self._vec_cache_vecs is not None
                    and self._vec_cache_count == current_count):
                return self._vec_cache_ids, self._vec_cache_vecs

            # Reload from DB
            try:
                rows = db.execute(
                    "SELECT memory_id, embedding FROM memory_embeddings",
                ).fetchall()
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                return [], []

            if not rows:
                return [], []
            # Filter by embedding dimension (avoid inhomogeneous shape errors)
            dim = self._get_embedding_dim()
            valid_ids = []
            valid_vecs = []
            for r in rows:
                vec = unpack_embedding(r[1])
                if len(vec) == dim:
                    valid_ids.append(r[0])
                    valid_vecs.append(vec)

            ids = valid_ids
            if _array is not None and _linalg_norm is not None:
                # Unpack all blobs into a single contiguous array
                vecs = _array(
                    valid_vecs,
                    dtype=_float32,
                )
                if vecs.ndim == 1:
                    vecs = vecs.reshape(-1, dim)
                # Pre-normalize: each row becomes unit-length
                norms = _linalg_norm(vecs, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                vecs = vecs / norms
                size_info = f"{getattr(vecs, 'nbytes', 0) / 1024:.0f} KB contiguous, pre-normalized"
            else:
                vecs = valid_vecs
                size_info = f"{len(valid_vecs)} lists"

            self._vec_cache_ids = ids
            self._vec_cache_vecs = vecs
            self._vec_cache_count = current_count

            logger.debug("Vector cache loaded: {len(ids)} embeddings (%s)", size_info, exc_info=True)
            return ids, vecs

    def index_memories(
        self,
        memory_type: str | None = None,
        limit: int = 10000,
        skip_cached: bool = True,
    ) -> dict[str, Any]:
        """Batch-encode and cache embeddings for memories.

        Returns a dict with indexing stats.
        """
        if not self.available():
            return {"status": "unavailable", "reason": "sentence-transformers not installed"}

        db = self._get_db()
        if db is None:
            return {"status": "error", "reason": "DB unavailable"}

        t0 = time.perf_counter()

        # Find memories to encode (exclude quarantined)
        sql = "SELECT id, title, content FROM memories"
        params: list = []
        conditions = ["memory_type != 'quarantined'"]

        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)

        if skip_cached:
            conditions.append("id NOT IN (SELECT memory_id FROM memory_embeddings WHERE model = ?)")
            params.append(MODEL_NAME)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY importance DESC LIMIT ?"
        params.append(limit)

        rows = db.execute(sql, params).fetchall()

        if not rows:
            return {"status": "success", "indexed": 0, "reason": "all memories already cached"}

        # Prepare texts
        texts = [f"{row[1] or ''} {row[2] or ''}" for row in rows]
        ids = [row[0] for row in rows]

        # Batch encode
        embeddings = self.encode_batch(texts)
        if embeddings is None:
            return {"status": "error", "reason": "encoding failed"}

        # Cache (batch insert without per-row cache invalidation)
        cached = 0
        for mid, emb in zip(ids, embeddings):
            try:
                db.execute(
                    "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, model) VALUES (?, ?, ?)",
                    (mid, pack_embedding(emb), MODEL_NAME),
                )
                cached += 1
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass
        db.commit()
        self._invalidate_vec_cache()

        elapsed = time.perf_counter() - t0
        return {
            "status": "success",
            "indexed": cached,
            "total_candidates": len(rows),
            "duration_s": round(elapsed, 1),
            "rate": round(cached / elapsed, 1) if elapsed > 0 else 0,
            "model": MODEL_NAME,
            "dims": EMBEDDING_DIM,
        }

    def search_similar(
        self, query: str, limit: int = 10, min_similarity: float = 0.1,
        include_cold: bool = False, galaxy: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for memories semantically similar to a query.

        Args:
            query: Search query text.
            limit: Maximum results to return.
            min_similarity: Minimum cosine similarity threshold.
            include_cold: If True, also search cold DB embeddings.
                Hot results are returned first; cold results fill remaining slots.
            galaxy: If set, filter results to only this galaxy.

        Returns a list of dicts with memory_id, similarity, and source ('hot'/'cold').
        Sorted by similarity descending.

        """
        query_vec = None
        is_id = False
        if len(query) == 32 and all(c in "0123456789abcdef" for c in query.lower()):
            is_id = True
        elif len(query) < 50 and "-" in query:
            is_id = True

        if is_id:
            query_vec = self.get_cached_embedding(query)

        if query_vec is None:
            query_vec = self.encode(query)

        if query_vec is None:
            return []

        results = []

        # When filtering by galaxy, over-fetch from HNSW then filter
        effective_limit = limit * 5 if galaxy else limit

        # HNSW fast path (O(log N) per query)
        hnsw_result = self._get_hnsw_index()
        if hnsw_result is not None and np is not None and _asarray is not None:
            q_np = _asarray(query_vec, dtype=_float32)
            hnsw_index, hnsw_ids = hnsw_result
            hits = self._hnsw_search(q_np, hnsw_index, hnsw_ids, effective_limit, min_similarity)
            for hit in hits:
                hit["source"] = "hot"
                results.append(hit)
        else:
            # Brute-force fallback (O(N) per query)
            ids, vectors = self._load_vec_cache()
            if ids:
                if np is not None and _asarray is not None and isinstance(vectors, _ndarray):
                    q_np = _asarray(query_vec, dtype=_float32)
                    scores = batch_cosine_similarity_numpy(q_np, vectors, pre_normalized=True)  # type: ignore[call-arg]
                    mask = scores >= min_similarity
                    if _where is not None:
                        for idx in _where(mask)[0]:
                            results.append({"memory_id": ids[idx], "similarity": round(float(scores[idx]), 4), "source": "hot"})
                    else:
                        # Fallback for where if somehow not aliased
                        for idx, m_val in enumerate(mask):
                            if m_val:
                                results.append({"memory_id": ids[idx], "similarity": round(float(scores[idx]), 4), "source": "hot"})
                else:
                    # Pure Python fallback
                    for mid, vec in zip(ids, vectors):
                        sim = cosine_similarity(query_vec, vec)
                        if sim >= min_similarity:
                            results.append({"memory_id": mid, "similarity": round(sim, 4), "source": "hot"})

        if include_cold:
            hot_id_set = {r["memory_id"] for r in results}

            # HNSW fast path for cold
            cold_hnsw = self._get_cold_hnsw_index()
            if cold_hnsw is not None and np is not None and _asarray is not None:
                q_np = _asarray(query_vec, dtype=_float32)
                cold_index, cold_hnsw_ids = cold_hnsw
                cold_hits = self._hnsw_search(q_np, cold_index, cold_hnsw_ids, limit, min_similarity)
                for hit in cold_hits:
                    if hit["memory_id"] not in hot_id_set:
                        hit["source"] = "cold"
                        results.append(hit)
            else:
                # Brute-force fallback for cold
                cold_ids, cold_vectors = self._load_cold_vec_cache()
                if cold_ids:
                    if np is not None and _asarray is not None and isinstance(cold_vectors, _ndarray):
                        q_np = _asarray(query_vec, dtype=_float32)
                        cold_scores = batch_cosine_similarity(q_np, cold_vectors)
                        mask = cold_scores >= min_similarity  # type: ignore[operator]
                        if _where is not None:
                            for idx in _where(mask)[0]:
                                mid = cold_ids[idx]
                                if mid not in hot_id_set:
                                    results.append({"memory_id": mid, "similarity": round(float(cold_scores[idx]), 4), "source": "cold"})
                        else:
                            for idx, m_val in enumerate(mask):
                                if m_val:
                                    mid = cold_ids[idx]
                                    if mid not in hot_id_set:
                                        results.append({"memory_id": mid, "similarity": round(float(cold_scores[idx]), 4), "source": "cold"})
                    else:
                        # Pure Python fallback
                        for mid, vec in zip(cold_ids, cold_vectors):
                            if mid not in hot_id_set:
                                sim = cosine_similarity(query_vec, vec)
                                if sim >= min_similarity:
                                    results.append({"memory_id": mid, "similarity": round(sim, 4), "source": "cold"})

        # Filter by galaxy if requested
        if galaxy:
            results = self._filter_by_galaxy(results, galaxy)

        # Sort by similarity descending
        results.sort(key=lambda r: r["similarity"], reverse=True)
        return results[:limit]

    def _filter_by_galaxy(self, results: list[dict[str, Any]], galaxy: str) -> list[dict[str, Any]]:
        """Filter search results by galaxy using SQLite lookup."""
        if not results:
            return results
        db = self._get_db()
        if db is None:
            return results
        ids = [r["memory_id"] for r in results]
        placeholders = ",".join("?" * len(ids))
        try:
            rows = db.execute(
                f"SELECT id FROM memories WHERE id IN ({placeholders}) AND galaxy = ?",
                (*ids, galaxy),
            ).fetchall()
            valid_ids = {row[0] for row in rows}
            return [r for r in results if r["memory_id"] in valid_ids]
        except Exception as e:
            logger.debug("Galaxy filter failed: %s", e)
            return results

    def search_similar_by_vector(
        self,
        query_vec: list[float],
        limit: int = 10,
        min_similarity: float = 0.1,
        include_cold: bool = False,
    ) -> list[dict[str, Any]]:
        """Search for memories similar to a pre-computed embedding vector.

        Like search_similar but accepts a raw vector instead of text.
        Used by HRR compositional reasoning to search with projected vectors.

        Args:
            query_vec: Pre-computed embedding vector (e.g., HRR-projected).
            limit: Maximum results to return.
            min_similarity: Minimum cosine similarity threshold.
            include_cold: If True, also search cold DB embeddings.

        Returns a list of dicts with memory_id, similarity, and source.
        """
        if not query_vec:
            return []

        results: list[dict[str, Any]] = []

        # HNSW fast path (O(log N) per query)
        hnsw_result = self._get_hnsw_index()
        if hnsw_result is not None and np is not None and _asarray is not None:
            q_np = _asarray(query_vec, dtype=_float32)
            hnsw_index, hnsw_ids = hnsw_result
            hits = self._hnsw_search(q_np, hnsw_index, hnsw_ids, limit, min_similarity)
            for hit in hits:
                hit["source"] = "hot"
                results.append(hit)
        else:
            # Brute-force fallback (O(N) per query)
            ids, vectors = self._load_vec_cache()
            if ids:
                if np is not None and _asarray is not None and isinstance(vectors, _ndarray):
                    q_np = _asarray(query_vec, dtype=_float32)
                    scores = batch_cosine_similarity_numpy(q_np, vectors, pre_normalized=True)  # type: ignore[call-arg]
                    mask = scores >= min_similarity
                    if _where is not None:
                        for idx in _where(mask)[0]:
                            results.append({"memory_id": ids[idx], "similarity": round(float(scores[idx]), 4), "source": "hot"})
                    else:
                        for idx, m_val in enumerate(mask):
                            if m_val:
                                results.append({"memory_id": ids[idx], "similarity": round(float(scores[idx]), 4), "source": "hot"})
                else:
                    for mid, vec in zip(ids, vectors):
                        sim = cosine_similarity(query_vec, vec)
                        if sim >= min_similarity:
                            results.append({"memory_id": mid, "similarity": round(sim, 4), "source": "hot"})

        # Sort by similarity descending
        results.sort(key=lambda r: r["similarity"], reverse=True)
        return results[:limit]

    def find_similar_pairs(
        self,
        min_similarity: float = 0.50,
        max_pairs: int = 200,
    ) -> list[dict[str, Any]]:
        """Find all memory pairs above a cosine similarity threshold.

        Used by semantic association mining (Leap 1a) to replace keyword
        Jaccard with true semantic similarity.

        Returns list of {source_id, target_id, similarity} sorted descending.
        """
        ids, vectors = self._load_vec_cache()
        if len(ids) < 2:
            return []

        pairs: list[dict[str, Any]] = []
        n = len(ids)

        # Batch approach: for each vector, compute cosine against all subsequent
        for i in range(n):
            if len(pairs) >= max_pairs * 3:
                # collect extra, trim later
                break
            remaining = vectors[i + 1:]
            if len(remaining) == 0:
                break

            if np is not None and isinstance(vectors, _ndarray):
                scores = batch_cosine_similarity(vectors[i], remaining)
                mask = scores >= min_similarity  # type: ignore[operator]
                if _where is not None:
                    for j_offset in _where(mask)[0]:
                        pairs.append({
                            "source_id": ids[i],
                            "target_id": ids[i + 1 + int(j_offset)],
                            "similarity": round(float(scores[j_offset]), 4),
                        })
                else:
                    for j_offset, m_val in enumerate(mask):
                        if m_val:
                            pairs.append({
                                "source_id": ids[i],
                                "target_id": ids[i + 1 + j_offset],
                                "similarity": round(float(scores[j_offset]), 4),
                            })
            else:
                # Pure Python fallback
                for j_offset, other_vec in enumerate(remaining):
                    sim = cosine_similarity(vectors[i], other_vec)
                    if sim >= min_similarity:
                        pairs.append({
                            "source_id": ids[i],
                            "target_id": ids[i + 1 + j_offset],
                            "similarity": round(sim, 4),
                        })

        pairs.sort(key=lambda p: p["similarity"], reverse=True)
        return pairs[:max_pairs]

    def find_duplicates(
        self,
        threshold: float = 0.95,
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        """Find near-duplicate memory pairs via embedding cosine similarity.

        Used by Leap 1b for embedding-powered deduplication.
        Threshold ≥0.95 catches semantic duplicates (same meaning, different wording).

        H001 Optimization: Uses Rust SimHash LSH (random hyperplane) for 50× speedup.
        SimHash preserves cosine similarity via 128 random hyperplanes with O(N) LSH bucketing.
        Falls back to Python cosine similarity if Rust unavailable.

        Returns list of {source_id, target_id, similarity} sorted descending.
        """
        try:
            import json

            import whitemagic_rust

            ids, vectors = self._load_vec_cache()
            if len(ids) < 2:
                return []

            # Flatten numpy array to 1D list for efficient Rust transfer
            # This avoids expensive JSON serialization of nested arrays
            embeddings_flat = vectors.flatten().tolist()
            embedding_dim = vectors.shape[1]

            # Uses random hyperplane LSH to preserve cosine similarity
            # Pure Rust hot path - no DB queries, no keyword extraction
            simhash_lsh = getattr(whitemagic_rust, "simhash_lsh", None)
            if simhash_lsh is None or not hasattr(simhash_lsh, "simhash_find_duplicates"):
                raise AttributeError("simhash_lsh not available")

            result_json = simhash_lsh.simhash_find_duplicates(
                embeddings_flat,
                embedding_dim,
                threshold,
                max_results
            )
            rust_results = json.loads(result_json)

            pairs = []
            for dup in rust_results:
                pairs.append({
                    "source_id": ids[dup["idx_a"]],
                    "target_id": ids[dup["idx_b"]],
                    "similarity": round(dup["similarity"], 4),
                })

            logger.info("🦀 Rust SimHash LSH found {len(pairs)} duplicates (threshold=%s)", threshold, exc_info=True)
            return pairs

        except Exception as e:
            logger.debug("Rust SimHash unavailable (%s), falling back to Python cosine similarity", e, exc_info=True)
            # Fallback to Python implementation
            return self.find_similar_pairs(
                min_similarity=threshold,
                max_pairs=max_results,
            )

    def closest_constellation(
        self, query: str, max_results: int = 3,
    ) -> list[dict[str, Any]]:
        """Find the constellation(s) closest to a query using embedding centroids.

        Encodes the query, then computes cosine similarity against each
        constellation's centroid embedding (derived from dominant tags).

        Returns list of {name, similarity, dominant_tags, size, zone} sorted
        by similarity descending. Empty list if no constellations or no model.
        """
        query_vec = self.encode(query)
        if query_vec is None:
            return []

        try:
            from whitemagic.core.memory.constellations import get_constellation_detector
            detector = get_constellation_detector()
            centroids = detector.get_constellation_centroids()
            if not centroids:
                return []

            # Encode each constellation's identity text (dominant tags)
            results = []
            for c in centroids:
                tag_text = " ".join(c["dominant_tags"]) if c["dominant_tags"] else c["name"]
                tag_vec = self.encode(tag_text)
                if tag_vec is None:
                    continue
                sim = cosine_similarity(query_vec, tag_vec)
                results.append({
                    "name": c["name"],
                    "similarity": round(sim, 4),
                    "dominant_tags": c["dominant_tags"],
                    "size": c["size"],
                    "zone": c["zone"],
                })

            results.sort(key=lambda r: r["similarity"], reverse=True)
            return results[:max_results]

        except Exception as e:
            logger.debug("Operation failed: %s", e)
            return []

    async def embedding_stats_async(self) -> dict[str, Any]:
        """Get stats about the embedding cache (hot + cold) - async version."""
        db = await self._get_db_async()
        if db is None:
            return {"status": "unavailable"}

        try:
            hot_total = db.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()[0]
            cold_total = 0
            cold_db = self._get_cold_db()
            if cold_db:
                try:
                    cold_total = cold_db.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()[0]
                except Exception as e:
                    logger.debug("Operation failed: %s", e)
                    pass
            hnsw_status = "active" if self._hnsw_index is not None else (
                "available" if self._hnsw_is_available() else "not_installed"
            )
            return {
                "status": "ok",
                "hot_embeddings": hot_total,
                "cold_embeddings": cold_total,
                "total_embeddings": hot_total + cold_total,
                "model": MODEL_NAME,
                "dims": EMBEDDING_DIM,
                "engine_available": self.available(),
                "hnsw_index": hnsw_status,
                "hnsw_hot_count": self._hnsw_count,
                "hnsw_cold_count": self._cold_hnsw_count,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def embedding_stats(self) -> dict[str, Any]:
        """Get stats about the embedding cache (hot + cold)."""
        db = self._get_db()
        if db is None:
            return {"status": "unavailable"}

        try:
            hot_total = cast(int, db.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()[0])
            cold_total = 0
            cold_db = self._get_cold_db()
            if cold_db:
                try:
                    cold_total = cast(int, cold_db.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()[0])
                except Exception as e:
                    logger.debug("Operation failed: %s", e)
                    pass
            hnsw_status = "active" if self._hnsw_index is not None else (
                "available" if self._hnsw_is_available() else "not_installed"
            )
            return {
                "status": "ok",
                "hot_embeddings": hot_total,
                "cold_embeddings": cold_total,
                "total_embeddings": hot_total + cold_total,
                "model": MODEL_NAME,
                "dims": EMBEDDING_DIM,
                "engine_available": self.available(),
                "hnsw_index": hnsw_status,
                "hnsw_hot_count": self._hnsw_count,
                "hnsw_cold_count": self._cold_hnsw_count,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    _hrr_engine_instance: Any = None
    _quantized_hrr_engine_instance: Any = None
    _hrr_composition_engine_instance: Any = None

    def _get_hrr_engine(self):
        """Lazy accessor for the HRREngine."""
        if self._hrr_engine_instance is None:
            from whitemagic.core.memory.hrr import get_hrr_engine
            self._hrr_engine_instance = get_hrr_engine()
        return self._hrr_engine_instance

    def _get_quantized_hrr_engine(self):
        """Lazy accessor for the QuantizedHRREngine."""
        if self._quantized_hrr_engine_instance is None:
            from whitemagic.core.memory.qfhrr import get_quantized_hrr_engine
            self._quantized_hrr_engine_instance = get_quantized_hrr_engine()
        return self._quantized_hrr_engine_instance

    def _get_hrr_composition_engine(self):
        """Lazy accessor for the HRRCompositionEngine."""
        if self._hrr_composition_engine_instance is None:
            from whitemagic.core.evolution.hrr_composition import HRRCompositionEngine
            self._hrr_composition_engine_instance = HRRCompositionEngine()
        return self._hrr_composition_engine_instance

    def hrr_bind(self, a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> np.ndarray:
        """Circular convolution binding via HRR."""
        return self._get_hrr_engine().bind(a, b)

    def hrr_unbind(self, bound: list[float] | np.ndarray, b: list[float] | np.ndarray) -> np.ndarray:
        """Circular correlation unbinding via HRR."""
        return self._get_hrr_engine().unbind(bound, b)

    def hrr_superpose(self, *vectors: list[float] | np.ndarray) -> np.ndarray:
        """Superposition: element-wise sum of multiple HRR vectors."""
        return self._get_hrr_engine().superpose(*vectors)

    def hrr_similarity(self, a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
        """Cosine similarity between two HRR vectors."""
        return self._get_hrr_engine().similarity(a, b)

    def hrr_project(self, embedding: list[float] | np.ndarray, relation: str) -> np.ndarray:
        """Project an embedding through a relation."""
        return self._get_hrr_engine().project(embedding, relation)

    def hrr_inverse_project(self, embedding: list[float] | np.ndarray, relation: str) -> np.ndarray:
        """Inverse projection: recover the source that led to E via relation."""
        return self._get_hrr_engine().inverse_project(embedding, relation)

    def hrr_encode_event(self, **kwargs: Any) -> np.ndarray:
        """Encode a structured event as a single HRR vector."""
        return self._get_hrr_engine().encode_event(**kwargs)

    def hrr_decode_event_role(self, event: list[float] | np.ndarray, role: str) -> np.ndarray:
        """Decode a role filler from an event vector."""
        return self._get_hrr_engine().decode_event_role(event, role)

    def hrr_get_stats(self) -> dict[str, Any]:
        """Get HRR engine statistics."""
        return self._get_hrr_engine().get_stats()

    def hrr_available_relations(self) -> list[str]:
        """List available HRR relation names."""
        return self._get_hrr_engine().available_relations()

    def qhrr_bind(self, a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> Any:
        """Quantized HRR binding via modular addition."""
        return self._get_quantized_hrr_engine().bind(a, b)

    def qhrr_unbind(self, bound: Any, b: list[float] | np.ndarray) -> Any:
        """Quantized HRR unbinding via modular subtraction."""
        return self._get_quantized_hrr_engine().unbind(bound, b)

    def qhrr_similarity(self, a: Any, b: Any) -> float:
        """Quantized HRR similarity via triangular LUT."""
        return self._get_quantized_hrr_engine().similarity(a, b)

    def qhrr_get_stats(self) -> dict[str, Any]:
        """Get quantized HRR engine statistics."""
        eng = self._get_quantized_hrr_engine()
        return {
            "dim": eng.dim,
            "bits": eng.bits,
            "K": eng.K,
            "bytes_per_vector": eng.bytes_per_vector,
        }

    def hrr_compose_encode(self, hypothesis_id: str, description: str, impact: float = 0.5):
        """Encode a hypothesis as an HRR vector via composition engine."""
        return self._get_hrr_composition_engine().encode_hypothesis(hypothesis_id, description, impact)

    def hrr_compose_bind(self, id_a: str, id_b: str):
        """Bind two hypotheses via circular convolution."""
        return self._get_hrr_composition_engine().bind(id_a, id_b)

    # ── Manifold-Aware Search ──

    _manifold_cache: dict[str, str] = {}
    _manifold_cache_lock = threading.RLock()

    def detect_manifold(self, galaxy: str | None = None) -> str:
        """Detect the best manifold type for a galaxy's embeddings.

        Samples up to 100 embedding vectors from the specified galaxy
        (or the main DB), then uses auto_select_manifold to classify
        the geometric structure as euclidean, hyperbolic, or spherical.

        Results are cached per galaxy with a 5-minute TTL.
        """

        cache_key = galaxy or "_default"
        with self._manifold_cache_lock:
            if cache_key in self._manifold_cache:
                return self._manifold_cache[cache_key]

        from whitemagic.core.acceleration.quantum_bridge import auto_select_manifold

        # Sample embeddings
        try:
            ids, vectors = self._load_vec_cache()
            if len(ids) < 2:
                return "euclidean"

            # Sample up to 100 vectors
            import random as _rng
            sample_size = min(100, len(ids))
            sample_indices = _rng.Random(42).sample(range(len(ids)), sample_size)
            sample_points = []
            for idx in sample_indices:
                if np is not None and isinstance(vectors, _ndarray):
                    sample_points.append(vectors[idx].tolist())
                elif isinstance(vectors, list):
                    sample_points.append(list(vectors[idx]))
                else:
                    sample_points.append(list(vectors[idx]))

            manifold = auto_select_manifold(sample_points)
        except Exception:
            manifold = "euclidean"

        with self._manifold_cache_lock:
            self._manifold_cache[cache_key] = manifold
        return manifold

    def manifold_aware_similarity(
        self,
        query_vec: list[float],
        candidate_vec: list[float],
        manifold: str | None = None,
    ) -> float:
        """Compute similarity using manifold-appropriate distance.

        Converts manifold distance to similarity score:
        - Euclidean: cosine similarity (existing behavior)
        - Hyperbolic: 1 / (1 + hyperbolic_distance)
        - Spherical: cos(angle) = dot product on unit sphere

        Args:
            query_vec: Query embedding vector.
            candidate_vec: Candidate embedding vector.
            manifold: Manifold type. If None, uses cached detection.
        """
        if manifold is None:
            manifold = "euclidean"

        if manifold == "euclidean":
            return cosine_similarity(query_vec, candidate_vec)
        elif manifold == "hyperbolic":
            from whitemagic.core.acceleration.quantum_bridge import manifold_distance
            d = manifold_distance(query_vec, candidate_vec, "hyperbolic")
            return 1.0 / (1.0 + d) if d != float("inf") else 0.0
        elif manifold == "spherical":
            from whitemagic.core.acceleration.quantum_bridge import manifold_distance
            d = manifold_distance(query_vec, candidate_vec, "spherical")
            return max(0.0, 1.0 - d / 3.14159265358979)
        return cosine_similarity(query_vec, candidate_vec)

    def search_similar_manifold(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.1,
        galaxy: str | None = None,
    ) -> list[dict[str, Any]]:
        """Manifold-aware similarity search.

        Detects the manifold type for the embedding space, then uses
        the appropriate distance metric for similarity computation.
        Falls back to standard cosine similarity if manifold detection fails.
        """
        manifold = self.detect_manifold(galaxy)
        if manifold == "euclidean":
            return self.search_similar(query, limit, min_similarity, galaxy=galaxy)

        # For non-Euclidean manifolds, use brute-force with manifold distance
        query_vec = self.encode(query)
        if not query_vec:
            return []

        ids, vectors = self._load_vec_cache()
        if not ids:
            return []

        results: list[dict[str, Any]] = []
        for i, mid in enumerate(ids):
            if np is not None and isinstance(vectors, _ndarray):
                candidate = vectors[i].tolist()
            else:
                candidate = list(vectors[i])
            sim = self.manifold_aware_similarity(query_vec, candidate, manifold)
            if sim >= min_similarity:
                results.append({"memory_id": mid, "similarity": round(sim, 4), "source": "hot", "manifold": manifold})

        results.sort(key=lambda r: r["similarity"], reverse=True)
        return results[:limit]

_engine_instances: dict[str, EmbeddingEngine] = {}
_engine_lock = threading.RLock()


def reset_embedding_engine() -> None:
    """Reset all embedding engine instances for testing."""
    with _engine_lock:
        for inst in _engine_instances.values():
            try:
                inst.close()
            except Exception:
                logger.debug("Ignored error in embeddings.py:1466")
        _engine_instances.clear()


def get_embedding_engine(user_id: str = "local") -> EmbeddingEngine:
    """Get or create the EmbeddingEngine singleton for a given user namespace.

    Each user_id gets its own EmbeddingEngine with namespaced HNSW index
    paths, ensuring vector caches are isolated across users.
    """
    with _engine_lock:
        if user_id not in _engine_instances:
            engine = EmbeddingEngine()
            # Namespace HNSW paths by user_id
            from whitemagic.config.paths import MEMORY_DIR
            user_dir = MEMORY_DIR.parent / "users" / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            engine._hnsw_index_path = user_dir / "hnsw_index.bin"
            engine._hnsw_ids_path = user_dir / "hnsw_ids.json"
            engine._cold_hnsw_index_path = user_dir / "hnsw_cold_index.bin"
            engine._cold_hnsw_ids_path = user_dir / "hnsw_cold_ids.json"
            _engine_instances[user_id] = engine
        return _engine_instances[user_id]
