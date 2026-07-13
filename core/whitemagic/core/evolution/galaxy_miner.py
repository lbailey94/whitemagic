# ruff: noqa: BLE001
"""🌌 Galaxy Pattern Miner - Extract Patterns from Archive DBs

Mines patterns from holographic galaxy memory databases to feed the
recursive evolution engine. Analyzes 111K+ archived memories for:
- Access patterns (frequency, co-access, temporal)
- Semantic clusters (cross-galaxy links)
- Optimization opportunities (hot paths, cache candidates)

Part of Phase 3 Recursive Evolution - Data Lake Integration.
"""

import logging
import sqlite3
from whitemagic.core.memory.db_manager import safe_connect
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Rust acceleration (S026 VC4)
try:
    import whitemagic_rust as _wr

    _rust_galaxy_miner = getattr(_wr, "galaxy_miner", None)
    RUST_GALAXY_MINER_AVAILABLE = _rust_galaxy_miner is not None
except ImportError:
    _rust_galaxy_miner = None
    RUST_GALAXY_MINER_AVAILABLE = False
    logger.debug("Rust galaxy_miner not available, using Python fallback")


@dataclass
class AccessPattern:
    """Represents a discovered access pattern."""

    pattern_id: str
    pattern_type: str  # 'frequent_access', 'co_access', 'temporal', 'cache_candidate'
    memory_ids: list[str]
    frequency: int
    confidence: float
    metadata: dict[str, Any]
    discovered_at: str


@dataclass
class SemanticCluster:
    """Represents a semantic cluster across galaxies."""

    cluster_id: str
    memory_ids: list[str]
    common_tags: set[str]
    avg_importance: float
    galaxy_sources: list[str]
    confidence: float


