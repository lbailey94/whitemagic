# ruff: noqa: BLE001
# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Memory Vector Subsystem (Consolidated v2.0 — No Longer Stub).
==============================================================
Delegates to real implementations in embeddings.py, vector_search.py,
hnsw_index.py, and umap_projection.py.

Part of Milestone 4.3 Singleton Reduction — updated to wire to real engines.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    """Generates and manages vector embeddings for memories.

    Delegates to the full EmbeddingEngine from embeddings.py.
    """
    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                from whitemagic.core.memory.embeddings import (
                    get_embedding_engine as _get_real_engine,
                )
                self._engine = _get_real_engine()
            except Exception as e:
                logger.warning("Real EmbeddingEngine unavailable: %s", e, exc_info=True)
                self._engine = None
        return self._engine

    def embed_text(self, text: str) -> list[float]:
        """
        Perform the embed text operation.

        Args:
            text: Parameter description.

        Returns:
            list[float]
        """
        engine = self._get_engine()
        if engine:
            return engine.encode(text)
        # Graceful fallback: deterministic hash-based vector
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        return [(b - 128) / 128.0 for b in h[:384]]

    def encode(self, text: str) -> list[float]:
        """
        Perform the encode operation.

        Args:
            text: Parameter description.

        Returns:
            list[float]
        """
        return self.embed_text(text)

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Perform the encode batch operation.

        Args:
            texts: Parameter description.

        Returns:
            list[list[float]]
        """
        engine = self._get_engine()
        if engine:
            return engine.encode_batch(texts)
        return [self.embed_text(t) for t in texts]

    def search_similar(self, query: str, limit: int = 10, include_cold: bool = False) -> list[dict]:
        """
        Find similar matching the criteria.

        Args:
            query: Parameter description.
            limit: Parameter description.
            include_cold: Parameter description.

        Returns:
            list[dict]
        """
        engine = self._get_engine()
        if engine:
            return engine.search_similar(query, limit=limit, include_cold=include_cold)
        return []

    def index_memories(self, memory_type: str = "LONG_TERM", batch_size: int = 100) -> int:
        """
        Perform the index memories operation.

        Args:
            memory_type: Parameter description.
            batch_size: Parameter description.

        Returns:
            int
        """
        engine = self._get_engine()
        if engine:
            return engine.index_memories(memory_type=memory_type, batch_size=batch_size)
        return 0

class VectorSearch:
    """Performs similarity search across embedded memories.

    Delegates to the full VectorSearch from vector_search.py.
    """
    def __init__(self):
        self._search = None

    def _get_search(self):
        if self._search is None:
            try:
                from whitemagic.core.memory.vector_search import (
                    VectorSearch as RealSearch,
                )
                self._search = RealSearch()
            except Exception as e:
                logger.warning("Real VectorSearch unavailable: %s", e, exc_info=True)
                self._search = None
        return self._search

    def search(self, query_vec: list[float], limit: int = 10) -> list[tuple[str, float]]:
        """
        Perform the search operation.

        Args:
            query_vec: Parameter description.
            limit: Parameter description.

        Returns:
            list[tuple[str, float]]
        """
        search = self._get_search()
        if search:
            return search.search(query_vec, limit=limit)
        return []

    def search_by_text(self, query: str, limit: int = 10) -> list[dict]:
        """
        Find by text matching the criteria.

        Args:
            query: Parameter description.
            limit: Parameter description.

        Returns:
            list[dict]
        """
        search = self._get_search()
        if search:
            return search.search_by_text(query, limit=limit)
        return []

class HNSWIndex:
    """In-memory HNSW index for fast vector retrieval.

    Delegates to the full HNSWIndex from hnsw_index.py.
    """
    def __init__(self, dim: int = 384):
        self._index = None
        self.dim = dim
        self.nodes: dict = {}

    def _get_index(self):
        if self._index is None:
            try:
                from whitemagic.core.memory.hnsw_index import HNSWIndex as RealIndex
                self._index = RealIndex(dim=self.dim)
            except Exception as e:
                logger.warning("Real HNSWIndex unavailable: %s", e, exc_info=True)
                self._index = None
        return self._index

    def add(self, id: str, vec: list[float]):
        """
        Perform the add operation.

        Args:
            id: Parameter description.
            vec: Parameter description.
        """
        self.nodes[id] = vec
        index = self._get_index()
        if index:
            index.add(id, vec)

    def search(self, vec: list[float], k: int = 10) -> list[tuple[str, float]]:
        """
        Perform the search operation.

        Args:
            vec: Parameter description.
            k: Parameter description.

        Returns:
            list[tuple[str, float]]
        """
        index = self._get_index()
        if index:
            return index.search(vec, k=k)
        # Brute-force fallback
        import math
        scores = []
        for mid, node_vec in self.nodes.items():
            dot = sum(a * b for a, b in zip(vec, node_vec))
            norm_a = math.sqrt(sum(a * a for a in vec))
            norm_b = math.sqrt(sum(b * b for b in node_vec))
            if norm_a > 0 and norm_b > 0:
                scores.append((mid, dot / (norm_a * norm_b)))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

_embeddings: EmbeddingEngine | None = None
_search: VectorSearch | None = None

def get_embedding_engine() -> EmbeddingEngine:
    """
    Get the embedding engine.

    Returns:
        EmbeddingEngine
    """
    global _embeddings
    if _embeddings is None:
        _embeddings = EmbeddingEngine()
    return _embeddings

def get_vector_search() -> VectorSearch:
    """
    Get the vector search.

    Returns:
        VectorSearch
    """
    global _search
    if _search is None:
        _search = VectorSearch()
    return _search
