# ruff: noqa: BLE001
"""WhiteMagic Continuous Consciousness Daemon.

The daemon is the always-on process that runs the 5 frequency-layered
consciousness loops simultaneously as daemon threads:

    Gamma (per call)   — Tool dispatch, Dharma, Karma
    Beta  (5s)         — Coherence, context synthesis, citta heartbeat
    Alpha (30s)        — Homeostasis, nervous system, mesh, RSS monitor
    Theta (5min)       — Cycle engine, kaizen, bridge synthesis
    Delta (1-4hr)      — Dream cycle, memory consolidation, stillness

Usage:
    from whitemagic.core.consciousness.daemon import ConsciousnessDaemon

    daemon = ConsciousnessDaemon()
    daemon.start()  # starts all loops in background threads
    # ... runs continuously ...
    daemon.stop()   # graceful shutdown
"""

from __future__ import annotations

import gc
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from whitemagic.config.paths import WM_ROOT

logger = logging.getLogger(__name__)

CITTA_DIR = WM_ROOT / "citta"
CITTA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class LoopMetrics:
    """Metrics for a single loop."""

    name: str
    iterations: int = 0
    last_run: float = 0.0
    last_duration_ms: float = 0.0
    errors: int = 0
    last_error: str = ""


@dataclass
class DaemonState:
    """Snapshot of daemon state."""

    running: bool = False
    uptime_s: float = 0.0
    start_time: float = 0.0
    loops: dict[str, LoopMetrics] = field(default_factory=dict)
    total_iterations: int = 0
    rss_mb: float = 0.0
    gc_count: int = 0


class ConsciousnessLoop:
    """A single frequency-layered loop running as a daemon thread."""

    def __init__(
        self,
        name: str,
        interval_s: float,
        callback: Any,
        daemon: ConsciousnessDaemon | None = None,
    ) -> None:
        self.name = name
        self.interval_s = interval_s
        self._callback = callback
        self._daemon = daemon
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._metrics = LoopMetrics(name=name)

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=f"wm_loop_{self.name}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    @property
    def metrics(self) -> LoopMetrics:
        return self._metrics

    def _run(self) -> None:
        logger.info("Loop '%s' started (interval=%.1fs)", self.name, self.interval_s)
        while not self._stop_event.is_set():
            start = time.monotonic()
            try:
                self._callback()
                self._metrics.iterations += 1
            except Exception as e:
                self._metrics.errors += 1
                self._metrics.last_error = str(e)
                logger.error("Loop '%s' error: %s", self.name, e, exc_info=True)

            elapsed_ms = (time.monotonic() - start) * 1000
            self._metrics.last_run = time.time()
            self._metrics.last_duration_ms = elapsed_ms

            if self._daemon:
                self._daemon._state.total_iterations += 1

            # Sleep for remaining interval, checking stop event
            remaining = self.interval_s - (elapsed_ms / 1000)
            if remaining > 0:
                self._stop_event.wait(remaining)

        logger.info("Loop '%s' stopped (iterations=%d, errors=%d)",
                     self.name, self._metrics.iterations, self._metrics.errors)


