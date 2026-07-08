"""Meta-Galaxy — Top-down meta-cognitive index of all galaxies.

The meta-galaxy maintains an overhead view of every other galaxy in the system.
It automatically updates to reflect changes, providing the system (and the AI
using it) with a cybernetic steering wheel for self-directed cognition.

The meta-galaxy stores:
- Galaxy summaries (memory count, top tags, importance distribution)
- Cross-galaxy associations (which galaxies reference each other)
- Knowledge gap maps (what's missing, where)
- Strategic index (what the system should focus on next)

This is NOT a separate SQLite database — it's a virtual layer that aggregates
data from all galaxy backends and caches the result for fast access.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Cache TTL in seconds
CACHE_TTL = 60.0


@dataclass
class GalaxySummary:
    """Summary of a single galaxy's state."""

    name: str
    memory_count: int = 0
    top_tags: list[tuple[str, int]] = field(default_factory=list)
    avg_importance: float = 0.0
    oldest_memory: str = ""
    newest_memory: str = ""
    galaxy_zone: str = "INNER_RIM"
    health_score: float = 1.0
    knowledge_gaps: list[str] = field(default_factory=list)
    cross_references: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "memory_count": self.memory_count,
            "top_tags": [{"tag": t, "count": c} for t, c in self.top_tags[:10]],
            "avg_importance": round(self.avg_importance, 4),
            "oldest_memory": self.oldest_memory,
            "newest_memory": self.newest_memory,
            "galaxy_zone": self.galaxy_zone,
            "health_score": round(self.health_score, 4),
            "knowledge_gaps": self.knowledge_gaps,
            "cross_references": dict(self.cross_references),
        }


@dataclass
class MetaGalaxyIndex:
    """The complete meta-galaxy index."""

    galaxies: dict[str, GalaxySummary] = field(default_factory=dict)
    total_memories: int = 0
    total_galaxies: int = 0
    cross_galaxy_associations: int = 0
    top_knowledge_gaps: list[str] = field(default_factory=list)
    strategic_priorities: list[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_memories": self.total_memories,
            "total_galaxies": self.total_galaxies,
            "cross_galaxy_associations": self.cross_galaxy_associations,
            "galaxies": {k: v.to_dict() for k, v in self.galaxies.items()},
            "top_knowledge_gaps": self.top_knowledge_gaps,
            "strategic_priorities": self.strategic_priorities,
            "generated_at": self.generated_at,
        }


