"""Galaxy Router — 6D Holographic Galaxy routing for memory operations.

Maps cognitive subsystem outputs to specialized galaxies, enabling
partitioned memory with per-galaxy lifecycle, search, and sharing.

v23.1: Phase 1 — substrate layer (Python-side routing).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Default galaxy types — user-extensible via register_galaxy()
DEFAULT_GALAXIES: dict[str, dict[str, Any]] = {
    "universal": {
        "description": "General-purpose memories (default)",
        "color": "#6b7280",
        "decay_multiplier": 1.0,
    },
    "self_learning": {
        "description": "Recursive improvement outcomes, pattern applications",
        "color": "#3b82f6",
        "decay_multiplier": 0.8,  # Slower decay — learning is valuable
    },
    "self_discovery": {
        "description": "Emergence insights, creative tensions, bicameral low-confidence",
        "color": "#8b5cf6",
        "decay_multiplier": 0.7,  # Slower decay — discoveries are precious
    },
    "insight": {
        "description": "Briefings, foresight, predictions, serendipity results",
        "color": "#f59e0b",
        "decay_multiplier": 0.9,
    },
    "creative_solutions": {
        "description": "HRR analogies, dream artifacts, novel combinations",
        "color": "#ec4899",
        "decay_multiplier": 0.85,
    },
    "oracle": {
        "description": "Calibration data, oracle suggestions, forecasting accuracy",
        "color": "#10b981",
        "decay_multiplier": 0.6,  # Slowest decay — calibration is long-term
    },
}


@dataclass
class GalaxyInfo:
    """Metadata about a galaxy."""

    name: str
    description: str
    color: str
    decay_multiplier: float
    created_at: datetime = field(default_factory=datetime.now)
    memory_count: int = 0


class GalaxyRouter:
    """Routes memories to galaxies based on source subsystem and content.

    The router maintains a registry of galaxies and a mapping from
    cognitive subsystems to default galaxies. When a memory is stored,
    the router determines which galaxy it belongs to.

    Usage:
        router = GalaxyRouter()
        galaxy = router.route("recursive_improvement_loop", metadata={"source": "ril"})
        # galaxy == "self_learning"

        memory = unified.store(content, galaxy=galaxy)
    """

    # Subsystem → default galaxy mapping
    SUBSYSTEM_MAP: dict[str, str] = {
        # Self-learning galaxy
        "recursive_improvement_loop": "self_learning",
        "pattern_miner": "self_learning",
        "kaizen_engine": "self_learning",
        "guideline_evolution": "self_learning",

        # Self-discovery galaxy
        "emergence_engine": "self_discovery",
        "bicameral_reasoner": "self_discovery",
        "corpus_callosum": "self_discovery",
        "multi_spectral_reasoner": "self_discovery",

        # Insight galaxy
        "insight_pipeline": "insight",
        "foresight_engine": "insight",
        "serendipity_engine": "insight",
        "predictive_engine": "insight",
        "self_model": "insight",

        # Creative solutions galaxy
        "dream_cycle": "creative_solutions",
        "dream_artifact_writer": "creative_solutions",
        "hrr_engine": "creative_solutions",
        "narrative_compressor": "creative_solutions",

        # Oracle galaxy
        "oracle": "oracle",
        "temporal_forecast_db": "oracle",
        "brier_score": "oracle",
        "prescience": "oracle",

        # Default → universal
        "user": "universal",
        "external": "universal",
        "mcp_bridge": "universal",
        "researcher": "universal",
        "knowledge_graph": "universal",
        # v23.4: Additional subsystem mappings
        "consolidation": "self_learning",
        "bridge_synthesizer": "self_discovery",
        "session_crystallizer": "insight",
        "entropy_scorer": "universal",
        "holographic_intake": "universal",
        "unified_orchestrator": "universal",
        "oms": "universal",
        "archaeology": "universal",
        "homeostatic_loop": "self_learning",
        "autonomous_learner": "self_learning",
        # v24: Codebase self-model → codex galaxy
        "codebase_scanner": "codex",
        "codebase_self_model": "codex",
    }

    def __init__(self) -> None:
        self._galaxies: dict[str, GalaxyInfo] = {}
        self._subsystem_overrides: dict[str, str] = {}
        self._init_default_galaxies()

    def _init_default_galaxies(self) -> None:
        for name, info in DEFAULT_GALAXIES.items():
            self._galaxies[name] = GalaxyInfo(
                name=name,
                description=info["description"],
                color=info["color"],
                decay_multiplier=info["decay_multiplier"],
            )

    def register_galaxy(
        self,
        name: str,
        description: str = "",
        color: str = "#6b7280",
        decay_multiplier: float = 1.0,
    ) -> GalaxyInfo:
        """Register a new user-defined galaxy."""
        if name in self._galaxies:
            logger.warning("Galaxy '%s' already exists, updating", name)
        info = GalaxyInfo(
            name=name,
            description=description,
            color=color,
            decay_multiplier=decay_multiplier,
        )
        self._galaxies[name] = info
        logger.info("Registered galaxy: %s", name)
        return info

    def map_subsystem(self, subsystem: str, galaxy: str) -> None:
        """Override the default galaxy mapping for a subsystem."""
        if galaxy not in self._galaxies:
            raise ValueError(f"Unknown galaxy: {galaxy}. Register it first.")
        self._subsystem_overrides[subsystem] = galaxy
        logger.debug("Mapped subsystem '%s' → galaxy '%s'", subsystem, galaxy)

    def route(self, subsystem: str, metadata: dict[str, Any] | None = None) -> str:
        """Determine which galaxy a memory from a subsystem belongs to.

        Args:
            subsystem: The name of the cognitive subsystem producing the memory.
            metadata: Optional metadata that may contain an explicit galaxy override.

        Returns:
            Galaxy name string.
        """
        # 1. Explicit override in metadata takes highest priority
        if metadata and "galaxy" in metadata:
            galaxy = str(metadata["galaxy"])
            if galaxy in self._galaxies:
                return galaxy
            logger.warning("Metadata specified unknown galaxy '%s', falling back", galaxy)

        # 2. Subsystem override (runtime mapping)
        if subsystem in self._subsystem_overrides:
            return self._subsystem_overrides[subsystem]

        # 3. Default subsystem mapping
        if subsystem in self.SUBSYSTEM_MAP:
            return self.SUBSYSTEM_MAP[subsystem]

        # 4. Default to universal
        return "universal"

    def get_galaxy(self, name: str) -> GalaxyInfo | None:
        """Get info about a galaxy by name."""
        return self._galaxies.get(name)

    def list_galaxies(self) -> dict[str, GalaxyInfo]:
        """List all registered galaxies."""
        return dict(self._galaxies)

    def get_decay_multiplier(self, galaxy: str) -> float:
        """Get the decay multiplier for a galaxy."""
        info = self._galaxies.get(galaxy)
        if info:
            return info.decay_multiplier
        return 1.0

    def migrate(
        self,
        memory_id: str,
        target_galaxy: str,
        unified_memory: Any,
    ) -> bool:
        """Migrate a memory from one galaxy to another.

        Args:
            memory_id: The ID of the memory to migrate.
            target_galaxy: The destination galaxy name.
            unified_memory: The UnifiedMemory instance to operate on.

        Returns:
            True if migration succeeded, False otherwise.
        """
        if target_galaxy not in self._galaxies:
            logger.error("Cannot migrate to unknown galaxy: %s", target_galaxy)
            return False

        memory = unified_memory.recall(memory_id)
        if memory is None:
            logger.error("Cannot migrate non-existent memory: %s", memory_id)
            return False

        old_galaxy = memory.galaxy
        memory.galaxy = target_galaxy
        memory.metadata["galaxy_migrated_from"] = old_galaxy
        memory.metadata["galaxy_migrated_at"] = datetime.now().isoformat()

        try:
            unified_memory.backend.store(memory)
            logger.info(
                "Migrated memory %s: %s → %s",
                memory_id,
                old_galaxy,
                target_galaxy,
            )
            return True
        except Exception as e:
            logger.error("Galaxy migration failed for %s: %s", memory_id, e)
            return False

    def get_galaxy_stats(self, galaxy: str, unified_memory: Any) -> dict[str, Any]:
        """Get statistics for a specific galaxy.

        Args:
            galaxy: Galaxy name.
            unified_memory: UnifiedMemory instance for DB access.

        Returns:
            Dict with count, avg_importance, avg_galactic_distance, zone_distribution.
        """
        import sqlite3

        try:
            with unified_memory.backend.pool.connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT COUNT(*) as count, "
                    "COALESCE(AVG(importance), 0) as avg_importance, "
                    "COALESCE(AVG(galactic_distance), 0) as avg_distance "
                    "FROM memories WHERE galaxy = ?",
                    (galaxy,),
                ).fetchone()

                # Zone distribution
                zone_rows = conn.execute(
                    "SELECT "
                    "CASE "
                    "  WHEN galactic_distance < 0.2 THEN 'core' "
                    "  WHEN galactic_distance < 0.4 THEN 'inner_rim' "
                    "  WHEN galactic_distance < 0.6 THEN 'mid_band' "
                    "  WHEN galactic_distance < 0.8 THEN 'outer_rim' "
                    "  ELSE 'far_edge' "
                    "END as zone, COUNT(*) as count "
                    "FROM memories WHERE galaxy = ? "
                    "GROUP BY zone ORDER BY zone",
                    (galaxy,),
                ).fetchall()

                zones = {r["zone"]: r["count"] for r in zone_rows}

                return {
                    "galaxy": galaxy,
                    "count": row["count"],
                    "avg_importance": round(row["avg_importance"], 3),
                    "avg_galactic_distance": round(row["avg_distance"], 3),
                    "zone_distribution": zones,
                }
        except (sqlite3.Error, AttributeError, TypeError) as e:
            logger.error("Galaxy stats failed for '%s': %s", galaxy, e)
            return {"galaxy": galaxy, "count": 0, "error": str(e)}


# Singleton
_router: GalaxyRouter | None = None


def get_galaxy_router() -> GalaxyRouter:
    """Get the singleton GalaxyRouter instance."""
    global _router
    if _router is None:
        _router = GalaxyRouter()
    return _router
