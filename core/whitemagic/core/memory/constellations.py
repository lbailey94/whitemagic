# ruff: noqa: BLE001
"""Constellation Detection — Named Clusters in 5D Holographic Space.
==================================================================
Discovers dense clusters of semantically related memories in the 5D
holographic coordinate space (X, Y, Z, W, V). Each cluster is named
a "constellation" — a persistent semantic theme that emerges organically
from the Data Sea.

Constellations are persisted as PATTERN memories with special tags,
allowing them to be searched, visualized, and used for contextual recall.

Strategy (v14.1.1 — dual algorithm):
  1. Load all memories with holographic coordinates.
  2a. HDBSCAN: variable-density clustering with noise rejection (preferred).
  2b. Grid-based density scan fallback when hdbscan unavailable.
  3. Name each constellation from dominant tags/keywords.
  4. Persist as metadata (not as new memories — avoids bloat).
  5. Track drift via Hungarian optimal centroid matching.

Usage:
    from whitemagic.core.memory.constellations import get_constellation_detector
    detector = get_constellation_detector()
    report = detector.detect()
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

try:
    from scipy.optimize import linear_sum_assignment as _hungarian
    _SCIPY_AVAILABLE = True
except ImportError:
    _hungarian = None  # type: ignore[assignment]
    _SCIPY_AVAILABLE = False

# Rust acceleration (still needed for Hungarian matching)
try:
    import whitemagic_rust as _wr
    _rust_const: Any = getattr(_wr, "constellations", None)
    _RUST_AVAILABLE = _rust_const is not None
except ImportError:
    _rust_const = None  # type: ignore[assignment]
    _RUST_AVAILABLE = False

# Import extracted clustering algorithms
from whitemagic.core.memory.constellation_algorithms import (
    detect_grid,
    detect_hdbscan,
    distance_5d,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Constellation:
    """A named cluster of semantically related memories in 5D space."""

    name: str
    member_ids: list[str]
    centroid: tuple[float, float, float, float, float]  # (x, y, z, w, v)
    radius: float  # Average distance from centroid
    dominant_tags: list[str]
    dominant_type: str  # Most common memory_type
    avg_importance: float
    zone: str  # Galactic zone of centroid's V coordinate
    stability: float = 0.0  # HDBSCAN cluster persistence (0-1), 0 for grid-based

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.
        
        Returns:
            dict[str, Any]
        """
        return {
            "name": self.name,
            "size": len(self.member_ids),
            "centroid": {
                "x": round(self.centroid[0], 3),
                "y": round(self.centroid[1], 3),
                "z": round(self.centroid[2], 3),
                "w": round(self.centroid[3], 3),
                "v": round(self.centroid[4], 3),
            },
            "radius": round(self.radius, 3),
            "dominant_tags": self.dominant_tags[:5],
            "dominant_type": self.dominant_type,
            "avg_importance": round(self.avg_importance, 3),
            "zone": self.zone,
            "member_ids": self.member_ids[:10],  # Sample
        }