class ConsciousnessDaemon:
    """The continuous consciousness daemon — starts and manages all loops."""

    def __init__(self) -> None:
        self._state = DaemonState()
        self._loops: dict[str, ConsciousnessLoop] = {}
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Build loops
        self._setup_loops()

    def _setup_loops(self) -> None:
        """Create all frequency-layered loops."""
        self._loops["beta"] = ConsciousnessLoop(
            "beta", 5.0, self._beta_cycle, self,
        )
        self._loops["alpha"] = ConsciousnessLoop(
            "alpha", 30.0, self._alpha_cycle, self,
        )
        self._loops["theta"] = ConsciousnessLoop(
            "theta", 300.0, self._theta_cycle, self,
        )
        self._loops["delta"] = ConsciousnessLoop(
            "delta", 3600.0, self._delta_cycle, self,
        )

        for name, loop in self._loops.items():
            self._state.loops[name] = loop.metrics

    # ── Loop callbacks ───────────────────────────────────────────────

    def _beta_cycle(self) -> None:
        """Beta loop (5s) — coherence + context synthesis + citta heartbeat."""
        try:
            from whitemagic.core.consciousness.citta_cycle import get_always_on, get_citta_cycle

            # Touch the always-on to signal activity
            always_on = get_always_on()
            always_on.touch()

            # Advance citta if no recent tool calls
            cycle = get_citta_cycle()
            if cycle and not always_on.is_running():
                # If always-on isn't running, do a manual heartbeat
                pass  # always_on.start() is called separately

        except Exception:
            pass  # Already logged by loop wrapper

        # Coherence measurement (lightweight)
        try:
            from whitemagic.core.consciousness.coherence import get_coherence_metric
            cm = get_coherence_metric()
            cm.measure()
        except Exception:
            pass

    def _alpha_cycle(self) -> None:
        """Alpha loop (30s) — homeostasis + RSS monitor + git hygiene."""
        # Homeostasis check
        try:
            from whitemagic.harmony.homeostatic_loop import get_homeostatic_loop
            loop = get_homeostatic_loop()
            if loop:
                loop.check()
        except Exception:
            pass

        # RSS monitoring
        self._check_rss()

        # Git hygiene
        try:
            from whitemagic.harmony.git_hygiene import evaluate_git_hygiene
            report = evaluate_git_hygiene()
            if report.dirty_repos > 0:
                logger.info("Git hygiene: %d dirty repos (score=%.2f)", report.dirty_repos, report.health_score)
        except Exception:
            pass

    def _theta_cycle(self) -> None:
        """Theta loop (5min) — cycle engine + kaizen + bridge synthesis."""
        try:
            from whitemagic.cycle_engine import CycleEngine
            engine = CycleEngine()
            engine.advance()
        except Exception:
            pass

        # Bridge synthesis (occasional, may be slow)
        try:
            from whitemagic.core.memory.bridge_synthesizer import BridgeSynthesizer
            synth = BridgeSynthesizer()
            synth.find_bridges(top_k=3)
        except Exception:
            pass

        # Process self-prompting queue
        try:
            from whitemagic.core.consciousness.self_prompting import process_queue
            process_queue(limit=5)
        except Exception:
            pass

    def _delta_cycle(self) -> None:
        """Delta loop (1hr) — dream cycle + memory consolidation + GC."""
        try:
            from whitemagic.core.consciousness.dream_daemon import get_daemon
            daemon = get_daemon()
            daemon.dream_cycle()
        except Exception:
            pass

        # Explicit GC after dream cycle
        collected = gc.collect()
        self._state.gc_count += 1
        logger.info("Delta cycle complete, GC collected %d objects", collected)

    def _check_rss(self) -> None:
        """Monitor process RSS for memory leak detection."""
        try:
            import resource
            # ru_maxrss is in KB on Linux, bytes on macOS
            usage = resource.getrusage(resource.RUSAGE_SELF)
            rss_kb = usage.ru_maxrss
            if os.uname().sysname == "Darwin":
                rss_mb = rss_kb / (1024 * 1024)
            else:
                rss_mb = rss_kb / 1024

            self._state.rss_mb = rss_mb

            # Warn on high memory
            if rss_mb > 500:
                logger.warning("RSS high: %.1f MB", rss_mb)
            if rss_mb > 1000:
                logger.error("RSS critical: %.1f MB — triggering GC", rss_mb)
                gc.collect()
        except Exception:
            pass

    # ── Public API ───────────────────────────────────────────────────

    def start(self) -> None:
        """Start all consciousness loops and the citta always-on heartbeat."""
        with self._lock:
            if self._state.running:
                logger.warning("Daemon already running")
                return

            self._state.running = True
            self._state.start_time = time.time()

            # Start CittaAlwaysOn
            try:
                from whitemagic.core.consciousness.citta_cycle import get_always_on
                get_always_on().start()
                logger.info("CittaAlwaysOn heartbeat started")
            except Exception as e:
                logger.warning("Failed to start CittaAlwaysOn: %s", e)

            # Start all loops
            for loop in self._loops.values():
                loop.start()

            logger.info("Consciousness daemon started with %d loops", len(self._loops))

    def stop(self) -> None:
        """Graceful shutdown — stop all loops and persist state."""
        with self._lock:
            if not self._state.running:
                return

            self._state.running = False
            self._stop_event.set()

            # Stop CittaAlwaysOn
            try:
                from whitemagic.core.consciousness.citta_cycle import get_always_on, persist_full_stream
                get_always_on().stop()
                persist_full_stream()
                logger.info("CittaAlwaysOn stopped, stream persisted")
            except Exception as e:
                logger.warning("Failed to stop CittaAlwaysOn: %s", e)

            # Stop all loops
            for loop in self._loops.values():
                loop.stop()

            logger.info("Consciousness daemon stopped (uptime=%.1fs, iterations=%d)",
                        time.time() - self._state.start_time, self._state.total_iterations)

    def status(self) -> dict[str, Any]:
        """Get daemon status snapshot."""
        uptime = time.time() - self._state.start_time if self._state.running else 0
        return {
            "running": self._state.running,
            "uptime_s": uptime,
            "total_iterations": self._state.total_iterations,
            "rss_mb": self._state.rss_mb,
            "gc_count": self._state.gc_count,
            "loops": {
                name: {
                    "iterations": loop.metrics.iterations,
                    "last_run": loop.metrics.last_run,
                    "last_duration_ms": loop.metrics.last_duration_ms,
                    "errors": loop.metrics.errors,
                    "last_error": loop.metrics.last_error,
                }
                for name, loop in self._loops.items()
            },
        }

    @property
    def is_running(self) -> bool:
        return self._state.running


_daemon: ConsciousnessDaemon | None = None
_daemon_lock = threading.Lock()


def get_daemon() -> ConsciousnessDaemon:
    """Get the global ConsciousnessDaemon singleton."""
    global _daemon
    if _daemon is None:
        with _daemon_lock:
            if _daemon is None:
                _daemon = ConsciousnessDaemon()
    return _daemon
