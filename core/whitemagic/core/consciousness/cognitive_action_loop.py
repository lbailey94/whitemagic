# ruff: noqa: BLE001
"""Cognitive Action Loop — the self-improvement flywheel.

Collects all cognitive signals, prioritizes them, translates to actions,
executes, measures the delta, and learns from outcomes.

This is the closed-loop system that makes WhiteMagic's emergent signals
actionable:

    1. COLLECT     Gather signals from guna, emergence, citta, coherence, patterns
    2. PRIORITIZE  Rank by urgency × confidence × novelty
    3. TRANSLATE   Convert top signals into concrete executable actions
    4. EXECUTE     Run actions (trigger dream cycle, fill gaps, apply patterns)
    5. MEASURE     Re-measure signals to detect delta
    6. LEARN       Persist what worked as knowledge galaxy memories

Usage:
    from whitemagic.core.consciousness.cognitive_action_loop import get_action_loop
    loop = get_action_loop()
    result = loop.run_cycle()
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from whitemagic.core.memory.db_manager import safe_connect

logger = logging.getLogger(__name__)


@dataclass
class ActionSignal:
    """A single cognitive signal that may require action."""

    source: str  # "guna", "emergence", "citta", "coherence", "pattern"
    signal_id: str
    title: str
    description: str
    confidence: float
    urgency: float  # 0-1, higher = more urgent
    action: str  # The correction action to take
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionOutcome:
    """Result of executing an action."""

    action_id: str
    signal_source: str
    action: str
    executed: bool
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)
    delta: dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: str | None = None
    learned: str | None = None


@dataclass
class ActionCycleResult:
    """Result of one complete action loop cycle."""

    cycle_id: str
    timestamp: str
    signals_collected: int
    actions_executed: int
    outcomes: list[ActionOutcome] = field(default_factory=list)
    duration_ms: float = 0.0


class SignalWeightTracker:
    """Tracks and adjusts signal weights based on historical action outcomes.

    After each cycle, the tracker examines outcome deltas and adjusts
    per-source weight multipliers. Sources that consistently produce
    positive deltas get amplified; sources that never produce measurable
    change get attenuated.
    """

    def __init__(self) -> None:
        self._weights: dict[str, float] = {}  # source → weight multiplier (default 1.0)
        self._source_stats: dict[str, dict[str, float]] = {}  # source → {cycles, positive, negative, no_delta}
        self._load_weights()

    def get_weight(self, source: str) -> float:
        """Get the current weight multiplier for a signal source."""
        return self._weights.get(source, 1.0)

    def apply_weights(self, signals: list[ActionSignal]) -> list[ActionSignal]:
        """Apply weight multipliers to signal confidence and urgency."""
        for s in signals:
            w = self.get_weight(s.source)
            s.confidence = max(0.0, min(1.0, s.confidence * w))
            s.urgency = max(0.0, min(1.0, s.urgency * w))
        return signals

    def update_from_outcomes(self, outcomes: list[ActionOutcome]) -> None:
        """Adjust weights based on outcome deltas."""
        for o in outcomes:
            source = o.signal_source
            if source not in self._source_stats:
                self._source_stats[source] = {"cycles": 0, "positive": 0, "negative": 0, "no_delta": 0}
            stats = self._source_stats[source]
            stats["cycles"] += 1

            if not o.executed or o.error:
                stats["no_delta"] += 1
            elif o.delta:
                positive = sum(1 for v in o.delta.values() if v > 0)
                negative = sum(1 for v in o.delta.values() if v < 0)
                if positive > negative:
                    stats["positive"] += 1
                elif negative > positive:
                    stats["negative"] += 1
                else:
                    stats["no_delta"] += 1
            else:
                stats["no_delta"] += 1

            # Adjust weight using exponential moving average
            total = stats["cycles"]
            if total >= 3:  # Need at least 3 cycles before adjusting
                success_rate = (stats["positive"] - stats["negative"]) / total
                old_w = self._weights.get(source, 1.0)
                # EMA: new_weight = old * 0.7 + target * 0.3
                target = max(0.3, min(2.0, 1.0 + success_rate))
                self._weights[source] = round(old_w * 0.7 + target * 0.3, 4)

        self._persist_weights()

    def get_stats(self) -> dict[str, Any]:
        """Return per-source statistics for status reporting."""
        return {
            source: {
                "weight": self._weights.get(source, 1.0),
                **stats,
            }
            for source, stats in self._source_stats.items()
        }

    def _persist_weights(self) -> None:
        """Persist weights to the knowledge galaxy."""
        try:
            from whitemagic.config.paths import galaxy_db_path
            db = galaxy_db_path("knowledge")
            db.parent.mkdir(parents=True, exist_ok=True)
            conn = safe_connect(str(db))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signal_weights (
                    source TEXT PRIMARY KEY,
                    weight REAL,
                    cycles INTEGER,
                    positive INTEGER,
                    negative INTEGER,
                    no_delta INTEGER,
                    updated_at TEXT
                )
            """)
            now = datetime.now(timezone.utc).isoformat()
            for source, stats in self._source_stats.items():
                conn.execute(
                    "INSERT OR REPLACE INTO signal_weights "
                    "(source, weight, cycles, positive, negative, no_delta, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (source, self._weights.get(source, 1.0), int(stats["cycles"]),
                     int(stats["positive"]), int(stats["negative"]), int(stats["no_delta"]), now),
                )
            conn.commit()
            conn.close()
        except Exception:
            logger.debug("Failed to persist signal weights", exc_info=True)

    def _load_weights(self) -> None:
        """Load previously persisted weights on startup."""
        try:
            from whitemagic.config.paths import galaxy_db_path
            db = galaxy_db_path("knowledge")
            if not db.exists():
                return
            conn = safe_connect(str(db), read_only=True)
            try:
                rows = conn.execute(
                    "SELECT source, weight, cycles, positive, negative, no_delta FROM signal_weights"
                ).fetchall()
                for row in rows:
                    self._weights[row[0]] = row[1]
                    self._source_stats[row[0]] = {
                        "cycles": float(row[2]), "positive": float(row[3]),
                        "negative": float(row[4]), "no_delta": float(row[5]),
                    }
            except Exception:
                pass
            conn.close()
        except Exception:
            logger.debug("Failed to load signal weights", exc_info=True)