class GalaxyPatternMiner:
    """Mine patterns from galaxy archive databases."""

    def __init__(self, galaxy_paths: list[str]):
        """Initialize the miner.

        Args:
            galaxy_paths: List of paths to galaxy DB files
        """
        self.galaxy_paths = galaxy_paths
        self.connections: dict[str, sqlite3.Connection] = {}
        self.patterns: list[AccessPattern] = []
        self.clusters: list[SemanticCluster] = []

        logger.info(
            "🌌 GalaxyPatternMiner initialized with %s galaxies", len(galaxy_paths)
        )

    def connect(self) -> None:
        """Connect to all galaxy databases."""
        for path in self.galaxy_paths:
            if not Path(path).exists():
                logger.warning("Galaxy DB not found: %s", path)
                continue

            try:
                conn = safe_connect(path)
                conn.row_factory = sqlite3.Row
                self.connections[path] = conn
                logger.info("✓ Connected to: %s", Path(path).name)
            except Exception as e:
                logger.error("Failed to connect to %s: %s", path, e, exc_info=True)

    def disconnect(self) -> None:
        """Close all database connections."""
        for conn in self.connections.values():
            conn.close()
        self.connections.clear()

    def mine_access_patterns(self, min_frequency: int = 5) -> list[AccessPattern]:
        """Mine memory access patterns from access logs.

        Args:
            min_frequency: Minimum access count to consider

        Returns:
            List of discovered access patterns
        """
        # Route to Rust if available
        if RUST_GALAXY_MINER_AVAILABLE and _rust_galaxy_miner is not None:
            patterns = []
            for db_path in self.galaxy_paths:
                if Path(db_path).exists():
                    try:
                        rust_patterns = _rust_galaxy_miner.mine_access_patterns(
                            db_path, min_frequency
                        )
                        for rp in rust_patterns:
                            patterns.append(
                                AccessPattern(
                                    pattern_id=rp.pattern_id,
                                    pattern_type=rp.pattern_type,
                                    memory_ids=rp.memory_ids,
                                    frequency=rp.frequency,
                                    confidence=rp.confidence,
                                    metadata={"source_galaxy": rp.source_galaxy},
                                    discovered_at=datetime.now().isoformat(),
                                )
                            )
                    except Exception as e:
                        logger.warning(
                            "Rust mining failed for %s: %s", db_path, e, exc_info=True
                        )
            self.patterns.extend(patterns)
            logger.info("✓ Discovered %s access patterns (Rust)", len(patterns))
            return patterns

        # Python fallback
        logger.info("🔍 Mining access patterns...")
        patterns = []

        for db_path, conn in self.connections.items():
            try:
                cursor = conn.execute(
                    """
                    SELECT id, access_count, accessed_at
                    FROM memories
                    WHERE access_count >= ?
                    AND memory_type != 'quarantined'
                    ORDER BY access_count DESC
                    LIMIT 1000
                """,
                    (min_frequency,),
                )

                frequent_memories = cursor.fetchall()

                if frequent_memories:
                    # Create pattern for frequently accessed memories
                    memory_ids = [row["id"] for row in frequent_memories]
                    avg_access = sum(
                        row["access_count"] for row in frequent_memories
                    ) / len(frequent_memories)

                    pattern = AccessPattern(
                        pattern_id=f"freq_access_{Path(db_path).stem}",
                        pattern_type="frequent_access",
                        memory_ids=memory_ids,
                        frequency=int(avg_access),
                        confidence=min(1.0, len(memory_ids) / 100.0),
                        metadata={
                            "source_galaxy": Path(db_path).name,
                            "total_memories": len(memory_ids),
                            "avg_access_count": avg_access,
                            "max_access_count": max(
                                row["access_count"] for row in frequent_memories
                            ),
                        },
                        discovered_at=datetime.now().isoformat(),
                    )
                    patterns.append(pattern)
                    logger.info(
                        "  Found %s frequently accessed memories in %s",
                        len(memory_ids),
                        Path(db_path).name,
                    )

            except Exception as e:
                logger.error(
                    "Error mining access patterns from %s: %s",
                    db_path,
                    e,
                    exc_info=True,
                )

        self.patterns.extend(patterns)
        logger.info("✓ Discovered %s access patterns", len(patterns))
        return patterns

    def mine_co_access_patterns(
        self, min_co_occurrence: int = 3
    ) -> list[AccessPattern]:
        """Mine co-access patterns (memories accessed together).

        Args:
            min_co_occurrence: Minimum times memories must be accessed together

        Returns:
            List of co-access patterns
        """
        logger.info("🔍 Mining co-access patterns...")
        patterns = []

        for db_path, conn in self.connections.items():
            try:
                cursor = conn.execute(
                    """
                    SELECT m1.id as id1, m2.id as id2,
                           COUNT(*) as co_access_count
                    FROM memories m1
                    JOIN memories m2 ON
                        m1.id < m2.id AND
                        ABS(JULIANDAY(m1.accessed_at) - JULIANDAY(m2.accessed_at)) < 0.042
                    WHERE m1.memory_type != 'quarantined'
                    AND m2.memory_type != 'quarantined'
                    GROUP BY m1.id, m2.id
                    HAVING co_access_count >= ?
                    ORDER BY co_access_count DESC
                    LIMIT 100
                """,
                    (min_co_occurrence,),
                )

                co_access_pairs = cursor.fetchall()

                if co_access_pairs:
                    # Group into clusters
                    for row in co_access_pairs:
                        pattern = AccessPattern(
                            pattern_id=f"co_access_{row['id1'][:8]}_{row['id2'][:8]}",
                            pattern_type="co_access",
                            memory_ids=[row["id1"], row["id2"]],
                            frequency=row["co_access_count"],
                            confidence=min(1.0, row["co_access_count"] / 10.0),
                            metadata={
                                "source_galaxy": Path(db_path).name,
                                "co_access_count": row["co_access_count"],
                            },
                            discovered_at=datetime.now().isoformat(),
                        )
                        patterns.append(pattern)

                    logger.info(
                        "  Found %s co-access pairs in %s",
                        len(co_access_pairs),
                        Path(db_path).name,
                    )

            except Exception as e:
                logger.error(
                    "Error mining co-access patterns from %s: %s",
                    db_path,
                    e,
                    exc_info=True,
                )

        self.patterns.extend(patterns)
        logger.info("✓ Discovered %s co-access patterns", len(patterns))
        return patterns

    def mine_cache_candidates(
        self, min_access: int = 10, min_importance: float = 0.7
    ) -> list[AccessPattern]:
        """Identify memories that should be cached.

        Args:
            min_access: Minimum access count
            min_importance: Minimum importance score

        Returns:
            List of cache candidate patterns
        """
        # Route to Rust if available
        if RUST_GALAXY_MINER_AVAILABLE and _rust_galaxy_miner is not None:
            patterns = []
            for db_path in self.galaxy_paths:
                if Path(db_path).exists():
                    try:
                        rust_patterns = _rust_galaxy_miner.mine_cache_candidates(
                            db_path, min_access, min_importance
                        )
                        for rp in rust_patterns:
                            patterns.append(
                                AccessPattern(
                                    pattern_id=rp.pattern_id,
                                    pattern_type=rp.pattern_type,
                                    memory_ids=rp.memory_ids,
                                    frequency=rp.frequency,
                                    confidence=rp.confidence,
                                    metadata={"source_galaxy": rp.source_galaxy},
                                    discovered_at=datetime.now().isoformat(),
                                )
                            )
                    except Exception as e:
                        logger.warning(
                            "Rust cache mining failed for %s: %s",
                            db_path,
                            e,
                            exc_info=True,
                        )
            self.patterns.extend(patterns)
            logger.info("✓ Discovered %s cache candidates (Rust)", len(patterns))
            return patterns

        # Python fallback
        logger.info("🔍 Mining cache candidates...")
        patterns = []

        for db_path, conn in self.connections.items():
            try:
                cursor = conn.execute(
                    """
                    SELECT id, title, access_count, importance,
                           LENGTH(content) as content_size
                    FROM memories
                    WHERE access_count >= ?
                    AND importance >= ?
                    AND memory_type != 'quarantined'
                    ORDER BY access_count * importance DESC
                    LIMIT 500
                """,
                    (min_access, min_importance),
                )

                candidates = cursor.fetchall()

                if candidates:
                    memory_ids = [row["id"] for row in candidates]
                    avg_access = sum(row["access_count"] for row in candidates) / len(
                        candidates
                    )
                    avg_importance = sum(row["importance"] for row in candidates) / len(
                        candidates
                    )

                    pattern = AccessPattern(
                        pattern_id=f"cache_candidates_{Path(db_path).stem}",
                        pattern_type="cache_candidate",
                        memory_ids=memory_ids,
                        frequency=int(avg_access),
                        confidence=min(1.0, (avg_access * avg_importance) / 10.0),
                        metadata={
                            "source_galaxy": Path(db_path).name,
                            "total_candidates": len(memory_ids),
                            "avg_access_count": avg_access,
                            "avg_importance": avg_importance,
                            "avg_content_size": sum(
                                row["content_size"] for row in candidates
                            )
                            / len(candidates),
                        },
                        discovered_at=datetime.now().isoformat(),
                    )
                    patterns.append(pattern)
                    logger.info(
                        "  Found %s cache candidates in %s",
                        len(memory_ids),
                        Path(db_path).name,
                    )

            except Exception as e:
                logger.error(
                    "Error mining cache candidates from %s: %s",
                    db_path,
                    e,
                    exc_info=True,
                )

        self.patterns.extend(patterns)
        logger.info("✓ Discovered %s cache candidate patterns", len(patterns))
        return patterns

    def mine_semantic_clusters(
        self, min_cluster_size: int = 3
    ) -> list[SemanticCluster]:
        """Mine semantic clusters based on tags and content.

        Args:
            min_cluster_size: Minimum memories in a cluster

        Returns:
            List of semantic clusters
        """
        # Route to Rust if available
        if RUST_GALAXY_MINER_AVAILABLE and _rust_galaxy_miner is not None:
            clusters = []
            for db_path in self.galaxy_paths:
                if Path(db_path).exists():
                    try:
                        rust_clusters = _rust_galaxy_miner.mine_semantic_clusters(
                            db_path, min_cluster_size
                        )
                        for rc in rust_clusters:
                            clusters.append(
                                SemanticCluster(
                                    cluster_id=rc.cluster_id,
                                    memory_ids=rc.memory_ids,
                                    common_tags=set(rc.common_tags),
                                    avg_importance=rc.avg_importance,
                                    galaxy_sources=[Path(db_path).name],
                                    confidence=min(1.0, rc.size / 50.0),
                                )
                            )
                    except Exception as e:
                        logger.warning(
                            "Rust cluster mining failed for %s: %s",
                            db_path,
                            e,
                            exc_info=True,
                        )
            self.clusters.extend(clusters)
            logger.info("✓ Discovered %s semantic clusters (Rust)", len(clusters))
            return clusters

        # Python fallback
        logger.info("🔍 Mining semantic clusters...")
        clusters = []

        # Aggregate tags across all galaxies
        tag_to_memories: dict[str, list[tuple[str, str, float]]] = defaultdict(list)

        for db_path, conn in self.connections.items():
            try:
                cursor = conn.execute("""
                    SELECT m.id, GROUP_CONCAT(t.tag, ',') as tags, m.importance
                    FROM memories m
                    JOIN tags t ON m.id = t.memory_id
                    WHERE m.memory_type != 'quarantined'
                    GROUP BY m.id
                    HAVING tags IS NOT NULL
                    LIMIT 10000
                """)

                for row in cursor.fetchall():
                    memory_id = row["id"]
                    tags_str = row["tags"] or ""
                    importance = row["importance"] or 0.5

                    tags = set(t.strip() for t in tags_str.split(",") if t.strip())

                    for tag in tags:
                        tag_to_memories[tag].append(
                            (memory_id, Path(db_path).name, importance)
                        )

            except Exception as e:
                logger.error(
                    "Error mining semantic clusters from %s: %s",
                    db_path,
                    e,
                    exc_info=True,
                )

        # Create clusters from tags with enough members
        for tag, memories in tag_to_memories.items():
            if len(memories) >= min_cluster_size:
                memory_ids = [m[0] for m in memories]
                galaxy_sources = list(set(m[1] for m in memories))
                avg_importance = sum(m[2] for m in memories) / len(memories)

                cluster = SemanticCluster(
                    cluster_id=f"semantic_{tag}",
                    memory_ids=memory_ids,
                    common_tags={tag},
                    avg_importance=avg_importance,
                    galaxy_sources=galaxy_sources,
                    confidence=min(1.0, len(memories) / 50.0),
                )
                clusters.append(cluster)

        self.clusters.extend(clusters)
        logger.info("✓ Discovered %s semantic clusters", len(clusters))
        return clusters

    def get_summary(self) -> dict[str, Any]:
        """Get mining summary statistics."""
        pattern_types = Counter(p.pattern_type for p in self.patterns)

        return {
            "total_patterns": len(self.patterns),
            "total_clusters": len(self.clusters),
            "pattern_types": dict(pattern_types),
            "galaxies_analyzed": len(self.connections),
            "avg_pattern_confidence": sum(p.confidence for p in self.patterns)
            / len(self.patterns)
            if self.patterns
            else 0.0,
            "avg_cluster_size": sum(len(c.memory_ids) for c in self.clusters)
            / len(self.clusters)
            if self.clusters
            else 0.0,
        }


