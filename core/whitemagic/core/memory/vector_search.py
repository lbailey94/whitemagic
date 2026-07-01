# ruff: noqa: BLE001
"""Vector Memory Search — Embedding-based similarity search.
Uses sentence-transformers if available, TF-IDF fallback otherwise.
Stores embeddings in SQLite. In-memory brute-force cosine search.
"""
from __future__ import annotations

import hashlib
import importlib.util
import logging
import math
import os
import sqlite3
import struct
import threading
from collections import Counter
from dataclasses import dataclass
from typing import Any, cast

from whitemagic.config.paths import DB_PATH, MEMORY_DIR

logger = logging.getLogger(__name__)
_sbert_model = None
_sbert_lock = threading.Lock()
_sbert_init_attempted = False
_sbert_error: str | None = None
_sbert_class: Any | None = None
_has_sbert_package: bool | None = None


def _has_sbert() -> bool:
    global _has_sbert_package
    if _has_sbert_package is None:
        _has_sbert_package = importlib.util.find_spec("sentence_transformers") is not None
    return bool(_has_sbert_package)


def _allow_remote_model_download() -> bool:
    raw = os.environ.get("WM_ALLOW_MODEL_DOWNLOAD", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _get_sbert() -> Any:
    global _sbert_model, _sbert_error, _sbert_init_attempted, _sbert_class
    if _sbert_model is None and _has_sbert() and not _sbert_init_attempted:
        with _sbert_lock:
            if _sbert_model is None and not _sbert_init_attempted:
                _sbert_init_attempted = True
                name = os.environ.get("WM_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
                try:
                    if _sbert_class is None:
                        from sentence_transformers import (
                            SentenceTransformer as _SentenceTransformer,
                        )
                        _sbert_class = _SentenceTransformer
                    kwargs: dict[str, Any] = {}
                    if not _allow_remote_model_download():
                        kwargs["local_files_only"] = True
                    _sbert_model = _sbert_class(name, **kwargs)
                    _sbert_error = None
                except Exception as exc:
                    _sbert_error = str(exc)
                    logger.info("SBERT unavailable; using TF-IDF fallback: %s", exc)
    return _sbert_model

class TFIDFEmbedder:
    """TFIDFEmbedder: tfidf embedder."""
    def __init__(self, dim: int = 256) -> None: self._dim = dim
    def _tok(self, t: str) -> list[str]: return [w.strip(".,!?;:'\"()[]{}") for w in t.lower().split() if len(w)>2]
    def _h(self, t: str) -> int: return int(hashlib.md5(t.encode()).hexdigest(),16) % self._dim
    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        Perform the encode operation.

        Args:
            texts: Parameter description.

        Returns:
            list[list[float]]
        """
        out = []
        for t in texts:
            tf = Counter(self._tok(t))
            v=[0.0]*self._dim
            for tok,c in tf.items():
                v[self._h(tok)]+=c
            n=math.sqrt(sum(x*x for x in v))
            out.append([x/n for x in v] if n>0 else v)
        return out

def _cosine(a: list[float], b: list[float]) -> float:
    try:
        from whitemagic.core.acceleration.simd_cosine import (
            cosine_similarity as _simd_cos,
        )
        return cast(float, _simd_cos(a, b))
    except (ImportError, AttributeError):
        pass
    d=sum(x*y for x,y in zip(a,b))
    na=math.sqrt(sum(x*x for x in a))
    nb=math.sqrt(sum(x*x for x in b))
    return d/(na*nb) if na>0 and nb>0 else 0.0

@dataclass
class VSearchResult:
    """VSearchResult: v search result.

    Value object: equality and repr are field-based."""
    memory_id: str
    score: float
    title: str=""
    snippet: str=""
    """
    Convert to/from dict.

    Returns:
        dict[str, Any]
    """
    """
    Convert to/from dict.

    Returns:
        dict[str, Any]
    """
    def to_dict(self) -> dict[str, Any]: return {"memory_id":self.memory_id,"score":round(self.score,4),"title":self.title,"snippet":self.snippet[:200]}

class VectorSearch:
    """VectorSearch: vector search."""
    def __init__(self, db_path: str | None = None) -> None:
        self._lock = threading.Lock()
        self._db = db_path or str(MEMORY_DIR / "embeddings.db")
        self._tfidf = TFIDFEmbedder()
        self._cache: dict[str,list[float]] = {}
        self._meta: dict[str,dict[str,str]] = {}
        self._init_db()
        self._load()

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self._db),exist_ok=True)
        with sqlite3.connect(self._db) as c:
            c.execute("CREATE TABLE IF NOT EXISTS embeddings(memory_id TEXT PRIMARY KEY,vector BLOB,title TEXT DEFAULT '',snippet TEXT DEFAULT '')")

    def _load(self) -> None:
        try:
            with sqlite3.connect(self._db) as c:
                for mid,vb,t,s in c.execute("SELECT memory_id,vector,title,snippet FROM embeddings"):
                    n=len(vb)//4
                    vec=list(struct.unpack(f"{n}f",vb))
                    self._cache[mid]=vec
                    self._meta[mid]={"title":t or "","snippet":s or ""}
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass

    def _encode(self, texts: list[str]) -> list[list[float]]:
        m=_get_sbert()
        if m:
            return [e.tolist() for e in m.encode(texts,show_progress_bar=False)]
        return self._tfidf.encode(texts)

    def index_memory(self, memory_id: str, content: str, title: str = "") -> None:
        """
        Perform the index memory operation.

        Args:
            memory_id: Parameter description.
            content: Parameter description.
            title: Parameter description.

        Returns:
            None
        """
        vecs = self._encode([content[:5000]])
        vec = vecs[0]
        blob = struct.pack(f"{len(vec)}f",*vec)
        snip = content[:300]
        with sqlite3.connect(self._db) as c:
            c.execute("INSERT OR REPLACE INTO embeddings(memory_id,vector,title,snippet) VALUES(?,?,?,?)",(memory_id,blob,title,snip))
        with self._lock:
            self._cache[memory_id]=vec
            self._meta[memory_id]={"title":title,"snippet":snip}

            import numpy as np
            # Sync to Koka SHM Engine
            try:
                from whitemagic.core.memory.shm_manager import get_shm_manager
                shm = get_shm_manager()
                shm.add_or_update(memory_id, np.array(vec, dtype=np.float32))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Failed to sync embedding to SHM: %s", e)

    def search(self, query: str, limit: int = 10) -> list[VSearchResult]:
            """
            Perform the search operation.

            Args:
                query: Parameter description.
                limit: Parameter description.

            Returns:
                list[VSearchResult]
            """
            qvec = self._encode([query])[0]
            scored = []

            # 1. Try Koka Shared Memory Bridge (Native C AVX2) - Fastest!
            try:
                from whitemagic.core.acceleration.koka_native_bridge import (
                    get_koka_bridge,
                )
                from whitemagic.core.memory.shm_manager import get_shm_manager

                shm = get_shm_manager()
                bridge = get_koka_bridge()

                # Ensure DB is loaded into SHM if not already
                if shm.get_count() == 0:
                    from whitemagic.core.memory.db_manager import get_db_pool

                    pool = get_db_pool(str(DB_PATH))
                    shm.sync_from_db(pool)

                if bridge.is_available("shm_search") and shm.get_count() > 0:
                    import numpy as np
                    # We need to write the query vector into the SHM segment
                    # We'll use index count + 1 as the temporary query slot
                    query_idx = shm.get_count() + 1
                    shm.write_query(query_idx, np.array(qvec, dtype=np.float32))

                    # Dispatch to Koka
                    res = bridge.dispatch("shm_search", "search", {"query_id": query_idx})

                    if res and res.get("status") == "ok":
                        results: list[VSearchResult] = []
                        for item in res.get("results", []):
                            int_id = item["id"]
                            score = item["score"]

                            # Only return top limit
                            if len(results) >= limit:
                                break

                            # Lookup UUID from SHM manager
                            mem_id = shm.get_uuid(int_id)
                            if mem_id:
                                m = self._meta.get(mem_id, {})
                                results.append(
                                    VSearchResult(
                                        memory_id=mem_id,
                                        score=score,
                                        title=m.get("title", ""),
                                        snippet=m.get("snippet", "")
                                    )
                                )
                        if results:
                            return results
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Koka SHM Search failed, falling back to Python: %s", e)

            with self._lock:
                if len(self._cache) > 50:
                    try:
                        from whitemagic.core.acceleration.simd_vector_batch import (
                            batch_topk_cosine,
                        )
                        ids = list(self._cache.keys())
                        vecs = list(self._cache.values())
                        topk = batch_topk_cosine(qvec, vecs, limit)
                        scored = [(ids[idx], score) for idx, score in topk]
                    except (ImportError, AttributeError):
                        scored = []

                if not scored and len(self._cache) > 10:
                    try:
                        import numpy as np
                        import whitemagic_rs

                        ids = list(self._cache.keys())
                        vecs = list(self._cache.values())
                        query_arr = np.ascontiguousarray(qvec, dtype=np.float64)
                        candidates_arr = np.ascontiguousarray(vecs, dtype=np.float64)
                        similarities = whitemagic_rs.rust_batch_cosine_numpy(query_arr, candidates_arr)

                        if similarities is not None:
                            scored = [(ids[i], float(similarities[i])) for i in range(len(similarities))]
                            scored.sort(key=lambda x: x[1], reverse=True)
                    except Exception:
                        scored = []

                if not scored:
                    for mid,vec in self._cache.items():
                        s = _cosine(qvec, vec)
                        scored.append((mid, s))
                    scored.sort(key=lambda x:x[1], reverse=True)
            results = []
            for mid,s in scored[:
                limit]:
                m = self._meta.get(mid,{})
                results.append(VSearchResult(memory_id=mid,score=s,title=m.get("title",""),snippet=m.get("snippet","")))
            return results

    """
    Perform the index count operation.

    Returns:
        int
    """
    """
    Perform the index count operation.

    Returns:
        int
    """
    def index_count(self) -> int: return len(self._cache)

    def status(self) -> dict[str, Any]:
        """
        Perform the status operation.

        Returns:
            dict[str, Any]
        """
        return {
            "indexed": len(self._cache),
            "has_sbert": _has_sbert(),
            "sbert_loaded": _sbert_model is not None,
            "sbert_init_attempted": _sbert_init_attempted,
            "sbert_error": _sbert_error,
            "allow_model_download": _allow_remote_model_download(),
            "model": os.environ.get("WM_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            "db": self._db,
        }

_vs=None
_vs_lock=threading.Lock()
def get_vector_status() -> dict[str, Any]:
    """
    Get the vector status.

    Returns:
        dict[str, Any]
    """
    db = str(MEMORY_DIR / "embeddings.db")
    indexed = 0
    db_exists = os.path.exists(db)
    db_size_bytes = os.path.getsize(db) if db_exists else 0

    if _vs is not None:
        status = _vs.status()
        status["db_exists"] = db_exists
        status["db_size_bytes"] = db_size_bytes
        status["engine_initialized"] = True
        return status

    try:
        if db_exists:
            with sqlite3.connect(db) as c:
                row = c.execute("SELECT COUNT(*) FROM embeddings").fetchone()
                indexed = int(row[0]) if row else 0
    except Exception as e:
        logger.debug("Operation failed: %s", e)
        indexed = 0

    return {
        "indexed": indexed,
        "has_sbert": _has_sbert(),
        "sbert_loaded": _sbert_model is not None,
        "sbert_init_attempted": _sbert_init_attempted,
        "sbert_error": _sbert_error,
        "allow_model_download": _allow_remote_model_download(),
        "model": os.environ.get("WM_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        "db": db,
        "db_exists": db_exists,
        "db_size_bytes": db_size_bytes,
        "engine_initialized": False,
    }


def get_vector_search() -> VectorSearch:
    """
    Get the vector search.

    Returns:
        VectorSearch
    """
    global _vs
    if _vs is None:
        with _vs_lock:
            if _vs is None:
                _vs=VectorSearch()
    return _vs