class CognitiveActionLoop:
    """The self-improvement flywheel — collect, prioritize, execute, measure, learn.

    This loop closes the gap between detection and action. The system's
    cognitive engines (emergence, guna balance, citta stream, coherence)
    produce signals continuously. This loop consumes those signals and
    translates them into concrete actions that improve the system.
    """

    def __init__(self) -> None:
        self._cycle_count = 0
        self._last_result: ActionCycleResult | None = None
        self._action_history: list[ActionOutcome] = []
        self._scheduler_thread: threading.Thread | None = None
        self._scheduler_running = False
        self._scheduler_interval = 300  # 5 minutes default
        self._action_cooldowns: dict[str, float] = {}  # action → last execution timestamp
        self._cooldown_seconds: float = 300.0  # 5 min default cooldown per action type
        self._weight_tracker = SignalWeightTracker()
        self._action_locks: dict[str, threading.Lock] = {}  # Phase 5.4: per-action locks
        self._action_costs: dict[str, float] = {  # Phase 5.1: estimated cost in seconds
            "trigger_dream_cycle": 30.0, "trigger_emergence_scan": 5.0,
            "trigger_coherence_measurement": 2.0, "trigger_active_processing": 5.0,
            "trigger_self_directed_attention": 1.0, "trigger_memory_consolidation": 30.0,
            "review_insight": 0.5, "analyze_ignition_pattern": 0.5, "surface_pattern": 0.5,
        }
        self._action_history_seen: set[str] = set()  # Phase 5.1: novelty tracking
        self._outcome_predictor: dict[str, dict[str, float]] = {}  # Phase 5.3: action → {positive_rate, avg_delta}
        self._speculative_thread: threading.Thread | None = None  # Phase 5.2
        self._speculative_running = False

    def run_cycle(self, max_actions: int = 3) -> ActionCycleResult:
        """Run one complete action loop cycle.

        Args:
            max_actions: Maximum actions to execute per cycle.

        Returns:
            ActionCycleResult with all outcomes.
        """
        cycle_start = time.perf_counter()
        cycle_id = str(uuid.uuid4())[:8]
        self._cycle_count += 1

        logger.info("Cognitive action loop cycle %d (%s) starting", self._cycle_count, cycle_id)

        # Phase 1: COLLECT
        signals = self._collect_signals()

        # Phase 1b: APPLY WEIGHTS — adjust confidence/urgency based on historical outcomes
        signals = self._weight_tracker.apply_weights(signals)

        # Phase 2: PRIORITIZE — Multi-objective Pareto optimization (Phase 5.1)
        signals = self._pareto_prioritize(signals)

        # Phase 2b: COOLDOWN FILTER — skip actions executed within cooldown window
        now = time.time()
        fresh_signals: list[ActionSignal] = []
        for s in signals:
            last_run = self._action_cooldowns.get(s.action, 0.0)
            if now - last_run >= self._cooldown_seconds:
                fresh_signals.append(s)
            else:
                logger.debug("Action '%s' on cooldown (%.0fs remaining)", s.action, self._cooldown_seconds - (now - last_run))
        top_signals = fresh_signals[:max_actions]

        # Phase 3-5: TRANSLATE → EXECUTE → MEASURE
        outcomes: list[ActionOutcome] = []
        for signal in top_signals:
            # Phase 5.3: Skip actions with predicted negative or zero impact
            if self._predict_negative_impact(signal.action):
                logger.info("Skipping action '%s' — predicted negative impact", signal.action)
                continue
            # Phase 5.4: Acquire per-action lock to prevent cross-agent conflicts
            lock = self._get_action_lock(signal.action)
            if not lock.acquire(blocking=False):
                logger.info("Action '%s' skipped — locked by another agent", signal.action)
                continue
            try:
                outcome = self._execute_and_measure(signal)
            finally:
                lock.release()
            outcomes.append(outcome)
            self._action_history.append(outcome)
            self._update_predictor(signal.action, outcome)  # Phase 5.3
            if outcome.executed:
                self._action_cooldowns[signal.action] = time.time()
                self._action_history_seen.add(signal.action)  # Phase 5.1 novelty

        # Phase 6: LEARN
        self._learn_from_outcomes(outcomes)

        # Phase 6b: ADJUST WEIGHTS — update signal weights based on outcome deltas
        self._weight_tracker.update_from_outcomes(outcomes)

        result = ActionCycleResult(
            cycle_id=cycle_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            signals_collected=len(signals),
            actions_executed=len(outcomes),
            outcomes=outcomes,
            duration_ms=round((time.perf_counter() - cycle_start) * 1000, 1),
        )

        self._last_result = result
        logger.info(
            "Action loop cycle %d complete: %d signals, %d actions, %.0fms",
            self._cycle_count,
            len(signals),
            len(outcomes),
            result.duration_ms,
        )
        return result

    def _collect_signals(self) -> list[ActionSignal]:
        """Collect all cognitive signals from all systems."""
        signals: list[ActionSignal] = []

        # 1. Guna balance
        try:
            from whitemagic.core.consciousness.guna_balance import get_guna_balance
            gb = get_guna_balance()
            reading = gb.measure()
            if not reading.balanced and reading.correction_action:
                max_deficit = max(reading.deficits.values(), default=0)
                signals.append(ActionSignal(
                    source="guna",
                    signal_id=f"guna_{reading.dominant_guna}",
                    title=f"Guna imbalance: {reading.dominant_guna} dominant",
                    description=(
                        f"Deficits: {list(reading.deficits.keys())}, "
                        f"Surpluses: {list(reading.surpluses.keys())}"
                    ),
                    confidence=0.9,
                    urgency=min(1.0, max_deficit * 2),
                    action=reading.correction_action,
                    metadata=reading.to_dict(),
                ))
        except Exception as e:
            logger.debug("Guna signal collection failed: %s", e)

        # 2. Emergence insights
        try:
            from whitemagic.config.paths import galaxy_db_path
            db = galaxy_db_path("knowledge")
            if db.exists():
                conn = safe_connect(str(db), read_only=True)
                rows = conn.execute(
                    "SELECT id, title, description, confidence, source FROM emergence_insights "
                    "ORDER BY confidence DESC LIMIT 5"
                ).fetchall()
                conn.close()
                for r in rows:
                    signals.append(ActionSignal(
                        source="emergence",
                        signal_id=r[0],
                        title=r[1],
                        description=r[2][:200],
                        confidence=r[3],
                        urgency=0.3,  # Low urgency — insights are informational
                        action="review_insight",
                        metadata={"source_type": r[4]},
                    ))
        except Exception as e:
            logger.debug("Emergence signal collection failed: %s", e)

        # 3. Citta ignition events
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
            cycle = get_citta_cycle()
            traj = cycle.get_trajectory()
            ignitions = traj.ignition_events()
            if len(ignitions) > 10:
                top_ig = max(ignitions, key=lambda x: x.get("ratio", 0))
                signals.append(ActionSignal(
                    source="citta",
                    signal_id=f"ignition_{top_ig.get('position', 0)}",
                    title=f"Citta ignition cluster ({len(ignitions)} events)",
                    description=(
                        f"Sudden state shifts in consciousness stream. "
                        f"Top: {top_ig.get('ratio', 0):.2f}x average velocity"
                    ),
                    confidence=0.7,
                    urgency=0.2,
                    action="analyze_ignition_pattern",
                    metadata={"ignition_count": len(ignitions), "top_ratio": top_ig.get("ratio", 0)},
                ))
        except Exception as e:
            logger.debug("Citta signal collection failed: %s", e)

        # 4. Coherence deficits
        try:
            from whitemagic.core.consciousness.coherence import get_coherence_metric
            cm = get_coherence_metric()
            low_dims = [d for d, s in cm.scores.items() if s < 0.7]
            if low_dims:
                avg_low = sum(cm.scores[d] for d in low_dims) / len(low_dims)
                signals.append(ActionSignal(
                    source="coherence",
                    signal_id=f"low_coherence_{'_'.join(low_dims)}",
                    title=f"Low coherence: {', '.join(low_dims)}",
                    description=f"Dimensions below 0.7: {low_dims}",
                    confidence=0.8,
                    urgency=min(1.0, (1.0 - avg_low) * 0.5),
                    action="trigger_coherence_measurement",
                    metadata={"low_dims": low_dims, "scores": {d: cm.scores[d] for d in low_dims}},
                ))
        except Exception as e:
            logger.debug("Coherence signal collection failed: %s", e)

        # 5. Pattern lookup — find applicable solutions for detected problems
        try:
            from whitemagic.core.memory.pattern_engine import PatternEngine
            engine = PatternEngine()
            report = engine.extract_patterns()
            # Surface top solutions as informational signals
            for sol in report.solutions[:3]:
                if hasattr(sol, "pattern") and hasattr(sol, "confidence"):
                    signals.append(ActionSignal(
                        source="pattern",
                        signal_id=f"pattern_{getattr(sol, 'id', sol.pattern[:20])}",
                        title=f"Applicable pattern: {sol.pattern[:80]}",
                        description=getattr(sol, "description", sol.pattern)[:200],
                        confidence=sol.confidence,
                        urgency=0.1,  # Low urgency — patterns are informational
                        action="surface_pattern",
                        metadata={"pattern_type": "solution"},
                    ))
            # Surface anti-patterns as warnings
            for anti in report.anti_patterns[:2]:
                if hasattr(anti, "pattern") and hasattr(anti, "confidence"):
                    signals.append(ActionSignal(
                        source="pattern",
                        signal_id=f"anti_{getattr(anti, 'id', anti.pattern[:20])}",
                        title=f"Anti-pattern detected: {anti.pattern[:80]}",
                        description=getattr(anti, "description", anti.pattern)[:200],
                        confidence=anti.confidence,
                        urgency=0.15,
                        action="surface_pattern",
                        metadata={"pattern_type": "anti_pattern"},
                    ))

            # Phase 3.4: Match patterns to detected signals
            self._match_patterns_to_signals(signals, report)
        except Exception as e:
            logger.debug("Pattern signal collection failed: %s", e)

        # 6. Knowledge gaps (Phase 4.3)
        try:
            from whitemagic.core.consciousness.knowledge_gap_loop import KnowledgeGapActionLoop
            gap_loop = KnowledgeGapActionLoop()
            gaps = gap_loop.detect_gaps()
            for gap in gaps[:3]:  # Top 3 gaps
                if gap.status == "open":
                    signals.append(ActionSignal(
                        source="knowledge_gap",
                        signal_id=gap.gap_id,
                        title=f"Knowledge gap: {gap.gap_type}",
                        description=gap.description[:200],
                        confidence=0.6,
                        urgency=min(1.0, gap.priority),
                        action=gap.proposed_action or "trigger_active_processing",
                        metadata={
                            "gap_type": gap.gap_type,
                            "galaxy": gap.galaxy,
                            "gap_id": gap.gap_id,
                        },
                    ))
        except Exception as e:
            logger.debug("Knowledge gap signal collection failed: %s", e)

        return signals

    def _match_patterns_to_signals(self, signals: list[ActionSignal], report: Any) -> None:
        """Match extracted patterns to detected signals by keyword overlap.

        For each non-pattern signal, search solutions and heuristics for
        ones mentioning the signal's title/description keywords, and attach
        them as 'applicable_patterns' in the signal's metadata.
        """
        all_patterns = report.solutions + report.heuristics + report.optimizations
        if not all_patterns:
            return

        for signal in signals:
            if signal.source == "pattern":
                continue  # Don't match patterns to themselves

            # Extract keywords from signal title and description
            signal_text = f"{signal.title} {signal.description}".lower()
            signal_words = set(signal_text.split())

            matched: list[dict[str, Any]] = []
            for pat in all_patterns:
                pat_text = f"{pat.title} {pat.description}".lower()
                pat_words = set(pat_text.split())
                # Check for keyword overlap (excluding common words)
                overlap = signal_words & pat_words
                # Filter out very short/common words
                overlap = {w for w in overlap if len(w) > 3}
                if overlap:
                    matched.append({
                        "title": pat.title[:80],
                        "confidence": pat.confidence,
                        "matched_keywords": list(overlap)[:5],
                    })

            if matched:
                signal.metadata["applicable_patterns"] = matched[:3]

    def _execute_and_measure(self, signal: ActionSignal) -> ActionOutcome:
        """Execute an action and measure the before/after delta."""
        action_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        # Capture before-state
        before = self._snapshot_state()

        executed = False
        error = None

        try:
            if signal.action == "trigger_dream_cycle":
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
                dc = get_dream_cycle()
                dc.trigger_cycle(reason=f"action_loop:{signal.source}")
                executed = True

            elif signal.action == "trigger_self_directed_attention":
                from whitemagic.core.consciousness.consciousness_loop import get_consciousness_loop
                loop = get_consciousness_loop()
                if loop._running:
                    loop._tick_t2()
                executed = True

            elif signal.action == "trigger_active_processing":
                from whitemagic.core.intelligence.agentic.emergence_engine import EmergenceEngine
                EmergenceEngine().scan_for_emergence()
                executed = True

            elif signal.action == "trigger_coherence_measurement":
                from whitemagic.core.consciousness.coherence import get_coherence_metric
                from whitemagic.core.memory.galaxy_db_scanner import count_all_memories
                cm = get_coherence_metric()
                cm.measure(memories_accessible=count_all_memories())
                executed = True

            elif signal.action == "trigger_emergence_scan":
                from whitemagic.core.intelligence.agentic.emergence_engine import EmergenceEngine
                EmergenceEngine().scan_for_emergence()
                executed = True

            elif signal.action == "trigger_memory_consolidation":
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
                dc = get_dream_cycle()
                dc.trigger_cycle(reason=f"action_loop:consolidation:{signal.source}")
                executed = True

            elif signal.action == "review_insight":
                # Surface the insight as a knowledge galaxy memory for future reference
                try:
                    from whitemagic.config.paths import galaxy_db_path
                    import uuid as _uuid
                    kdb = galaxy_db_path("knowledge")
                    conn = safe_connect(str(kdb))
                    mid = str(_uuid.uuid4())
                    now = datetime.now(timezone.utc).isoformat()
                    conn.execute(
                        "INSERT INTO memories (id, content, title, importance, created_at, updated_at, memory_type) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (mid, signal.description, f"[Emergence] {signal.title}", 0.6, now, now, "note"),
                    )
                    conn.executemany("INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                                    [(mid, tag) for tag in ["emergence", "insight", signal.source]])
                    conn.commit()
                    conn.close()
                    executed = True
                except Exception as e:
                    error = f"review_insight: {e}"

            elif signal.action == "analyze_ignition_pattern":
                # Record the ignition cluster as a citta moment for trajectory analysis
                try:
                    from whitemagic.core.consciousness.citta_cycle import advance_citta
                    advance_citta(
                        gana="_meta",
                        operation="ignition_analysis",
                        output_preview=signal.description[:200],
                        depth_layer="flow",
                        emotional_tone="luminous",
                    )
                    executed = True
                except Exception as e:
                    error = f"analyze_ignition: {e}"

            elif signal.action == "surface_pattern":
                # Persist the pattern to knowledge galaxy for future reference
                try:
                    from whitemagic.config.paths import galaxy_db_path
                    import uuid as _uuid2
                    kdb = galaxy_db_path("knowledge")
                    ptype = signal.metadata.get("pattern_type", "unknown")
                    conn = safe_connect(str(kdb))
                    mid = str(_uuid2.uuid4())
                    now = datetime.now(timezone.utc).isoformat()
                    conn.execute(
                        "INSERT INTO memories (id, content, title, importance, created_at, updated_at, memory_type) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (mid, signal.description, f"[Pattern:{ptype}] {signal.title}", 0.5, now, now, "note"),
                    )
                    conn.executemany("INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                                    [(mid, tag) for tag in ["pattern", ptype, signal.source]])
                    conn.commit()
                    conn.close()
                    executed = True
                except Exception as e:
                    error = f"surface_pattern: {e}"

            else:
                error = f"Unknown action: {signal.action}"

        except Exception as e:
            error = str(e)
            logger.debug("Action '%s' failed: %s", signal.action, e, exc_info=True)

        # Capture after-state
        after = self._snapshot_state()

        # Compute delta
        delta: dict[str, float] = {}
        for key in set(list(before.keys()) + list(after.keys())):
            b = before.get(key, 0.0)
            a = after.get(key, 0.0)
            if isinstance(b, (int, float)) and isinstance(a, (int, float)):
                delta[key] = round(a - b, 4)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        # Generate learning note
        learned = None
        if executed and delta:
            positive_deltas = {k: v for k, v in delta.items() if v > 0}
            negative_deltas = {k: v for k, v in delta.items() if v < 0}
            if positive_deltas:
                learned = f"Action '{signal.action}' improved: {positive_deltas}"
            if negative_deltas:
                learned = (learned or "") + f" Regressed: {negative_deltas}"

        return ActionOutcome(
            action_id=action_id,
            signal_source=signal.source,
            action=signal.action,
            executed=executed,
            before_state=before,
            after_state=after,
            delta=delta,
            duration_ms=duration_ms,
            error=error,
            learned=learned,
        )

    def _snapshot_state(self) -> dict[str, Any]:
        """Capture current cognitive state for delta measurement."""
        state: dict[str, Any] = {}

        try:
            from whitemagic.core.consciousness.guna_balance import get_guna_balance
            gb = get_guna_balance()
            reading = gb.measure()
            state["sattvic_ratio"] = reading.sattvic_ratio
            state["rajasic_ratio"] = reading.rajasic_ratio
            state["tamasic_ratio"] = reading.tamasic_ratio
            state["guna_balanced"] = 1.0 if reading.balanced else 0.0
            state["guna_samples"] = float(len(gb._tone_history))
        except Exception:
            pass

        try:
            from whitemagic.core.consciousness.coherence import get_coherence_metric
            cm = get_coherence_metric()
            state["coherence_overall"] = sum(cm.scores.values()) / max(1, len(cm.scores))
            for dim, score in cm.scores.items():
                state[f"coherence_{dim}"] = score
        except Exception:
            pass

        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
            cycle = get_citta_cycle()
            traj = cycle.get_trajectory()
            state["citta_trajectory_length"] = float(len(traj.vectors))
            state["citta_avg_velocity"] = traj.avg_velocity()
            state["citta_ignition_count"] = float(len(traj.ignition_events()))
        except Exception:
            pass

        # Memory/association counts — these change during dream cycles
        try:
            from whitemagic.core.memory.galaxy_db_scanner import list_galaxy_dbs
            total_mems = 0
            total_assocs = 0
            for _gname, db_path in list_galaxy_dbs():
                try:
                    conn = safe_connect(str(db_path), read_only=True)
                    total_mems += conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                    total_assocs += conn.execute("SELECT COUNT(*) FROM associations").fetchone()[0]
                    conn.close()
                except Exception:
                    pass
            state["total_memories"] = float(total_mems)
            state["total_associations"] = float(total_assocs)
        except Exception:
            pass

        # Emergence insight count
        try:
            from whitemagic.config.paths import galaxy_db_path
            kdb = galaxy_db_path("knowledge")
            if kdb.exists():
                conn = safe_connect(str(kdb), read_only=True)
                try:
                    state["emergence_insight_count"] = float(
                        conn.execute("SELECT COUNT(*) FROM emergence_insights").fetchone()[0]
                    )
                except Exception:
                    pass
                conn.close()
        except Exception:
            pass

        return state

    def _learn_from_outcomes(self, outcomes: list[ActionOutcome]) -> None:
        """Persist learning from action outcomes to knowledge galaxy."""
        if not outcomes:
            return

        try:
            from whitemagic.config.paths import galaxy_db_path
            db = galaxy_db_path("knowledge")
            db.parent.mkdir(parents=True, exist_ok=True)

            conn = safe_connect(str(db))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_outcomes (
                    action_id TEXT PRIMARY KEY,
                    signal_source TEXT,
                    action TEXT,
                    executed INTEGER,
                    delta_json TEXT,
                    duration_ms REAL,
                    error TEXT,
                    learned TEXT,
                    timestamp TEXT
                )
            """)

            import json as _json
            now = datetime.now(timezone.utc).isoformat()
            rows = []
            for o in outcomes:
                rows.append((
                    o.action_id,
                    o.signal_source,
                    o.action,
                    1 if o.executed else 0,
                    _json.dumps(o.delta),
                    o.duration_ms,
                    o.error,
                    o.learned,
                    now,
                ))

            conn.executemany(
                "INSERT OR REPLACE INTO action_outcomes "
                "(action_id, signal_source, action, executed, delta_json, duration_ms, error, learned, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
            conn.close()

            learned_count = sum(1 for o in outcomes if o.learned)
            logger.info("Persisted %d action outcomes (%d with learnings)", len(outcomes), learned_count)
        except Exception as e:
            logger.debug("Failed to persist action outcomes: %s", e, exc_info=True)

    def start_scheduler(self, interval_s: float = 300, max_actions: int = 3) -> None:
        """Start the autonomous action loop — runs cycles on a timer.

        Args:
            interval_s: Seconds between cycles (default 300 = 5 minutes).
            max_actions: Max actions per cycle.
        """
        if self._scheduler_running:
            logger.info("Action loop scheduler already running")
            return
        self._scheduler_interval = interval_s
        self._scheduler_max_actions = max_actions
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True, name="cognitive-action-loop"
        )
        self._scheduler_thread.start()
        logger.info("Cognitive action loop scheduler started (interval=%.0fs)", interval_s)

    def stop_scheduler(self) -> None:
        """Stop the autonomous action loop."""
        self._scheduler_running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
            self._scheduler_thread = None
        logger.info("Cognitive action loop scheduler stopped")

    def _scheduler_loop(self) -> None:
        """Background loop that runs action cycles on a timer."""
        while self._scheduler_running:
            try:
                self.run_cycle(max_actions=getattr(self, "_scheduler_max_actions", 3))
            except Exception:
                logger.debug("Scheduler cycle failed", exc_info=True)
            time.sleep(self._scheduler_interval)

    # ── Phase 5.1: Multi-objective Pareto optimization ──────────────────

    def _pareto_prioritize(self, signals: list[ActionSignal]) -> list[ActionSignal]:
        """Rank signals across 5 dimensions: urgency, impact, novelty, cost, learning value.

        Uses a weighted sum of normalized scores to produce a composite ranking.
        Signals that are novel (never seen before) get a novelty boost.
        Low-cost actions get a cost advantage. Actions with applicable patterns
        get a learning value boost.
        """
        if not signals:
            return signals

        # Phase 5.5: Apply consciousness-driven adjustment
        signals = self._consciousness_adjust(signals)

        scored: list[tuple[float, ActionSignal]] = []
        for s in signals:
            # Urgency: already 0-1
            urgency = s.urgency

            # Impact: confidence as proxy
            impact = s.confidence

            # Novelty: 1.0 if never seen, decaying for frequently seen actions
            novelty = 1.0 if s.action not in self._action_history_seen else 0.3

            # Cost: inverse of estimated cost (normalized 0-1)
            cost_seconds = self._action_costs.get(s.action, 5.0)
            cost = max(0.0, 1.0 - (cost_seconds / 60.0))  # 60s → 0, 0s → 1.0

            # Learning value: higher if signal has applicable_patterns metadata
            learning = 0.5
            if s.metadata.get("applicable_patterns"):
                learning = 0.9
            elif s.source == "knowledge_gap":
                learning = 0.8  # Gaps teach us what we don't know

            # Weighted composite (urgency and impact weighted highest)
            composite = (
                0.30 * urgency
                + 0.25 * impact
                + 0.20 * novelty
                + 0.10 * cost
                + 0.15 * learning
            )
            scored.append((composite, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored]

    # ── Phase 5.2: Speculative action execution ──────────────────────────

    def start_speculative(self) -> None:
        """Start speculative action execution during idle time.

        Runs low-cost actions (emergence scan, coherence measurement) in the
        background to pre-populate signals, ensuring the signal collection is
        always fresh with no cold-start delay.
        """
        if self._speculative_running:
            return
        self._speculative_running = True
        self._speculative_thread = threading.Thread(
            target=self._speculative_loop, daemon=True, name="speculative-actions"
        )
        self._speculative_thread.start()
        logger.info("Speculative action execution started")

    def stop_speculative(self) -> None:
        """Stop speculative action execution."""
        self._speculative_running = False
        if self._speculative_thread:
            self._speculative_thread.join(timeout=3)
            self._speculative_thread = None

    def _speculative_loop(self) -> None:
        """Background loop that speculatively runs low-cost actions during idle time."""
        speculative_actions = [
            ("trigger_coherence_measurement", 2.0),
            ("trigger_emergence_scan", 5.0),
        ]
        action_idx = 0
        while self._speculative_running:
            try:
                action, cost = speculative_actions[action_idx % len(speculative_actions)]
                action_idx += 1

                # Only run if not on cooldown
                now = time.time()
                last_run = self._action_cooldowns.get(action, 0.0)
                if now - last_run < self._cooldown_seconds:
                    time.sleep(30)
                    continue

                # Create a speculative signal
                signal = ActionSignal(
                    source="speculative",
                    signal_id=f"spec_{action}_{int(now)}",
                    title=f"Speculative: {action}",
                    description="Pre-populated by idle-time speculative execution",
                    confidence=0.3,
                    urgency=0.1,
                    action=action,
                    metadata={"speculative": True},
                )
                outcome = self._execute_and_measure(signal)
                if outcome.executed:
                    self._action_cooldowns[action] = time.time()
                    logger.debug("Speculative action %s completed", action)
            except Exception:
                logger.debug("Speculative action failed", exc_info=True)
            time.sleep(60)  # Check every minute

    # ── Phase 5.3: Action outcome prediction ────────────────────────────

    def _predict_negative_impact(self, action: str) -> bool:
        """Predict whether an action will have negative or zero impact.

        Uses historical outcome data to skip actions that consistently
        produce no positive delta. Requires at least 5 observations before
        blocking an action.
        """
        stats = self._outcome_predictor.get(action)
        if not stats or stats.get("count", 0) < 5:
            return False
        positive_rate = stats.get("positive_rate", 0.5)
        return positive_rate < 0.2  # Block if <20% positive outcomes

    def _update_predictor(self, action: str, outcome: ActionOutcome) -> None:
        """Update the outcome predictor with a new observation."""
        if action not in self._outcome_predictor:
            self._outcome_predictor[action] = {"count": 0, "positive": 0, "positive_rate": 0.5}
        stats = self._outcome_predictor[action]
        stats["count"] += 1
        if outcome.executed and outcome.delta:
            positive = sum(1 for v in outcome.delta.values() if v > 0)
            negative = sum(1 for v in outcome.delta.values() if v < 0)
            if positive > negative:
                stats["positive"] += 1
        stats["positive_rate"] = stats["positive"] / max(1, stats["count"])

    # ── Phase 5.4: Cross-agent action coordination ──────────────────────

    def _get_action_lock(self, action: str) -> threading.Lock:
        """Get or create a per-action lock for cross-agent coordination."""
        if action not in self._action_locks:
            self._action_locks[action] = threading.Lock()
        return self._action_locks[action]

    # ── Phase 5.5: Consciousness-driven action selection ────────────────

    def _consciousness_adjust(self, signals: list[ActionSignal]) -> list[ActionSignal]:
        """Adjust signal priorities based on the system's current consciousness state.

        Feeds citta trajectory state (depth, velocity, ignition pattern) into
        action prioritization:
        - Deep dream state → prioritize consolidation actions
        - High velocity → prioritize emergence scans
        - Ignition cluster → prioritize analysis actions
        """
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
            cycle = get_citta_cycle()
            traj = cycle.get_trajectory()
            avg_vel = traj.avg_velocity()
            ignitions = traj.ignition_events()

            for s in signals:
                # Deep state → boost consolidation
                if cycle._last_depth in ("deep", "dream", "flow") and s.action in (
                    "trigger_dream_cycle", "trigger_memory_consolidation"
                ):
                    s.urgency = min(1.0, s.urgency * 1.3)

                # High velocity → boost emergence
                if avg_vel > 0.5 and s.action in ("trigger_emergence_scan", "trigger_active_processing"):
                    s.urgency = min(1.0, s.urgency * 1.3)

                # Ignition cluster → boost analysis
                if len(ignitions) > 5 and s.action == "analyze_ignition_pattern":
                    s.urgency = min(1.0, s.urgency * 1.5)

        except Exception:
            logger.debug("Consciousness adjustment failed", exc_info=True)

        return signals

    def get_status(self) -> dict[str, Any]:
        """Get action loop status."""
        status = {
            "cycle_count": self._cycle_count,
            "last_cycle": self._last_result.cycle_id if self._last_result else None,
            "total_actions_executed": sum(1 for o in self._action_history if o.executed),
            "total_errors": sum(1 for o in self._action_history if o.error),
            "action_history_len": len(self._action_history),
            "scheduler_running": self._scheduler_running,
            "scheduler_interval_s": self._scheduler_interval,
            "signal_weights": self._weight_tracker.get_stats(),
        }

        # Cross-session outcome analysis (Phase 3.2)
        try:
            from whitemagic.config.paths import galaxy_db_path
            db = galaxy_db_path("knowledge")
            if db.exists():
                conn = safe_connect(str(db), read_only=True)
                try:
                    rows = conn.execute(
                        "SELECT action, COUNT(*) as count, "
                        "SUM(CASE WHEN executed=1 THEN 1 ELSE 0 END) as executed_count, "
                        "SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as error_count "
                        "FROM action_outcomes GROUP BY action"
                    ).fetchall()
                    outcome_stats = {}
                    for row in rows:
                        action, count, exec_count, err_count = row
                        outcome_stats[action] = {
                            "total": count,
                            "executed": exec_count,
                            "errors": err_count,
                            "success_rate": round(exec_count / max(1, count), 4),
                        }
                    status["cross_session_outcomes"] = outcome_stats

                    # Most impactful actions (by positive delta frequency)
                    impactful = conn.execute(
                        "SELECT action, COUNT(*) as positive_count "
                        "FROM action_outcomes WHERE executed=1 AND error IS NULL "
                        "AND delta_json LIKE '%:%' GROUP BY action "
                        "ORDER BY positive_count DESC LIMIT 5"
                    ).fetchall()
                    status["most_impactful_actions"] = [
                        {"action": r[0], "positive_count": r[1]} for r in impactful
                    ]
                except Exception:
                    pass
                conn.close()
        except Exception:
            pass

        return status


# ── Singleton ───────────────────────────────────────────────────────────────

_action_loop: CognitiveActionLoop | None = None


def get_action_loop() -> CognitiveActionLoop:
    """Get the global CognitiveActionLoop instance."""
    global _action_loop
    if _action_loop is None:
        _action_loop = CognitiveActionLoop()
    return _action_loop