# Singleton instance
_galaxy_miner: GalaxyPatternMiner | None = None


def get_galaxy_miner(galaxy_paths: list[str] | None = None) -> GalaxyPatternMiner:
    """Get the singleton GalaxyPatternMiner instance.

    Args:
        galaxy_paths: List of galaxy DB paths (only used on first call)

    Returns:
        GalaxyPatternMiner instance
    """
    global _galaxy_miner
    if _galaxy_miner is None:
        if galaxy_paths is None:
            from whitemagic.config.paths import MEMORY_DIR, PROJECT_ROOT, WM_ROOT

            galaxy_paths = []
            # Scan per-galaxy DBs (v23+ galaxy-first architecture)
            galaxies_dir = MEMORY_DIR / "galaxies"
            if galaxies_dir.exists():
                for gdir in galaxies_dir.iterdir():
                    if gdir.is_dir():
                        gdb = gdir / "whitemagic.db"
                        if gdb.exists():
                            galaxy_paths.append(str(gdb))
            # Legacy fallbacks (may be empty post-migration)
            legacy = [
                str(WM_ROOT / "memory/whitemagic.db"),
                str(WM_ROOT / "memory/whitemagic_cold.db"),
                str(PROJECT_ROOT / "archive/memory_archive/whitemagic_hot.db"),
            ]
            for p in legacy:
                if p not in galaxy_paths:
                    galaxy_paths.append(p)
        _galaxy_miner = GalaxyPatternMiner(galaxy_paths)
    return _galaxy_miner
