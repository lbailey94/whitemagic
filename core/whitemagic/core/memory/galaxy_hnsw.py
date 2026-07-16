"""Per-Galaxy HNSW Index Manager — isolated vector indices per galaxy.

Implements Phase 5 of the Memory & Cognitive Systems Strategy 2026.

Instead of a single global HNSW index, this module maintains separate
HNSW indices per galaxy. Benefits:
  - Smaller indices = faster search (sub-ms per galaxy)
  - Isolated corruption risk (one galaxy's corruption doesn't affect others)
  - Parallel search across galaxies with bounded concurrency
  - Cross-galaxy RRF merge of per-galaxy results

Usage:
    from whitemagic.core.memory.galaxy_hnsw import GalaxyHNSWManager

    manager = GalaxyHNSWManager()
    manager.add_to_galaxy("codex", memory_id, vector)
    results = manager.search_across_galaxies(query_vec, k=10)
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np

from whitemagic.config.paths import MEMORY_DIR

logger = logging.getLogger(__name__)

# Default parameters
DEFAULT_DIM = 384
DEFAULT_M = 16
DEFAULT_EF_CONSTRUCTION = 200
DEFAULT_EF_SEARCH = 50
MAX_WORKERS = 4


class GalaxyHNSWManager:
    """Manages per-galaxy HNSW indices.

    Each galaxy gets its own HNSW index file, enabling:
      - Isolated search (search one galaxy)
      - Federated search (search multiple galaxies in parallel)
      - Cross-galaxy RRF merge
    """

    def __init__(
        self,
        dim: int = DEFAULT_DIM,
        m: int = DEFAULT_M,
        ef_construction: int = DEFAULT_EF_CONSTRUCTION,
        base_path: Path | None = None,
    ) -> None:
        self._dim = dim
        self._m = m
        self._ef_construction = ef_construction
        self._base_path = base_path or MEMORY_DIR / "galaxy_hnsw"
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._indices: dict[str, Any] = {}
        self._lock = threading.RLock()

    def _get_or_create_index(self, galaxy: str) -> Any:
        """Get or create an HNSW index for a galaxy."""
        with self._lock:
            if galaxy in self._indices:
                return self._indices[galaxy]

            try:
                from whitemagic.core.memory.hnsw_index import HNSWIndex

                index_path = self._base_path / f"hnsw_{galaxy}.pkl"
                index = HNSWIndex(
                    dim=self._dim,
                    m=self._m,
                    ef_construction=self._ef_construction,
                    db_path=index_path,
                )
                self._indices[galaxy] = index
                return index
            except Exception as e:
                logger.warning("Failed to create HNSW index for galaxy %s: %s", galaxy, e)
                return None

    def add_to_galaxy(
        self,
        galaxy: str,
        memory_id: str,
        vector: np.ndarray | list[float],
    ) -> bool:
        """Add a vector to a galaxy's HNSW index.

        Args:
            galaxy: Galaxy name
            memory_id: Memory ID
            vector: Embedding vector

        Returns:
            True if added successfully.
        """
        index = self._get_or_create_index(galaxy)
        if index is None:
            return False

        try:
            vec = np.array(vector, dtype=np.float32)
            index.add_item(memory_id, vec)
            return True
        except Exception as e:
            logger.debug("Failed to add item to galaxy %s HNSW: %s", galaxy, e)
            return False

    def search_galaxy(
        self,
        galaxy: str,
        query_vector: np.ndarray | list[float],
        k: int = 10,
        ef: int = DEFAULT_EF_SEARCH,
    ) -> list[tuple[str, float]]:
        """Search a single galaxy's HNSW index.

        Args:
            galaxy: Galaxy name
            query_vector: Query embedding
            k: Number of results
            ef: Search parameter (higher = more accurate, slower)

        Returns:
            List of (memory_id, similarity_score) tuples.
        """
        index = self._get_or_create_index(galaxy)
        if index is None:
            return []

        try:
            vec = np.array(query_vector, dtype=np.float32)
            return index.search(vec, k=k, ef=ef)
        except Exception as e:
            logger.debug("Galaxy HNSW search failed for %s: %s", galaxy, e)
            return []

    def search_across_galaxies(
        self,
        query_vector: np.ndarray | list[float],
        galaxies: list[str] | None = None,
        k: int = 10,
        ef: int = DEFAULT_EF_SEARCH,
        max_workers: int = MAX_WORKERS,
    ) -> dict[str, list[tuple[str, float]]]:
        """Search multiple galaxies in parallel.

        Args:
            query_vector: Query embedding
            galaxies: List of galaxy names. If None, searches all loaded.
            k: Results per galaxy
            ef: Search parameter
            max_workers: Max parallel searches

        Returns:
            Dict mapping galaxy name to list of (memory_id, score) tuples.
        """
        if galaxies is None:
            galaxies = list(self._indices.keys())

        if not galaxies:
            return {}

        results: dict[str, list[tuple[str, float]]] = {}

        with ThreadPoolExecutor(max_workers=min(len(galaxies), max_workers)) as executor:
            futures = {
                executor.submit(self.search_galaxy, g, query_vector, k, ef): g
                for g in galaxies
            }
            for future in as_completed(futures):
                galaxy = futures[future]
                try:
                    results[galaxy] = future.result()
                except Exception as e:
                    logger.debug("Galaxy search failed for %s: %s", galaxy, e)
                    results[galaxy] = []

        return results

    def cross_galaxy_rrf(
        self,
        query_vector: np.ndarray | list[float],
        galaxies: list[str] | None = None,
        k: int = 10,
        ef: int = DEFAULT_EF_SEARCH,
        rrf_k: int = 60,
    ) -> list[tuple[str, float]]:
        """Cross-galaxy search with Reciprocal Rank Fusion.

        Searches each galaxy in parallel, then merges results using RRF.

        Args:
            query_vector: Query embedding
            galaxies: Galaxies to search (None = all)
            k: Final number of results
            ef: HNSW search parameter
            rrf_k: RRF constant

        Returns:
            Fused list of (memory_id, rrf_score) tuples, sorted by score.
        """
        per_galaxy = self.search_across_galaxies(
            query_vector, galaxies=galaxies, k=k * 3, ef=ef,
        )

        # RRF fusion
        rrf_scores: dict[str, float] = {}
        for galaxy, hits in per_galaxy.items():
            for rank, (mid, _score) in enumerate(hits):
                rrf_scores[mid] = rrf_scores.get(mid, 0.0) + 1.0 / (rrf_k + rank + 1)

        # Sort by RRF score
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:k]

    def save_galaxy(self, galaxy: str) -> bool:
        """Save a galaxy's HNSW index to disk."""
        index = self._indices.get(galaxy)
        if index is None:
            return False
        try:
            index.save()
            return True
        except Exception as e:
            logger.debug("Failed to save galaxy %s HNSW: %s", galaxy, e)
            return False

    def save_all(self) -> dict[str, bool]:
        """Save all loaded galaxy indices."""
        results: dict[str, bool] = {}
        for galaxy in list(self._indices.keys()):
            results[galaxy] = self.save_galaxy(galaxy)
        return results

    def stats(self) -> dict[str, Any]:
        """Get statistics for all loaded galaxy indices."""
        stats: dict[str, Any] = {}
        for galaxy, index in self._indices.items():
            try:
                stats[galaxy] = {
                    "size": len(index),
                    "dim": index.dim if hasattr(index, "dim") else self._dim,
                }
            except Exception:
                stats[galaxy] = {"size": 0, "error": "unknown"}
        return stats


# Singleton
_instance: GalaxyHNSWManager | None = None
_lock = threading.RLock()


def get_galaxy_hnsw_manager() -> GalaxyHNSWManager:
    """Get the global GalaxyHNSWManager singleton."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = GalaxyHNSWManager()
    return _instance
