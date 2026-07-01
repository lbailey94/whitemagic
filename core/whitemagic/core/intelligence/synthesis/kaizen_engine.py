# ruff: noqa: BLE001
"""KaizenEngine - Continuous Self-Improvement Discovery.

改善 (Kaizen) - Change for the better through continuous small improvements.
Analyzes memory system to find quality issues, gaps, and improvement opportunities.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ImprovementProposal:
    """A single improvement proposal."""

    id: str
    category: str  # quality, gap, integration, theme, performance
    title: str
    description: str
    impact: str  # high, medium, low
    effort: str  # high, medium, low
    auto_fixable: bool = False
    fix_action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KaizenReport:
    """Complete analysis report."""

    timestamp: datetime
    proposals: list[ImprovementProposal]
    metrics: dict[str, Any]

    @property
    def by_category(self) -> dict[str, list[ImprovementProposal]]:
        """
        Perform the by category operation.

        Returns:
            dict[str, list[ImprovementProposal]]
        """
        result: dict[str, list[ImprovementProposal]] = {}
        for p in self.proposals:
            if p.category not in result:
                result[p.category] = []
            result[p.category].append(p)
        return result


class KaizenEngine:
    """Continuous improvement engine for WhiteMagic memory system.

    Analyzes:
    - Quality issues (untitled, untagged, orphan tags)
    - Knowledge gaps (sparse regions in 4D space)
    - Integration opportunities (large clusters)
    - Emergent themes (potential new gardens)
    - Performance issues (duplicates, stale data)
    """

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            from whitemagic.config.paths import DB_PATH

            self.db_path = str(DB_PATH)
        else:
            self.db_path = str(Path(db_path))
        self._conn: sqlite3.Connection | None = None
        self._solution_lib = None

    def _get_solution_library(self) -> Any:
        """Lazy-load the SolutionLibrary."""
        if self._solution_lib is None:
            try:
                from whitemagic.core.intelligence.synthesis.solution_library import (
                    get_solution_library,
                )

                self._solution_lib = get_solution_library()  # type: ignore[assignment]
            except ImportError:
                self._solution_lib = None
        return self._solution_lib

    def _get_core_access(self) -> Any:
        """Lazy-load the CoreAccessLayer."""
        try:
            from whitemagic.core.intelligence.core_access import get_core_access

            return get_core_access()
        except ImportError:
            return None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            self._conn = conn
        return self._conn

    def analyze(self) -> KaizenReport:
        """Run full kaizen analysis with Rust acceleration for metrics."""
        proposals = []
        metrics = {}

        rust_metrics = self._gather_rust_metrics()
        if rust_metrics:
            metrics.update(rust_metrics)
            logger.info("Rust metrics: %s fields gathered", len(rust_metrics))

        # Quality checks
        proposals.extend(self._check_untitled())
        proposals.extend(self._check_untagged())
        proposals.extend(self._check_orphan_tags())

        # Gap analysis
        proposals.extend(self._find_knowledge_gaps())

        # Integration opportunities
        proposals.extend(self._find_large_clusters())

        # Theme discovery
        proposals.extend(self._discover_themes())

        # Performance
        proposals.extend(self._find_duplicates())

        # Core-connected analysis
        proposals.extend(self._find_constellation_anomalies())
        proposals.extend(self._find_broken_associations())
        proposals.extend(self._find_cross_constellation_gaps())

        # Solution Library Applications
        proposals.extend(self._find_solution_applications(proposals))

        # Codebase analysis (STRATA integration)
        codebase_proposals = self._analyze_codebase()
        proposals.extend(codebase_proposals)
        if codebase_proposals:
            metrics["strata_findings"] = len(codebase_proposals)

        # Collect remaining metrics from SQLite if not from Rust
        if "total_memories" not in metrics:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM memories")
            metrics["total_memories"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT tag) FROM tags")
            metrics["unique_tags"] = cur.fetchone()[0]

        return KaizenReport(
            timestamp=datetime.now(),
            proposals=proposals,
            metrics=metrics,
        )

    def _gather_rust_metrics(self) -> dict[str, Any]:
        """Gather metrics using Rust fast-path acceleration."""
        try:
            import whitemagic_rust as rs

            if not hasattr(rs, "synthesis_engine") or not hasattr(
                rs.synthesis_engine, "fast_kaizen_metrics"
            ):
                return {}

            conn = self._get_conn()
            cur = conn.cursor()

            # Gather memory titles
            cur.execute("SELECT title FROM memories")
            titles = [row[0] or "" for row in cur.fetchall()]

            # Gather holographic coordinates
            cur.execute("SELECT x, y, z, w FROM holographic_coords")
            coords = [[row[0], row[1], row[2], row[3]] for row in cur.fetchall()]

            rust_result = rs.synthesis_engine.fast_kaizen_metrics(titles, coords)

            metrics = {
                "untitled_count": rust_result.get("untitled_count", 0),
                "total_memories": len(titles),
                "quadrant_counts": dict(rust_result.get("quadrant_counts", {})),
                "avg_gravity": rust_result.get("avg_gravity", 0.0),
                "max_gravity": rust_result.get("max_gravity", 0.0),
                "min_gravity": rust_result.get("min_gravity", 0.0),
                "high_gravity_count": rust_result.get("high_gravity_count", 0),
            }

            return metrics
        except Exception as e:
            logger.debug(
                "Rust metrics gathering failed, using Python fallback: %s",
                e,
                exc_info=True,
            )
            return {}

    def _analyze_codebase(self) -> list[ImprovementProposal]:
        """Run STRATA static analysis on the WhiteMagic codebase itself.

        This extends kaizen beyond memory DB analysis to include codebase
        quality checks: structural stubs, dead code, archive drift, hardcoded
        paths, and 80+ other checks across 15 languages.
        """
        try:
            from whitemagic.tools.strata import FindingSeverity, Strata

            # Determine the WhiteMagic core path
            core_path = str(Path(__file__).parent.parent.parent.parent.parent)
            if not Path(core_path, "AGENTS.md").exists():
                return []

            strata = Strata(core_path)
            findings = strata.analyze(parallel=True, incremental=True)

            severity_to_impact = {
                FindingSeverity.ERROR: "high",
                FindingSeverity.WARNING: "medium",
                FindingSeverity.INFO: "low",
            }

            proposals: list[ImprovementProposal] = []
            for f in findings:
                proposals.append(
                    ImprovementProposal(
                        id=f"strata_{f.category}_{f.file}_{f.line}",
                        category="codebase_quality",
                        title=f"{f.category}: {f.message}",
                        description=f.file + (f":{f.line}" if f.line else ""),
                        impact=severity_to_impact.get(f.severity, "low"),
                        effort="low"
                        if f.severity == FindingSeverity.ERROR
                        else "medium",
                        auto_fixable=False,
                        metadata={
                            "source": "strata",
                            "category": f.category,
                            "file": f.file,
                            "line": f.line,
                            "suggestion": f.suggestion,
                        },
                    )
                )
            return proposals
        except Exception as e:
            logger.debug("STRATA codebase analysis skipped: %s", e)
            return []

    def _check_untitled(self) -> list[ImprovementProposal]:
        """Find memories without meaningful titles."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, title FROM memories
            WHERE title IS NULL OR title = '' OR title LIKE 'Untitled%'
        """)
        untitled = cur.fetchall()

        if not untitled:
            return []

        return [
            ImprovementProposal(
                id=f"quality_untitled_{len(untitled)}",
                category="quality",
                title=f"Fix {len(untitled)} untitled memories",
                description=f"Found {len(untitled)} memories without meaningful titles",
                impact="medium",
                effort="low",
                auto_fixable=True,
                fix_action="title_generator.fix_all()",
                metadata={
                    "count": len(untitled),
                    "sample_ids": [r["id"] for r in untitled[:5]],
                },
            )
        ]

    def _check_untagged(self) -> list[ImprovementProposal]:
        """Find memories without tags."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT m.id, m.title FROM memories m
            LEFT JOIN tags t ON m.id = t.memory_id
            WHERE t.tag IS NULL
        """)
        untagged = cur.fetchall()

        if not untagged:
            return []

        return [
            ImprovementProposal(
                id=f"quality_untagged_{len(untagged)}",
                category="quality",
                title=f"Tag {len(untagged)} untagged memories",
                description=f"Found {len(untagged)} memories without any tags",
                impact="medium",
                effort="medium",
                auto_fixable=True,
                fix_action="tag_normalizer.auto_tag_untagged()",
                metadata={"count": len(untagged)},
            )
        ]

    def _check_orphan_tags(self) -> list[ImprovementProposal]:
        """Find tags used only once."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT tag, COUNT(*) as cnt FROM tags
            GROUP BY tag HAVING cnt = 1
        """)
        orphans = cur.fetchall()

        if len(orphans) < 10:
            return []

        return [
            ImprovementProposal(
                id=f"quality_orphans_{len(orphans)}",
                category="quality",
                title=f"Review {len(orphans)} orphan tags",
                description="Tags used only once may need merging or removal",
                impact="low",
                effort="medium",
                auto_fixable=False,
                metadata={
                    "count": len(orphans),
                    "sample": [r["tag"] for r in orphans[:10]],
                },
            )
        ]

    def _find_knowledge_gaps(self) -> list[ImprovementProposal]:
        """Find sparse regions in 4D holographic space."""
        conn = self._get_conn()
        cur = conn.cursor()

        gaps = []
        try:
            cur.execute("""
                SELECT
                    CASE WHEN x < 0 THEN 'logical' ELSE 'emotional' END as x_region,
                    CASE WHEN y < 0 THEN 'detail' ELSE 'strategic' END as y_region,
                    COUNT(*) as cnt
                FROM holographic_coords
                GROUP BY x_region, y_region
            """)

            quadrants = {
                (r["x_region"], r["y_region"]): r["cnt"] for r in cur.fetchall()
            }

            for (x_reg, y_reg), count in quadrants.items():
                if count < 10:
                    gaps.append(
                        ImprovementProposal(
                            id=f"gap_{x_reg}_{y_reg}",
                            category="gap",
                            title=f"Knowledge gap: {x_reg} + {y_reg}",
                            description=f"Only {count} memories in {x_reg}/{y_reg} quadrant",
                            impact="medium",
                            effort="high",
                            auto_fixable=False,
                            metadata={"quadrant": f"{x_reg}/{y_reg}", "count": count},
                        )
                    )
        except Exception as e:
            logger.debug(
                "Knowledge gap analysis skipped (no holographic_coords): %s",
                e,
                exc_info=True,
            )

        return gaps

    def _find_large_clusters(self) -> list[ImprovementProposal]:
        """Find clusters that may need subdivision."""
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    ROUND(x, 1) as rx, ROUND(y, 1) as ry,
                    COUNT(*) as cnt
                FROM holographic_coords
                GROUP BY rx, ry
                HAVING cnt > 20
                ORDER BY cnt DESC
                LIMIT 5
            """)
        except Exception as e:
            logger.debug(
                "Large cluster analysis skipped (no holographic_coords): %s",
                e,
                exc_info=True,
            )
            return []

        large = cur.fetchall()
        proposals = []

        for cluster in large:
            proposals.append(
                ImprovementProposal(
                    id=f"integration_cluster_{cluster['rx']}_{cluster['ry']}",
                    category="integration",
                    title=f"Large cluster at ({cluster['rx']}, {cluster['ry']})",
                    description=f"{cluster['cnt']} memories clustered together - consider subdivision",
                    impact="medium",
                    effort="medium",
                    auto_fixable=True,
                    fix_action="sub_clustering.subdivide()",
                    metadata={
                        "location": (cluster["rx"], cluster["ry"]),
                        "size": cluster["cnt"],
                    },
                )
            )

        return proposals

    def _discover_themes(self) -> list[ImprovementProposal]:
        """Find emergent themes that could become gardens."""
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT t.tag, COUNT(*) as cnt, AVG(h.w) as avg_gravity
                FROM tags t
                JOIN holographic_coords h ON t.memory_id = h.memory_id
                GROUP BY t.tag
                HAVING cnt >= 5 AND avg_gravity > 0.6
                ORDER BY avg_gravity DESC
                LIMIT 10
            """)
        except Exception as e:
            logger.debug(
                "Theme discovery skipped (no holographic_coords): %s", e, exc_info=True
            )
            return []

        themes = cur.fetchall()
        proposals = []

        for theme in themes:
            if theme["tag"] not in ["long_term", "short_term", "session", "handoff"]:
                proposals.append(
                    ImprovementProposal(
                        id=f"theme_{theme['tag']}",
                        category="theme",
                        title=f"Potential garden: '{theme['tag']}'",
                        description=f"{theme['cnt']} memories, avg gravity {theme['avg_gravity']:.2f}",
                        impact="high",
                        effort="medium",
                        auto_fixable=False,
                        metadata={
                            "tag": theme["tag"],
                            "count": theme["cnt"],
                            "gravity": theme["avg_gravity"],
                        },
                    )
                )

        return proposals

    def _find_duplicates(self) -> list[ImprovementProposal]:
        """Find potential duplicate memories using Rust-accelerated similarity."""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT title, COUNT(*) as cnt FROM memories
            WHERE title IS NOT NULL AND title != ''
            GROUP BY title HAVING cnt > 1
        """)
        exact_dupes = cur.fetchall()

        similar_pairs = []
        try:
            from whitemagic.core.polyglot.mansion_bridge import get_mansion_bridge

            bridge = get_mansion_bridge()

            cur.execute(
                "SELECT id, title FROM memories WHERE title IS NOT NULL AND title != '' LIMIT 200"
            )
            memories = cur.fetchall()

            for i, m1 in enumerate(memories):
                for j, m2 in enumerate(memories):
                    if i < j:
                        sim = bridge.similarity(m1["title"], m2["title"])
                        if sim > 0.7:
                            similar_pairs.append(
                                {
                                    "id1": m1["id"],
                                    "id2": m2["id"],
                                    "title1": m1["title"],
                                    "title2": m2["title"],
                                    "similarity": sim,
                                }
                            )
        except Exception as e:
            logger.warning(
                "MansionBridge similarity check failed: %s", e, exc_info=True
            )

        proposals = []

        if exact_dupes:
            total_exact = sum(r["cnt"] - 1 for r in exact_dupes)
            proposals.append(
                ImprovementProposal(
                    id=f"perf_exact_duplicates_{total_exact}",
                    category="performance",
                    title=f"Review {total_exact} exact duplicate titles",
                    description=f"Found {len(exact_dupes)} titles with multiple memories",
                    impact="medium",
                    effort="low",
                    auto_fixable=True,
                    fix_action="consolidator.merge_exact_duplicates()",
                    metadata={
                        "duplicate_titles": len(exact_dupes),
                        "total_extra": total_exact,
                    },
                )
            )

        if similar_pairs:
            proposals.append(
                ImprovementProposal(
                    id=f"perf_similar_{len(similar_pairs)}",
                    category="performance",
                    title=f"Review {len(similar_pairs)} semantically similar memories",
                    description="Rust-detected similar titles that may be duplicates",
                    impact="medium",
                    effort="medium",
                    auto_fixable=False,
                    metadata={"pairs": similar_pairs[:10], "total": len(similar_pairs)},
                )
            )

        return proposals

    def _find_constellation_anomalies(self) -> list[ImprovementProposal]:
        """Find constellation anomalies: too dense, too sparse, or drifting."""
        cal = self._get_core_access()
        if not cal:
            return []

        proposals: list[ImprovementProposal] = []
        constellations = cal.get_all_constellations()
        if not constellations:
            return proposals

        for c in constellations:
            if c.size > 200:
                proposals.append(
                    ImprovementProposal(
                        id=f"constellation_overloaded_{c.name[:20]}",
                        category="integration",
                        title=f"Overloaded Constellation: {c.name} ({c.size} members)",
                        description=(
                            f"Constellation '{c.name}' has {c.size} members, which may "
                            f"indicate an overly broad cluster. Consider subdividing by "
                            f"sub-topic. Tags: {', '.join(c.dominant_tags[:3])}"
                        ),
                        impact="high",
                        effort="medium",
                        auto_fixable=False,
                        metadata={
                            "constellation": c.name,
                            "size": c.size,
                            "zone": c.zone,
                        },
                    )
                )

        for c in constellations:
            if c.zone in ("core", "inner_rim") and c.size < 5:
                proposals.append(
                    ImprovementProposal(
                        id=f"constellation_sparse_core_{c.name[:20]}",
                        category="quality",
                        title=f"Sparse Core Constellation: {c.name} ({c.size} members)",
                        description=(
                            f"Constellation '{c.name}' is in {c.zone} zone but has only "
                            f"{c.size} members. It may need enrichment or reclassification."
                        ),
                        impact="medium",
                        effort="low",
                        auto_fixable=False,
                        metadata={"constellation": c.name, "zone": c.zone},
                    )
                )

        return proposals

    def _find_broken_associations(self) -> list[ImprovementProposal]:
        """Find high-strength associations where one end has decayed."""
        cal = self._get_core_access()
        if not cal:
            return []

        broken = cal.find_broken_associations(limit=20)
        if not broken:
            return []

        return [
            ImprovementProposal(
                id=f"broken_associations_{len(broken)}",
                category="quality",
                title=f"Broken Associations: {len(broken)} high-strength links to decayed memories",
                description=(
                    "Found associations with strength > 0.5 where one memory has drifted "
                    "to FAR_EDGE (galactic_distance > 0.85). These are decayed knowledge "
                    "links that should be pruned or the drifted memory re-anchored."
                ),
                impact="medium",
                effort="low",
                auto_fixable=True,
                fix_action="association_miner.prune_broken(min_strength=0.5, max_distance=0.85)",
                metadata={"broken_count": len(broken), "sample": broken[:5]},
            )
        ]

    def _find_cross_constellation_gaps(self) -> list[ImprovementProposal]:
        """Find constellations that should be connected but have no association bridges."""
        cal = self._get_core_access()
        if not cal:
            return []

        constellations = cal.get_all_constellations()
        if len(constellations) < 2:
            return []

        bridges = cal.find_constellation_bridges(limit=50)
        bridged_pairs = set()
        for b in bridges:
            pair = tuple(sorted([b["constellation_1"], b["constellation_2"]]))
            bridged_pairs.add(pair)

        proposals = []
        unbridged = []
        for i, constellation in enumerate(constellations):
            for j in range(i + 1, len(constellations)):
                c1, c2 = constellations[i], constellations[j]
                pair = tuple(sorted([c1.name, c2.name]))
                if pair in bridged_pairs:
                    continue

                overlap = set(c1.dominant_tags) & set(c2.dominant_tags)
                if overlap:
                    unbridged.append(
                        {
                            "c1": c1.name,
                            "c2": c2.name,
                            "shared_tags": list(overlap),
                        }
                    )

        if unbridged:
            proposals.append(
                ImprovementProposal(
                    id=f"cross_constellation_gaps_{len(unbridged)}",
                    category="gap",
                    title=f"Unbridged Constellation Pairs ({len(unbridged)})",
                    description=(
                        f"Found {len(unbridged)} constellation pairs with overlapping tags "
                        f"but no association bridges. These represent potential cross-domain "
                        f"connections that haven't been mined."
                    ),
                    impact="high",
                    effort="medium",
                    auto_fixable=False,
                    metadata={"unbridged_pairs": unbridged[:10]},
                )
            )

        return proposals

    def _find_solution_applications(
        self, existing_proposals: list[ImprovementProposal]
    ) -> list[ImprovementProposal]:
        """Cross-reference existing proposals with the Solution Library to find implementation-ready code."""
        lib = self._get_solution_library()
        if not lib:
            return []

        apps = []
        for prop in existing_proposals:
            if prop.category in ["gap", "integration", "theme"]:
                context = {
                    "content": f"{prop.title} {prop.description}",
                    "tags": [prop.category, "kaizen"],
                }
                solutions = lib.find_nearest_solutions(context, k=1)

                if solutions:
                    sol = solutions[0]
                    apps.append(
                        ImprovementProposal(
                            id=f"sol_app_{prop.id}",
                            category="implementation",
                            title=f"Implementation: {sol.title}",
                            description=f"Actionable code found for '{prop.title}': {sol.description}",
                            impact=prop.impact,
                            effort="low",
                            auto_fixable=True,
                            fix_action=f"solution_library.apply('{sol.id}')",
                            metadata={"solution_id": sol.id, "original_prop": prop.id},
                        )
                    )
        return apps

    def apply_auto_fixes(self) -> dict[str, int]:
        """Apply all auto-fixable proposals."""
        report = self.analyze()
        results = {"applied": 0, "skipped": 0, "errors": 0}

        for proposal in report.proposals:
            if proposal.auto_fixable and proposal.fix_action:
                try:
                    if "title_generator" in proposal.fix_action:
                        from whitemagic.core.intelligence.synthesis.title_generator import (
                            get_title_generator,
                        )

                        get_title_generator().fix_all()
                    elif "tag_normalizer" in proposal.fix_action:
                        from whitemagic.core.intelligence.synthesis.tag_normalizer import (
                            get_tag_normalizer,
                        )

                        get_tag_normalizer().auto_tag_untagged()
                    elif "sub_clustering" in proposal.fix_action:
                        from whitemagic.core.intelligence.synthesis.sub_clustering import (
                            get_sub_clustering_engine,
                        )

                        get_sub_clustering_engine().subdivide_large_clusters()
                    results["applied"] += 1
                except Exception as e:
                    logger.debug("Kaizen proposal apply failed: %s", e, exc_info=True)
                    results["errors"] += 1
            else:
                results["skipped"] += 1

        return results

    _evolution_engine_instance: Any = None
    _meta_learning_engine_instance: Any = None
    _apotheosis_engine_instance: Any = None

    def _get_evolution_engine(self):
        """Lazy accessor for the ContinuousEvolutionEngine."""
        if self._evolution_engine_instance is None:
            from whitemagic.core.evolution.continuous_evolution import (
                ContinuousEvolutionEngine,
            )

            self._evolution_engine_instance = ContinuousEvolutionEngine()
        return self._evolution_engine_instance

    def evolution_run_cycle(self) -> dict[str, Any]:
        """Run a single continuous evolution cycle."""
        return self._get_evolution_engine().run_single_cycle()

    def evolution_get_status(self) -> dict[str, Any]:
        """Get continuous evolution engine status."""
        return self._get_evolution_engine().get_status()

    def evolution_stop(self) -> None:
        """Stop continuous evolution."""
        self._get_evolution_engine().stop()

    def _get_meta_learning_engine(self):
        """Lazy accessor for the MetaLearningEngine."""
        if self._meta_learning_engine_instance is None:
            from whitemagic.core.evolution.meta_learning import MetaLearningEngine

            self._meta_learning_engine_instance = MetaLearningEngine()
        return self._meta_learning_engine_instance

    def meta_update_pattern_metrics(self, **kwargs: Any) -> None:
        """Update metrics for a pattern after application."""
        self._get_meta_learning_engine().update_pattern_metrics(**kwargs)

    def meta_discover_patterns(self) -> list[Any]:
        """Discover meta-patterns from pattern metrics."""
        return self._get_meta_learning_engine().discover_meta_patterns()

    def meta_get_recommendations(
        self, context: dict | None = None, limit: int = 5
    ) -> list[tuple[str, float, str]]:
        """Get pattern recommendations based on meta-learning."""
        return self._get_meta_learning_engine().get_pattern_recommendations(
            context or {}, limit
        )

    def meta_get_summary(self) -> dict[str, Any]:
        """Get meta-learning summary."""
        return self._get_meta_learning_engine().get_meta_learning_summary()

    def _get_apotheosis_engine(self):
        """Lazy accessor for the ApotheosisEngine."""
        if self._apotheosis_engine_instance is None:
            from whitemagic.core.consciousness.apotheosis_engine import (
                get_apotheosis_engine,
            )

            self._apotheosis_engine_instance = get_apotheosis_engine()
        return self._apotheosis_engine_instance

    def apotheosis_start(self) -> None:
        """Start the Apotheosis Engine."""
        self._get_apotheosis_engine().start()

    def apotheosis_stop(self) -> None:
        """Stop the Apotheosis Engine."""
        self._get_apotheosis_engine().stop()

    def apotheosis_tick(self, available_tools: list[str]) -> dict[str, Any]:
        """Run a single Apotheosis Engine iteration."""
        return self._get_apotheosis_engine().tick(available_tools)

    def apotheosis_status_report(self) -> str:
        """Get human-readable Apotheosis status report."""
        return self._get_apotheosis_engine().get_status_report()


_kaizen_engine = None


def get_kaizen_engine() -> KaizenEngine:
    """
    Get the kaizen engine.

    Returns:
        KaizenEngine
    """
    global _kaizen_engine
    if _kaizen_engine is None:
        _kaizen_engine = KaizenEngine()
    return _kaizen_engine
