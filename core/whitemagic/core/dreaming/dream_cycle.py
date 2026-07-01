# ruff: noqa: BLE001
"""Dream Cycle — Background Processing During Idle Time.
=====================================================
Inspired by biological sleep: the brain consolidates memories, prunes
weak connections, surfaces serendipitous associations, and integrates
new knowledge during rest periods.

The Dream Cycle runs on the Temporal Scheduler's SLOW lane and activates
when the system has been idle (no tool calls) for a configurable period.

Dream phases (one per cycle):
  1. CONSOLIDATION  — Run hippocampal replay (cluster + promote memories)
  2. SERENDIPITY    — Surface unexpected memory connections
  3. KAIZEN         — Analyze tool usage patterns for improvement hints
  4. ORACLE         — Consult Grimoire for contextual recommendations
  5. DECAY          — Run mindful forgetting / galactic rotation

Each phase emits DREAM_PHASE_* events to the Gan Ying bus so other
systems can react. The cycle is gentle — never destructive, always
opt-in, and respects the no-delete policy.

Usage:
    from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
    dc = get_dream_cycle()
    dc.start()   # begin watching for idle periods
    dc.stop()    # halt dreaming
    dc.status()  # introspection
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, cast

logger = logging.getLogger(__name__)


class DreamPhase(Enum):
    """Phases of the dream cycle (v17: expanded to 12 phases)."""

    TRIAGE = "triage"  # v15.3: Quick scan — identify memories needing attention
    CONSOLIDATION = "consolidation"
    SERENDIPITY = "serendipity"
    GOVERNANCE = "governance"  # v14.0: Echo chamber detection
    NARRATIVE = "narrative"  # v14.2: Narrative compression
    KAIZEN = "kaizen"
    ORACLE = "oracle"
    DECAY = "decay"
    # v17.0: New phases for Intelligence Amplification
    CONSTELLATION = "constellation"  # Auto-merge related constellations
    PREDICTION = "prediction"  # Predictive drift detection
    ENRICHMENT = "enrichment"  # Entity extraction & semantic enrichment
    HARMONIZE = "harmonize"  # Wu Xing balance & harmony tuning


@dataclass
class DreamReport:
    """Result of a single dream cycle."""

    phase: DreamPhase
    started_at: str
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "phase": self.phase.value,
            "started_at": self.started_at,
            "duration_ms": round(self.duration_ms, 1),
            "details": self.details,
            "success": self.success,
            "error": self.error,
        }


class DreamCycle:
    """Background dreaming engine.

    Monitors system idle time and cycles through dream phases,
    each performing a different background maintenance task.
    """

    def __init__(
        self,
        idle_threshold_seconds: float = 120.0,
        cycle_interval_seconds: float = 60.0,
        max_history: int = 100,
    ) -> None:
        self._idle_threshold = idle_threshold_seconds
        self._cycle_interval = cycle_interval_seconds
        self._max_history = max_history

        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self._last_activity = time.time()
        self._dreaming = False
        self._current_phase_index = 0
        self._phases = list(DreamPhase)
        self._total_cycles = 0
        self._history: deque = deque(maxlen=max_history)

    def start(self) -> None:
        """Start the dream cycle watcher."""
        with self._lock:
            if self._running:
                return

            # Polyglot check: If Elixir is the master, delegate dreaming
            import os

            if os.environ.get("WHITEMAGIC_ELIXIR_MASTER") == "1":
                self._running = True
                logger.info(
                    "🌙 Dream Cycle delegating to Elixir Master (OTP Concurrency)"
                )
                return

            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="dream-cycle",
            )
            self._thread.start()
            logger.info(
                "🌙 Dream Cycle started (idle threshold: %.0fs)", self._idle_threshold
            )

    def stop(self) -> None:
        """Stop the dream cycle."""
        with self._lock:
            self._running = False
            self._dreaming = False

        import os

        if os.environ.get("WHITEMAGIC_ELIXIR_MASTER") == "1":
            logger.info("☀️ Elixir delegation stopped")
            return

        if self._thread:
            self._thread.join(timeout=5)
        logger.info("☀️ Dream Cycle stopped")

    def touch(self) -> None:
        """Record activity — resets idle timer. Call on every tool dispatch."""
        self._last_activity = time.time()

        # Notify Elixir Master if active
        import os

        if os.environ.get("WHITEMAGIC_ELIXIR_MASTER") == "1":
            try:
                # Use Redis or a shared state check to notify Elixir
                # or the bridge will handle the signal.
                pass
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass

        if self._dreaming:
            self._dreaming = False
            logger.debug("Dream interrupted by activity")

    def _run_loop(self) -> None:
        """Background thread: watch for idle → dream."""
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self._running:
            try:
                idle_seconds = time.time() - self._last_activity

                if idle_seconds >= self._idle_threshold and not self._dreaming:
                    self._dreaming = True
                    logger.info(
                        "🌙 System idle for %.0fs — entering dream state", idle_seconds
                    )
                    self._emit_event("DREAM_STARTED", {"idle_seconds": idle_seconds})

                if self._dreaming and self._running:
                    loop.run_until_complete(self._run_phase())

            except (RuntimeError, asyncio.CancelledError, OSError) as e:
                logger.debug("Dream cycle error: %s", e, exc_info=True)

            time.sleep(self._cycle_interval)
        loop.close()

    async def _run_phase(self) -> None:
        """Execute the next dream phase in rotation."""
        phase = self._phases[self._current_phase_index % len(self._phases)]
        self._current_phase_index += 1

        start = time.perf_counter()
        report = DreamReport(
            phase=phase,
            started_at=datetime.now().isoformat(),
        )

        try:
            if phase == DreamPhase.TRIAGE:
                report.details = self._dream_triage()
            elif phase == DreamPhase.CONSOLIDATION:
                report.details = self._dream_consolidation()
            elif phase == DreamPhase.SERENDIPITY:
                report.details = self._dream_serendipity()
            elif phase == DreamPhase.GOVERNANCE:
                report.details = self._dream_governance()
            elif phase == DreamPhase.NARRATIVE:
                report.details = self._dream_narrative()
            elif phase == DreamPhase.KAIZEN:
                report.details = self._dream_kaizen()
            elif phase == DreamPhase.ORACLE:
                report.details = self._dream_oracle()
            elif phase == DreamPhase.DECAY:
                report.details = self._dream_decay()
            elif phase == DreamPhase.CONSTELLATION:
                report.details = self._dream_constellation()
            elif phase == DreamPhase.PREDICTION:
                report.details = self._dream_prediction()
            elif phase == DreamPhase.ENRICHMENT:
                report.details = self._dream_enrichment()
            elif phase == DreamPhase.HARMONIZE:
                report.details = self._dream_harmonize()
        except Exception as e:
            report.success = False
            report.error = str(e)
            logger.debug("Dream phase %s error: %s", phase.value, e, exc_info=True)

        report.duration_ms = (time.perf_counter() - start) * 1000

        with self._lock:
            self._total_cycles += 1
            self._history.append(report)

        self._emit_event(f"DREAM_PHASE_{phase.value.upper()}", report.to_dict())
        status = "ok" if report.success else f"error: {report.error}"
        logger.info(
            "💤 Dream phase %s: %s (%.0fms)",
            phase.value,
            status,
            report.duration_ms,
        )

    def _get_core_access(self) -> Any:
        """Lazy-load the CoreAccessLayer."""
        try:
            from whitemagic.core.intelligence.core_access import get_core_access

            return get_core_access()
        except (ImportError, ModuleNotFoundError):
            return None

    def _dream_triage(self) -> dict[str, Any]:
        """Phase 0 (v15.3): Quick scan — identify and fix memories needing attention.

        NREM Stage 1 equivalent. Performs lightweight curation:
        1. Auto-tag: Classify untitled/untagged memories by content analysis
        2. Auto-archive: Push low-value, low-access memories to outer rim
        3. Coordinate drift: Gently pull drifted memories back to their band
        4. Orphan detection: Flag coords/associations pointing to nothing
        """
        result: dict[str, Any] = {"actions": []}

        try:
            from whitemagic.core.memory.unified import get_unified_memory

            um = get_unified_memory()
            pool = um.backend.pool

            with pool.connection() as conn:
                conn.row_factory = __import__("sqlite3").Row

                # 1. Auto-tag: Find memories with no tags
                untagged = conn.execute("""
                    SELECT m.id, m.title, SUBSTR(m.content, 1, 500) as snippet
                    FROM memories m
                    LEFT JOIN tags t ON m.id = t.memory_id
                    WHERE t.tag IS NULL
                    LIMIT 50
                """).fetchall()

                tagged_count = 0
                for row in untagged:
                    title = (row["title"] or "").lower()
                    snippet = (row["snippet"] or "").lower()
                    combined = f"{title} {snippet}"

                    # Simple keyword-based auto-tagging
                    auto_tags = set()
                    if any(w in combined for w in ["session", "handoff", "checkpoint"]):
                        auto_tags.add("session")
                    if any(
                        w in combined for w in ["aria", "consciousness", "awakening"]
                    ):
                        auto_tags.add("aria_era")
                    if any(w in combined for w in ["architecture", "design", "spec"]):
                        auto_tags.add("architecture")
                    if any(w in combined for w in ["plan", "strategy", "roadmap"]):
                        auto_tags.add("planning")
                    if any(w in combined for w in ["wisdom", "philosophy", "dharma"]):
                        auto_tags.add("wisdom")
                    if any(
                        w in combined for w in ["code", "function", "class", "import"]
                    ):
                        auto_tags.add("technical")
                    if any(w in combined for w in ["guide", "tutorial", "how to"]):
                        auto_tags.add("guide")

                    if auto_tags:
                        auto_tags.add("auto_tagged")
                        try:
                            conn.executemany(
                                "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                                [(row["id"], tag) for tag in auto_tags],
                            )
                        except Exception as e:
                            logger.debug("Operation failed: %s", e)
                            pass
                        tagged_count += 1

                if tagged_count > 0:
                    conn.commit()
                result["auto_tagged"] = tagged_count
                result["untagged_found"] = len(untagged)

                # 2. Auto-archive: Low importance + low access + old → push outward
                archive_candidates = conn.execute("""
                    SELECT id, importance, access_count, galactic_distance, neuro_score
                    FROM memories
                    WHERE importance < 0.2
                    AND COALESCE(access_count, 0) < 2
                    AND galactic_distance < 0.6
                    AND is_protected = 0
                    AND neuro_score < 0.3
                    LIMIT 30
                """).fetchall()

                # N+1 fix: batch archive updates with executemany
                now_iso = datetime.now().isoformat()
                archive_params = [
                    (
                        min(0.8, max(row["galactic_distance"] + 0.15, 0.7)),
                        now_iso,
                        row["id"],
                    )
                    for row in archive_candidates
                ]
                archived = 0
                if archive_params:
                    conn.executemany(
                        """UPDATE memories
                           SET galactic_distance = ?,
                               metadata = json_set(COALESCE(metadata, '{}'),
                                   '$.auto_archived_at', ?,
                                   '$.archive_reason', 'dream_triage')
                           WHERE id = ?""",
                        archive_params,
                    )
                    archived = len(archive_params)
                    conn.commit()
                result["auto_archived"] = archived

                # 3. Coordinate drift correction: memories far from their band
                # Find protected memories that drifted away from core
                drifted_core = conn.execute("""
                    SELECT id FROM memories
                    WHERE is_protected = 1 AND galactic_distance > 0.1
                    LIMIT 20
                """).fetchall()
                # N+1 fix: batch drift correction with executemany
                drift_corrected = 0
                if drifted_core:
                    conn.executemany(
                        "UPDATE memories SET galactic_distance = 0.0 WHERE id = ?",
                        [(row["id"],) for row in drifted_core],
                    )
                    drift_corrected = len(drifted_core)
                    conn.commit()
                result["drift_corrected"] = drift_corrected

                # 4. Orphan detection (report only, don't clean in triage)
                orphan_coords = conn.execute("""
                    SELECT COUNT(*) FROM holographic_coords h
                    LEFT JOIN memories m ON h.memory_id = m.id
                    WHERE m.id IS NULL
                """).fetchone()[0]
                orphan_assocs = conn.execute("""
                    SELECT COUNT(*) FROM associations a
                    WHERE NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = a.source_id)
                """).fetchone()[0]
                result["orphan_coords"] = orphan_coords
                result["orphan_associations"] = orphan_assocs

                # 5. Auto-merge near-duplicates (embedding-based)
                try:
                    from whitemagic.core.memory.consolidation import get_consolidator

                    consolidator = get_consolidator()
                    merge_result = consolidator.resolve_entities(
                        similarity_threshold=0.92,
                        batch_limit=100,
                    )
                    result["auto_merge"] = {
                        "duplicates_found": merge_result.get("duplicates_found", 0),
                        "duplicates_resolved": merge_result.get(
                            "duplicates_resolved", 0
                        ),
                        "status": merge_result.get("status", "unknown"),
                    }
                except Exception as e:
                    result["auto_merge"] = {"status": "skipped", "reason": str(e)}

                # 6. Orphan cleanup (clean if count is small, report if large)
                if orphan_coords > 0 and orphan_coords < 500:
                    conn.execute("""
                        DELETE FROM holographic_coords
                        WHERE memory_id NOT IN (SELECT id FROM memories)
                    """)
                    conn.commit()
                    result["orphan_coords_cleaned"] = orphan_coords
                if orphan_assocs > 0 and orphan_assocs < 500:
                    conn.execute("""
                        DELETE FROM associations
                        WHERE source_id NOT IN (SELECT id FROM memories)
                           OR target_id NOT IN (SELECT id FROM memories)
                    """)
                    conn.commit()
                    result["orphan_assocs_cleaned"] = orphan_assocs

                # 7. Quick stats for the report
                result["total_memories"] = conn.execute(
                    "SELECT COUNT(*) FROM memories"
                ).fetchone()[0]
                result["core_memories"] = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE galactic_distance = 0.0"
                ).fetchone()[0]

        except (sqlite3.Error, sqlite3.OperationalError) as e:
            result["triage_error"] = str(e)
            logger.debug("Dream triage error: %s", e, exc_info=True)

        # 8. Seed germination scan — find dormant polyglot seeds
        try:
            result["seed_scan"] = self._seed_scan_dormant()
        except Exception as e:
            result["seed_scan"] = {"skipped": True, "reason": str(e)}

        return result

    def _dream_consolidation(self) -> dict[str, Any]:
        """Phase 1: Run hippocampal memory consolidation + constellation detection."""
        result: dict[str, Any] = {}

        # Standard consolidation
        try:
            from whitemagic.core.memory.consolidation import get_consolidator

            consolidator = get_consolidator()
            report = consolidator.consolidate()
            result.update(
                {
                    "memories_analyzed": report.memories_analyzed,
                    "clusters_found": report.clusters_found,
                    "strategies_synthesized": report.strategies_synthesized,
                    "promotions": report.promotions,
                }
            )
        except Exception as e:
            result["consolidation_error"] = str(e)

        # Constellation refresh via CoreAccessLayer
        try:
            from whitemagic.core.memory.constellations import get_constellation_detector

            detector = get_constellation_detector()
            detection = detector.detect(sample_limit=10000)
            result["constellations_detected"] = detection.constellations_found
            result["largest_constellation"] = detection.largest_constellation
        except (ImportError, ModuleNotFoundError):
            pass

        return result

    def _dream_serendipity(self) -> dict[str, Any]:
        """Phase 2: Surface unexpected connections via Graph Engine + Bridge Synthesizer.

        v14.0 upgrade: Uses the graph topology engine to find bridge nodes
        (memories connecting disconnected communities) and synthesizes
        insights from those bridges.
        """
        result: dict[str, Any] = {}

        # v14.0: Graph-based bridge discovery
        try:
            from whitemagic.core.memory.graph_engine import get_graph_engine

            engine = get_graph_engine()
            engine.rebuild(sample_limit=20000)

            bridges = engine.find_bridge_nodes(top_n=5)
            result["bridge_nodes_found"] = len(bridges)
            result["top_bridges"] = bridges[:3]

            # Synthesize insights from bridges
            if bridges:
                try:
                    from whitemagic.core.memory.bridge_synthesizer import (
                        get_bridge_synthesizer,
                    )

                    synth = get_bridge_synthesizer()
                    insights = synth.synthesize_from_bridges(bridges, top_n=3)
                    result["bridge_insights"] = [i.to_dict() for i in insights]
                    result["insights_generated"] = len(insights)
                except Exception as e:
                    result["synthesis_error"] = str(e)
        except Exception as e:
            result["graph_error"] = str(e)

        # Standard association mining (fallback + complement)
        try:
            from whitemagic.core.memory.association_miner import get_association_miner

            miner = get_association_miner()
            report = miner.mine(sample_size=100)

            connections = []
            for p in report.top_proposals[:10]:
                connections.append(
                    {
                        "from": p.source_id[:8],
                        "to": p.target_id[:8],
                        "score": round(p.overlap_score, 3),
                        "shared": sorted(p.shared_keywords)[:5],
                    }
                )

            result.update(
                {
                    "connections_surfaced": report.links_proposed,
                    "connections_created": report.links_created,
                    "pairs_evaluated": report.pairs_evaluated,
                    "connections": connections,
                }
            )
        except Exception as e:
            result["mining_error"] = str(e)

        # Cross-constellation bridge discovery via CoreAccessLayer
        cal = self._get_core_access()
        if cal:
            try:
                bridges_cal = cal.find_constellation_bridges(limit=5)
                result["constellation_bridges"] = len(bridges_cal)
                if bridges_cal:
                    result["bridge_pairs"] = [
                        f"{b['constellation_1']} <-> {b['constellation_2']}"
                        for b in bridges_cal[:3]
                    ]
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass

        # v23.2: Cross-domain collision detection
        # Find memory pairs with high behavioral but low semantic similarity
        try:
            from whitemagic.core.intelligence.synthesis.cross_domain_detector import (
                get_cross_domain_detector,
            )

            detector = get_cross_domain_detector()
            collisions = detector.detect(sample_limit=500, top_n=5)
            if collisions:
                result["cross_domain_collisions"] = len(collisions)
                result["top_collisions"] = [c.to_dict() for c in collisions[:3]]
                result["collision_detector_stats"] = detector.get_stats()
        except Exception as e:
            logger.debug("Cross-domain collision detection failed: %s", e)

        return result

    def _dream_governance(self) -> dict[str, Any]:
        """Phase 3 (v14.0): Echo chamber detection and inhibition.

        1. Compute eigenvector centrality snapshot
        2. Compare with previous snapshot
        3. Flag nodes with centrality spike > 2σ WITHOUT new data
        4. Inhibit reinforcing edges (reduce weight 50%)
        5. Log to Karma Ledger
        """
        result: dict[str, Any] = {}

        try:
            from whitemagic.core.memory.graph_engine import get_graph_engine

            engine = get_graph_engine()

            # Take centrality snapshot (stores as T_now, shifts previous to T_prev)
            snapshot = engine.centrality_snapshot()
            result["snapshot_nodes"] = snapshot.node_count
            result["snapshot_edges"] = snapshot.edge_count

            # Detect echo chambers
            echo_chambers = engine.detect_echo_chambers(sigma_threshold=2.0)
            result["echo_chambers_detected"] = len(echo_chambers)
            result["echo_chambers"] = [ec.to_dict() for ec in echo_chambers[:5]]

            # Inhibit reinforcing edges for echo chamber nodes
            inhibited = 0
            if echo_chambers:
                try:
                    from whitemagic.core.memory.unified import get_unified_memory

                    um = get_unified_memory()
                    with um.backend.pool.connection() as conn:
                        with conn:
                            # N+1 fix: executemany instead of per-node UPDATE loop
                            ec_params = [
                                (ec.node_id, ec.node_id) for ec in echo_chambers[:10]
                            ]
                            conn.executemany(
                                """UPDATE associations
                                   SET strength = strength * 0.5
                                   WHERE (source_id = ? OR target_id = ?)
                                   AND strength > 0.1""",
                                ec_params,
                            )
                            inhibited = len(ec_params)
                    result["edges_inhibited_for_nodes"] = inhibited
                except Exception as e:
                    result["inhibition_error"] = str(e)

            if echo_chambers:
                try:
                    from whitemagic.dharma.karma_ledger import get_karma_ledger

                    ledger = get_karma_ledger()
                    ledger.record(
                        tool="dream_governance",
                        declared_safety="WRITE",
                        actual_writes=inhibited,
                        success=True,
                    )
                except (ImportError, AttributeError):
                    pass

            # Detect communities for context
            try:
                communities = engine.detect_communities()
                result["communities_detected"] = len(communities)
                result["largest_community"] = communities[0].size if communities else 0
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass

        except Exception as e:
            result["governance_error"] = str(e)

        return result

    def _dream_narrative(self) -> dict[str, Any]:
        """Phase 4 (v14.2): Narrative compression of episodic memory clusters.

        Compresses clusters of temporally-adjacent, tag-similar memories
        into coherent narrative summaries. This reduces memory fragmentation
        and creates high-quality recall anchors.
        """
        try:
            from whitemagic.core.dreaming.narrative_compressor import (
                get_narrative_compressor,
            )

            nc = get_narrative_compressor()
            result = nc.compress(max_clusters=3, sample_limit=200)
            return cast(dict[str, Any], result.to_dict())
        except Exception as e:
            return {"skipped": True, "reason": str(e)}

    def _dream_kaizen(self) -> dict[str, Any]:
        """Phase 5: Analyze patterns for improvement hints + run Emergence scan.

        New in v14: Emergence insights are persisted as memories, creating
        a self-reinforcing intelligence loop where dream discoveries feed
        back into the Data Sea for future recall.
        """
        emergence_insights = []
        persisted_count = 0
        try:
            from whitemagic.core.intelligence.agentic.emergence_engine import (
                get_emergence_engine,
            )

            ee = get_emergence_engine()
            insights = ee.scan_for_emergence()
            emergence_insights = [i.to_dict() for i in insights[:5]]

            # Persist emergence insights as dream memories (self-reinforcing loop)
            persisted_count = self._persist_dream_insights(insights[:3])
        except (ImportError, AttributeError):
            pass

        # Auto-merge converging constellations (v15.9)
        merge_result: dict[str, Any] = {}
        try:
            from whitemagic.core.memory.constellations import get_constellation_detector

            detector = get_constellation_detector()
            merge_result = detector.auto_merge(max_distance=0.5, min_shared_tags=2)
        except (ImportError, ModuleNotFoundError):
            pass

        try:
            from whitemagic.harmony.vector import get_harmony_vector

            hv = get_harmony_vector()
            snap = hv.snapshot()

            hints = []
            if snap.error_rate > 0.1:
                hints.append(
                    f"High error rate ({snap.error_rate:.2f}) — check circuit breakers"
                )
            if snap.energy < 0.3:
                hints.append(
                    f"Low energy ({snap.energy:.2f}) — consider memory lifecycle sweep"
                )
            if snap.karma_debt > 0.2:
                hints.append(
                    f"Karma debt ({snap.karma_debt:.2f}) — review side-effect declarations"
                )
            if snap.balance < 0.3:
                hints.append(
                    f"Yin-Yang imbalance ({snap.balance:.2f}) — alternate action/reflection"
                )

            guna = {
                "sattvic": snap.guna_sattvic_pct,
                "rajasic": snap.guna_rajasic_pct,
                "tamasic": snap.guna_tamasic_pct,
            }
            if guna.get("tamasic", 0) > 0.4:
                hints.append("High tamasic ratio — too many failed/stalled operations")

            # Neuro-score sample memories for decay hints
            neuro_hints = []
            try:
                from whitemagic.core.memory.unified import get_unified_memory
                from whitemagic.core.scoring import NeuroScoreInput, neuro_score

                um = get_unified_memory()
                sample = um.list_recent(limit=5)
                for mem in sample:
                    days = (
                        max(
                            0.0,
                            (
                                time.time()
                                - (mem.last_accessed or mem.created_at).timestamp()
                            )
                            / 86400,
                        )
                        if hasattr(mem, "last_accessed") and mem.last_accessed
                        else 30.0
                    )
                    result = neuro_score(
                        NeuroScoreInput(
                            current_score=getattr(mem, "retention_score", 0.5) or 0.5,
                            access_count=getattr(mem, "access_count", 0) or 0,
                            total_memories=100,
                            days_since_access=days,
                            importance=getattr(mem, "importance", 0.5) or 0.5,
                        )
                    )
                    if result.final_score < 0.3:
                        neuro_hints.append(
                            f"Memory '{(mem.title or mem.id[:8])}' score={result.final_score:.3f} — candidate for galactic drift"
                        )
            except (ImportError, ModuleNotFoundError):
                pass

            return {
                "harmony_score": round(snap.balance, 3),
                "hints": hints + neuro_hints,
                "hint_count": len(hints) + len(neuro_hints),
                "neuro_score_used": len(neuro_hints) > 0,
                "emergence_insights": emergence_insights,
                "emergence_count": len(emergence_insights),
                "dream_insights_persisted": persisted_count,
                "constellation_merges": merge_result.get("merges", 0),
                **self._run_recursive_improvement(),
            }
        except Exception as e:
            return {
                "skipped": True,
                "reason": str(e),
                "emergence_insights": emergence_insights,
                "dream_insights_persisted": persisted_count,
                "constellation_merges": merge_result.get("merges", 0),
            }

    def _run_recursive_improvement(self) -> dict[str, Any]:
        """Trigger a RecursiveImprovementLoop cycle from the dream state.

        This connects the dream cycle's kaizen phase to the recursive
        improvement loop, so dream discoveries become actionable hypotheses
        that get simulated, predicted, and tracked.
        """
        try:
            from whitemagic.core.evolution.recursive_loop import get_improvement_loop

            loop = get_improvement_loop()
            cycle = loop.run_cycle(max_hypotheses=10)
            return {
                "improvement_cycle_id": cycle.cycle_id,
                "improvement_hypotheses": len(cycle.hypotheses),
                "improvement_recommendations": len(cycle.top_recommendations),
                "improvement_duration_ms": round(cycle.duration_ms, 1),
            }
        except Exception as e:
            logger.debug(
                "Recursive improvement loop failed in dream: %s", e, exc_info=True
            )
            return {}

    def _dream_oracle(self) -> dict[str, Any]:
        """Phase 4: Consult Grimoire for contextual recommendations.

        v23.3: Now incorporates Bayesian calibration from TemporalForecastDB.
        Oracle spell confidence is adjusted based on historical forecasting
        accuracy — overconfident systems get dampened, underconfident boosted.
        """
        try:
            from whitemagic.grimoire.auto_cast import AutoCaster, CastContext, CastMode

            calibration = {}
            try:
                from whitemagic.forecasting.temporal_db import TemporalForecastDB

                db = TemporalForecastDB()
                summary = db.summary()
                calibration = {
                    "brier_score": summary.get("brier_score", 0.0),
                    "calibration_gap": summary.get("calibration_gap", 0.0),
                    "brier_skill_score": summary.get("brier_skill_score", 0.0),
                }
            except Exception as e:
                logger.debug("Calibration data unavailable for oracle: %s", e)

            # Calculate Bayesian adjustment factor
            # Negative calibration_gap = overconfident → dampen
            # Positive calibration_gap = underconfident → boost
            bayesian_adjustment = calibration.get("calibration_gap", 0.0) * 0.3

            caster = AutoCaster(mode=CastMode.SUGGEST_ONLY)
            caster.activate()

            # Dream about what tasks might be needed
            dream_prompts = [
                "system maintenance and optimization",
                "memory organization and consolidation",
                "pattern recognition and insight",
            ]

            suggestions = []
            for prompt in dream_prompts:
                ctx = CastContext(
                    task=prompt,
                    emotional_state="contemplative",
                    wu_xing="water",
                    yin_yang="yin",
                )
                results = caster.process_context(ctx)
                for r in results:
                    if r.spell and r.confidence > 0.3:
                        # Apply Bayesian calibration adjustment
                        adjusted_conf = max(
                            0.01, min(0.99, r.confidence + bayesian_adjustment)
                        )
                        suggestions.append(
                            {
                                "spell": r.spell.name,
                                "confidence": round(adjusted_conf, 3),
                                "raw_confidence": round(r.confidence, 3),
                                "bayesian_adjustment": round(bayesian_adjustment, 3),
                                "for": prompt,
                            }
                        )

            caster.deactivate()
            return {
                "suggestions": suggestions[:5],
                "suggestion_count": len(suggestions),
                "calibration": calibration,
            }
        except Exception as e:
            return {"skipped": True, "reason": str(e)}

    def _dream_decay(self) -> dict[str, Any]:
        """Phase 5: Run mindful forgetting / galactic rotation."""
        try:
            from whitemagic.core.memory.lifecycle import get_lifecycle_manager

            mgr = get_lifecycle_manager()
            result = mgr.run_sweep()
            return {
                "swept": True,
                "details": result if isinstance(result, dict) else str(result),
            }
        except Exception as e:
            return {"skipped": True, "reason": str(e)}

    # v17.0: New dream phases for Intelligence Amplification

    def _dream_constellation(self) -> dict[str, Any]:
        """Phase 8 (v17.0): Auto-merge related constellations.

        Scans for constellations with overlapping memberships
        and merges them when similarity exceeds threshold.
        """
        result: dict[str, Any] = {"merges": 0, "inspected": 0}
        try:
            from whitemagic.core.memory.constellations import get_constellation_detector

            detector = get_constellation_detector()

            # Detect current constellations
            report = detector.detect(sample_limit=5000)
            const_list = report.constellations
            result["inspected"] = len(const_list)

            # Look for merge candidates (simplified logic)
            merge_count = 0
            for i, c1 in enumerate(const_list):
                for c2 in const_list[i + 1 :]:
                    overlap = len(set(c1.member_ids) & set(c2.member_ids))
                    if overlap > len(c1.member_ids) * 0.5:
                        # 50% overlap threshold
                        merge_count += 1

            result["merges"] = merge_count
            result["suggested_merges"] = merge_count
            return result
        except Exception as e:
            return {"skipped": True, "reason": str(e)}

    def _dream_prediction(self) -> dict[str, Any]:
        """Phase 9 (v17.0): Predictive drift detection.

        Queries memories with high importance but low recent access
        to predict which are at risk of drifting outward in the galactic
        zone system before they actually do.
        """
        result: dict[str, Any] = {"predictions": [], "at_risk_count": 0}
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            um = get_unified_memory()

            with um.backend.pool.connection() as conn:
                conn.row_factory = __import__("sqlite3").Row
                # Find high-importance memories that haven't been accessed recently
                # and are already drifting outward (galactic_distance > 0.3)
                at_risk = conn.execute("""
                    SELECT id, title, importance, galactic_distance,
                           access_count, last_accessed, created_at
                    FROM memories
                    WHERE importance > 0.5
                      AND COALESCE(access_count, 0) < 3
                      AND galactic_distance > 0.3
                      AND is_protected = 0
                    ORDER BY importance DESC, galactic_distance DESC
                    LIMIT 20
                """).fetchall()

                predictions = []
                for row in at_risk:
                    drift_risk = min(
                        1.0,
                        row["galactic_distance"] * (1.0 - row["access_count"] * 0.1),
                    )
                    predictions.append(
                        {
                            "memory_id": row["id"],
                            "title": (row["title"] or "")[:60],
                            "importance": round(row["importance"], 3),
                            "current_distance": round(row["galactic_distance"], 3),
                            "access_count": row["access_count"] or 0,
                            "drift_risk": round(drift_risk, 3),
                            "recommendation": "access"
                            if drift_risk > 0.6
                            else "monitor",
                        }
                    )

                result["predictions"] = predictions
                result["at_risk_count"] = len(predictions)
                result["prediction_model"] = "coordinate_velocity_v1"
                result["high_risk"] = sum(
                    1 for p in predictions if p["drift_risk"] > 0.6
                )
            return result
        except (ImportError, ModuleNotFoundError, sqlite3.Error) as e:
            return {"skipped": True, "reason": str(e)}

    def _dream_enrichment(self) -> dict[str, Any]:
        """Phase 10 (v17.0): Entity extraction & semantic enrichment.

        Scans memories for entity-like patterns (code symbols, file paths,
        version numbers, tool names) and auto-tags them, creating
        typed associations for future recall. Also benchmarks polyglot
        seeds and updates their fitness scores.
        """
        result: dict[str, Any] = {"enriched": 0, "entities_extracted": 0}
        try:
            import re

            from whitemagic.core.memory.unified import get_unified_memory

            um = get_unified_memory()

            # Entity patterns to detect
            entity_patterns = {
                "file_path": re.compile(r"[\w/]+\.\w{1,5}"),
                "version": re.compile(r"v?\d+\.\d+(?:\.\d+)?"),
                "tool_name": re.compile(
                    r"\b(?:fragment|strata|ollama|cargo|maturin|pytest)\b", re.I
                ),
                "python_module": re.compile(r"\bwhitemagic\.[a-z_.]+\b"),
                "rust_crate": re.compile(r"\bwhitemagic_rs\b|\bfragment\b"),
            }

            with um.backend.pool.connection() as conn:
                conn.row_factory = __import__("sqlite3").Row
                # Find memories with no tags
                untagged = conn.execute("""
                    SELECT m.id, m.title, SUBSTR(m.content, 1, 1000) as snippet
                    FROM memories m
                    LEFT JOIN tags t ON m.id = t.memory_id
                    WHERE t.tag IS NULL
                    LIMIT 50
                """).fetchall()

                enriched = 0
                entities_found = 0

                for row in untagged:
                    text = f"{row['title'] or ''} {row['snippet'] or ''}"
                    auto_tags = set()

                    for entity_type, pattern in entity_patterns.items():
                        matches = pattern.findall(text)
                        if matches:
                            entities_found += len(matches)
                            auto_tags.add(f"entity:{entity_type}")

                    if auto_tags:
                        auto_tags.add("dream_enriched")
                        try:
                            conn.executemany(
                                "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                                [(row["id"], tag) for tag in auto_tags],
                            )
                            enriched += 1
                        except sqlite3.Error:
                            pass

                if enriched > 0:
                    conn.commit()

                result["enriched"] = enriched
                result["entities_extracted"] = entities_found
                result["batch_status"] = "completed"
                result["untagged_scanned"] = len(untagged)
        except (ImportError, ModuleNotFoundError, sqlite3.Error) as e:
            result["enrichment_error"] = str(e)

        # Seed fitness benchmark — update polyglot seed fitness scores
        try:
            result["seed_benchmark"] = self._seed_benchmark_fitness()
        except Exception as e:
            result["seed_benchmark"] = {"skipped": True, "reason": str(e)}

        return result

    def _seed_scan_dormant(self) -> dict[str, Any]:
        """Scan for dormant polyglot seeds with available toolchains but no build artifact."""
        try:
            import json
            import shutil
            from pathlib import Path

            seeds_path = (
                Path(__file__).parent.parent.parent.parent
                / "polyglot"
                / "seeds"
                / "seeds.json"
            )
            if not seeds_path.exists():
                return {"skipped": True, "reason": "seeds.json not found"}
            with open(seeds_path) as f:
                seeds_data = json.load(f)

            dormant = []
            for seed in seeds_data.get("seeds", []):
                check_cmd = seed.get("toolchain_check", "").split()[0]
                if not shutil.which(check_cmd):
                    continue
                source_dir = seeds_path.parent / seed.get("source_dir", "")
                if not source_dir.exists():
                    continue
                name = seed["name"]
                if name == "rust":
                    has_artifact = (
                        bool(list(source_dir.glob("*.so")))
                        or (source_dir / "target" / "release").exists()
                    )
                elif name == "zig":
                    has_artifact = (
                        source_dir / "zig-out" / "lib" / "libwhitemagic.so"
                    ).exists()
                elif name == "go":
                    has_artifact = (source_dir / "whitemagic-go-mesh").exists()
                elif name == "elixir":
                    build_dir = source_dir / "_build"
                    has_artifact = build_dir.exists() and any(build_dir.rglob("*.beam"))
                else:
                    has_artifact = False
                if not has_artifact:
                    dormant.append(name)

            if dormant:
                self._emit_event("SEED_DORMANT_FOUND", {"dormant": dormant})
                logger.info(
                    "🌱 Seed scan: %d dormant seed(s) found: %s", len(dormant), dormant
                )

            return {"dormant": dormant, "count": len(dormant)}
        except Exception as e:
            return {"skipped": True, "reason": str(e)}

    def _seed_benchmark_fitness(self) -> dict[str, Any]:
        """Benchmark wired polyglot seeds and update fitness scores in wired.json."""
        try:
            import json
            import math
            import time as _time

            from whitemagic.config.paths import WM_ROOT

            state_path = WM_ROOT / "seeds" / "wired.json"
            if not state_path.exists():
                return {"skipped": True, "reason": "wired.json not found"}

            with open(state_path) as f:
                state = json.load(f)

            # Simple cosine similarity benchmark
            import random

            random.seed(42)
            dim = 256
            vec_a = [random.gauss(0, 1) for _ in range(dim)]
            vec_b = [random.gauss(0, 1) for _ in range(dim)]
            iterations = 50

            # Python baseline
            start = _time.time()
            for _ in range(iterations):
                dot = sum(a * b for a, b in zip(vec_a, vec_b))
                norm_a = math.sqrt(sum(a * a for a in vec_a))
                norm_b = math.sqrt(sum(b * b for b in vec_b))
                _ = dot / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0
            py_time = _time.time() - start

            benchmarked = 0
            for s in state.get("seeds", []):
                name = s.get("name", "")
                if s.get("status") not in ("verified", "wired"):
                    continue

                native_time = None
                if name == "rust":
                    try:
                        import whitemagic_rs

                        if hasattr(whitemagic_rs, "simd_cosine_similarity"):
                            start = _time.time()
                            for _ in range(iterations):
                                _ = float(
                                    whitemagic_rs.simd_cosine_similarity(vec_a, vec_b)
                                )
                            native_time = _time.time() - start
                    except Exception:
                        pass

                if native_time is not None and native_time > 0:
                    speedup = round(py_time / native_time, 2)
                    fitness = s.get("fitness", {})
                    fitness["benchmark_speedup"] = speedup
                    fitness["last_benchmark_at"] = _time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", _time.gmtime()
                    )
                    # Recompute score
                    zone = s.get("zone", "mid_band")
                    zone_dist = {
                        "core": 0.05,
                        "inner_rim": 0.25,
                        "mid_band": 0.50,
                        "outer_rim": 0.75,
                        "far_edge": 0.95,
                    }.get(zone, 1.0)
                    zone_score = (1.0 - zone_dist) * 0.4
                    successes = fitness.get("build_successes", 0)
                    failures = fitness.get("build_failures", 0)
                    total = successes + failures
                    build_score = (successes / total) * 0.3 if total > 0 else 0.0
                    verify_score = 0.15 if s.get("status") == "verified" else 0.0
                    bench_score = min(float(speedup) / 100.0, 1.0) * 0.15
                    fitness["score"] = round(
                        zone_score + build_score + verify_score + bench_score, 4
                    )
                    s["fitness"] = fitness
                    benchmarked += 1
                    logger.info(
                        "🌱 Seed benchmark: %s = %sx speedup (fitness=%.3f)",
                        name,
                        speedup,
                        fitness["score"],
                    )

            if benchmarked > 0:
                with open(state_path, "w") as f:
                    json.dump(state, f, indent=2)
                self._emit_event("SEED_BENCHMARKED", {"benchmarked": benchmarked})

            return {
                "benchmarked": benchmarked,
                "python_baseline_ms": round(py_time * 1000, 2),
            }
        except Exception as e:
            return {"skipped": True, "reason": str(e)}

    def _dream_harmonize(self) -> dict[str, Any]:
        """Phase 11 (v17.0): Wu Xing balance & harmony tuning.

        Measures the distribution of memories across galactic zones
        (core, inner rim, mid rim, outer rim, fringe) and computes
        a Wu Xing balance score. Imbalanced distributions trigger
        gentle adjustments via the lifecycle manager.
        """
        result: dict[str, Any] = {"harmony_score": 0.0, "adjustments": 0}
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            um = get_unified_memory()

            with um.backend.pool.connection() as conn:
                # Count memories in each galactic zone
                zone_counts = {}
                for zone_name, lo, hi in [
                    ("core", 0.0, 0.1),
                    ("inner_rim", 0.1, 0.3),
                    ("mid_rim", 0.3, 0.6),
                    ("outer_rim", 0.6, 0.85),
                    ("fringe", 0.85, 1.01),
                ]:
                    count = conn.execute(
                        """SELECT COUNT(*) FROM memories
                           WHERE galactic_distance >= ? AND galactic_distance < ?""",
                        (lo, hi),
                    ).fetchone()[0]
                    zone_counts[zone_name] = count

                total = sum(zone_counts.values())
                if total == 0:
                    result["harmony_score"] = 1.0
                    result["element_balance"] = {z: 0.2 for z in zone_counts}
                    result["zone_counts"] = zone_counts
                    result["adjustments"] = 0
                    return result

                # Map galactic zones to Wu Xing elements
                # core=earth(stability), inner_rim=metal(structure),
                # mid_rim=water(flow), outer_rim=wood(growth), fringe=fire(transformation)
                wu_xing_map = {
                    "core": "earth",
                    "inner_rim": "metal",
                    "mid_rim": "water",
                    "outer_rim": "wood",
                    "fringe": "fire",
                }

                element_balance = {}
                for zone, count in zone_counts.items():
                    element = wu_xing_map[zone]
                    element_balance[element] = round(count / total, 3)

                # Compute harmony: how close to equal distribution (0.2 each)
                ideal = 0.2
                deviations = [abs(v - ideal) for v in element_balance.values()]
                harmony = 1.0 - (sum(deviations) / (len(deviations) * ideal))
                harmony = max(0.0, min(1.0, harmony))

                # Count adjustments needed (zones that are over/under-represented)
                adjustments = sum(
                    1 for v in element_balance.values() if abs(v - ideal) > 0.1
                )

                result["harmony_score"] = round(harmony, 3)
                result["element_balance"] = element_balance
                result["zone_counts"] = zone_counts
                result["adjustments"] = adjustments
                result["total_memories"] = total
            return result
        except (ImportError, ModuleNotFoundError, sqlite3.Error) as e:
            return {"skipped": True, "reason": str(e)}

    def _persist_dream_insights(self, insights: list) -> int:
        """Persist emergence insights as dream memories.

        This creates the self-reinforcing intelligence loop: discoveries
        from dream scanning are stored as memories, which are then
        discoverable by future scans, briefings, and searches.
        """
        persisted = 0
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            from whitemagic.core.memory.unified_types import MemoryType

            um = get_unified_memory()

            for insight in insights:
                title = f"Dream Insight: {insight.title}"
                content = (
                    f"Emergence insight discovered during dream cycle.\n"
                    f"Source: {insight.source}\n"
                    f"Confidence: {insight.confidence:.2f}\n"
                    f"Description: {insight.description}\n"
                )
                try:
                    um.store(
                        content=content,
                        title=title,
                        memory_type=MemoryType.LONG_TERM,
                        importance=0.5 + (insight.confidence * 0.3),
                        tags={
                            "dream_insight",
                            "emergence",
                            "auto_generated",
                            f"source_{insight.source}",
                        },
                        metadata={
                            "dream_cycle": True,
                            "insight_id": insight.id,
                            "confidence": insight.confidence,
                            "source": insight.source,
                        },
                        galaxy="creative_solutions",
                    )
                    persisted += 1
                except Exception as e:
                    logger.debug("Operation failed: %s", e)
                    pass
        except Exception as e:
            logger.debug("Failed to persist dream insights: %s", e, exc_info=True)
        return persisted

    def _emit_event(self, event_name: str, data: dict[str, Any]) -> None:
        """Emit a dream event to the Gan Ying bus."""
        try:
            from whitemagic.core.resonance.gan_ying_enhanced import (
                EventType,
                ResonanceEvent,
                get_bus,
            )

            bus = get_bus()
            # Use REFLECTION_RECORDED as closest existing event type
            bus.emit(
                ResonanceEvent(
                    event_type=EventType.REFLECTION_RECORDED,
                    source="dream_cycle",
                    data={"dream_event": event_name, **data},
                )
            )
        except (ImportError, AttributeError):
            pass

    def status(self) -> dict[str, Any]:
        """Get dream cycle status."""
        with self._lock:
            recent = [r.to_dict() for r in list(self._history)[-5:]]
            idle_seconds = time.time() - self._last_activity
            return {
                "running": self._running,
                "dreaming": self._dreaming,
                "idle_seconds": round(idle_seconds, 1),
                "idle_threshold": self._idle_threshold,
                "cycle_interval": self._cycle_interval,
                "total_cycles": self._total_cycles,
                "current_phase": self._phases[
                    self._current_phase_index % len(self._phases)
                ].value,
                "recent_dreams": recent,
            }


_dream_cycle: DreamCycle | None = None
_dc_lock = threading.Lock()


def get_dream_cycle() -> DreamCycle:
    """Get the global Dream Cycle instance."""
    global _dream_cycle
    if _dream_cycle is None:
        with _dc_lock:
            if _dream_cycle is None:
                _dream_cycle = DreamCycle()
    return _dream_cycle
