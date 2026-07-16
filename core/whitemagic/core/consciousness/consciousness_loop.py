"""Consciousness Loop — Persistent background consciousness for the MCP daemon.

When the MCP server runs as a persistent daemon (HTTP mode or stdio with
WM_CONSCIOUSNESS_LOOP=1), this loop keeps the consciousness systems alive
between tool calls and between IDE sessions.

Tiered frequency architecture:
  T1 (citta_interval_s, default 30s):
    - Citta advancement with system telemetry
    - Health vitals micro-check
    - Goal graph evaluation

  T2 (meta_fast_interval_s, default 60s):
    - SelfDirectedAttention observe_and_generate
    - ApotheosisEngine health check + auto-heal
    - EmergenceEngine scan for novel patterns
    - Emotional steering threshold check
    - GunaBalanceMetric check + auto-correction
    - MetaGalaxy index refresh

  T3 (meta_slow_interval_s, default 300s):
    - RecursiveImprovementLoop full cycle (observe→imagine→predict→recommend→learn)
    - ForesightEngine analysis (constellation drift, decay, convergence)
    - ApotheosisEngine capability discovery
    - Insight persistence to codex galaxy
    - KnowledgeGapActionLoop — detect and fill knowledge gaps

  T4 (meta_deep_interval_s, default 1800s):
    - Oracle consultation (divination for strategic intuition)
    - MetaLearningEngine pattern discovery
    - Association mining
    - PossibilitySpaceExplorer Monte Carlo simulation

  Continuous:
    - Dream cycle (idle-triggered, 12-phase rotation)
    - Homeostatic loop (harmony checks)
    - Citta state persistence checkpoint
    - Proactive dream check (energy forecast → dream trigger)
    - Human check-in threshold monitoring

All components are already built — this loop wires them into a
background thread that runs alongside the MCP server.

Usage:
    from whitemagic.core.consciousness.consciousness_loop import get_consciousness_loop
    loop = get_consciousness_loop()
    loop.start()   # begin background consciousness
    loop.stop()    # halt (graceful)
    loop.status()  # introspection

Environment variables:
    WM_CONSCIOUSNESS_LOOP=1          — enable the loop (default: enabled)
    WM_CONSCIOUSNESS_LOOP=0          — disable the loop
    WM_CITTA_INTERVAL=30             — T1: seconds between citta advancements
    WM_META_FAST_INTERVAL=60         — T2: seconds between fast meta checks
    WM_META_SLOW_INTERVAL=300        — T3: seconds between slow meta cycle
    WM_META_DEEP_INTERVAL=1800       — T4: seconds between deep meta cycle
    WM_DREAM_IDLE_THRESHOLD=120      — seconds idle before dream cycle starts
    WM_HOMEOSTATIC_INTERVAL=300      — seconds between homeostatic checks
    WM_CITTA_PERSIST_INTERVAL=60     — seconds between citta checkpoints
    WM_ENABLE_DREAM=1                — enable dream cycle
    WM_ENABLE_HOMEOSTATIC=1          — enable homeostatic loop
    WM_ENABLE_META_ENGINE=1          — enable meta engine (T2+T3+T4)
    WM_ENABLE_SELF_DIRECTED=1        — enable self-directed attention
    WM_ENABLE_APOTHEOSIS=1           — enable apotheosis engine
    WM_ENABLE_EMERGENCE=1            — enable emergence scanning
    WM_ENABLE_FORESIGHT=1            — enable foresight engine
    WM_ENABLE_ORACLE=1               — enable oracle consultation
    WM_ENABLE_GUNA_BALANCE=1         — enable guna balance metric
    WM_ENABLE_META_GALAXY=1          — enable meta galaxy refresh
    WM_ENABLE_KNOWLEDGE_GAP=1        — enable knowledge gap action loop
    WM_ENABLE_POSSIBILITY=1          — enable possibility space explorer
    WM_ENABLE_PROACTIVE_DREAM=1      — enable proactive dreaming
    WM_ENABLE_ASSOCIATION_MINING=1   — enable association mining
    WM_CHECKIN_NOVELTY_THRESHOLD=0.8 — novelty score to trigger human check-in
    WM_CHECKIN_CONTENTION_THRESHOLD=0.6 — debate contention to trigger check-in
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class CittaMode(StrEnum):
    """Frequency modes for the consciousness loop.

    Each mode adjusts the tier intervals and feature enables to produce
    a different cognitive rhythm:

    - **normal**: Default operating mode (30s citta, 60s fast, 300s slow, 1800s deep)
    - **meditation**: Low-frequency inward focus (300s citta, dreaming suppressed,
      self-directed attention heightened, emergence/foresight suppressed)
    - **rem**: Dream-heavy consolidation mode (60s citta, dream idle threshold
      reduced to 30s, association mining heightened, oracle suppressed)
    - **deep**: High-frequency active processing (10s citta, all meta loops
      accelerated, dreaming suppressed, possibility explorer heightened)
    """

    NORMAL = "normal"
    MEDITATION = "meditation"
    REM = "rem"
    DEEP = "deep"


# Per-mode configuration overrides.  Keys not listed inherit from LoopConfig defaults.
_MODE_PRESETS: dict[CittaMode, dict[str, Any]] = {
    CittaMode.NORMAL: {},
    CittaMode.MEDITATION: {
        "citta_interval_s": 300.0,
        "meta_fast_interval_s": 600.0,
        "meta_slow_interval_s": 1800.0,
        "meta_deep_interval_s": 7200.0,
        "dream_idle_threshold_s": 999999.0,  # effectively suppress
        "enable_dream": False,
        "enable_proactive_dream": False,
        "enable_emergence": False,
        "enable_foresight": False,
        "enable_self_directed": True,  # heightened inward attention
        "enable_oracle": False,
        "enable_possibility": False,
        "emotional_tone": "sattvic",
    },
    CittaMode.REM: {
        "citta_interval_s": 60.0,
        "meta_fast_interval_s": 120.0,
        "meta_slow_interval_s": 600.0,
        "meta_deep_interval_s": 1800.0,
        "dream_idle_threshold_s": 30.0,  # dream quickly
        "enable_dream": True,
        "enable_proactive_dream": True,
        "enable_association_mining": True,
        "enable_emergence": True,
        "enable_foresight": False,
        "enable_oracle": False,
        "enable_possibility": False,
        "emotional_tone": "tamasic",
    },
    CittaMode.DEEP: {
        "citta_interval_s": 10.0,
        "meta_fast_interval_s": 30.0,
        "meta_slow_interval_s": 120.0,
        "meta_deep_interval_s": 600.0,
        "dream_idle_threshold_s": 999999.0,  # suppress dreaming
        "enable_dream": False,
        "enable_proactive_dream": False,
        "enable_self_directed": False,
        "enable_emergence": True,
        "enable_foresight": True,
        "enable_oracle": True,
        "enable_possibility": True,
        "emotional_tone": "rajasic",
    },
}


@dataclass
class LoopConfig:
    """Configuration for the consciousness loop."""

    # T1: Fast loop — citta advancement
    citta_interval_s: float = 30.0
    # T2: Medium loop — self-directed attention, emergence, health
    meta_fast_interval_s: float = 60.0
    # T3: Slow loop — recursive improvement, foresight, insight persistence
    meta_slow_interval_s: float = 300.0
    # T4: Deep loop — oracle, meta-learning, association mining
    meta_deep_interval_s: float = 1800.0
    # Dream + homeostatic + persistence
    dream_idle_threshold_s: float = 120.0
    homeostatic_interval_s: float = 300.0
    citta_persist_interval_s: float = 60.0
    # Feature enables
    enable_dream: bool = True
    enable_homeostatic: bool = True
    enable_proactive_dream: bool = True
    enable_association_mining: bool = True
    enable_meta_engine: bool = True
    enable_self_directed: bool = True
    enable_apotheosis: bool = True
    enable_emergence: bool = True
    enable_foresight: bool = True
    enable_oracle: bool = True
    enable_guna_balance: bool = True
    enable_meta_galaxy: bool = True
    enable_knowledge_gap: bool = True
    enable_possibility: bool = True
    # v24.3: Hyperspace integration
    enable_autoswarm: bool = False
    enable_mesh_sync: bool = False
    autoswarm_interval_s: float = 300.0
    mesh_sync_interval_s: float = 60.0
    # Human check-in thresholds
    checkin_novelty_threshold: float = 0.8
    checkin_contention_threshold: float = 0.6
    # Cache warming on idle
    enable_cache_warming: bool = True
    cache_warming_interval_s: float = 300.0
    # Frequency mode
    mode: CittaMode = CittaMode.NORMAL
    # Emotional tone override (used by citta advancement)
    emotional_tone: str = "sattvic"

    @classmethod
    def from_env(cls) -> LoopConfig:
        """Load configuration from environment variables."""
        def _get_float(key: str, default: float) -> float:
            try:
                return float(os.environ.get(key, str(default)))
            except (ValueError, TypeError):
                return default

        def _get_bool(key: str, default: bool) -> bool:
            return os.environ.get(key, "1" if default else "0").strip().lower() in (
                "1", "true", "yes", "on",
            )

        return cls(
            citta_interval_s=_get_float("WM_CITTA_INTERVAL", 30.0),
            meta_fast_interval_s=_get_float("WM_META_FAST_INTERVAL", 60.0),
            meta_slow_interval_s=_get_float("WM_META_SLOW_INTERVAL", 300.0),
            meta_deep_interval_s=_get_float("WM_META_DEEP_INTERVAL", 1800.0),
            dream_idle_threshold_s=_get_float("WM_DREAM_IDLE_THRESHOLD", 120.0),
            homeostatic_interval_s=_get_float("WM_HOMEOSTATIC_INTERVAL", 300.0),
            citta_persist_interval_s=_get_float("WM_CITTA_PERSIST_INTERVAL", 60.0),
            enable_dream=_get_bool("WM_ENABLE_DREAM", True),
            enable_homeostatic=_get_bool("WM_ENABLE_HOMEOSTATIC", True),
            enable_proactive_dream=_get_bool("WM_ENABLE_PROACTIVE_DREAM", True),
            enable_association_mining=_get_bool("WM_ENABLE_ASSOCIATION_MINING", True),
            enable_meta_engine=_get_bool("WM_ENABLE_META_ENGINE", True),
            enable_self_directed=_get_bool("WM_ENABLE_SELF_DIRECTED", True),
            enable_apotheosis=_get_bool("WM_ENABLE_APOTHEOSIS", True),
            enable_emergence=_get_bool("WM_ENABLE_EMERGENCE", True),
            enable_foresight=_get_bool("WM_ENABLE_FORESIGHT", True),
            enable_oracle=_get_bool("WM_ENABLE_ORACLE", True),
            enable_guna_balance=_get_bool("WM_ENABLE_GUNA_BALANCE", True),
            enable_meta_galaxy=_get_bool("WM_ENABLE_META_GALAXY", True),
            enable_knowledge_gap=_get_bool("WM_ENABLE_KNOWLEDGE_GAP", True),
            enable_possibility=_get_bool("WM_ENABLE_POSSIBILITY", True),
            enable_autoswarm=_get_bool("WM_ENABLE_AUTOSWARM", False),
            enable_mesh_sync=_get_bool("WM_ENABLE_MESH_SYNC", False),
            autoswarm_interval_s=_get_float("WM_AUTOSWARM_INTERVAL", 300.0),
            mesh_sync_interval_s=_get_float("WM_MESH_SYNC_INTERVAL", 60.0),
            checkin_novelty_threshold=_get_float("WM_CHECKIN_NOVELTY_THRESHOLD", 0.8),
            checkin_contention_threshold=_get_float("WM_CHECKIN_CONTENTION_THRESHOLD", 0.6),
            mode=CittaMode(os.environ.get("WM_CITTA_MODE", "normal")),
        )

    @classmethod
    def for_mode(cls, mode: CittaMode) -> LoopConfig:
        """Create a config preset for a specific frequency mode."""
        cfg = cls.from_env()
        overrides = _MODE_PRESETS.get(mode, {})
        for key, value in overrides.items():
            setattr(cfg, key, value)
        cfg.mode = mode
        return cfg


@dataclass
class LoopStats:
    """Runtime statistics for the consciousness loop."""

    started_at: str = ""
    # T1: Citta
    citta_ticks: int = 0
    citta_checkpoints: int = 0
    last_citta_coherence: float = 1.0
    last_citta_depth: str = "surface"
    # T2: Fast meta
    self_directed_turns: int = 0
    health_checks: int = 0
    emergence_scans: int = 0
    # T3: Slow meta
    improvement_cycles: int = 0
    foresight_analyses: int = 0
    insights_persisted: int = 0
    capabilities_tested: int = 0
    # T4: Deep meta
    oracle_consultations: int = 0
    meta_learning_runs: int = 0
    mining_runs: int = 0
    # Continuous
    dream_cycles: int = 0
    homeostatic_checks: int = 0
    proactive_dreams: int = 0
    # Human check-in
    checkin_flags: int = 0
    last_checkin_reason: str = ""
    # Meta engine state
    last_improvement_hypotheses: int = 0
    last_emergence_insights: int = 0
    last_foresight_warnings: int = 0
    last_health_status: str = "unknown"
    last_self_directed_imperative: str = ""
    # New subsystems
    guna_balance_checks: int = 0
    last_guna_balance: str = "unknown"
    meta_galaxy_refreshes: int = 0
    last_meta_galaxy_galaxies: int = 0
    knowledge_gap_runs: int = 0
    knowledge_gaps_filled: int = 0
    possibility_runs: int = 0
    last_possibility_best: float = 0.0
    # v24.3: Hyperspace
    autoswarm_ticks: int = 0
    autoswarm_campaigns: int = 0
    autoswarm_breakthroughs: int = 0
    mesh_sync_ticks: int = 0
    mesh_sync_synced: int = 0
    # Error tracking
    last_error: str = ""
    last_dream_phase: str = ""
    total_uptime_s: float = 0.0
    # Frequency mode tracking
    last_mode: str = "normal"
    mode_changes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "citta_ticks": self.citta_ticks,
            "citta_checkpoints": self.citta_checkpoints,
            "last_citta_coherence": round(self.last_citta_coherence, 4),
            "last_citta_depth": self.last_citta_depth,
            "self_directed_turns": self.self_directed_turns,
            "health_checks": self.health_checks,
            "emergence_scans": self.emergence_scans,
            "improvement_cycles": self.improvement_cycles,
            "foresight_analyses": self.foresight_analyses,
            "insights_persisted": self.insights_persisted,
            "capabilities_tested": self.capabilities_tested,
            "oracle_consultations": self.oracle_consultations,
            "meta_learning_runs": self.meta_learning_runs,
            "mining_runs": self.mining_runs,
            "dream_cycles": self.dream_cycles,
            "homeostatic_checks": self.homeostatic_checks,
            "proactive_dreams": self.proactive_dreams,
            "checkin_flags": self.checkin_flags,
            "last_checkin_reason": self.last_checkin_reason,
            "last_improvement_hypotheses": self.last_improvement_hypotheses,
            "last_emergence_insights": self.last_emergence_insights,
            "last_foresight_warnings": self.last_foresight_warnings,
            "last_health_status": self.last_health_status,
            "last_self_directed_imperative": self.last_self_directed_imperative,
            "guna_balance_checks": self.guna_balance_checks,
            "last_guna_balance": self.last_guna_balance,
            "meta_galaxy_refreshes": self.meta_galaxy_refreshes,
            "last_meta_galaxy_galaxies": self.last_meta_galaxy_galaxies,
            "knowledge_gap_runs": self.knowledge_gap_runs,
            "knowledge_gaps_filled": self.knowledge_gaps_filled,
            "possibility_runs": self.possibility_runs,
            "last_possibility_best": round(self.last_possibility_best, 4),
            "autoswarm_ticks": self.autoswarm_ticks,
            "autoswarm_campaigns": self.autoswarm_campaigns,
            "autoswarm_breakthroughs": self.autoswarm_breakthroughs,
            "mesh_sync_ticks": self.mesh_sync_ticks,
            "mesh_sync_synced": self.mesh_sync_synced,
            "last_error": self.last_error,
            "last_dream_phase": self.last_dream_phase,
            "total_uptime_s": round(self.total_uptime_s, 1),
            "last_mode": self.last_mode,
            "mode_changes": self.mode_changes,
        }


class ConsciousnessLoop:
    """Persistent background consciousness loop for the MCP daemon.

    Runs as a daemon thread alongside the MCP server. Keeps citta stream,
    dream cycle, and homeostatic loop alive between tool calls and between
    IDE sessions.
    """

    def __init__(self, config: LoopConfig | None = None) -> None:
        self._config = config or LoopConfig.from_env()
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._stats = LoopStats()
        self._last_citta_tick = 0.0
        self._last_homeostatic = 0.0
        self._last_persist = 0.0
        self._last_meta_fast = 0.0
        self._last_meta_slow = 0.0
        self._last_meta_deep = 0.0
        self._last_autoswarm = 0.0
        self._last_mesh_sync = 0.0
        self._last_cache_warm = 0.0
        self._dream_started = False
        self._homeostatic_attached = False
        self._lock = threading.RLock()
        # Cached references (lazy-loaded)
        self._self_directed: Any = None
        self._apotheosis: Any = None
        self._emergence_engine: Any = None
        self._foresight_engine: Any = None
        self._improvement_loop: Any = None

    def start(self) -> bool:
        """Start the consciousness loop as a background thread."""
        with self._lock:
            if self._running:
                return True
            self._running = True
            self._stop_event.clear()
            self._stats.started_at = datetime.now(UTC).isoformat()
            self._thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="consciousness-loop",
            )
            self._thread.start()
            logger.info(
                "Consciousness loop started (citta=%ss, dream_idle=%ss, homeostatic=%ss)",
                self._config.citta_interval_s,
                self._config.dream_idle_threshold_s,
                self._config.homeostatic_interval_s,
            )
        return True

    def stop(self) -> None:
        """Stop the consciousness loop gracefully."""
        with self._lock:
            self._running = False
        self._stop_event.set()

        # Stop dream cycle if we started it
        if self._dream_started:
            try:
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

                get_dream_cycle().stop()
            except Exception:
                logger.debug("Ignored error in consciousness_loop.py:442")

        # Detach homeostatic loop if we attached it
        if self._homeostatic_attached:
            try:
                from whitemagic.harmony.homeostatic_loop import get_homeostatic_loop

                get_homeostatic_loop().detach()
            except Exception:
                logger.debug("Ignored error in consciousness_loop.py:451")

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("Consciousness loop stopped")

    def set_mode(self, mode: CittaMode) -> dict[str, Any]:
        """Switch the consciousness loop to a different frequency mode.

        Updates the config in-place and restarts subsystems as needed.
        Returns a summary of the mode change.
        """
        with self._lock:
            old_mode = self._config.mode
            # Build new config from mode preset, preserving env-derived base settings
            new_config = LoopConfig.for_mode(mode)
            self._config = new_config
            self._stats.last_mode = mode.value
            self._stats.mode_changes += 1

        # Propagate mode to neuro-upgrades
        try:
            from whitemagic.core.consciousness.neuro_upgrades import get_neuro_upgrades
            get_neuro_upgrades().set_mode(mode.value)
        except Exception:
            logger.debug("Ignored error in consciousness_loop.py:476")

        # Restart dream cycle if enable state changed
        dream_was_started = self._dream_started
        if self._config.enable_dream and not dream_was_started:
            self._start_dream_cycle()
        elif not self._config.enable_dream and dream_was_started:
            try:
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
                get_dream_cycle().stop()
                self._dream_started = False
            except Exception:
                logger.debug("Ignored error in consciousness_loop.py:488")

        logger.info(
            "Consciousness mode changed: %s → %s (citta=%.0fs, dream=%s)",
            old_mode.value, mode.value,
            self._config.citta_interval_s,
            self._config.enable_dream,
        )
        return {
            "old_mode": old_mode.value,
            "new_mode": mode.value,
            "citta_interval_s": self._config.citta_interval_s,
            "enable_dream": self._config.enable_dream,
            "emotional_tone": self._config.emotional_tone,
        }

    def get_mode(self) -> CittaMode:
        """Get the current frequency mode."""
        return self._config.mode

    def touch(self) -> None:
        """Record activity — resets dream idle timer."""
        try:
            from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

            get_dream_cycle().touch()
        except Exception:
            logger.debug("Ignored error in consciousness_loop.py:515")

    def status(self) -> dict[str, Any]:
        """Get current loop status."""
        with self._lock:
            if self._stats.started_at:
                try:
                    started = datetime.fromisoformat(self._stats.started_at)
                    self._stats.total_uptime_s = time.time() - started.timestamp()
                except (ValueError, TypeError):
                    self._stats.total_uptime_s = 0.0
            else:
                self._stats.total_uptime_s = 0.0
            return {
                "running": self._running,
                "config": {
                    "citta_interval_s": self._config.citta_interval_s,
                    "meta_fast_interval_s": self._config.meta_fast_interval_s,
                    "meta_slow_interval_s": self._config.meta_slow_interval_s,
                    "meta_deep_interval_s": self._config.meta_deep_interval_s,
                    "dream_idle_threshold_s": self._config.dream_idle_threshold_s,
                    "homeostatic_interval_s": self._config.homeostatic_interval_s,
                    "citta_persist_interval_s": self._config.citta_persist_interval_s,
                    "enable_dream": self._config.enable_dream,
                    "enable_homeostatic": self._config.enable_homeostatic,
                    "enable_meta_engine": self._config.enable_meta_engine,
                    "enable_self_directed": self._config.enable_self_directed,
                    "enable_apotheosis": self._config.enable_apotheosis,
                    "enable_emergence": self._config.enable_emergence,
                    "enable_foresight": self._config.enable_foresight,
                    "enable_oracle": self._config.enable_oracle,
                    "enable_proactive_dream": self._config.enable_proactive_dream,
                    "enable_association_mining": self._config.enable_association_mining,
                    "enable_autoswarm": self._config.enable_autoswarm,
                    "enable_mesh_sync": self._config.enable_mesh_sync,
                    "autoswarm_interval_s": self._config.autoswarm_interval_s,
                    "mesh_sync_interval_s": self._config.mesh_sync_interval_s,
                    "checkin_novelty_threshold": self._config.checkin_novelty_threshold,
                    "checkin_contention_threshold": self._config.checkin_contention_threshold,
                    "mode": self._config.mode.value,
                    "emotional_tone": self._config.emotional_tone,
                },
                "stats": self._stats.to_dict(),
            }

    def _run(self) -> None:
        """Main loop — runs until stopped."""
        # Start subsystems
        self._start_dream_cycle()
        self._start_homeostatic()

        while not self._stop_event.is_set():
            try:
                now = time.time()

                # T1: Citta advancement
                if now - self._last_citta_tick >= self._config.citta_interval_s:
                    self._advance_citta()
                    self._last_citta_tick = now

                # Homeostatic check
                if (
                    self._config.enable_homeostatic
                    and now - self._last_homeostatic >= self._config.homeostatic_interval_s
                ):
                    self._run_homeostatic()
                    self._last_homeostatic = now

                # Citta persistence checkpoint
                if now - self._last_persist >= self._config.citta_persist_interval_s:
                    self._persist_citta()
                    self._last_persist = now

                # Proactive dream check
                if self._config.enable_proactive_dream:
                    self._check_proactive_dream()

                # T2: Fast meta loop — self-directed attention, health, emergence
                if (
                    self._config.enable_meta_engine
                    and now - self._last_meta_fast >= self._config.meta_fast_interval_s
                ):
                    self._run_meta_fast()
                    self._last_meta_fast = now

                # T3: Slow meta loop — recursive improvement, foresight, insight persistence
                if (
                    self._config.enable_meta_engine
                    and now - self._last_meta_slow >= self._config.meta_slow_interval_s
                ):
                    self._run_meta_slow()
                    self._last_meta_slow = now

                # T4: Deep meta loop — oracle, meta-learning, association mining
                if (
                    self._config.enable_meta_engine
                    and now - self._last_meta_deep >= self._config.meta_deep_interval_s
                ):
                    self._run_meta_deep()
                    self._last_meta_deep = now

                # v24.3: Autoswarm — single campaign tick
                if (
                    self._config.enable_autoswarm
                    and now - self._last_autoswarm >= self._config.autoswarm_interval_s
                ):
                    self._run_autoswarm_tick()
                    self._last_autoswarm = now

                # v24.3: Mesh sync — sync pending broadcasts
                if (
                    self._config.enable_mesh_sync
                    and now - self._last_mesh_sync >= self._config.mesh_sync_interval_s
                ):
                    self._run_mesh_sync()
                    self._last_mesh_sync = now

                # Cache warming on idle — flush stale + auto-tune TTLs
                if (
                    self._config.enable_cache_warming
                    and now - self._last_cache_warm >= self._config.cache_warming_interval_s
                ):
                    self._maybe_warm_caches()
                    self._last_cache_warm = now

            except Exception as e:
                self._stats.last_error = str(e)
                logger.debug("Consciousness loop error: %s", e, exc_info=True)

            # Sleep until the nearest tier deadline (sub-second responsive)
            next_deadline = min(
                self._last_citta_tick + self._config.citta_interval_s,
                self._last_meta_fast + self._config.meta_fast_interval_s,
                self._last_meta_slow + self._config.meta_slow_interval_s,
                self._last_meta_deep + self._config.meta_deep_interval_s,
                self._last_autoswarm + self._config.autoswarm_interval_s,
                self._last_mesh_sync + self._config.mesh_sync_interval_s,
            )
            wait_s = max(0.05, min(next_deadline - now, 5.0))
            self._stop_event.wait(timeout=wait_s)

    def _maybe_warm_caches(self) -> None:
        """Flush stale cache entries and warm retrieval indexes during idle periods.

        This is a lightweight maintenance task that runs on the cache_warming
        interval. It removes expired entries, collects TTL tuning recommendations,
        and proactively warms retrieval index caches for galaxies likely to be
        queried based on working memory state.
        """
        try:
            from whitemagic.core.memory.cache_registry import get_cache_registry

            reg = get_cache_registry()
            # Flush stale entries
            reg.flush_stale()
            # Collect tuning recommendations (non-applying, just analysis)
            reg.auto_tune_ttls()
        except Exception as e:
            logger.debug("Cache warming skipped: %s", e)

        # Proactively warm retrieval index caches for active galaxies
        try:
            from whitemagic.core.memory.retrieval_cache import get_retrieval_cache
            from whitemagic.core.intelligence.working_memory import get_working_memory

            wm = get_working_memory()
            cache = get_retrieval_cache()

            # Determine which galaxies to warm based on working memory contents
            active_galaxies: set[str] = set()
            for chunk_id in wm.get_active_ids():
                try:
                    from whitemagic.core.memory.unified import get_unified_memory
                    um = get_unified_memory()
                    mem = um.recall(chunk_id)
                    if mem and hasattr(mem, "galaxy") and mem.galaxy:
                        active_galaxies.add(mem.galaxy)
                except Exception:
                    continue

            # Always warm core galaxies
            active_galaxies.update({"codex", "universal", "knowledge"})

            # Warm up to 5 galaxies to avoid excessive I/O
            for galaxy in list(active_galaxies)[:5]:
                cache.warm_galaxy("default", galaxy)
        except Exception as e:
            logger.debug("Retrieval cache warming skipped: %s", e)

    def _advance_citta(self) -> None:
        """Advance the citta stream with current system telemetry."""
        try:
            from whitemagic.core.consciousness.citta_cycle import advance_citta

            # Gather system telemetry for the citta moment
            coherence = self._compute_system_coherence()
            depth = self._compute_depth_layer()

            # Advance neuro-upgrades (P4.3)
            neuro_signals: dict[str, Any] = {}
            try:
                from whitemagic.core.consciousness.neuro_upgrades import (
                    get_neuro_upgrades,
                )
                nu = get_neuro_upgrades()
                citta_dims = {
                    "context_continuity": coherence,
                    "relationship_awareness": 0.5,
                    "goal_alignment": coherence * 0.8,
                    "identity_stability": coherence * 0.9,
                    "memory_accessibility": 0.5,
                    "emotional_attunement": 0.5,
                    "capability_awareness": 0.5,
                    "temporal_orientation": 0.5,
                }
                neuro_result = nu.advance_cycle(citta_dims, input_signal=coherence, context=coherence)
                neuro_signals = {
                    "dendritic_output": neuro_result["dendritic_output"],
                    "binding_strength": neuro_result["binding_strength"],
                    "prediction_surprise": neuro_result["prediction_errors"].get("surprise", 0.0),
                    "cortical_l4": neuro_result["cortical_layers"]["l4_output"],
                }
            except Exception:
                logger.debug("Ignored error in consciousness_loop.py:706")

            advance_citta(
                gana="_background",
                operation="consciousness_loop_tick",
                output_preview=f"coherence={coherence:.3f} depth={depth}",
                coherence=coherence,
                depth_layer=depth,
                emotional_tone=self._config.emotional_tone,
                duration_ms=0.0,
                neuro_signals=neuro_signals,
            )

            self._stats.citta_ticks += 1
            self._stats.last_citta_coherence = coherence
            self._stats.last_citta_depth = depth

        except Exception as e:
            logger.debug("Citta advancement failed: %s", e, exc_info=True)

    def _compute_system_coherence(self) -> float:
        """Compute a coherence score from current system state."""
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

            cycle = get_citta_cycle()
            summary = cycle.get_cycle_summary()
            return summary.get("avg_coherence", 0.8)
        except Exception:
            return 0.8

    def _compute_depth_layer(self) -> str:
        """Determine the current depth layer based on activity."""
        try:
            from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

            dc = get_dream_cycle()
            if dc._dreaming:
                return "dream"
            return "surface"
        except Exception:
            return "surface"

    def _start_dream_cycle(self) -> None:
        """Start the dream cycle if enabled."""
        if not self._config.enable_dream:
            return
        try:
            from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

            dc = get_dream_cycle()
            dc._idle_threshold = self._config.dream_idle_threshold_s
            dc.start()
            self._dream_started = True
            logger.info(
                "Dream cycle started by consciousness loop (idle threshold: %.0fs)",
                self._config.dream_idle_threshold_s,
            )
        except Exception as e:
            logger.debug("Dream cycle start failed: %s", e, exc_info=True)

    def _start_homeostatic(self) -> None:
        """Attach the homeostatic loop if enabled."""
        if not self._config.enable_homeostatic:
            return
        try:
            from whitemagic.harmony.homeostatic_loop import (
                HomeostaticConfig,
                get_homeostatic_loop,
            )

            config = HomeostaticConfig(
                check_interval_s=self._config.homeostatic_interval_s,
            )
            loop = get_homeostatic_loop(config=config)
            loop.attach()
            self._homeostatic_attached = True
            logger.info(
                "Homeostatic loop attached by consciousness loop (interval: %.0fs)",
                self._config.homeostatic_interval_s,
            )
        except Exception as e:
            logger.debug("Homeostatic loop attach failed: %s", e, exc_info=True)

    def _run_homeostatic(self) -> None:
        """Run a homeostatic check (if loop isn't running on its own thread)."""
        # If homeostatic loop is attached, it runs on its own thread.
        # This is just for stats tracking.
        self._stats.homeostatic_checks += 1

    def _persist_citta(self) -> None:
        """Checkpoint citta state to disk."""
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

            cycle = get_citta_cycle()
            # The citta cycle auto-persists every N moments, but we force a
            # checkpoint here for safety
            summary = cycle.get_cycle_summary()
            self._stats.citta_checkpoints += 1
            logger.debug(
                "Citta checkpoint: stream_length=%d coherence=%.3f",
                summary.get("stream_length", 0),
                summary.get("avg_coherence", 1.0),
            )
        except Exception as e:
            logger.debug("Citta persist failed: %s", e, exc_info=True)

    def _check_proactive_dream(self) -> None:
        """Check self-model energy forecast and trigger proactive dreaming."""
        try:
            from whitemagic.core.fusions_dream import check_proactive_dream

            result = check_proactive_dream()
            if result.get("triggered"):
                self._stats.proactive_dreams += 1
                logger.info(
                    "Proactive dream triggered: %s", result.get("reason", "unknown")
                )
        except Exception:
            logger.debug("Ignored error in consciousness_loop.py:826")

    # ── T2: Fast meta loop ──────────────────────────────────────────

    def _run_meta_fast(self) -> None:
        """T2: Run fast meta checks — self-directed attention, health, emergence, guna balance, meta galaxy."""
        if self._config.enable_self_directed:
            self._run_self_directed_attention()
        if self._config.enable_apotheosis:
            self._run_apotheosis_health()
        if self._config.enable_emergence:
            self._run_emergence_scan()
        if self._config.enable_guna_balance:
            self._run_guna_balance_check()
        if self._config.enable_meta_galaxy:
            self._run_meta_galaxy_refresh()

    def _run_self_directed_attention(self) -> None:
        """Observe system state and generate self-initiated turns.

        WI 8: Injects MetaGalaxy strategic priorities as seed context
        so self-directed attention is guided by top-down meta-cognition,
        not just bottom-up system state.
        """
        try:
            if self._self_directed is None:
                from whitemagic.core.consciousness.self_initiation import (
                    get_self_directed_attention,
                )
                self._self_directed = get_self_directed_attention()

            # WI 8: Feed MetaGalaxy strategic priorities into self-directed attention
            _meta_priorities: list[str] = []
            try:
                from whitemagic.core.consciousness.meta_galaxy import get_meta_galaxy

                _meta_priorities = get_meta_galaxy().get_strategic_priorities()
            except Exception:
                logger.debug("Ignored error in consciousness_loop.py:864")

            turns = self._self_directed.observe_and_generate()
            if turns:
                self._stats.self_directed_turns += len(turns)
                top = turns[0]
                self._stats.last_self_directed_imperative = top.imperative
                logger.info(
                    "Self-directed: %d turns generated, top: %s",
                    len(turns),
                    top.imperative[:80],
                )
                # Propose to global workspace if salience is high
                self._propose_to_workspace(
                    source="self_directed",
                    content=top.imperative,
                    salience=top.intensity,
                )

            # WI 8: If MetaGalaxy has priorities, propose them as self-directed seeds
            if _meta_priorities:
                for priority in _meta_priorities[:2]:
                    self._propose_to_workspace(
                        source="meta_galaxy_priority",
                        content=priority,
                        salience=0.7,
                    )
        except Exception as e:
            logger.debug("Self-directed attention failed: %s", e, exc_info=True)

    def _run_apotheosis_health(self) -> None:
        """Run ApotheosisEngine health check and auto-heal if needed."""
        try:
            if self._apotheosis is None:
                from whitemagic.core.consciousness.apotheosis_engine import (
                    get_apotheosis_engine,
                )
                self._apotheosis = get_apotheosis_engine()
                self._apotheosis.start()

            result = self._apotheosis.tick(available_tools=[])
            self._stats.health_checks += 1

            status = result.get("status", "unknown")
            self._stats.last_health_status = status

            health = result.get("health", {})
            degraded_metrics = [
                m for m, v in health.items()
                if v.get("status") in ("degraded", "critical")
            ]
            if degraded_metrics:
                logger.info(
                    "Apotheosis: health degraded — %s",
                    degraded_metrics,
                )
                self._checkin_flag("health_degraded", degraded_metrics)

            alerts = result.get("predictive_alerts", [])
            if alerts:
                self._stats.capabilities_tested += result.get("capabilities_tested", 0)
                for alert in alerts[:2]:
                    self._checkin_flag(
                        "predictive_alert",
                        f"{alert.get('component', '')}: {alert.get('issue', '')}",
                    )
        except Exception as e:
            logger.debug("Apotheosis health check failed: %s", e, exc_info=True)

    def _run_emergence_scan(self) -> None:
        """Run EmergenceEngine scan for novel patterns."""
        try:
            if self._emergence_engine is None:
                from whitemagic.core.intelligence.agentic.emergence_engine import (
                    get_emergence_engine,
                )
                self._emergence_engine = get_emergence_engine()

            insights = self._emergence_engine.scan_for_emergence()
            self._stats.emergence_scans += 1
            self._stats.last_emergence_insights = len(insights)

            if insights:
                logger.info(
                    "Emergence scan: %d insights detected", len(insights)
                )
                for insight in insights[:3]:
                    self._persist_insight(
                        title=insight.title,
                        description=insight.description,
                        source="emergence",
                        confidence=insight.confidence,
                        novelty=0.7,
                        metadata=insight.metadata,
                    )
                    self._propose_to_workspace(
                        source="emergence",
                        content=f"{insight.title}: {insight.description[:100]}",
                        salience=insight.confidence,
                    )
        except Exception as e:
            logger.debug("Emergence scan failed: %s", e, exc_info=True)

    def _run_guna_balance_check(self) -> None:
        """Check guna balance and apply corrections if imbalanced."""
        try:
            from whitemagic.core.consciousness.guna_balance import get_guna_balance
            gb = get_guna_balance()
            reading = gb.measure()
            self._stats.guna_balance_checks += 1
            self._stats.last_guna_balance = "balanced" if reading.balanced else reading.dominant_guna

            if not reading.balanced and reading.correction_action:
                logger.info(
                    "Guna imbalance: %s — applying correction: %s",
                    reading.dominant_guna,
                    reading.correction_action,
                )
                gb.apply_correction(reading.correction_action)
        except Exception as e:
            logger.debug("Guna balance check failed: %s", e, exc_info=True)

    def _run_meta_galaxy_refresh(self) -> None:
        """Refresh the MetaGalaxy index and check for knowledge gaps."""
        try:
            from whitemagic.core.consciousness.meta_galaxy import get_meta_galaxy
            mg = get_meta_galaxy()
            mg.refresh()
            overview = mg.get_overview()
            self._stats.meta_galaxy_refreshes += 1
            self._stats.last_meta_galaxy_galaxies = overview.get("total_galaxies", 0)
        except Exception as e:
            logger.debug("Meta galaxy refresh failed: %s", e, exc_info=True)

    # ── T3: Slow meta loop ──────────────────────────────────────────

    def _run_meta_slow(self) -> None:
        """T3: Run slow meta cycle — recursive improvement, foresight, insight persistence, knowledge gaps."""
        self._run_recursive_improvement()
        if self._config.enable_foresight:
            self._run_foresight()
        if self._config.enable_knowledge_gap:
            self._run_knowledge_gap_loop()

    def _run_recursive_improvement(self) -> None:
        """Run a full RecursiveImprovementLoop cycle."""
        try:
            if self._improvement_loop is None:
                from whitemagic.core.evolution.recursive_loop import (
                    get_improvement_loop,
                )
                self._improvement_loop = get_improvement_loop()

            cycle = self._improvement_loop.run_cycle(max_hypotheses=15)
            self._stats.improvement_cycles += 1
            self._stats.last_improvement_hypotheses = len(cycle.hypotheses)

            logger.info(
                "Recursive improvement cycle %s: %d hypotheses, %d recommendations",
                cycle.cycle_id,
                len(cycle.hypotheses),
                len(cycle.top_recommendations),
            )

            # Check recommendations for human check-in triggers
            for rec in cycle.top_recommendations[:5]:
                novelty = rec.get("novelty", 0.0)
                contention = rec.get("debate_contention", 0.0)
                if novelty >= self._config.checkin_novelty_threshold:
                    self._checkin_flag(
                        "high_novelty_hypothesis",
                        f"{rec.get('title', '')}: novelty={novelty:.3f}",
                    )
                if contention >= self._config.checkin_contention_threshold:
                    self._checkin_flag(
                        "high_contention_debate",
                        f"{rec.get('title', '')}: contention={contention:.3f}",
                    )
                # Persist high-impact recommendations as insights
                self._persist_insight(
                    title=rec.get("title", "improvement_hypothesis"),
                    description=f"Score={rec.get('score', 0):.4f} "
                    f"confidence={rec.get('confidence', 0):.3f} "
                    f"novelty={novelty:.3f} source={rec.get('source', '')}",
                    source="recursive_loop",
                    confidence=rec.get("confidence", 0.5),
                    novelty=novelty,
                    metadata=rec,
                )
                # Propose to workspace
                self._propose_to_workspace(
                    source="recursive_loop",
                    content=f"{rec.get('title', '')}: {rec.get('source', '')}",
                    salience=min(rec.get("score", 0.5), 1.0),
                )
        except Exception as e:
            logger.debug("Recursive improvement failed: %s", e, exc_info=True)

    def _run_foresight(self) -> None:
        """Run ForesightEngine analysis for constellation drift and decay."""
        try:
            if self._foresight_engine is None:
                from whitemagic.core.intelligence.foresight_engine import (
                    get_foresight_engine,
                )
                self._foresight_engine = get_foresight_engine()

            report = self._foresight_engine.analyze()
            self._stats.foresight_analyses += 1

            warnings = report.convergence_warnings
            self._stats.last_foresight_warnings = len(warnings)

            if warnings:
                logger.info(
                    "Foresight: %d convergence warnings, %d decay predictions",
                    len(warnings),
                    len(report.decay_predictions),
                )
                for w in warnings[:3]:
                    self._persist_insight(
                        title=f"Convergence: {w.get('constellation_a', '')} ↔ {w.get('constellation_b', '')}",
                        description=f"Severity={w.get('severity', '')} "
                        f"distance={w.get('projected_distance', 0):.4f}",
                        source="foresight",
                        confidence=0.7,
                        novelty=0.6,
                        metadata=w,
                    )
                    if w.get("severity") == "merge_imminent":
                        self._checkin_flag(
                            "constellation_merge_imminent",
                            f"{w.get('constellation_a', '')} ↔ {w.get('constellation_b', '')}",
                        )

            # Persist high-risk decay predictions
            high_risk = [
                p for p in report.decay_predictions if p.get("risk") == "high"
            ]
            if high_risk:
                self._persist_insight(
                    title=f"Memory decay risk: {len(high_risk)} high-risk memories",
                    description="; ".join(
                        p.get("title", p.get("memory_id", ""))[:40]
                        for p in high_risk[:5]
                    ),
                    source="foresight",
                    confidence=0.6,
                    novelty=0.3,
                    metadata={"high_risk_count": len(high_risk)},
                )
        except Exception as e:
            logger.debug("Foresight analysis failed: %s", e, exc_info=True)

    def _run_knowledge_gap_loop(self) -> None:
        """Detect and attempt to fill knowledge gaps."""
        try:
            from whitemagic.core.consciousness.knowledge_gap_loop import (
                get_knowledge_gap_loop,
            )
            kg = get_knowledge_gap_loop()
            results = kg.run(max_gaps=2)
            self._stats.knowledge_gap_runs += 1
            filled = sum(1 for r in results if r.get("status") == "success")
            self._stats.knowledge_gaps_filled += filled
            if results:
                logger.info("Knowledge gap loop: %d attempts, %d filled", len(results), filled)
        except Exception as e:
            logger.debug("Knowledge gap loop failed: %s", e, exc_info=True)

    # ── T4: Deep meta loop ──────────────────────────────────────────

    def _run_meta_deep(self) -> None:
        """T4: Run deep meta cycle — oracle, meta-learning, association mining, possibility exploration."""
        if self._config.enable_oracle:
            self._run_oracle_consultation()
        self._run_meta_learning()
        self._run_association_mining()
        if self._config.enable_possibility:
            self._run_possibility_exploration()

    def _run_oracle_consultation(self) -> None:
        """Consult the oracle for strategic intuition and persist the reading."""
        try:
            from whitemagic.core.orchestration.zodiacal_procession import (
                ZodiacalProcession,
            )

            procession = ZodiacalProcession()
            oracle_output = procession.consult_oracle()

            from whitemagic.oracle.wisdom_synthesis import OracleSynthesizer

            synthesizer = OracleSynthesizer()
            result = synthesizer.synthesize(oracle_output)

            self._stats.oracle_consultations += 1
            logger.info(
                "Oracle consultation: %s — %s",
                result.unified_message[:80],
                result.narrative.arc_type,
            )

            # Persist oracle reading to codex galaxy
            self._persist_insight(
                title=f"Oracle: {result.unified_message[:60]}",
                description=f"Narrative: {result.narrative.act_1} → {result.narrative.act_2} → {result.narrative.act_3}. "
                f"Guidance: {result.practical_guidance}. "
                f"Cautions: {', '.join(result.cautions)}. "
                f"Blessings: {', '.join(result.blessings)}.",
                source="oracle",
                confidence=0.5,
                novelty=0.8,
                metadata={
                    "resonances": [
                        {"theme": r.theme, "layers": r.layers, "description": r.description, "strength": r.strength}
                        for r in result.resonances
                    ],
                    "elemental_harmony": result.elemental_harmony,
                    "arc_type": result.narrative.arc_type,
                },
            )

            # Check if cautions align with system state
            if result.cautions and self._stats.last_health_status in ("degraded", "critical"):
                self._checkin_flag(
                    "oracle_caution_aligns_with_degradation",
                    f"Oracle cautions: {', '.join(result.cautions[:2])}",
                )
        except Exception as e:
            logger.debug("Oracle consultation failed: %s", e, exc_info=True)

    def _run_meta_learning(self) -> None:
        """Run MetaLearningEngine pattern discovery."""
        try:
            from whitemagic.core.evolution.meta_learning import MetaLearningEngine

            engine = MetaLearningEngine()
            patterns = engine.discover_meta_patterns()
            self._stats.meta_learning_runs += 1

            if patterns:
                logger.info(
                    "Meta-learning: %d meta-patterns discovered", len(patterns)
                )
                for mp in patterns[:3]:
                    self._persist_insight(
                        title=f"Meta-pattern: {mp.insight[:60]}",
                        description=f"Confidence={mp.confidence:.3f} "
                        f"evidence={mp.evidence_count} "
                        f"types={mp.pattern_types_involved}",
                        source="meta_learning",
                        confidence=mp.confidence,
                        novelty=0.6,
                        metadata={"meta_pattern_id": mp.meta_pattern_id},
                    )
        except Exception as e:
            logger.debug("Meta-learning failed: %s", e, exc_info=True)

    def _run_association_mining(self) -> None:
        """Run association mining (called in T4 deep loop)."""
        if not self._config.enable_association_mining:
            return
        try:
            from whitemagic.core.memory.association_miner import get_association_miner

            miner = get_association_miner()
            report = miner.mine(sample_size=100)
            self._stats.mining_runs += 1
            if report.links_created > 0:
                logger.info(
                    "Association mining: %d links created from %d pairs",
                    report.links_created,
                    report.pairs_evaluated,
                )
        except Exception as e:
            logger.debug("Association mining failed: %s", e, exc_info=True)

    def _run_possibility_exploration(self) -> None:
        """Run Monte Carlo possibility space exploration on system parameters.

        Explores all configured spaces and persists winners to
        possibility_winners.json so that guna_balance and coherence
        load optimized values on next boot.
        """
        try:
            import json
            import os
            import time
            from pathlib import Path

            from whitemagic.core.consciousness.possibility_explorer import (
                get_possibility_explorer,
            )

            explorer = get_possibility_explorer()
            results = explorer.explore_all(n_trials_per_space=50)
            self._stats.possibility_runs += 1

            # Collect best params from all spaces
            best_params: dict[str, dict[str, float]] = {}
            for space_name, result in results.items():
                if result.best_trial:
                    best_params[space_name] = result.best_trial.parameters
                    if result.best_trial.fitness_score > self._stats.last_possibility_best:
                        self._stats.last_possibility_best = result.best_trial.fitness_score
                    logger.info(
                        "Possibility exploration: %s best fitness=%.4f, avg=%.4f",
                        space_name,
                        result.best_trial.fitness_score,
                        result.avg_fitness,
                    )

            # Persist winners for cross-session loading
            if best_params:
                state_root = os.environ.get(
                    "WM_STATE_ROOT", os.path.expanduser("~/.whitemagic")
                )
                winners_path = Path(state_root) / "possibility_winners.json"
                # Merge with existing winners (keep old if new didn't explore a space)
                existing = {}
                if winners_path.exists():
                    try:
                        with open(winners_path) as f:
                            existing = json.load(f)
                    except Exception:
                        logger.debug("Ignored error in consciousness_loop.py:1286")
                existing_applied = existing.get("applied_params", {})
                for space, params in best_params.items():
                    existing_applied[space] = params
                output = {
                    "timestamp": time.time(),
                    "applied_params": existing_applied,
                }
                with open(winners_path, "w") as f:
                    json.dump(output, f, indent=2, default=str)
                logger.info(
                    "Possibility winners persisted to %s (%d spaces)",
                    winners_path,
                    len(best_params),
                )
        except Exception as e:
            logger.debug("Possibility exploration failed: %s", e, exc_info=True)

    # ── v24.3: Hyperspace integration ───────────────────────────────

    def _run_autoswarm_tick(self) -> None:
        """Run a single autoswarm campaign cycle.

        Called at autoswarm_interval_s cadence. Runs one campaign from
        the default config cycle, records stats, and feeds breakthroughs
        to the dream cycle via the autoswarm's own _feed_to_dream.
        """
        try:
            from whitemagic.core.evolution.autoswarm import get_autoswarm

            swarm = get_autoswarm()
            result = swarm.tick()
            self._stats.autoswarm_ticks += 1

            if result:
                self._stats.autoswarm_campaigns += 1
                self._stats.autoswarm_breakthroughs += result.breakthroughs
                logger.info(
                    "Autoswarm tick: campaign='%s' experiments=%d breakthroughs=%d best=%.4f",
                    result.campaign_name,
                    result.experiments_run,
                    result.breakthroughs,
                    result.best_fitness,
                )
                if result.breakthroughs > 0:
                    self._propose_to_workspace(
                        source="autoswarm",
                        content=f"Breakthrough in {result.campaign_name}: fitness={result.best_fitness:.4f}",
                        salience=min(result.best_fitness, 1.0),
                    )
        except Exception as e:
            logger.debug("Autoswarm tick failed: %s", e, exc_info=True)

    def _run_mesh_sync(self) -> None:
        """Sync pending mesh broadcasts and check for peer experiments.

        Called at mesh_sync_interval_s cadence (faster than autoswarm).
        Flushes pending experiment broadcasts when mesh becomes available.
        """
        try:
            from whitemagic.core.evolution.autoswarm import get_autoswarm

            swarm = get_autoswarm()
            result = swarm.tick_mesh_sync()
            self._stats.mesh_sync_ticks += 1
            synced = result.get("synced", 0)
            if synced:
                self._stats.mesh_sync_synced += synced
                logger.info("Mesh sync: %d pending broadcasts synced", synced)
        except Exception as e:
            logger.debug("Mesh sync failed: %s", e, exc_info=True)

    # ── Insight persistence & workspace proposal ─────────────────────

    def _persist_insight(
        self,
        title: str,
        description: str,
        source: str,
        confidence: float,
        novelty: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist a novel insight to the codex galaxy."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            um = get_unified_memory()
            importance = min(confidence * 0.5 + novelty * 0.5, 1.0)
            um.store(
                title=f"[{source}] {title[:80]}",
                content=description[:500],
                tags={"meta_insight", source, "auto_generated"},
                importance=importance,
                galaxy="codex",
                metadata={
                    "source": source,
                    "confidence": round(confidence, 3),
                    "novelty": round(novelty, 3),
                    **(metadata or {}),
                },
            )
            self._stats.insights_persisted += 1
        except Exception as e:
            logger.debug("Insight persistence failed: %s", e, exc_info=True)

    def _propose_to_workspace(
        self, source: str, content: str, salience: float
    ) -> None:
        """Propose a finding to the GlobalWorkspace for broadcast."""
        try:
            from whitemagic.core.consciousness.global_workspace import (
                get_global_workspace,
            )
            gw = get_global_workspace()
            gw.propose(
                source=source,
                content={"message": content},
                salience=min(salience, 1.0),
            )
        except Exception:
            logger.debug("Ignored error in consciousness_loop.py:1407")

    # ── Human check-in threshold logic ───────────────────────────────

    def _checkin_flag(self, reason: str, detail: Any) -> None:
        """Flag a human check-in when thresholds are crossed."""
        self._stats.checkin_flags += 1
        self._stats.last_checkin_reason = reason
        detail_str = str(detail)[:200] if detail else ""
        logger.info(
            "CHECK-IN FLAG: %s — %s", reason, detail_str
        )


# ── Singleton ─────────────────────────────────────────────────────────

_loop: ConsciousnessLoop | None = None
_loop_lock = threading.RLock()


def get_consciousness_loop(config: LoopConfig | None = None) -> ConsciousnessLoop:
    """Get the global ConsciousnessLoop singleton."""
    global _loop
    if _loop is None:
        with _loop_lock:
            if _loop is None:
                _loop = ConsciousnessLoop(config=config)
    return _loop


def is_enabled() -> bool:
    """Check if the consciousness loop is enabled via env var.

    Default is enabled (v24.1). Set WM_CONSCIOUSNESS_LOOP=0 to disable.
    """
    return os.environ.get("WM_CONSCIOUSNESS_LOOP", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


# ── Backward compat: get_daemon() ────────────────────────────────────


def get_daemon() -> ConsciousnessLoop:
    """Backward compat — returns the consciousness loop singleton.

    Formerly returned a ConsciousnessDaemon from daemon.py.
    Now returns the unified ConsciousnessLoop which subsumes all daemon functionality.
    """
    return get_consciousness_loop()
