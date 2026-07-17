# ruff: noqa: BLE001
"""Spreading Activation Engine — Cross-Galaxy Memory Priming.

================================================================
Implements biologically-inspired spreading activation across the
galactic memory system. When a memory is recalled (or "thought about"),
activation spreads to its associative neighbors across galaxy boundaries,
priming them for future recall. This mirrors hippocampal-cortical
spreading activation in biological memory.

Activation Model:
    1. Seed memories receive initial activation (1.0)
    2. Activation spreads along association edges, decaying by:
       - Edge strength (biological: synaptic weight)
       - Galaxy affinity (same-galaxy > cross-galaxy, modulated by
         a cross-galaxy bridge factor)
       - Distance penalty (hops from seed)
       - Decay rate (biological: exponential decay)
    3. Activation accumulates in a priority queue
    4. Memories above threshold are "primed" — their recall_count
       and neuro_score are boosted, making them more likely to
       appear in future searches

Usage:
    from whitemagic.core.memory.spreading_activation import get_spreading_activation

    engine = get_spreading_activation()
    result = engine.spread(
        seed_ids=["mem-1", "mem-2"],
        max_hops=3,
        decay=0.7,
        cross_galaxy_factor=0.5,
    )
    # result.primed contains memories activated by spreading
"""

from __future__ import annotations

import heapq
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from whitemagic.core.memory.db_manager import safe_connect

logger = logging.getLogger(__name__)


@dataclass
class ActivationNode:
    """A single node in the activation spreading graph."""

    memory_id: str
    activation: float
    hop: int
    galaxy: str = ""
    title: str = ""
    source_galaxy: str = ""  # Galaxy of the seed that activated this
    path: list[str] = field(default_factory=list)  # Traversal path

    def __lt__(self, other: ActivationNode) -> bool:
        # Higher activation = higher priority (min-heap, so negate)
        return self.activation > other.activation


@dataclass
class SpreadResult:
    """Result of a spreading activation pass."""

    seed_ids: list[str]
    primed: list[ActivationNode]
    total_activated: int = 0
    cross_galaxy_links: int = 0
    galaxies_reached: set[str] = field(default_factory=set)
    duration_ms: float = 0.0
    max_activation: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_ids": self.seed_ids,
            "total_activated": self.total_activated,
            "cross_galaxy_links": self.cross_galaxy_links,
            "galaxies_reached": sorted(self.galaxies_reached),
            "duration_ms": round(self.duration_ms, 2),
            "max_activation": round(self.max_activation, 4),
            "primed": [
                {
                    "memory_id": n.memory_id,
                    "activation": round(n.activation, 4),
                    "hop": n.hop,
                    "galaxy": n.galaxy,
                    "title": n.title[:80] if n.title else "",
                    "source_galaxy": n.source_galaxy,
                }
                for n in self.primed
            ],
        }


