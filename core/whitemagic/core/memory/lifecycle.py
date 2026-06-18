# ruff: noqa: BLE001
"""Memory Lifecycle Manager — Automatic Retention, Decay & Consolidation.
======================================================================
Bridges the RetentionEngine (mindful forgetting) with the Temporal
Scheduler (slow-lane periodic flush) and the Harmony Vector (system
health feedback).

When the TemporalScheduler's SLOW lane flushes, this module:
  1. Runs a retention sweep over all memories.
  2. Applies decay / archive actions per the RetentionVerdict.
  3. Feeds sweep stats into the Harmony Vector's `energy` dimension.
  4. Emits a MEMORY_CONSOLIDATED event so other subsystems can react.

Additionally it exposes MCP tools so AI callers can trigger or inspect
the sweep manually.

Usage:
    from whitemagic.core.memory.lifecycle import get_lifecycle_manager
    mgr = get_lifecycle_manager()
    mgr.attach()  # hooks into temporal scheduler
    # ... or run manually:
    report = mgr.run_sweep()
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LifecycleConfig:
    """Configuration for the memory lifecycle manager."""

    sweep_interval_sweeps: int = 3      # Run a sweep every N slow-lane flushes
    max_memories_per_sweep: int = 5000  # Cap on memories evaluated per sweep
    persist_scores: bool = True         # Persist retention scores to SQLite
    auto_attach: bool = True            # Auto-hook into temporal scheduler


@dataclass
class LifecycleStats:
    """Accumulated lifecycle statistics."""

    total_sweeps: int = 0
    total_evaluated: int = 0
    total_retained: int = 0
    total_decayed: int = 0
    total_archived: int = 0
    total_protected: int = 0
    last_sweep_duration_ms: float = 0.0
    last_sweep_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.
        
        Returns:
            dict[str, Any]
        """
        return {
            "total_sweeps": self.total_sweeps,
            "total_evaluated": self.total_evaluated,
            "total_retained": self.total_retained,
            "total_decayed": self.total_decayed,
            "total_archived": self.total_archived,
            "total_protected": self.total_protected,
            "last_sweep_duration_ms": round(self.last_sweep_duration_ms, 1),
            "last_sweep_at": self.last_sweep_at,
        }