class MetaGalaxy:
    """Meta-galactic cognitive index — top-down view of all galaxies.

    Provides:
    - Galaxy summaries with memory counts, top tags, importance distribution
    - Cross-galaxy association mapping
    - Knowledge gap detection across galaxies
    - Strategic priority generation
    - Automatic refresh on memory changes

    This enables the system to cybernetically steer itself by understanding
    where its knowledge is concentrated and where it's lacking.
    """

    def __init__(self) -> None:
        self._cache: MetaGalaxyIndex | None = None
        self._cache_time: float = 0.0
        self._lock = threading.RLock()
        self._refresh_callbacks: list[Any] = []

    def _get_galaxy_backend(self) -> Any:
        """Get the GalaxyAwareBackend for scanning all galaxies."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            return um._galaxy_backend
        except Exception as e:
            logger.debug("MetaGalaxy: could not get galaxy backend: %s", e)
            return None

    def _summarize_galaxy(self, name: str, backend: Any) -> GalaxySummary:
        """Summarize a single galaxy's state."""
        summary = GalaxySummary(name=name)

        try:
            stats = backend.get_stats()
            summary.memory_count = stats.get("total_memories", 0)
            summary.avg_importance = stats.get("avg_importance", 0.0)
        except Exception as e:
            logger.debug("MetaGalaxy: stats failed for %s: %s", name, e)

        try:
            # Get top tags
            conn = backend._get_conn() if hasattr(backend, "_get_conn") else None
            if conn is not None:
                cur = conn.cursor()
                cur.execute(
                    "SELECT tag, COUNT(*) as cnt FROM tags GROUP BY tag ORDER BY cnt DESC LIMIT 10"
                )
                for row in cur.fetchall():
                    summary.top_tags.append((row[0], row[1]))

                # Get oldest and newest memories
                cur.execute("SELECT MIN(created_at), MAX(created_at) FROM memories")
                row = cur.fetchone()
                if row:
                    summary.oldest_memory = row[0] or ""
                    summary.newest_memory = row[1] or ""
        except Exception as e:
            logger.debug("MetaGalaxy: tag scan failed for %s: %s", name, e)

        # Determine galaxy zone based on memory count and importance
        if summary.memory_count == 0:
            summary.galaxy_zone = "FAR_EDGE"
            summary.health_score = 0.3
        elif summary.memory_count < 10:
            summary.galaxy_zone = "OUTER_RIM"
            summary.health_score = 0.6
        elif summary.memory_count < 50:
            summary.galaxy_zone = "MID_BAND"
            summary.health_score = 0.8
        elif summary.memory_count < 200:
            summary.galaxy_zone = "INNER_RIM"
            summary.health_score = 0.9
        else:
            summary.galaxy_zone = "CORE"
            summary.health_score = 1.0

        # Detect knowledge gaps
        summary.knowledge_gaps = self._detect_galaxy_gaps(name, summary)

        return summary

    def _detect_galaxy_gaps(self, galaxy_name: str, summary: GalaxySummary) -> list[str]:
        """Detect knowledge gaps within a galaxy."""
        gaps: list[str] = []

        if summary.memory_count == 0:
            gaps.append(f"Galaxy '{galaxy_name}' is empty — no memories stored")
        elif summary.memory_count < 5:
            gaps.append(f"Galaxy '{galaxy_name}' is sparse — only {summary.memory_count} memories")

        if summary.avg_importance < 0.3 and summary.memory_count > 0:
            gaps.append(f"Galaxy '{galaxy_name}' has low average importance ({summary.avg_importance:.2f})")

        # Check for temporal staleness
        if summary.newest_memory:
            try:
                from datetime import datetime, timedelta
                newest = datetime.fromisoformat(summary.newest_memory.replace("Z", ""))
                if datetime.now() - newest > timedelta(days=7):
                    gaps.append(f"Galaxy '{galaxy_name}' is stale — no new memories in >7 days")
            except Exception:
                pass

        return gaps

    def _detect_cross_galaxy_refs(self, galaxies: dict[str, GalaxySummary]) -> int:
        """Count cross-galaxy associations."""
        total = 0
        try:
            backend = self._get_galaxy_backend()
            if backend is None:
                return 0
            for name, gb in getattr(backend, "_galaxy_backends", {}).items():
                try:
                    conn = gb._get_conn() if hasattr(gb, "_get_conn") else None
                    if conn is None:
                        continue
                    cur = conn.cursor()
                    # Check for memories that reference other galaxies
                    cur.execute(
                        "SELECT COUNT(*) FROM memories WHERE content LIKE '%galaxy:%'"
                    )
                    total += cur.fetchone()[0]
                except Exception:
                    continue
        except Exception as e:
            logger.debug("MetaGalaxy: cross-galaxy ref scan failed: %s", e)
        return total

    def _generate_strategic_priorities(
        self, galaxies: dict[str, GalaxySummary], gaps: list[str]
    ) -> list[str]:
        """Generate strategic priorities from the meta-galaxy view."""
        priorities: list[str] = []

        # Prioritize empty/sparse galaxies
        empty_galaxies = [g for g, s in galaxies.items() if s.memory_count == 0]
        if empty_galaxies:
            priorities.append(f"Seed memories in empty galaxies: {', '.join(empty_galaxies)}")

        # Prioritize stale galaxies
        stale_galaxies = [g for g, s in galaxies.items() if any("stale" in gap for gap in s.knowledge_gaps)]
        if stale_galaxies:
            priorities.append(f"Refresh stale galaxies: {', '.join(stale_galaxies)}")

        # Prioritize low-health galaxies
        low_health = [(g, s.health_score) for g, s in galaxies.items() if s.health_score < 0.7]
        if low_health:
            low_health.sort(key=lambda x: x[1])
            priorities.append(
                f"Improve galaxy health: {', '.join(f'{g}({h:.1f})' for g, h in low_health[:3])}"
            )

        # General knowledge gaps
        if gaps:
            priorities.append(f"Address knowledge gaps: {gaps[0]}")

        return priorities

    def refresh(self) -> MetaGalaxyIndex:
        """Refresh the meta-galaxy index by scanning all galaxies."""
        with self._lock:
            backend = self._get_galaxy_backend()
            if backend is None:
                return MetaGalaxyIndex()

            galaxies: dict[str, GalaxySummary] = {}

            # Scan all galaxy backends
            galaxy_backends = getattr(backend, "_galaxy_backends", {})
            for name, gb in galaxy_backends.items():
                try:
                    galaxies[name] = self._summarize_galaxy(name, gb)
                except Exception as e:
                    logger.debug("MetaGalaxy: failed to summarize galaxy %s: %s", name, e)
                    galaxies[name] = GalaxySummary(name=name)

            # Also scan the default backend
            try:
                default_backend = getattr(backend, "_get_default_backend", lambda: None)()
                if default_backend is not None:
                    galaxies["universal"] = self._summarize_galaxy("universal", default_backend)
            except Exception:
                pass

            # Collect all knowledge gaps
            all_gaps: list[str] = []
            for name, summary in galaxies.items():
                all_gaps.extend(summary.knowledge_gaps)

            # Detect cross-galaxy associations
            cross_refs = self._detect_cross_galaxy_refs(galaxies)

            # Generate strategic priorities
            priorities = self._generate_strategic_priorities(galaxies, all_gaps)

            # Build index
            index = MetaGalaxyIndex(
                galaxies=galaxies,
                total_memories=sum(s.memory_count for s in galaxies.values()),
                total_galaxies=len(galaxies),
                cross_galaxy_associations=cross_refs,
                top_knowledge_gaps=all_gaps[:10],
                strategic_priorities=priorities[:5],
            )

            self._cache = index
            self._cache_time = time.time()

            logger.info(
                "MetaGalaxy refreshed: %s galaxies, %s memories, %s gaps, %s priorities",
                index.total_galaxies,
                index.total_memories,
                len(all_gaps),
                len(priorities),
            )

            # Notify refresh callbacks
            for cb in self._refresh_callbacks:
                try:
                    cb(index)
                except Exception:
                    pass

            return index

    def get_index(self, force_refresh: bool = False) -> MetaGalaxyIndex:
        """Get the meta-galaxy index, refreshing if stale."""
        with self._lock:
            if (
                self._cache is None
                or force_refresh
                or (time.time() - self._cache_time) > CACHE_TTL
            ):
                return self.refresh()
            return self._cache

    def get_overview(self) -> dict[str, Any]:
        """Get a quick overview dict for API responses."""
        index = self.get_index()
        return index.to_dict()

    def get_strategic_priorities(self) -> list[str]:
        """Get current strategic priorities."""
        return self.get_index().strategic_priorities

    def get_knowledge_gaps(self) -> list[str]:
        """Get top knowledge gaps across all galaxies."""
        return self.get_index().top_knowledge_gaps

    def get_galaxy_summary(self, name: str) -> dict[str, Any] | None:
        """Get summary of a specific galaxy."""
        index = self.get_index()
        summary = index.galaxies.get(name)
        return summary.to_dict() if summary else None

    def on_refresh(self, callback: Any) -> None:
        """Register a callback to be called when the index is refreshed."""
        self._refresh_callbacks.append(callback)

    def get_report(self) -> str:
        """Generate a human-readable meta-galaxy report."""
        index = self.get_index()
        lines = [
            "META-GALAXY OVERVIEW",
            "=" * 50,
            f"Galaxies: {index.total_galaxies} | Memories: {index.total_memories} | Cross-refs: {index.cross_galaxy_associations}",
            "",
            "Galaxy Summaries:",
        ]
        for name, summary in sorted(index.galaxies.items(), key=lambda x: -x[1].memory_count):
            lines.append(
                f"  {name:20} | {summary.memory_count:5} memories | "
                f"zone={summary.galaxy_zone:10} | health={summary.health_score:.2f}"
            )
            if summary.knowledge_gaps:
                for gap in summary.knowledge_gaps[:2]:
                    lines.append(f"    └─ ⚠ {gap}")

        if index.strategic_priorities:
            lines.append("\nStrategic Priorities:")
            for i, p in enumerate(index.strategic_priorities, 1):
                lines.append(f"  {i}. {p}")

        if index.top_knowledge_gaps:
            lines.append("\nKnowledge Gaps:")
            for gap in index.top_knowledge_gaps[:5]:
                lines.append(f"  └─ {gap}")

        return "\n".join(lines)


# ── Singleton ───────────────────────────────────────────────────────

_meta_galaxy: MetaGalaxy | None = None
_mg_lock = threading.Lock()


def get_meta_galaxy() -> MetaGalaxy:
    """Get the global MetaGalaxy instance."""
    global _meta_galaxy
    if _meta_galaxy is None:
        with _mg_lock:
            if _meta_galaxy is None:
                _meta_galaxy = MetaGalaxy()
    return _meta_galaxy
