"""Wu Xing phase controller — 5-phase thread modulation for thermal management.

Cycles through Fire→Wood→Earth→Metal→Water phases, activating and
deactivating trigram thread groups to prevent thermal throttling on
the i5-8350U (15W TDP). Only 2 trigrams are active per phase, meaning
at most 2 cores are under load at any time.

The controller integrates with:
  - HexagramState: Phase transitions update the cognitive state machine
  - TrigramPool: is_active flags per trigram are toggled on phase changes
  - Gan Ying Bus: Phase transitions emit resonance events

Phase durations (configurable via env vars):
  Fire  (火):  60s — Active generation (Draft + Verify)
  Wood  (木):  30s — Input processing (Event + Route)
  Earth (土):  45s — Persistence + health (Memory + Heartbeat)
  Metal (金):  15s — Refinement (Output)
  Water (水): 120s — Background consolidation (Dream)

Total cycle: 270s (4.5 minutes)

Usage::

    from whitemagic.core.consciousness.wu_xing_controller import WuXingPhaseController
    from whitemagic.core.consciousness.hexagram_state import HexagramState

    state = HexagramState()
    controller = WuXingPhaseController(state)
    controller.start()

    # Check which trigrams should be active
    active = controller.get_active_trigrams()  # {"Qian", "Li"} during Fire

    controller.stop()
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from typing import Any

from whitemagic.core.consciousness.hexagram_state import HexagramState
from whitemagic.wu_xing import Element

logger = logging.getLogger(__name__)

# Phase → active trigrams mapping
PHASE_TRIGRAMS: dict[Element, set[str]] = {
    Element.FIRE: {"Qian", "Li"},
    Element.WOOD: {"Zhen", "Xun"},
    Element.EARTH: {"Kun", "Gen"},
    Element.METAL: {"Dui"},
    Element.WATER: {"Kan"},
}

# Phase → trigram for hexagram state transition
# Lower trigram = inner disposition, Upper trigram = outer action
PHASE_LOWER_TRIGRAM: dict[Element, str] = {
    Element.FIRE: "Li",     # Inner: illumination/clarity
    Element.WOOD: "Zhen",   # Inner: initiative/awakening
    Element.EARTH: "Kun",   # Inner: receptivity/grounding
    Element.METAL: "Dui",   # Inner: expression/joy
    Element.WATER: "Kan",   # Inner: depth/flow
}

PHASE_UPPER_TRIGRAM: dict[Element, str] = {
    Element.FIRE: "Qian",   # Outer: creative generation
    Element.WOOD: "Xun",    # Outer: gentle penetration/routing
    Element.EARTH: "Gen",   # Outer: stillness/heartbeat
    Element.METAL: "Dui",   # Outer: output/refinement
    Element.WATER: "Kan",   # Outer: dreaming/consolidation
}

# Phase cycle order (generating cycle: Wood→Fire→Earth→Metal→Water)
PHASE_CYCLE: list[Element] = [
    Element.FIRE,
    Element.WOOD,
    Element.EARTH,
    Element.METAL,
    Element.WATER,
]


def _get_phase_duration(element: Element) -> float:
    """Get phase duration from env var or default."""
    env_map = {
        Element.FIRE: "WM_WUXING_PHASE_FIRE",
        Element.WOOD: "WM_WUXING_PHASE_WOOD",
        Element.EARTH: "WM_WUXING_PHASE_EARTH",
        Element.METAL: "WM_WUXING_PHASE_METAL",
        Element.WATER: "WM_WUXING_PHASE_WATER",
    }
    defaults = {
        Element.FIRE: 60.0,
        Element.WOOD: 30.0,
        Element.EARTH: 45.0,
        Element.METAL: 15.0,
        Element.WATER: 120.0,
    }
    env_key = env_map.get(element, "")
    if env_key:
        try:
            return float(os.environ.get(env_key, defaults[element]))
        except (ValueError, TypeError):
            pass
    return defaults[element]


class WuXingPhaseController:
    """5-phase thread modulation controller for thermal management.

    Cycles through Wu Xing elements, activating/deactivating trigram
    thread groups. Integrates with HexagramState for state logging
    and emits callbacks on phase transitions.

    Attributes:
        current_phase: The currently active Wu Xing element.
    """

    def __init__(self, hexagram_state: HexagramState) -> None:
        self._hexagram = hexagram_state
        self._current_phase: Element = Element.FIRE
        self._phase_start: float = time.time()
        self._running: bool = False
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event = threading.Event()
        self._phase_count: int = 0
        self._on_phase_change: list[Callable[[Element, Element], None]] = []
        self._lock: threading.RLock = threading.RLock()
        self._creation_time: float = time.time()

    @property
    def current_phase(self) -> Element:
        """The currently active Wu Xing element."""
        return self._current_phase

    @property
    def phase_count(self) -> int:
        """Total number of completed phase transitions."""
        return self._phase_count

    def start(self) -> None:
        """Start the phase controller in a background daemon thread."""
        if self._running:
            logger.warning("Wu Xing phase controller already running")
            return

        self._running = True
        self._stop_event.clear()
        self._phase_start = time.time()

        # Set initial hexagram state
        self._apply_phase(self._current_phase, reason="phase controller start")

        self._thread = threading.Thread(
            target=self._run_loop,
            name="wuxing-phase-controller",
            daemon=True,
        )
        self._thread.start()
        from whitemagic.core.worker_registry import register_worker

        register_worker("wuxing_controller", self._thread, stop_fn=self.stop, owner=__name__)
        logger.info(
            "Wu Xing phase controller started (initial phase: %s)",
            self._current_phase.value,
        )

    def stop(self) -> None:
        """Stop the phase controller."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        from whitemagic.core.worker_registry import unregister_worker

        unregister_worker("wuxing_controller")
        logger.info("Wu Xing phase controller stopped (completed %d phases)", self._phase_count)

    def get_active_trigrams(self) -> set[str]:
        """Return the set of trigram names active in the current phase."""
        return PHASE_TRIGRAMS.get(self._current_phase, set())

    def is_trigram_active(self, trigram: str) -> bool:
        """Check if a specific trigram should be running.

        Args:
            trigram: Trigram name (e.g., "Qian", "Li").

        Returns:
            True if the trigram is active in the current phase.
        """
        return trigram in self.get_active_trigrams()

    def register_phase_callback(
        self, callback: Callable[[Element, Element], None]
    ) -> None:
        """Register a callback invoked on phase transitions.

        The callback receives (old_phase, new_phase) as arguments.
        Trigram threads use this to pause/resume their work loops.
        """
        with self._lock:
            self._on_phase_change.append(callback)

    def get_status(self) -> dict[str, Any]:
        """Return current phase controller status for monitoring."""
        elapsed = time.time() - self._phase_start
        duration = _get_phase_duration(self._current_phase)
        remaining = max(0.0, duration - elapsed)
        return {
            "current_phase": self._current_phase.value,
            "elapsed_seconds": round(elapsed, 1),
            "remaining_seconds": round(remaining, 1),
            "phase_duration": duration,
            "active_trigrams": list(self.get_active_trigrams()),
            "phase_count": self._phase_count,
            "uptime_seconds": round(time.time() - self._creation_time, 1),
            "running": self._running,
        }

    def _run_loop(self) -> None:
        """Main phase cycling loop (runs in background thread)."""
        while self._running and not self._stop_event.is_set():
            duration = _get_phase_duration(self._current_phase)

            # Wait for phase duration or stop signal
            if self._stop_event.wait(duration):
                break

            # Transition to next phase
            current_idx = PHASE_CYCLE.index(self._current_phase)
            next_idx = (current_idx + 1) % len(PHASE_CYCLE)
            old_phase = self._current_phase
            new_phase = PHASE_CYCLE[next_idx]

            self._apply_phase(new_phase, reason=f"wu xing cycle: {old_phase.value}→{new_phase.value}")

    def _apply_phase(self, new_phase: Element, reason: str = "") -> None:
        """Apply a phase transition: update hexagram state, invoke callbacks."""
        old_phase = self._current_phase

        with self._lock:
            self._current_phase = new_phase
            self._phase_start = time.time()
            self._phase_count += 1

        # Update hexagram state
        lower = PHASE_LOWER_TRIGRAM.get(new_phase, "Kun")
        upper = PHASE_UPPER_TRIGRAM.get(new_phase, "Gen")
        self._hexagram.transition(new_lower=lower, new_upper=upper, reason=reason)

        # Invoke callbacks
        for callback in self._on_phase_change:
            try:
                callback(old_phase, new_phase)
            except Exception as e:
                logger.warning("Phase callback error: %s", e, exc_info=True)

        logger.info(
            "Wu Xing phase: %s → %s (%s) — active trigrams: %s",
            old_phase.value,
            new_phase.value,
            reason,
            list(self.get_active_trigrams()),
        )

        # Emit to Gan Ying Bus if available
        try:
            from datetime import datetime

            from whitemagic.core.resonance.gan_ying import (
                EventType,
                ResonanceEvent,
                get_bus,
            )

            bus = get_bus()
            bus.emit(
                ResonanceEvent(
                    source="wu_xing_controller",
                    event_type=EventType.INTERNAL_STATE_CHANGED,
                    data={
                        "old_phase": old_phase.value,
                        "new_phase": new_phase.value,
                        "active_trigrams": list(self.get_active_trigrams()),
                        "reason": reason,
                    },
                    timestamp=datetime.now(),
                    confidence=0.9,
                )
            )
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────────

_instance: WuXingPhaseController | None = None
_instance_lock = threading.Lock()


def get_wu_xing_controller() -> WuXingPhaseController:
    """Get the singleton WuXingPhaseController instance.

    Uses the singleton HexagramState for state tracking.
    """
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                from whitemagic.core.consciousness.hexagram_state import (
                    get_hexagram_state,
                )

                _instance = WuXingPhaseController(get_hexagram_state())
    return _instance