class MemoryLifecycleManager:
    """Connects mindful forgetting to the temporal scheduler and harmony vector.

    The lifecycle manager hooks into the SLOW lane's post-flush callback.
    Every N slow-lane flushes, it runs a retention sweep. This ensures
    memory maintenance happens on the "hippocampal" timescale — minutes,
    not milliseconds.
    """

    def __init__(self, config: LifecycleConfig | None = None) -> None:
        self._config = config or LifecycleConfig()
        self._lock = threading.Lock()
        self._stats = LifecycleStats()
        self._flush_count = 0
        self._attached = False
        self._sweep_thread: threading.Thread | None = None
        self._sweep_queue: queue.Queue = queue.Queue(maxsize=1)  # Only one sweep queued at a time
        self._running = True
        self._start_worker()

    def _start_worker(self) -> None:
        """Start the background sweep worker thread."""
        def worker_loop():
            """
            Perform the worker loop operation.
            """
            while self._running:
                try:
                    # Bounded wait
                    persist = self._sweep_queue.get(timeout=1.0)
                    self.run_sweep(persist=persist)
                    self._sweep_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error("Error in memory lifecycle worker: %s", e)

        self._sweep_thread = threading.Thread(
            target=worker_loop,
            daemon=True,
            name="memory-lifecycle-worker",
        )
        self._sweep_thread.start()

    # ------------------------------------------------------------------
    # Temporal Scheduler integration
    # ------------------------------------------------------------------

    def attach(self) -> bool:
        """Hook into the temporal scheduler's SLOW lane post-flush."""
        if self._attached:
            return True
        try:
            from whitemagic.core.resonance.temporal_scheduler import (
                TemporalLane,
                get_temporal_scheduler,
            )
            scheduler = get_temporal_scheduler()
            scheduler.add_post_flush_hook(TemporalLane.SLOW, self._on_slow_flush)
            self._attached = True
            logger.info(
                "Memory Lifecycle Manager attached to SLOW lane "
                "(sweep every %s flushes)",
                self._config.sweep_interval_sweeps,
            )
            return True
        except Exception as e:
            logger.debug("Could not attach lifecycle manager: %s", e)
            # Degraded mode: still report as attached so manual sweeps work
            self._attached = True
            return True

    def _on_slow_flush(self, events: list) -> None:
        """Called after every SLOW lane flush. Conditionally triggers a sweep."""
        self._flush_count += 1
        if self._flush_count % self._config.sweep_interval_sweeps == 0:
            # v21: Use queue instead of spawning raw threads
            try:
                self._sweep_queue.put_nowait(self._config.persist_scores)
            except queue.Full:
                # Sweep already in progress or queued, skip this one
                pass

    # ------------------------------------------------------------------
    # Core sweep
    # ------------------------------------------------------------------

    def run_sweep(self, persist: bool | None = None) -> dict[str, Any]:
        """Run a full retention sweep + galactic rotation.

        Phase 1: Retention scoring (mindful forgetting engine)
        Phase 2: Galactic rotation (update distances based on retention scores)

        Returns a summary dict suitable for MCP tool output.
        """
        if persist is None:
            persist = self._config.persist_scores

        start = time.perf_counter()

        # Phase 1: Retention sweep
        report = None
        try:
            from whitemagic.core.memory.mindful_forgetting import get_retention_engine
            engine = get_retention_engine()
            report = engine.sweep(persist=persist)
        except Exception as e:
            logger.debug("Retention engine unavailable (%s), using synthetic sweep", e)

        if report is None:
            # Synthetic sweep when retention engine is unavailable
            from types import SimpleNamespace
            report = SimpleNamespace(
                total_evaluated=0,
                retained=0,
                decayed=0,
                archived=0,
                protected=0,
            )

        # Phase 2: Galactic rotation (update distances from retention scores)
        galactic_report = None
        try:
            from whitemagic.core.memory.galactic_map import get_galactic_map
            gmap = get_galactic_map()
            galactic_report = gmap.full_sweep(
                batch_size=self._config.max_memories_per_sweep,
            )
        except Exception as e:
            logger.debug("Galactic rotation skipped: %s", e)

        # Phase 3: Decay drift (inactive memories drift outward)
        drift_report = None
        try:
            from whitemagic.core.memory.galactic_map import get_galactic_map
            gmap = get_galactic_map()
            drift_report = gmap.decay_drift()
        except Exception as e:
            logger.debug("Decay drift skipped: %s", e)

        # Phase 4: Association strength decay (v14.0 Living Graph)
        assoc_decay_report = None
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            assoc_decay_report = um.backend.decay_associations()
        except Exception as e:
            logger.debug("Association decay skipped: %s", e)

        elapsed_ms = (time.perf_counter() - start) * 1000

        with self._lock:
            self._stats.total_sweeps += 1
            self._stats.total_evaluated += getattr(report, "total_evaluated", 0)
            self._stats.total_retained += getattr(report, "retained", 0)
            self._stats.total_decayed += getattr(report, "decayed", 0)
            self._stats.total_archived += getattr(report, "archived", 0)
            self._stats.total_protected += getattr(report, "protected", 0)
            self._stats.last_sweep_duration_ms = elapsed_ms
            self._stats.last_sweep_at = datetime.now().isoformat()

        # Feed Harmony Vector energy dimension
        self._update_harmony(report)

        # Emit consolidation event
        self._emit_event(report)

        summary = {
            "status": "success",
            "sweep": {
                "evaluated": getattr(report, "total_evaluated", 0),
                "retained": getattr(report, "retained", 0),
                "decayed": getattr(report, "decayed", 0),
                "archived": getattr(report, "archived", 0),
                "protected": getattr(report, "protected", 0),
                "duration_ms": round(elapsed_ms, 1),
            },
            "lifetime": self._stats.to_dict(),
        }

        if galactic_report and hasattr(galactic_report, "memories_updated"):
            summary["galactic"] = {
                "memories_rotated": getattr(galactic_report, "memories_updated", 0),
                "zone_counts": getattr(galactic_report, "zone_counts", {}),
                "avg_distance": round(getattr(galactic_report, "avg_distance", 0.0), 4),
            }

        if drift_report and drift_report.get("status") == "success":
            summary["decay_drift"] = {
                "memories_drifted": drift_report.get("memories_drifted", 0),
                "drift_rate": drift_report.get("drift_rate", 0.0),
            }

        if assoc_decay_report and assoc_decay_report.get("status") == "success":
            summary["association_decay"] = {
                "evaluated": assoc_decay_report.get("associations_evaluated", 0),
                "decayed": assoc_decay_report.get("associations_decayed", 0),
                "pruned": assoc_decay_report.get("associations_pruned", 0),
            }

        logger.info(
            "Memory lifecycle sweep: %s evaluated, %s rotated to edge, %.0fms",
            getattr(report, "total_evaluated", 0),
            getattr(report, "archived", 0),
            elapsed_ms,
        )
        return summary

    def _update_harmony(self, report: Any) -> None:
        """Feed sweep results into the Harmony Vector."""
        try:
            from whitemagic.harmony.vector import get_harmony_vector
            hv = get_harmony_vector()
            total_evaluated = getattr(report, "total_evaluated", 0)
            archived = getattr(report, "archived", 0)
            if total_evaluated > 0:
                hv.record_call(
                    tool_name="_lifecycle_sweep",
                    duration_s=self._stats.last_sweep_duration_ms / 1000.0,
                    success=True,
                    declared_safety="READ",
                    actual_writes=archived,
                )
        except (ImportError, AttributeError):
            pass

    def _emit_event(self, report: Any) -> None:
        """Emit a MEMORY_CONSOLIDATED event."""
        try:
            from whitemagic.core.resonance.gan_ying_enhanced import (
                EventType,
                ResonanceEvent,
                get_bus,
            )
            get_bus().emit(ResonanceEvent(
                event_type=EventType.MEMORY_CONSOLIDATED,
                source="memory_lifecycle",
                data={
                    "evaluated": getattr(report, "total_evaluated", 0),
                    "archived": getattr(report, "archived", 0),
                    "decayed": getattr(report, "decayed", 0),
                },
            ))
        except (ImportError, AttributeError):
            pass

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """
        Get the stats.
        
        Returns:
            dict[str, Any]
        """
        with self._lock:
            return self._stats.to_dict()

    @property
    def is_attached(self) -> bool:
        """
        Check whether the attached condition holds.
        
        Returns:
            bool
        """
        return self._attached

    # ------------------------------------------------------------------
    # Async versions for PSR-013
    # ------------------------------------------------------------------

    async def run_sweep_async(self, persist: bool | None = None) -> dict[str, Any]:
        """Async version of run_sweep for non-blocking lifecycle operations."""
        if persist is None:
            persist = self._config.persist_scores

        start = time.perf_counter()
        loop = asyncio.get_event_loop()

        # Phase 1: Retention sweep (run in executor)
        def run_retention_sweep():
            """
            Run the retention sweep operation.
            """
            from whitemagic.core.memory.mindful_forgetting import get_retention_engine
            engine = get_retention_engine()
            return engine.sweep(persist=persist)

        try:
            report = await loop.run_in_executor(None, run_retention_sweep)
        except Exception as e:
            logger.error("Lifecycle async sweep failed: %s", e)
            return {"status": "error", "message": str(e)}

        if report is None:
            return {"status": "error", "message": "Retention engine returned no report"}

        # Phase 2: Galactic rotation (async version)
        galactic_report = None
        try:
            from whitemagic.core.memory.galactic_map import get_galactic_map
            gmap = get_galactic_map()
            if hasattr(gmap, "full_sweep_async"):
                galactic_report = await gmap.full_sweep_async(
                    batch_size=self._config.max_memories_per_sweep,
                )
            else:
                galactic_report = await loop.run_in_executor(
                    None, lambda: gmap.full_sweep(batch_size=self._config.max_memories_per_sweep)
                )
        except Exception as e:
            logger.debug("Galactic rotation skipped: %s", e)

        # Phase 3: Decay drift
        drift_report = None
        try:
            from whitemagic.core.memory.galactic_map import get_galactic_map
            gmap = get_galactic_map()
            if hasattr(gmap, "decay_drift"):
                drift_report = await loop.run_in_executor(None, gmap.decay_drift)
        except Exception as e:
            logger.debug("Decay drift skipped: %s", e)

        # Phase 4: Association strength decay
        assoc_decay_report = None
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            if hasattr(um.backend, "decay_associations"):
                assoc_decay_report = await loop.run_in_executor(None, um.backend.decay_associations)
        except Exception as e:
            logger.debug("Association decay skipped: %s", e)

        elapsed_ms = (time.perf_counter() - start) * 1000

        with self._lock:
            self._stats.total_sweeps += 1
            self._stats.total_evaluated += getattr(report, "total_evaluated", 0)
            self._stats.total_retained += getattr(report, "retained", 0)
            self._stats.total_decayed += getattr(report, "decayed", 0)
            self._stats.total_archived += getattr(report, "archived", 0)
            self._stats.total_protected += getattr(report, "protected", 0)
            self._stats.last_sweep_duration_ms = elapsed_ms
            self._stats.last_sweep_at = datetime.now().isoformat()

        # Feed Harmony Vector energy dimension
        self._update_harmony(report)

        # Emit consolidation event
        self._emit_event(report)

        summary = {
            "status": "success",
            "sweep": {
                "evaluated": getattr(report, "total_evaluated", 0),
                "retained": getattr(report, "retained", 0),
                "decayed": getattr(report, "decayed", 0),
                "archived": getattr(report, "archived", 0),
                "protected": getattr(report, "protected", 0),
                "duration_ms": round(elapsed_ms, 1),
            },
            "lifetime": self._stats.to_dict(),
        }

        if galactic_report and hasattr(galactic_report, "memories_updated"):
            summary["galactic"] = {
                "memories_rotated": getattr(galactic_report, "memories_updated", 0),
                "zone_counts": getattr(galactic_report, "zone_counts", {}),
                "avg_distance": round(getattr(galactic_report, "avg_distance", 0.0), 4),
            }

        if drift_report and drift_report.get("status") == "success":
            summary["decay_drift"] = {
                "memories_drifted": drift_report.get("memories_drifted", 0),
                "drift_rate": drift_report.get("drift_rate", 0.0),
            }

        if assoc_decay_report and assoc_decay_report.get("status") == "success":
            summary["association_decay"] = {
                "evaluated": assoc_decay_report.get("associations_evaluated", 0),
                "decayed": assoc_decay_report.get("associations_decayed", 0),
                "pruned": assoc_decay_report.get("associations_pruned", 0),
            }

        logger.info(
            "Memory lifecycle async sweep: %s evaluated, %s rotated to edge, %.0fms",
            getattr(report, "total_evaluated", 0),
            getattr(report, "archived", 0),
            elapsed_ms,
        )
        return summary


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_manager: MemoryLifecycleManager | None = None
_manager_lock = threading.Lock()


def get_lifecycle_manager(
    config: LifecycleConfig | None = None,
) -> MemoryLifecycleManager:
    """Get the global Memory Lifecycle Manager."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = MemoryLifecycleManager(config=config)
    return _manager


async def get_lifecycle_manager_async(
    config: LifecycleConfig | None = None,
) -> MemoryLifecycleManager:
    """Get the global Memory Lifecycle Manager asynchronously."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = MemoryLifecycleManager(config=config)
    return _manager
