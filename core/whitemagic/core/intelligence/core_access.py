# ruff: noqa: BLE001
"""CoreAccessLayer — Unified Read Interface to the Holographic Galactic Core.
==========================================================================
Provides every insight engine a clean, shared API to query the full richness
of the Data Sea: constellations, associations, temporal patterns, holographic
neighbors, and hybrid recall (vector + graph RRF).

This is the *connective tissue* that lets PredictiveEngine, KaizenEngine,
SerendipityEngine, and EmergenceEngine tap the same data structures without
duplicating SQL queries or importing each other's internals.

Usage:
    from whitemagic.core.intelligence.core_access import get_core_access
    cal = get_core_access()

    # Constellation context for a set of tags or coordinates
    context = cal.query_constellation_context(tags=["rust", "acceleration"])

    # N-hop association subgraph from seed memories
    subgraph = cal.query_association_subgraph(["mem_abc123"], depth=2)

    # Time-bucketed activity metrics
    activity = cal.query_temporal_activity(time_window="7d")

    # KNN in 5D holographic space
    neighbors = cal.query_holographic_neighbors(coords=(0.1, -0.3, 0.2, 0.8, 0.6), k=20)

    # Hybrid recall: embedding similarity + association graph walk
    results = cal.hybrid_recall("memory consolidation architecture", k=10)
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, cast

logger = logging.getLogger(__name__)


@dataclass
class ConstellationContext:
    """Constellation query result."""

    name: str
    size: int
    centroid: tuple[float, float, float, float, float]
    dominant_tags: list[str]
    zone: str
    distance: float = 0.0  # Distance from query point (0 if tag-matched)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "name": self.name,
            "size": self.size,
            "centroid": {
                "x": self.centroid[0],
                "y": self.centroid[1],
                "z": self.centroid[2],
                "w": self.centroid[3],
                "v": self.centroid[4],
            },
            "dominant_tags": self.dominant_tags,
            "zone": self.zone,
            "distance": round(self.distance, 3),
        }


@dataclass
class AssociationNode:
    """A node in the association subgraph."""

    memory_id: str
    title: str | None = None
    strength: float = 0.0
    depth: int = 0  # Hop distance from seed

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "memory_id": self.memory_id,
            "title": self.title,
            "strength": round(self.strength, 3),
            "depth": self.depth,
        }


@dataclass
class TemporalBucket:
    """One time bucket of activity metrics."""

    period: str  # ISO date string for the bucket
    memories_created: int = 0
    memories_accessed: int = 0
    associations_created: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "period": self.period,
            "memories_created": self.memories_created,
            "memories_accessed": self.memories_accessed,
            "associations_created": self.associations_created,
        }


@dataclass
class HolographicNeighbor:
    """A memory found via holographic KNN."""

    memory_id: str
    title: str | None = None
    distance: float = 0.0
    coords: tuple[float, float, float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "memory_id": self.memory_id,
            "title": self.title,
            "distance": round(self.distance, 3),
        }


@dataclass
class HybridResult:
    """A result from hybrid recall (vector + graph fusion)."""

    memory_id: str
    title: str | None = None
    content_preview: str = ""
    score: float = 0.0
    sources: list[str] = field(default_factory=list)  # "vector", "graph", "both"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "memory_id": self.memory_id,
            "title": self.title,
            "content_preview": self.content_preview[:200],
            "score": round(self.score, 4),
            "sources": self.sources,
        }


class CoreAccessLayer:
    """Unified read interface to the holographic galactic core.

    Delegates to existing subsystems:
    - ConstellationDetector for constellation queries
    - SQLiteBackend for association graph + temporal queries
    - HolographicMemory for 5D KNN
    - EmbeddingEngine for semantic search
    - Association graph traversal for multi-hop reasoning
    """

    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None
        self._conn_injected: bool = False
        self._lock = threading.Lock()
        # HRR pre-filter cache
        self._hrr_cache_ids: list[str] | None = None
        self._hrr_cache_vecs: Any | None = None  # (N, dim) quantized uint8
        self._hrr_cache_count: int = 0
        self._hrr_cache_lock = threading.Lock()

    def _get_conn(self) -> sqlite3.Connection:
        """Lazy-init a read-only SQLite connection to the hot DB."""
        if self._conn is None:
            import os

            from whitemagic.config.paths import DB_PATH

            self._conn = sqlite3.connect(
                str(DB_PATH), timeout=30, check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row

            try:
                self._conn.enable_load_extension(True)
                ext_path_params = [
                    os.path.join(
                        os.path.dirname(__file__),
                        "../../../whitemagic-rust/target/release/libwhitemagic_rust.so",
                    ),
                ]
                for ext_path in ext_path_params:
                    if os.path.exists(ext_path):
                        self._conn.load_extension(ext_path)
                        logger.info(
                            "Successfully injected native SIMD SQLite extension: %s",
                            ext_path,
                        )
                        break
            except AttributeError:
                logger.warning(
                    "SQLite extension loading not available in this Python build (requires sqlite3 compiled with enable-load-extension)."
                )
            except (sqlite3.Error, sqlite3.OperationalError) as e:
                logger.debug(
                    "Could not load native SQLite SIMD extension: %s. Falling back to standard graph calculations.",
                    e,
                    exc_info=True,
                )
            finally:
                try:
                    self._conn.enable_load_extension(False)
                except (sqlite3.Error, sqlite3.OperationalError) as e:
                    logger.debug(
                        "Failed to disable load extension: %s", e, exc_info=True
                    )

            try:
                self._conn.execute("PRAGMA journal_mode = WAL")
                self._conn.execute("PRAGMA synchronous = NORMAL")
                self._conn.execute("PRAGMA busy_timeout = 30000")
            except (sqlite3.Error, sqlite3.OperationalError) as e:
                logger.debug("Failed to set PRAGMA busy_timeout: %s", e, exc_info=True)
        return self._conn

    def query_constellation_context(
        self,
        tags: list[str] | None = None,
        coords: tuple[float, float, float, float, float] | None = None,
        k: int = 5,
    ) -> list[ConstellationContext]:
        """Find constellations relevant to given tags or coordinates.

        If tags are provided, matches constellations whose dominant_tags
        overlap with the query tags. If coords are provided, finds the
        k nearest constellations by 5D distance. Both can be combined.
        """
        try:
            from whitemagic.core.memory.constellations import get_constellation_detector

            detector = get_constellation_detector()
            # Use TTL-cached detection (avoids re-running detect on every query)
            cached = detector.get_cached_or_detect(sample_limit=10000)
            report = cached.to_dict() if cached else None
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("Constellation query failed: %s", e, exc_info=True)
            return []

        if not report or not report.get("constellations"):
            return []

        raw_constellations = report["constellations"]
        results: list[ConstellationContext] = []

        for c in raw_constellations:
            centroid_dict = c.get("centroid", {})
            centroid = (
                centroid_dict.get("x", 0),
                centroid_dict.get("y", 0),
                centroid_dict.get("z", 0),
                centroid_dict.get("w", 0),
                centroid_dict.get("v", 0),
            )

            # Tag matching
            tag_score = 0.0
            if tags:
                overlap = set(tags) & set(c.get("dominant_tags", []))
                tag_score = len(overlap) / max(1, len(tags))

            # Coordinate distance
            coord_dist = float("inf")
            if coords:
                import math

                coord_dist = math.sqrt(
                    sum((a - b) ** 2 for a, b in zip(coords, centroid))
                )

            # Include if matches tags or is spatially close
            if tag_score > 0 or (coords and coord_dist < 2.0):
                results.append(
                    ConstellationContext(
                        name=c["name"],
                        size=c.get("size", 0),
                        centroid=centroid,
                        dominant_tags=c.get("dominant_tags", []),
                        zone=c.get("zone", "unknown"),
                        distance=coord_dist if coords else 0.0,
                    )
                )

        # Sort: tag matches first (by overlap), then by distance
        results.sort(
            key=lambda r: (-len(set(tags or []) & set(r.dominant_tags)), r.distance)
        )
        return results[:k]

    def get_all_constellations(self) -> list[ConstellationContext]:
        """Return all detected constellations (TTL-cached)."""
        try:
            from whitemagic.core.memory.constellations import get_constellation_detector

            detector = get_constellation_detector()
            cached = detector.get_cached_or_detect(sample_limit=10000)
            report = cached.to_dict() if cached else None
        except (ImportError, ModuleNotFoundError):
            return []

        if not report or not report.get("constellations"):
            return []

        results = []
        for c in report["constellations"]:
            cd = c.get("centroid", {})
            results.append(
                ConstellationContext(
                    name=c["name"],
                    size=c.get("size", 0),
                    centroid=(
                        cd.get("x", 0),
                        cd.get("y", 0),
                        cd.get("z", 0),
                        cd.get("w", 0),
                        cd.get("v", 0),
                    ),
                    dominant_tags=c.get("dominant_tags", []),
                    zone=c.get("zone", "unknown"),
                )
            )
        return results

    def query_association_subgraph(
        self,
        seed_ids: list[str],
        depth: int = 2,
        min_strength: float = 0.3,
        max_nodes: int = 50,
    ) -> list[AssociationNode]:
        """Walk N-hop association graph from seed memories.

        Returns nodes reachable within `depth` hops, filtered by
        minimum association strength. BFS traversal.

        Uses Rust rusqlite accelerator when available (single call,
        no Python↔SQLite round trips per hop). Falls back to Python BFS.
        """
        try:
            if self._conn_injected:
                raise RuntimeError("injected conn — use Python path")
            import whitemagic_rs
            from whitemagic.config.paths import DB_PATH

            walk_nodes = whitemagic_rs.association_walk(
                str(DB_PATH),
                seed_ids,
                depth,
                min_strength,
                max_nodes,
            )
            nodes = [
                AssociationNode(
                    memory_id=n.memory_id,
                    title=n.title or None,
                    strength=n.strength,
                    depth=n.depth,
                )
                for n in walk_nodes
            ]
            logger.debug("Association walk: Rust path (%d nodes)", len(nodes))
            return nodes
        except Exception as e:
            logger.debug("Failed to execute core access query: %s", e, exc_info=True)

        conn = self._get_conn()
        visited: dict[str, AssociationNode] = {}
        frontier = list(seed_ids)
        current_depth = 0

        for sid in seed_ids:
            try:
                row = conn.execute(
                    "SELECT id, title FROM memories WHERE id = ?", (sid,)
                ).fetchone()
                title = row["title"] if row else None
            except (sqlite3.Error, sqlite3.OperationalError):
                title = None
            visited[sid] = AssociationNode(
                memory_id=sid,
                title=title,
                strength=1.0,
                depth=0,
            )

        while current_depth < depth and frontier and len(visited) < max_nodes:
            current_depth += 1
            next_frontier = []

            # Batch all frontier association queries into one IN(...) query per depth level
            frontier_neighbors: dict[str, list[tuple[str, float]]] = {
                mid: [] for mid in frontier
            }
            if frontier:
                try:
                    ph = ",".join("?" * len(frontier))
                    frontier_list = list(frontier)
                    batch_rows = conn.execute(
                        f"""
                        SELECT source_id, target_id as neighbor_id, strength FROM associations
                        WHERE source_id IN ({ph}) AND strength >= ?
                        UNION
                        SELECT target_id as source_id, source_id as neighbor_id, strength FROM associations
                        WHERE target_id IN ({ph}) AND strength >= ?
                        ORDER BY strength DESC
                        """,
                        frontier_list + [min_strength] + frontier_list + [min_strength],
                    ).fetchall()
                    for r in batch_rows:
                        src = r["source_id"]
                        if src in frontier_neighbors:
                            frontier_neighbors[src].append(
                                (r["neighbor_id"], r["strength"])
                            )
                except Exception as e:
                    logger.debug(
                        "Failed to process frontier neighbors: %s", e, exc_info=True
                    )

            # Collect all new neighbor IDs, then batch-fetch titles (N+1 fix)
            new_nids = [
                nid
                for neighbors in frontier_neighbors.values()
                for nid, _ in neighbors
                if nid not in visited
            ]
            neighbor_titles: dict[str, str | None] = {}
            if new_nids:
                try:
                    ph = ",".join("?" * len(new_nids))
                    title_rows = conn.execute(
                        f"SELECT id, title FROM memories WHERE id IN ({ph})",
                        new_nids,
                    ).fetchall()
                    neighbor_titles = {r["id"]: r["title"] for r in title_rows}
                except (sqlite3.Error, sqlite3.OperationalError) as e:
                    logger.debug(
                        "Failed to resolve neighbor titles: %s", e, exc_info=True
                    )

            for neighbors in frontier_neighbors.values():
                for nid, strength in neighbors:
                    if nid not in visited and len(visited) < max_nodes:
                        visited[nid] = AssociationNode(
                            memory_id=nid,
                            title=neighbor_titles.get(nid),
                            strength=strength,
                            depth=current_depth,
                        )
                        next_frontier.append(nid)

            frontier = next_frontier

        # Update traversal tracking for edges we actually walked
        self._record_traversals(visited, conn)

        nodes = list(visited.values())
        nodes.sort(key=lambda n: (n.depth, -n.strength))
        return nodes

    def _record_traversals(
        self,
        visited: dict[str, AssociationNode],
        conn: sqlite3.Connection,
    ) -> None:
        """Update last_traversed_at and traversal_count for walked edges."""
        now = datetime.now().isoformat()
        try:
            batch_params: list[tuple[str, str, str]] = []
            for node in visited.values():
                if node.depth == 0:
                    continue  # Skip seeds
                batch_params.append((now, node.memory_id, node.memory_id))
            if batch_params:
                conn.executemany(
                    """
                    UPDATE associations
                    SET last_traversed_at = ?,
                        traversal_count = COALESCE(traversal_count, 0) + 1
                    WHERE (source_id = ? OR target_id = ?)
                    AND strength >= 0.3
                """,
                    batch_params,
                )
                conn.commit()
        except (sqlite3.Error, sqlite3.OperationalError) as e:
            logger.debug(
                "Non-critical commit error in core_access: %s", e, exc_info=True
            )

    def get_association_stats(self) -> dict[str, Any]:
        """Get association graph statistics."""
        conn = self._get_conn()
        try:
            row = conn.execute("""
                SELECT COUNT(*) as total,
                       AVG(strength) as avg_strength,
                       MIN(strength) as min_strength,
                       MAX(strength) as max_strength
                FROM associations
            """).fetchone()
            return {
                "total_associations": row["total"],
                "avg_strength": round(row["avg_strength"] or 0, 3),
                "min_strength": round(row["min_strength"] or 0, 3),
                "max_strength": round(row["max_strength"] or 0, 3),
            }
        except (sqlite3.Error, TypeError):
            return {"total_associations": 0}

    def find_broken_associations(self, limit: int = 20) -> list[dict[str, Any]]:
        """Find high-strength associations where one end has drifted to FAR_EDGE."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT a.source_id, a.target_id, a.strength,
                       m1.galactic_distance as src_distance,
                       m2.galactic_distance as tgt_distance,
                       m1.title as src_title, m2.title as tgt_title
                FROM associations a
                JOIN memories m1 ON a.source_id = m1.id
                JOIN memories m2 ON a.target_id = m2.id
                WHERE a.strength > 0.5
                AND (m1.galactic_distance > 0.85 OR m2.galactic_distance > 0.85)
                ORDER BY a.strength DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error:
            return []

    def query_temporal_activity(
        self,
        time_window: str = "7d",
        bucket: str = "1d",
    ) -> list[TemporalBucket]:
        """Time-bucketed memory creation and access metrics.

        Args:
            time_window: How far back to look ("7d", "30d", "90d")
            bucket: Bucket granularity ("1d", "7d")

        Returns list of TemporalBucket objects.
        """
        conn = self._get_conn()

        days = int(time_window.rstrip("d"))
        bucket_days = int(bucket.rstrip("d"))

        threshold = (datetime.now() - timedelta(days=days)).isoformat()

        try:
            # Memory creation by date
            rows = conn.execute(
                """
                SELECT DATE(created_at) as day, COUNT(*) as cnt
                FROM memories
                WHERE created_at > ?
                GROUP BY day ORDER BY day
            """,
                (threshold,),
            ).fetchall()

            creation_by_day: dict[str, int] = {r["day"]: r["cnt"] for r in rows}

            # Memory access by date
            access_rows = conn.execute(
                """
                SELECT DATE(accessed_at) as day, COUNT(*) as cnt
                FROM memories
                WHERE accessed_at > ? AND accessed_at IS NOT NULL
                GROUP BY day ORDER BY day
            """,
                (threshold,),
            ).fetchall()

            access_by_day: dict[str, int] = {r["day"]: r["cnt"] for r in access_rows}
        except sqlite3.Error:
            return []

        # Build buckets
        buckets: list[TemporalBucket] = []
        current = datetime.now() - timedelta(days=days)
        end = datetime.now()

        while current < end:
            bucket_end = current + timedelta(days=bucket_days)
            created = 0
            accessed = 0

            d = current
            while d < bucket_end and d <= end:
                day_str = d.strftime("%Y-%m-%d")
                created += creation_by_day.get(day_str, 0)
                accessed += access_by_day.get(day_str, 0)
                d += timedelta(days=1)

            buckets.append(
                TemporalBucket(
                    period=current.strftime("%Y-%m-%d"),
                    memories_created=created,
                    memories_accessed=accessed,
                )
            )
            current = bucket_end

        return buckets

    def get_velocity_metrics(self) -> dict[str, float]:
        """Calculate memory creation velocity metrics."""
        conn = self._get_conn()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN created_at > datetime('now', '-1 days') THEN 1 END) as last_1d,
                    COUNT(CASE WHEN created_at > datetime('now', '-7 days') THEN 1 END) as last_7d,
                    COUNT(CASE WHEN created_at > datetime('now', '-30 days') THEN 1 END) as last_30d
                FROM memories
            """).fetchone()

            last_7d = row["last_7d"]
            last_30d = row["last_30d"]
            acceleration = (
                (last_7d / 7) / max(0.01, last_30d / 30) if last_30d > 0 else 1.0
            )

            return {
                "total": row["total"],
                "last_1d": row["last_1d"],
                "last_7d": last_7d,
                "last_30d": last_30d,
                "daily_avg_7d": round(last_7d / 7, 1),
                "daily_avg_30d": round(last_30d / 30, 1),
                "acceleration": round(acceleration, 2),  # >1 = accelerating
            }
        except (sqlite3.Error, TypeError):
            return {"total": 0}

    def query_holographic_neighbors(
        self,
        coords: tuple[float, float, float, float, float],
        k: int = 20,
        include_cold: bool = False,
    ) -> list[HolographicNeighbor]:
        """KNN in 5D holographic space.

        Uses Zig SIMD accelerated distance when available, falls back
        to SQL-based brute force.
        """
        conn = self._get_conn()
        x, y, z, w, v = coords

        try:
            # SQL-based brute force with distance calculation
            rows = conn.execute(
                """
                SELECT hc.memory_id,
                       m.title,
                       hc.x, hc.y, hc.z, hc.w, hc.v,
                       ((hc.x - ?) * (hc.x - ?) +
                        (hc.y - ?) * (hc.y - ?) +
                        (hc.z - ?) * (hc.z - ?) +
                        (hc.w - ?) * (hc.w - ?) +
                        (hc.v - ?) * (hc.v - ?)) as dist_sq
                FROM holographic_coords hc
                JOIN memories m ON hc.memory_id = m.id
                WHERE hc.x IS NOT NULL
                ORDER BY dist_sq ASC
                LIMIT ?
            """,
                (x, x, y, y, z, z, w, w, v, v, k),
            ).fetchall()

            import math

            return [
                HolographicNeighbor(
                    memory_id=r["memory_id"],
                    title=r["title"],
                    distance=math.sqrt(max(0, r["dist_sq"])),
                    coords=(r["x"], r["y"], r["z"], r["w"], r["v"]),
                )
                for r in rows
            ]
        except Exception as e:
            logger.debug("Holographic neighbor query failed: %s", e, exc_info=True)
            return []

    def invalidate_hrr_cache(self) -> None:
        """Invalidate the HRR pre-filter cache.

        Called after memory writes to ensure the cache doesn't serve
        stale results. The next _refresh_hrr_cache call will rebuild
        from the database.
        """
        with self._hrr_cache_lock:
            self._hrr_cache_ids = None
            self._hrr_cache_vecs = None
            self._hrr_cache_count = 0
        logger.debug("HRR pre-filter cache invalidated")

    def _refresh_hrr_cache(self) -> None:
        """Load all embeddings from DB and quantize them with qFHRR.

        This builds an in-memory cache of quantized vectors for O(1)
        similarity lookups. The cache is keyed by memory ID and stores
        uint8 quantized vectors (8-bit, 384 bytes per vector).
        """
        with self._hrr_cache_lock:
            if self._hrr_cache_vecs is not None:
                return  # Already cached

            try:
                import numpy as np

                from whitemagic.core.memory.qfhrr import get_quantized_hrr_engine

                conn = self._get_conn()
                rows = conn.execute(
                    "SELECT memory_id, embedding FROM memory_embeddings ORDER BY memory_id",
                ).fetchall()

                if not rows:
                    self._hrr_cache_ids = []
                    self._hrr_cache_vecs = np.zeros((0, 384), dtype=np.uint8)
                    self._hrr_cache_count = 0
                    return

                ids: list[str] = []
                embeddings: list[list[float]] = []
                for r in rows:
                    emb = r["embedding"]
                    if emb:
                        import json

                        vec = json.loads(emb) if isinstance(emb, str) else list(emb)
                        if len(vec) >= 64:
                            ids.append(r["memory_id"])
                            embeddings.append(vec[:384] if len(vec) > 384 else vec)

                if not embeddings:
                    self._hrr_cache_ids = []
                    self._hrr_cache_vecs = np.zeros((0, 384), dtype=np.uint8)
                    self._hrr_cache_count = 0
                    return

                # Quantize all embeddings with qFHRR (8-bit for balanced speed/precision)
                engine = get_quantized_hrr_engine(bits=8, dim=len(embeddings[0]))
                quantized = np.array(
                    [engine._to_quantized(emb) for emb in embeddings], dtype=np.uint8
                )

                self._hrr_cache_ids = ids
                self._hrr_cache_vecs = quantized
                self._hrr_cache_count = len(ids)
                logger.info("HRR pre-filter cache: %d vectors quantized", len(ids))
            except Exception as e:
                logger.debug("HRR cache build failed: %s", e, exc_info=True)
                self._hrr_cache_ids = []
                self._hrr_cache_count = 0

    def _hrr_prefilter(
        self,
        query: str,
        top_n: int = 40,
    ) -> list[tuple[str, float]]:
        """Pre-filter candidates using quantized HRR similarity.

        Encodes the query with the embedding engine, quantizes it with
        qFHRR, and computes similarity against all cached vectors.
        Returns top-N (memory_id, similarity) pairs.

        This is much faster than full embedding search because:
        1. Integer LUT lookups instead of float dot products
        2. No model loading (embeddings pre-cached)
        3. SIMD-friendly contiguous uint8 arrays
        """
        if self._hrr_cache_vecs is None or self._hrr_cache_count == 0:
            self._refresh_hrr_cache()

        if (
            not self._hrr_cache_ids
            or self._hrr_cache_vecs is None
            or self._hrr_cache_count == 0
        ):
            return []

        try:
            import numpy as np

            from whitemagic.core.memory.embeddings import get_embedding_engine
            from whitemagic.core.memory.qfhrr import get_quantized_hrr_engine

            # Encode query
            engine = get_embedding_engine()
            query_emb = engine.encode(query)
            if query_emb is None or len(query_emb) < 64:
                return []

            # Quantize query with same engine as cache
            qfhrr = get_quantized_hrr_engine(bits=8, dim=len(query_emb))
            query_q = qfhrr._to_quantized(query_emb)

            # Compute similarity against all cached vectors
            # Vectorized: for each cached vector, compute mean LUT similarity
            lut = qfhrr._sim_lut

            # Batch similarity: for each pair (query_q[d], cache[n, d]),
            # look up LUT value and average across dimensions
            # This is vectorized via numpy fancy indexing
            sims = np.zeros(self._hrr_cache_count, dtype=np.float32)
            for d in range(query_q.shape[0]):
                q_val = int(query_q[d])
                cache_col = self._hrr_cache_vecs[:, d].astype(np.intp)
                sims += lut[q_val, cache_col]

            sims /= query_q.shape[0]

            top_indices = np.argsort(sims)[::-1][:top_n]
            return [
                (self._hrr_cache_ids[idx], float(sims[idx]))
                for idx in top_indices
                if sims[idx] > 0.01  # Filter near-zero similarity
            ]
        except Exception as e:
            logger.debug("HRR pre-filter query failed: %s", e, exc_info=True)
            return []

    def hybrid_recall(
        self,
        query: str,
        k: int = 10,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4,
        graph_depth: int = 2,
        include_cold: bool = False,
        use_hrr_prefilter: bool = True,
    ) -> list[HybridResult]:
        """Reciprocal Rank Fusion: embedding similarity + association graph walk.

        1. Get top-K from embedding search (vector channel)
        2. For top vector results, walk their association graph (graph channel)
        3. Fuse via RRF: score = w_v / (k_rrf + rank_v) + w_g / (k_rrf + rank_g)
        4. Return unified ranked results
        """
        k_rrf = 60  # RRF constant (standard value from literature)
        vector_results: list[tuple[str, float]] = []  # (memory_id, similarity)
        graph_results: list[tuple[str, float]] = []  # (memory_id, strength)

        hrr_candidates: list[tuple[str, float]] = []
        if use_hrr_prefilter:
            try:
                hrr_candidates = self._hrr_prefilter(query, k * 4)
                if hrr_candidates:
                    logger.debug(
                        "HRR pre-filter: %d candidates from %d total (top sim=%.3f)",
                        len(hrr_candidates),
                        self._hrr_cache_count,
                        hrr_candidates[0][1],
                    )
            except Exception as e:
                logger.debug("HRR pre-filter failed: %s", e, exc_info=True)

        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine

            engine = get_embedding_engine()
            if hrr_candidates:
                # Use HRR candidates as filter — only search embeddings for these IDs
                candidate_ids = {mid for mid, _ in hrr_candidates}
                vec_hits = engine.search_similar(
                    query,
                    limit=k * 2,
                    include_cold=include_cold,
                )
                # Filter to HRR pre-selected candidates
                vec_hits = [
                    h
                    for h in vec_hits
                    if (h.get("memory_id") or h.get("id", "")) in candidate_ids
                ]
            else:
                vec_hits = engine.search_similar(
                    query, limit=k * 2, include_cold=include_cold
                )
            for hit in vec_hits:
                mid = hit.get("memory_id") or hit.get("id", "")
                sim = hit.get("similarity", 0.0)
                vector_results.append((mid, sim))
        except Exception as e:
            logger.debug("Vector channel failed: %s", e, exc_info=True)
            # use HRR scores as fallback vector channel
            if hrr_candidates:
                vector_results = hrr_candidates[: k * 2]

        if vector_results:
            seed_ids = [mid for mid, _ in vector_results[:5]]
            graph_nodes = self.query_association_subgraph(
                seed_ids,
                depth=graph_depth,
                min_strength=0.3,
                max_nodes=k * 3,
            )
            for node in graph_nodes:
                if node.depth > 0:
                    # Skip seeds themselves
                    graph_results.append((node.memory_id, node.strength))

        vec_ids = [mid for mid, _ in vector_results]
        graph_ids_sorted = [
            mid for mid, _ in sorted(graph_results, key=lambda x: -x[1])
        ]

        scored: list[tuple[str, float, list[str]]] = []
        try:
            import whitemagic_rs

            rrf_results = whitemagic_rs.rrf_fuse(
                vec_ids,
                graph_ids_sorted,
                vector_weight,
                graph_weight,
                k_rrf,
                k,
            )
            for r in rrf_results:
                sources = []
                if r.from_vector:
                    sources.append("vector")
                if r.from_graph:
                    sources.append("graph")
                scored.append((r.memory_id, r.score, sources))
            logger.debug("RRF: Rust-accelerated path (%d results)", len(scored))
        except (ImportError, AttributeError):
            # Python fallback
            vec_rank: dict[str, int] = {}
            for rank, mid in enumerate(vec_ids):
                vec_rank[mid] = rank + 1

            graph_rank: dict[str, int] = {}
            for rank, mid in enumerate(graph_ids_sorted):
                graph_rank[mid] = rank + 1

            all_ids = set(vec_rank.keys()) | set(graph_rank.keys())

            for mid in all_ids:
                score = 0.0
                src_list: list[str] = []
                if mid in vec_rank:
                    score += vector_weight / (k_rrf + vec_rank[mid])
                    src_list.append("vector")
                if mid in graph_rank:
                    score += graph_weight / (k_rrf + graph_rank[mid])
                    src_list.append("graph")
                scored.append((mid, score, src_list))

            scored.sort(key=lambda x: -x[1])

        conn = self._get_conn()
        results: list[HybridResult] = []
        for mid, score, sources in scored[:k]:
            title = None
            preview = ""
            try:
                row = conn.execute(
                    "SELECT title, SUBSTR(content, 1, 200) as preview FROM memories WHERE id = ?",
                    (mid,),
                ).fetchone()
                if row:
                    title = row["title"]
                    preview = row["preview"] or ""
            except Exception as e:
                logger.debug("Failed to get row preview info: %s", e, exc_info=True)

            results.append(
                HybridResult(
                    memory_id=mid,
                    title=title,
                    content_preview=preview,
                    score=score,
                    sources=sources,
                )
            )

        return results

    def find_constellation_bridges(self, limit: int = 10) -> list[dict[str, Any]]:
        """Find memories that sit between two constellations.

        These bridge memories potentially link disparate knowledge domains
        and are high-value for serendipitous insight generation.
        """
        constellations = self.get_all_constellations()
        if len(constellations) < 2:
            return []

        # Build set of member IDs per constellation
        try:
            from whitemagic.core.memory.constellations import get_constellation_detector

            detector = get_constellation_detector()
            report = detector.get_last_report()
            if not report:
                return []
        except (ImportError, ModuleNotFoundError):
            return []

        constellation_members: dict[str, set[str]] = {}
        for c in report.get("constellations", []):
            constellation_members[c["name"]] = set(c.get("member_ids", []))

        # Find memories that appear in associations linking two different constellations
        conn = self._get_conn()
        bridges: list[dict[str, Any]] = []

        try:
            names = list(constellation_members.keys())
            # Collect all sampled source IDs across all pairs in one batch query
            all_sample_ids: list[str] = []
            pair_meta: list[tuple[str, str, set[str], set[str]]] = []
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    c1_ids = constellation_members[names[i]]
                    c2_ids = constellation_members[names[j]]
                    sample = list(c1_ids)[:50]
                    all_sample_ids.extend(sample)
                    pair_meta.append((names[i], names[j], set(sample), c2_ids))

            if all_sample_ids:
                ph = ",".join("?" * len(all_sample_ids))
                assoc_rows = conn.execute(
                    f"SELECT source_id, target_id, strength FROM associations "
                    f"WHERE source_id IN ({ph}) AND strength > 0.4",
                    all_sample_ids,
                ).fetchall()
                # Index by source_id for fast lookup
                assoc_by_src: dict[str, list[tuple[str, float]]] = {}
                for r in assoc_rows:
                    assoc_by_src.setdefault(r["source_id"], []).append(
                        (r["target_id"], r["strength"])
                    )

                for c1_name, c2_name, sample_set, c2_ids in pair_meta:
                    for sid in sample_set:
                        for target_id, strength in assoc_by_src.get(sid, []):
                            if target_id in c2_ids:
                                bridges.append(
                                    {
                                        "source_id": sid,
                                        "target_id": target_id,
                                        "strength": strength,
                                        "constellation_1": c1_name,
                                        "constellation_2": c2_name,
                                    }
                                )
                    if len(bridges) >= limit:
                        break
        except Exception as e:
            logger.debug("Bridge search failed: %s", e, exc_info=True)

        return bridges[:limit]

    def get_constellation_drift(self, window_days: int = 7) -> list[dict[str, Any]]:
        """Get drift vectors for all tracked constellations over a time window.

        Returns dicts with name, current_centroid, drift_vector, drift_magnitude.
        Sorted by magnitude descending (biggest movers first).
        """
        try:
            from whitemagic.core.memory.constellations import get_constellation_detector

            detector = get_constellation_detector()
            return cast(
                list[dict[str, Any]],
                detector.get_drift_vectors(window_days=window_days),
            )
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("Drift query failed: %s", e, exc_info=True)
            return []

    def find_association_orphans(
        self, min_gravity: float = 0.6, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Find high-gravity memories with few or no associations.

        These are isolated knowledge nodes that should be connected.
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT m.id, m.title, h.w as gravity,
                       (SELECT COUNT(*) FROM associations
                        WHERE source_id = m.id OR target_id = m.id) as assoc_count
                FROM memories m
                JOIN holographic_coords h ON m.id = h.memory_id
                WHERE h.w > ?
                HAVING assoc_count < 3
                ORDER BY h.w DESC
                LIMIT ?
            """,
                (min_gravity, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error:
            return []

    def compress_context(
        self,
        items: list[dict[str, Any]],
        query: str | None = None,
        max_text_items: int = 5,
    ) -> dict[str, Any]:
        """Compress context items into a single HRR superposition vector.

        Uses VSAContextCompressor to pack N context items into 1 HRR vector
        that can be probed on demand. Provides 10-50x context compression
        for LLM calls.

        Args:
            items: List of dicts with 'content', 'source', 'id' keys.
            query: Optional query for ranking items in the summary.
            max_text_items: Max items to include in text summary.

        Returns:
            Dict with: summary, vector, item_count, compression_ratio, method.
        """
        try:
            from whitemagic.ai.vsa_context_compressor import get_vsa_context_compressor

            compressor = get_vsa_context_compressor()
            result = compressor.compress(
                items, query=query, max_text_items=max_text_items
            )
            return {
                "summary": result.summary,
                "vector": result.vector,
                "item_count": result.item_count,
                "original_tokens": result.original_tokens,
                "compressed_tokens": result.compressed_tokens,
                "compression_ratio": result.compression_ratio,
                "method": result.method,
                "latency_ms": round(result.latency_ms, 2),
            }
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("VSA compressor unavailable: %s", e, exc_info=True)
            summaries = [
                f"- [{i.get('source', '?')}] {str(i.get('content', ''))[:150]}"
                for i in items[:max_text_items]
            ]
            return {
                "summary": "\n".join(summaries),
                "vector": None,
                "item_count": len(items),
                "original_tokens": sum(
                    len(str(i.get("content", ""))) // 4 for i in items
                ),
                "compressed_tokens": len("\n".join(summaries)) // 4,
                "compression_ratio": 0.0,
                "method": "truncation_fallback",
                "latency_ms": 0.0,
            }

    def probe_context(
        self,
        compressed_vector: list[float],
        role: str,
    ) -> list[float]:
        """Probe a compressed VSA vector to recover items from a specific source.

        Args:
            compressed_vector: The HRR superposition vector from compress_context.
            role: Role vector name (e.g. "OBJECT", "AGENT", "ACTION").

        Returns:
            Approximate embedding vector for items from that source.
        """
        try:
            from whitemagic.ai.vsa_context_compressor import get_vsa_context_compressor

            compressor = get_vsa_context_compressor()
            return compressor.probe(compressed_vector, role)
        except (ImportError, ModuleNotFoundError):
            return []


_instance: CoreAccessLayer | None = None
_instance_lock = threading.Lock()


def get_core_access() -> CoreAccessLayer:
    """Get or create the global CoreAccessLayer singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = CoreAccessLayer()
        return _instance