class SpreadingActivation:
    """Cross-galaxy spreading activation engine.

    Activation spreads from seed memories through the association graph,
    crossing galaxy boundaries via cross-galaxy association edges.
    The engine uses a best-first search (priority queue) with
    exponential decay, modulated by edge strength and galaxy affinity.
    """

    def __init__(
        self,
        decay: float = 0.7,
        cross_galaxy_factor: float = 0.5,
        min_activation: float = 0.05,
        max_nodes: int = 200,
        max_hops: int = 3,
    ) -> None:
        self._decay = decay
        self._cross_galaxy_factor = cross_galaxy_factor
        self._min_activation = min_activation
        self._max_nodes = max_nodes
        self._max_hops = max_hops
        self._lock = threading.RLock()
        self._total_spreads = 0
        self._total_nodes_activated = 0
        self._total_cross_galaxy = 0
        self._mem_galaxy_cache: dict[str, tuple[str, str]] = {}  # mid -> (galaxy, title)
        self._cache_built = False

    def _build_mem_galaxy_cache(self, galaxy_db_paths: dict[str, str]) -> None:
        """Build a memory_id -> (galaxy, title) index from all galaxy DBs."""
        if self._cache_built and self._mem_galaxy_cache:
            return
        self._mem_galaxy_cache.clear()
        for galaxy_name, db_path in galaxy_db_paths.items():
            try:
                conn = safe_connect(db_path, timeout=5)
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT id, title FROM memories").fetchall()
                for r in rows:
                    self._mem_galaxy_cache[r["id"]] = (galaxy_name, r["title"] or "")
                conn.close()
            except Exception as e:
                logger.debug("Cache build failed for %s: %s", galaxy_name, e)
        self._cache_built = True
        logger.debug("Mem-galaxy cache: %d entries", len(self._mem_galaxy_cache))

    def spread(
        self,
        seed_ids: list[str],
        galaxy_db_paths: dict[str, str] | None = None,
        max_hops: int | None = None,
        decay: float | None = None,
        cross_galaxy_factor: float | None = None,
        min_activation: float | None = None,
    ) -> SpreadResult:
        """Spread activation from seed memories through the association graph.

        Args:
            seed_ids: Memory IDs to start activation from.
            galaxy_db_paths: Map of galaxy_name → db_path for cross-galaxy traversal.
                If None, only searches the default DB.
            max_hops: Maximum hops from seeds. Overrides default.
            decay: Activation decay per hop. Overrides default.
            cross_galaxy_factor: Multiplier for cross-galaxy edges. Overrides default.
            min_activation: Minimum activation to continue spreading. Overrides default.

        Returns:
            SpreadResult with primed memories and statistics.
        """
        start_time = time.time()
        hops = max_hops or self._max_hops
        d = decay if decay is not None else self._decay
        cgf = cross_galaxy_factor if cross_galaxy_factor is not None else self._cross_galaxy_factor
        threshold = min_activation if min_activation is not None else self._min_activation

        # Build memory→galaxy cache for fast lookups
        if galaxy_db_paths:
            self._build_mem_galaxy_cache(galaxy_db_paths)

        # Priority queue: (-activation, counter, node)
        # Using negative activation because heapq is a min-heap
        queue: list[tuple[float, int, ActivationNode]] = []
        counter = 0

        # Track visited and their max activation
        visited: dict[str, float] = {}
        primed: list[ActivationNode] = []
        galaxies_reached: set[str] = set()
        cross_galaxy_links = 0

        # Initialize seeds
        seed_galaxies: dict[str, str] = {}
        for sid in seed_ids:
            galaxy, title = self._lookup_memory(sid, galaxy_db_paths)
            seed_galaxies[sid] = galaxy
            galaxies_reached.add(galaxy)
            node = ActivationNode(
                memory_id=sid,
                activation=1.0,
                hop=0,
                galaxy=galaxy,
                title=title,
                source_galaxy=galaxy,
                path=[sid],
            )
            visited[sid] = 1.0
            heapq.heappush(queue, (-1.0, counter, node))
            counter += 1

        # Best-first spreading
        while queue and len(primed) < self._max_nodes:
            neg_act, _, node = heapq.heappop(queue)
            current_activation = -neg_act

            if current_activation < threshold:
                continue

            if node.hop > 0:
                primed.append(node)

            if node.hop >= hops:
                continue

            # Get neighbors from all galaxy DBs
            neighbors = self._get_neighbors_cross_galaxy(
                node.memory_id,
                node.galaxy,
                galaxy_db_paths,
            )

            for nid, strength, n_galaxy, n_title in neighbors:
                # Calculate activation
                edge_factor = strength
                galaxy_factor = 1.0 if n_galaxy == node.galaxy else cgf
                new_activation = current_activation * d * edge_factor * galaxy_factor

                if new_activation < threshold:
                    continue

                # Check if already visited with higher activation
                if nid in visited and visited[nid] >= new_activation:
                    continue

                visited[nid] = new_activation
                galaxies_reached.add(n_galaxy)

                if n_galaxy != node.galaxy:
                    cross_galaxy_links += 1

                new_node = ActivationNode(
                    memory_id=nid,
                    activation=new_activation,
                    hop=node.hop + 1,
                    galaxy=n_galaxy,
                    title=n_title,
                    source_galaxy=seed_galaxies.get(node.memory_id, node.galaxy),
                    path=node.path + [nid],
                )
                heapq.heappush(queue, (-new_activation, counter, new_node))
                counter += 1

        # Sort primed by activation (descending)
        primed.sort(key=lambda n: n.activation, reverse=True)

        duration = (time.time() - start_time) * 1000
        max_act = primed[0].activation if primed else 0.0

        with self._lock:
            self._total_spreads += 1
            self._total_nodes_activated += len(primed)
            self._total_cross_galaxy += cross_galaxy_links

        return SpreadResult(
            seed_ids=seed_ids,
            primed=primed,
            total_activated=len(primed),
            cross_galaxy_links=cross_galaxy_links,
            galaxies_reached=galaxies_reached,
            duration_ms=duration,
            max_activation=max_act,
        )

    def _lookup_memory(
        self,
        memory_id: str,
        galaxy_db_paths: dict[str, str] | None,
    ) -> tuple[str, str]:
        """Look up a memory's galaxy and title across all galaxy DBs."""
        # Fast path: check cache first
        if self._cache_built and memory_id in self._mem_galaxy_cache:
            return self._mem_galaxy_cache[memory_id]
        if galaxy_db_paths:
            for galaxy_name, db_path in galaxy_db_paths.items():
                try:
                    conn = safe_connect(db_path, timeout=5)
                    conn.row_factory = sqlite3.Row
                    row = conn.execute(
                        "SELECT title FROM memories WHERE id = ?", (memory_id,)
                    ).fetchone()
                    conn.close()
                    if row:
                        result = (galaxy_name, row["title"] or "")
                        self._mem_galaxy_cache[memory_id] = result
                        return result
                except Exception:
                    logger.debug("Ignored error in spreading_activation.py:278")
        return "", ""

    def _get_neighbors_cross_galaxy(
        self,
        memory_id: str,
        current_galaxy: str,
        galaxy_db_paths: dict[str, str] | None,
    ) -> list[tuple[str, float, str, str]]:
        """Get association neighbors from all galaxy DBs.

        Searches all galaxy databases for association edges involving this memory.
        Resolves the actual galaxy of each neighbor by checking which DB contains it.

        Returns list of (neighbor_id, strength, galaxy_name, title).
        """
        neighbors: list[tuple[str, float, str, str]] = []

        if not galaxy_db_paths:
            return neighbors

        # Collect all raw neighbor IDs from all DBs
        raw_neighbors: list[tuple[str, float, str]] = []  # (id, strength, source_db_galaxy)
        for galaxy_name, db_path in galaxy_db_paths.items():
            try:
                conn = safe_connect(db_path, timeout=5)
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """SELECT a.target_id as nid, a.strength
                       FROM associations a
                       WHERE a.source_id = ? AND a.strength >= 0.1
                       UNION
                       SELECT a.source_id as nid, a.strength
                       FROM associations a
                       WHERE a.target_id = ? AND a.strength >= 0.1
                       ORDER BY strength DESC LIMIT 30""",
                    (memory_id, memory_id),
                ).fetchall()
                for r in rows:
                    raw_neighbors.append((r["nid"], r["strength"], galaxy_name))
                conn.close()
            except Exception as e:
                logger.debug("Spreading activation neighbor lookup failed: %s", e)

        # Resolve each neighbor's actual galaxy and title
        for nid, strength, found_in_galaxy in raw_neighbors:
            resolved_galaxy = ""
            resolved_title = ""
            # Fast path: check cache
            if self._cache_built and nid in self._mem_galaxy_cache:
                resolved_galaxy, resolved_title = self._mem_galaxy_cache[nid]
            else:
                for galaxy_name, db_path in galaxy_db_paths.items():
                    try:
                        conn = safe_connect(db_path, timeout=5)
                        conn.row_factory = sqlite3.Row
                        row = conn.execute(
                            "SELECT title FROM memories WHERE id = ?", (nid,)
                        ).fetchone()
                        conn.close()
                        if row:
                            resolved_galaxy = galaxy_name
                            resolved_title = row["title"] or ""
                            self._mem_galaxy_cache[nid] = (resolved_galaxy, resolved_title)
                            break
                    except Exception:
                        logger.debug("Ignored error in spreading_activation.py:339")

            # If not found in any galaxy, use the galaxy where the association was found
            if not resolved_galaxy:
                resolved_galaxy = found_in_galaxy

            neighbors.append((nid, strength, resolved_galaxy, resolved_title))

        return neighbors

    def apply_priming(
        self,
        result: SpreadResult,
        galaxy_db_paths: dict[str, str] | None = None,
    ) -> int:
        """Apply priming effects to memories — boost neuro_score and recall_count.

        Args:
            result: SpreadResult from a spread() call.
            galaxy_db_paths: Map of galaxy_name → db_path.

        Returns:
            Number of memories primed.
        """
        if not galaxy_db_paths:
            return 0

        primed_count = 0
        for node in result.primed:
            db_path = galaxy_db_paths.get(node.galaxy)
            if not db_path:
                continue
            try:
                conn = safe_connect(db_path, timeout=5)
                # Boost neuro_score by activation amount (Hebbian strengthening)
                boost = node.activation * 0.1  # 10% of activation
                conn.execute(
                    """UPDATE memories
                       SET neuro_score = MIN(1.0, COALESCE(neuro_score, 1.0) + ?),
                           recall_count = COALESCE(recall_count, 0) + 1
                       WHERE id = ?""",
                    (boost, node.memory_id),
                )
                conn.commit()
                conn.close()
                primed_count += 1
            except Exception as e:
                logger.debug("Priming failed for %s: %s", node.memory_id, e)

        return primed_count

    def stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        with self._lock:
            return {
                "total_spreads": self._total_spreads,
                "total_nodes_activated": self._total_nodes_activated,
                "total_cross_galaxy_links": self._total_cross_galaxy,
                "decay": self._decay,
                "cross_galaxy_factor": self._cross_galaxy_factor,
                "min_activation": self._min_activation,
                "max_hops": self._max_hops,
            }


# Singleton
_instance: SpreadingActivation | None = None
_lock = threading.RLock()


def get_spreading_activation() -> SpreadingActivation:
    """Get the global SpreadingActivation singleton."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = SpreadingActivation()
    return _instance