@dataclass
class DetectionReport:
    """Results from a constellation detection run."""

    memories_scanned: int = 0
    constellations_found: int = 0
    largest_constellation: int = 0
    duration_ms: float = 0.0
    algorithm: str = "grid"  # "grid" or "hdbscan"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    constellations: list[Constellation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.
        
        Returns:
            dict[str, Any]
        """
        return {
            "memories_scanned": self.memories_scanned,
            "constellations_found": self.constellations_found,
            "largest_constellation": self.largest_constellation,
            "duration_ms": round(self.duration_ms, 1),
            "timestamp": self.timestamp,
            "constellations": [c.to_dict() for c in self.constellations],
        }


# ---------------------------------------------------------------------------
# Constellation Detector
# ---------------------------------------------------------------------------

class ConstellationDetector:
    """Discovers dense clusters in 5D holographic space.

    Uses grid-based density scanning: divide each axis into bins,
    count memories per cell, identify dense cells, merge neighbors.
    """

    def __init__(
        self,
        bins_per_axis: int = 8,
        min_cluster_size: int = 5,
        max_constellations: int = 30,
        cache_ttl_seconds: float = 3600.0,
    ) -> None:
        self._bins = bins_per_axis
        self._min_size = min_cluster_size
        self._max_constellations = max_constellations
        self._lock = threading.Lock()
        self._last_report: DetectionReport | None = None
        # TTL cache: avoid re-running detect() on every query
        self._cache_ttl = cache_ttl_seconds
        self._last_detect_time: float = 0.0
        # Drift tracking: historical centroids keyed by constellation name
        # Each entry: list of (timestamp_iso, centroid_5d) tuples
        self._centroid_history: dict[str, list[tuple[str, tuple[float, ...]]]] = {}
        self._max_history_per_constellation = 100

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    @staticmethod
    def _distance_5d(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        """Euclidean distance in 5D space. Uses Rust when available."""
        return distance_5d(a, b)

    def detect(self, sample_limit: int = 50000) -> DetectionReport:
        """Run constellation detection across the Data Sea.

        Uses HDBSCAN when available (variable-density, noise-aware).
        Falls back to grid-based density scan otherwise.

        Returns a DetectionReport with discovered constellations.
        """
        start = time.perf_counter()
        report = DetectionReport()

        try:
            import sqlite3

            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            backend = um.backend
        except Exception as e:
            logger.error(f"Constellation detection: backend unavailable: {e}")
            return report

        # Load coordinates + metadata
        with backend.pool.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT hc.memory_id, hc.x, hc.y, hc.z, hc.w, hc.v,
                       m.title, m.memory_type, m.importance, m.galactic_distance
                FROM holographic_coords hc
                JOIN memories m ON hc.memory_id = m.id AND m.memory_type != 'quarantined'
                WHERE hc.x IS NOT NULL AND hc.y IS NOT NULL
                ORDER BY m.importance DESC
                LIMIT ?
            """, (sample_limit,)).fetchall()

        if len(rows) < self._min_size:
            return report

        report.memories_scanned = len(rows)
        coords: list[tuple[float, ...]] = [
            (r["x"], r["y"], r["z"], r["w"], r["v"]) for r in rows
        ]

        # Choose algorithm - HDBSCAN preferred, grid fallback
        try:
            cluster_groups, stabilities = self._detect_hdbscan(coords)
            report.algorithm = "hdbscan"
        except ImportError:
            cluster_groups, stabilities = self._detect_grid(coords)
            report.algorithm = "grid"

        # Build Constellation objects
        used_names: set[str] = set()
        constellations = []
        for group_idx, member_indices in enumerate(cluster_groups):
            member_indices = list(set(member_indices))
            if len(member_indices) < self._min_size:
                continue

            # Compute centroid
            member_coords = [coords[i] for i in member_indices]
            _cx = [sum(c[d] for c in member_coords) / len(member_coords) for d in range(5)]
            centroid: tuple[float, float, float, float, float] = (
                _cx[0], _cx[1], _cx[2], _cx[3], _cx[4],
            )

            # Average distance from centroid
            avg_radius = sum(
                self._distance_5d(c, centroid) for c in member_coords
            ) / len(member_coords)

            # Dominant tags
            member_ids = [rows[i]["memory_id"] for i in member_indices]
            tag_counts = self._get_tag_counts(backend, member_ids)
            dominant_tags = sorted(tag_counts, key=lambda t: tag_counts.get(t, 0), reverse=True)[:5]

            # Dominant type
            type_counts: dict[str, int] = defaultdict(int)
            for i in member_indices:
                type_counts[rows[i]["memory_type"]] += 1
            dominant_type = max(type_counts, key=lambda t: type_counts.get(t, 0))

            # Average importance
            avg_imp = sum(rows[i]["importance"] for i in member_indices) / len(member_indices)

            # Zone from centroid V
            from whitemagic.core.memory.galactic_map import classify_zone
            zone = classify_zone(1.0 - centroid[4]).value  # V is inverted distance

            # Name from dominant tags
            name = self._generate_name(dominant_tags, dominant_type, zone, used_names)

            stability = stabilities[group_idx] if group_idx < len(stabilities) else 0.0

            constellations.append(Constellation(
                name=name,
                member_ids=member_ids,
                centroid=centroid,
                radius=avg_radius,
                dominant_tags=dominant_tags,
                dominant_type=dominant_type,
                avg_importance=avg_imp,
                zone=zone,
                stability=stability,
            ))

        # Sort by size descending, cap
        constellations.sort(key=lambda c: len(c.member_ids), reverse=True)
        constellations = constellations[:self._max_constellations]

        report.constellations = constellations
        report.constellations_found = len(constellations)
        report.largest_constellation = max(
            (len(c.member_ids) for c in constellations), default=0,
        )
        report.duration_ms = (time.perf_counter() - start) * 1000

        with self._lock:
            self._last_report = report
            self._last_detect_time = time.time()

        # Record centroid history for drift tracking
        self._record_centroid_history(constellations)

        # Gap A3 synthesis: Feed constellations into Knowledge Graph
        self._feed_knowledge_graph(constellations)

        # v14.3: Persist constellation memberships to DB for search-time boost
        self.persist_memberships()

        logger.info(
            f"✨ Constellation detection ({report.algorithm}): "
            f"{report.constellations_found} constellations "
            f"found in {report.memories_scanned} memories ({report.duration_ms:.0f}ms). "
            f"Largest: {report.largest_constellation} members",
        )
        return report

    # ------------------------------------------------------------------
    # HDBSCAN detection (preferred)
    # ------------------------------------------------------------------

    def _detect_hdbscan(
        self, coords: list[tuple[float, ...]],
    ) -> tuple[list[list[int]], list[float]]:
        """Cluster using HDBSCAN — variable-density with noise rejection.

        Returns (groups, stabilities) where groups is a list of member-index
        lists and stabilities is per-cluster persistence score (0-1).
        """
        return detect_hdbscan(coords, self._min_size)

    # ------------------------------------------------------------------
    # Grid-based detection (fallback)
    # ------------------------------------------------------------------

    def _detect_grid(
        self, coords: list[tuple[float, ...]],
    ) -> tuple[list[list[int]], list[float]]:
        """Grid-based density scan fallback.

        Returns (groups, stabilities) — stabilities are always 0.0 for grid.
        """
        return detect_grid(coords, self._bins, self._min_size, self._max_constellations)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_tag_counts(backend: Any, memory_ids: list[str]) -> dict[str, int]:
        """Get tag frequency for a set of memory IDs."""
        counts: dict[str, int] = defaultdict(int)
        if not memory_ids:
            return counts

        # Process in chunks to avoid huge IN clauses
        chunk_size = 200
        for i in range(0, len(memory_ids), chunk_size):
            chunk = memory_ids[i:i + chunk_size]
            placeholders = ",".join("?" * len(chunk))
            try:
                with backend.pool.connection() as conn:
                    rows = conn.execute(
                        f"SELECT tag, COUNT(*) as cnt FROM tags "
                        f"WHERE memory_id IN ({placeholders}) "
                        f"GROUP BY tag ORDER BY cnt DESC",
                        chunk,
                    ).fetchall()
                    for row in rows:
                        tag = row[0] if isinstance(row, tuple) else row["tag"]
                        cnt = row[1] if isinstance(row, tuple) else row["cnt"]
                        # Skip generic tags
                        if tag not in ("archive", "scavenged", "meta", "history"):
                            counts[tag] += cnt
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass

        return counts

    def _generate_name(
        self, dominant_tags: list[str], dominant_type: str, zone: str,
        used_names: set[str],
    ) -> str:
        """Generate a unique constellation name from its characteristics."""
        # Use top 2 tags as the name base
        tag_part = " ".join(t.replace("_", " ").title() for t in dominant_tags[:2])
        if not tag_part:
            tag_part = dominant_type.replace("_", " ").title()

        # Prefix by zone
        zone_prefix = {
            "core": "Corona",
            "inner_rim": "Aureola",
            "mid_band": "Nebula",
            "outer_rim": "Drift",
            "far_edge": "Veil",
        }
        prefix = zone_prefix.get(zone, "Cluster")
        base_name = f"{prefix} {tag_part}"

        # Ensure uniqueness with roman numeral suffixes
        if base_name not in used_names:
            used_names.add(base_name)
            return base_name

        _roman = ["II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
        for suffix in _roman:
            candidate = f"{base_name} {suffix}"
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate

        # Fallback: use size
        fallback = f"{base_name} ({len(used_names)})"
        used_names.add(fallback)
        return fallback

    # ------------------------------------------------------------------
    # Gap A3 synthesis: Constellations → Knowledge Graph
    # ------------------------------------------------------------------

    def _feed_knowledge_graph(self, constellations: list[Constellation]) -> None:
        """Register constellation entities and membership relations in the KG.

        Each constellation becomes a KG entity with its dominant tags.
        Members get 'belongs_to_constellation' relations, allowing the
        KG to answer queries like "which constellation does memory X
        belong to?" or "what are the themes of constellation Y?"
        """
        if not constellations:
            return
        try:
            from whitemagic.core.intelligence.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()

            entities_created = 0
            for c in constellations:
                # Register constellation as a KG entity
                kg.add_entity(
                    name=c.name,
                    entity_type="constellation",
                    metadata={
                        "zone": c.zone,
                        "size": len(c.member_ids),
                        "dominant_tags": c.dominant_tags,
                        "avg_importance": c.avg_importance,
                        "origin": "constellation_detector",
                    },
                )
                entities_created += 1

                # Link a sample of members (avoid huge fan-out)
                for mid in c.member_ids[:20]:
                    kg.add_relation(
                        source=mid,
                        relation="belongs_to_constellation",
                        target=c.name,
                        metadata={"zone": c.zone},
                    )

            if entities_created:
                logger.info(
                    f"KG enrichment: {entities_created} constellation entities registered",
                )
        except Exception as e:
            logger.debug(f"KG enrichment from constellations skipped: {e}")

    def find_nearest_constellation(
        self, x: float, y: float, z: float, w: float, v: float,
        max_distance: float = 0.5,
    ) -> dict[str, Any] | None:
        """Find the nearest constellation to a 5D point.

        Returns a dict with constellation name, distance, and zone if
        a constellation is within max_distance. Uses the last detection
        report (cached). Returns None if no constellations are cached
        or none are close enough.
        """
        with self._lock:
            if not self._last_report or not self._last_report.constellations:
                return None

        point = (x, y, z, w, v)
        best = None
        best_dist = max_distance

        for c in self._last_report.constellations:
            dist = self._distance_5d(point, c.centroid)
            if dist < best_dist:
                best_dist = dist
                best = c

        if best is None:
            return None

        return {
            "constellation": best.name,
            "distance": round(best_dist, 3),
            "zone": best.zone,
            "size": len(best.member_ids),
            "dominant_tags": best.dominant_tags[:3],
        }

    def annotate_memories(
        self, memories: list, backend: Any=None,
    ) -> list:
        """Annotate a list of Memory objects with constellation context.

        For each memory that has holographic coordinates, checks if it
        falls near a known constellation and adds metadata annotation.
        Modifies memories in-place and returns them.
        """
        with self._lock:
            if not self._last_report or not self._last_report.constellations:
                return memories

        if not backend:
            return memories

        for mem in memories:
            try:
                coords = backend.get_coords(mem.id)
                if not coords:
                    continue
                match = self.find_nearest_constellation(*coords)
                if match:
                    if not hasattr(mem, "metadata") or mem.metadata is None:
                        mem.metadata = {}
                    mem.metadata["constellation"] = match
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                continue

        return memories

    def get_constellation_centroids(self) -> list[dict[str, Any]]:
        """Return all constellation centroids from the last detection report.

        Each entry contains: name, centroid (5-tuple), dominant_tags, size, stability.
        Used by the embedding engine to find the closest constellation to a query.
        """
        with self._lock:
            if not self._last_report or not self._last_report.constellations:
                return []
            return [
                {
                    "name": c.name,
                    "centroid": c.centroid,
                    "dominant_tags": c.dominant_tags,
                    "size": len(c.member_ids),
                    "stability": c.stability,
                    "zone": c.zone,
                }
                for c in self._last_report.constellations
            ]

    def get_memory_constellation(self, memory_id: str) -> dict[str, Any] | None:
        """Look up the constellation for a specific memory from the DB index.

        Returns dict with constellation_name, membership_confidence, or None.
        Falls back to in-memory membership scan if DB index is empty.
        """
        # Fast path: DB index (persisted by persist_memberships)
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            result = um.backend.get_constellation_membership(memory_id)
            if result:
                return cast(dict[str, Any], result)
        except (ImportError, AttributeError):
            pass

        # Slow path: scan cached report member_ids
        with self._lock:
            if not self._last_report:
                return None
            for c in self._last_report.constellations:
                if memory_id in c.member_ids:
                    return {
                        "constellation_name": c.name,
                        "membership_confidence": c.stability if c.stability > 0 else 0.8,
                    }
        return None

    def persist_memberships(self) -> int:
        """Persist current constellation memberships to the DB index.

        Called after detection to make memberships queryable at search time.
        Returns number of memberships persisted.
        """
        with self._lock:
            if not self._last_report or not self._last_report.constellations:
                return 0
            memberships: list[tuple[str, str, float]] = []
            for c in self._last_report.constellations:
                confidence = c.stability if c.stability > 0 else 0.8
                for mid in c.member_ids:
                    memberships.append((mid, c.name, confidence))

        if not memberships:
            return 0

        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            count = um.backend.update_constellation_membership(memberships)
            logger.info(f"Persisted {count} constellation memberships to DB index")
            return cast(int, count)
        except Exception as e:
            logger.debug(f"Failed to persist constellation memberships: {e}")
            return 0

    def list_constellations(self) -> list[Constellation]:
        """List all discovered constellations from the last report."""
        with self._lock:
            if not self._last_report:
                return []
            return list(self._last_report.constellations)

    def get_last_report(self) -> dict[str, Any] | None:
        """Get the last detection report as a dictionary."""
        with self._lock:
            return self._last_report.to_dict() if self._last_report else None

    def get_cached_or_detect(self, sample_limit: int = 10000) -> DetectionReport | None:
        """Return cached report if TTL is valid, otherwise re-detect.

        This is the preferred entry point for callers that don't need
        guaranteed-fresh data (e.g., CoreAccessLayer, InsightPipeline).
        """
        with self._lock:
            elapsed = time.time() - self._last_detect_time
            if self._last_report is not None and elapsed < self._cache_ttl:
                return self._last_report
        return self.detect(sample_limit=sample_limit)

    # ------------------------------------------------------------------
    # Auto-Merge Converging Constellations
    # ------------------------------------------------------------------

    def auto_merge(
        self,
        max_distance: float = 0.5,
        min_shared_tags: int = 2,
    ) -> dict[str, Any]:
        """Merge converging constellations that share tags and are close in 5D space.

        Two constellations are merged when:
          1. Their centroid distance < max_distance
          2. They share >= min_shared_tags dominant tags

        The smaller constellation is absorbed into the larger one.
        Memberships are re-persisted after merging.

        Returns a summary dict with merge details.
        """
        with self._lock:
            if not self._last_report or not self._last_report.constellations:
                return {"status": "no_constellations", "merges": 0}
            constellations = list(self._last_report.constellations)

        if len(constellations) < 2:
            return {"status": "too_few", "merges": 0}

        # Find merge candidates
        merge_pairs: list[tuple[int, int, float, list[str]]] = []
        for i in range(len(constellations)):
            for j in range(i + 1, len(constellations)):
                a, b = constellations[i], constellations[j]
                dist = self._distance_5d(a.centroid, b.centroid)
                if dist >= max_distance:
                    continue
                shared_tags_set = set(a.dominant_tags) & set(b.dominant_tags)
                if len(shared_tags_set) >= min_shared_tags:
                    merge_pairs.append((i, j, dist, sorted(shared_tags_set)))

        if not merge_pairs:
            return {"status": "no_candidates", "merges": 0, "checked": len(constellations)}

        # Sort by distance (closest first)
        merge_pairs.sort(key=lambda p: p[2])

        merged_into: dict[int, int] = {}  # idx → absorbed_into_idx
        merge_log: list[dict[str, Any]] = []

        for i, j, dist, shared in merge_pairs:
            # Resolve transitive merges
            while i in merged_into:
                i = merged_into[i]
            while j in merged_into:
                j = merged_into[j]
            if i == j:
                continue  # Already merged via transitivity

            a, b = constellations[i], constellations[j]
            # Larger absorbs smaller
            if len(a.member_ids) < len(b.member_ids):
                i, j = j, i
                a, b = b, a

            # Merge b into a
            new_members = list(set(a.member_ids) | set(b.member_ids))
            new_tags = list(dict.fromkeys(a.dominant_tags + b.dominant_tags))[:10]

            # Recompute centroid as weighted average
            wa, wb = len(a.member_ids), len(b.member_ids)
            total = wa + wb
            new_centroid = tuple(
                (a.centroid[d] * wa + b.centroid[d] * wb) / total
                for d in range(5)
            )

            merge_log.append({
                "absorbed": b.name,
                "into": a.name,
                "distance": round(dist, 4),
                "shared_tags": shared,
                "new_size": len(new_members),
            })

            # Update a in-place
            a.member_ids = new_members
            a.dominant_tags = new_tags
            a.centroid = (new_centroid[0], new_centroid[1], new_centroid[2],
                          new_centroid[3], new_centroid[4])
            a.avg_importance = (a.avg_importance * wa + b.avg_importance * wb) / total
            a.stability = max(a.stability, b.stability)

            merged_into[j] = i

        # Remove absorbed constellations
        surviving = [
            c for idx, c in enumerate(constellations)
            if idx not in merged_into
        ]

        # Update cached report
        with self._lock:
            if self._last_report:
                self._last_report.constellations = surviving
                self._last_report.constellations_found = len(surviving)
                self._last_report.largest_constellation = max(
                    (len(c.member_ids) for c in surviving), default=0,
                )

        # Re-persist memberships
        if merge_log:
            self.persist_memberships()

        result = {
            "status": "ok",
            "merges": len(merge_log),
            "constellations_before": len(constellations),
            "constellations_after": len(surviving),
            "merge_log": merge_log,
        }

        if merge_log:
            logger.info(
                f"✨ Constellation auto-merge: {len(merge_log)} merges, "
                f"{len(constellations)} → {len(surviving)} constellations",
            )
        return result

    # ------------------------------------------------------------------
    # Drift Tracking
    # ------------------------------------------------------------------

    def _record_centroid_history(self, constellations: list[Constellation]) -> None:
        """Record current centroids into drift history."""
        now = datetime.now().isoformat()
        for c in constellations:
            if c.name not in self._centroid_history:
                self._centroid_history[c.name] = []
            history = self._centroid_history[c.name]
            history.append((now, c.centroid))
            # Trim to max history
            if len(history) > self._max_history_per_constellation:
                self._centroid_history[c.name] = history[-self._max_history_per_constellation:]

    def get_drift_vectors(self, window_days: int = 7) -> list[dict[str, Any]]:
        """Compute drift vectors for all tracked constellations.

        Uses Hungarian algorithm (scipy) for optimal centroid matching
        when available, falling back to name-based matching otherwise.

        Returns list of dicts with:
          - name: constellation name
          - current_centroid: current 5D position
          - drift_vector: 5D displacement over the window
          - drift_magnitude: Euclidean distance moved
          - samples: number of historical observations in the window
          - novel_concepts: constellations that appeared (no prior match)
          - forgotten_concepts: constellations that disappeared
        """
        import math as _math
        from datetime import datetime as _dt
        from datetime import timedelta as _td

        cutoff = (_dt.now() - _td(days=window_days)).isoformat()
        results: list[dict[str, Any]] = []

        with self._lock:
            current_report = self._last_report

        if not current_report:
            return []

        current_centroids: dict[str, tuple[float, ...]] = {
            c.name: c.centroid for c in current_report.constellations
        }

        # Collect earliest historical centroids within window
        historical_centroids: dict[str, tuple[float, ...]] = {}
        for name, history in self._centroid_history.items():
            window_points = [(ts, c) for ts, c in history if ts >= cutoff]
            if len(window_points) >= 2:
                historical_centroids[name] = window_points[0][1]

        # Try Hungarian matching for optimal correspondence
        if _SCIPY_AVAILABLE and historical_centroids and current_centroids:
            matched, novel, forgotten = self._hungarian_match(
                historical_centroids, current_centroids,
            )

            for curr_name, hist_name in matched.items():
                current = current_centroids[curr_name]
                earliest = historical_centroids[hist_name]
                drift_vec = tuple(c - e for c, e in zip(current, earliest))
                magnitude = _math.sqrt(sum(d * d for d in drift_vec))
                window_points = [(ts, c) for ts, c in self._centroid_history.get(hist_name, []) if ts >= cutoff]

                results.append({
                    "name": curr_name,
                    "matched_from": hist_name if hist_name != curr_name else None,
                    "current_centroid": {"x": current[0], "y": current[1],
                                         "z": current[2], "w": current[3],
                                         "v": current[4]},
                    "drift_vector": {"dx": round(drift_vec[0], 4),
                                     "dy": round(drift_vec[1], 4),
                                     "dz": round(drift_vec[2], 4),
                                     "dw": round(drift_vec[3], 4),
                                     "dv": round(drift_vec[4], 4)},
                    "drift_magnitude": round(magnitude, 4),
                    "samples": len(window_points),
                    "window_days": window_days,
                })

            # Emit events for novel / forgotten concepts
            self._emit_concept_events(novel, forgotten)

        else:
            # Fallback: name-based matching (original behavior)
            for name, history in self._centroid_history.items():
                if name not in current_centroids:
                    continue
                window_points = [(ts, c) for ts, c in history if ts >= cutoff]
                if len(window_points) < 2:
                    continue
                earliest = window_points[0][1]
                current = current_centroids[name]
                drift_vec = tuple(c - e for c, e in zip(current, earliest))
                magnitude = _math.sqrt(sum(d * d for d in drift_vec))

                results.append({
                    "name": name,
                    "current_centroid": {"x": current[0], "y": current[1],
                                         "z": current[2], "w": current[3],
                                         "v": current[4]},
                    "drift_vector": {"dx": round(drift_vec[0], 4),
                                     "dy": round(drift_vec[1], 4),
                                     "dz": round(drift_vec[2], 4),
                                     "dw": round(drift_vec[3], 4),
                                     "dv": round(drift_vec[4], 4)},
                    "drift_magnitude": round(magnitude, 4),
                    "samples": len(window_points),
                    "window_days": window_days,
                })

        results.sort(key=lambda r: -r["drift_magnitude"])
        return results

    # ------------------------------------------------------------------
    # Hungarian Optimal Matching
    # ------------------------------------------------------------------

    def _hungarian_match(
        self,
        old_centroids: dict[str, tuple[float, ...]],
        new_centroids: dict[str, tuple[float, ...]],
        max_match_distance: float = 2.0,
    ) -> tuple[dict[str, str], list[str], list[str]]:
        """Match old→new constellations using the Hungarian algorithm.

        Returns:
            matched: new_name → old_name for matched pairs
            novel: list of new constellation names with no match
            forgotten: list of old constellation names with no match
        """
        old_names = sorted(old_centroids.keys())
        new_names = sorted(new_centroids.keys())
        n_old, n_new = len(old_names), len(new_names)

        if n_old == 0 or n_new == 0:
            return {}, list(new_names), list(old_names)

        # Try Rust implementation first (S026 VC1)
        if _RUST_AVAILABLE:
            try:
                old_centroids_5d = {
                    name: (c[0], c[1], c[2], c[3], c[4])
                    for name, c in old_centroids.items()
                }
                new_centroids_5d = {
                    name: (c[0], c[1], c[2], c[3], c[4])
                    for name, c in new_centroids.items()
                }
                matched, novel, forgotten = _rust_const.py_hungarian_match(
                    old_centroids_5d, new_centroids_5d, max_match_distance
                )
                if novel or forgotten:
                    logger.info(
                        f"Drift tracking: {len(matched)} matched, "
                        f"{len(novel)} novel, {len(forgotten)} forgotten",
                    )
                return matched, novel, forgotten
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass  # Fall back to Python/NumPy

        # Build cost matrix: n_new × n_old (distances)
        import numpy as np
        cost: np.ndarray = np.zeros((n_new, n_old), dtype=np.float64)
        for i, nn in enumerate(new_names):
            for j, on in enumerate(old_names):
                cost[i, j] = self._distance_5d(new_centroids[nn], old_centroids[on])

        row_ind, col_ind = _hungarian(cost)

        matched_dict: dict[str, str] = {}
        matched_old: set[str] = set()
        matched_new: set[str] = set()

        for r, c in zip(row_ind, col_ind):
            if cost[r, c] <= max_match_distance:
                matched_dict[new_names[r]] = old_names[c]
                matched_new.add(new_names[r])
                matched_old.add(old_names[c])

        novel = [n for n in new_names if n not in matched_new]
        forgotten = [o for o in old_names if o not in matched_old]

        if novel or forgotten:
            logger.info(
                f"Drift tracking: {len(matched_dict)} matched, "
                f"{len(novel)} novel, {len(forgotten)} forgotten",
            )
        return matched_dict, novel, forgotten

    @staticmethod
    def _emit_concept_events(novel: list[str], forgotten: list[str]) -> None:
        """Emit NOVEL_CONCEPT / FORGOTTEN_CONCEPT events to Gan Ying bus."""
        if not novel and not forgotten:
            return
        try:
            from whitemagic.core.resonance.gan_ying import emit_event
            from whitemagic.core.resonance.gan_ying_enhanced import EventType

            for name in novel:
                emit_event(
                    source="constellation_detector",
                    event_type=EventType.PATTERN_DETECTED,
                    data={"type": "NOVEL_CONCEPT", "constellation": name},
                )
            for name in forgotten:
                emit_event(
                    source="constellation_detector",
                    event_type=EventType.PATTERN_DETECTED,
                    data={"type": "FORGOTTEN_CONCEPT", "constellation": name},
                )
        except (ImportError, AttributeError):
            pass  # Gan Ying bus optional


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_detector_instance: ConstellationDetector | None = None
_detector_lock = threading.Lock()


def get_constellation_detector(
    bins_per_axis: int = 8,
    min_cluster_size: int = 5,
    max_constellations: int = 30,
) -> ConstellationDetector:
    """Get or create the global ConstellationDetector singleton."""
    global _detector_instance
    with _detector_lock:
        if _detector_instance is None:
            _detector_instance = ConstellationDetector(
                bins_per_axis=bins_per_axis,
                min_cluster_size=min_cluster_size,
                max_constellations=max_constellations,
            )
        return _detector_instance


# ---------------------------------------------------------------------------
# Register with UnifiedMemory hooks to break circular dependency
# ---------------------------------------------------------------------------

try:
    from whitemagic.core.memory.unified import register_search_hook

    def _constellation_annotation_hook(results: list) -> None:
        """Hook: annotate search results with constellation context."""
        if not results:
            return
        try:
            detector = get_constellation_detector()
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            detector.annotate_memories(results, backend=um.backend)
        except (ImportError, AttributeError):
            pass

    register_search_hook(_constellation_annotation_hook)
except ImportError:
    pass
