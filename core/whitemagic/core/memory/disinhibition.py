"""Disinhibition Model — Sleep/Wake State-Dependent Gating.

================================================================
Implements a state machine: Wake → LightSleep → DeepSleep → REM
Each state modulates galaxy gating weights differently, enabling
sleep consolidation to operate with reduced cognitive access while
boosting creative associations during REM.

Based on PLOS Comp Bio 2025: "Sleep-modulated disinhibition enables
replay for memory consolidation."

Koka bridge: `polyglot/bridges/koka/disinhibition.kk`
Python fallback: this module.
"""

from __future__ import annotations

import json
import logging
import os
import select
import subprocess
import threading
from typing import Any

logger = logging.getLogger(__name__)

# State constants
WAKE = 0
LIGHT_SLEEP = 1
DEEP_SLEEP = 2
REM = 3

_STATE_NAMES = {WAKE: "Wake", LIGHT_SLEEP: "LightSleep", DEEP_SLEEP: "DeepSleep", REM: "REM"}

# Galaxy gating weights per state
_STATE_WEIGHTS: dict[int, dict[str, float]] = {
    WAKE: {
        "universal": 1.0, "codex": 1.0, "sessions": 1.0, "citta": 1.0,
        "dreams": 1.0, "research": 1.0, "aria": 1.0, "journals": 1.0,
        "substrate": 1.0, "tutorial": 1.0,
    },
    LIGHT_SLEEP: {
        "universal": 0.7, "codex": 0.8, "sessions": 0.3, "citta": 0.4,
        "dreams": 0.6, "research": 0.5, "aria": 0.6, "journals": 0.4,
        "substrate": 0.5, "tutorial": 0.3,
    },
    DEEP_SLEEP: {
        "universal": 0.3, "codex": 0.6, "sessions": 0.1, "citta": 0.2,
        "dreams": 0.3, "research": 0.4, "aria": 0.3, "journals": 0.2,
        "substrate": 0.3, "tutorial": 0.1,
    },
    REM: {
        "universal": 0.6, "codex": 0.3, "sessions": 0.2, "citta": 0.8,
        "dreams": 1.5, "research": 0.5, "aria": 1.3, "journals": 0.7,
        "substrate": 0.4, "tutorial": 0.3,
    },
}

_DISINHIBITION_LEVELS = {WAKE: 1.0, LIGHT_SLEEP: 0.5, DEEP_SLEEP: 0.2, REM: 0.7}

_TRANSITIONS = {WAKE: LIGHT_SLEEP, LIGHT_SLEEP: DEEP_SLEEP, DEEP_SLEEP: REM, REM: WAKE}

_KOKA_BRIDGE = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "polyglot", "bridges", "koka", "disinhibition.kk"
)


class DisinhibitionModel:
    """Sleep/wake state machine with galaxy gating modulation."""

    def __init__(self) -> None:
        self._state = WAKE
        self._lock = threading.RLock()
        self._proc: subprocess.Popen | None = None
        self._backend = "python"
        self._total_transitions = 0
        self._try_start_koka()

    def _try_start_koka(self) -> None:
        """Try to start the Koka subprocess bridge."""
        if os.environ.get("WM_SKIP_POLYGLOT"):
            return
        try:
            bridge_path = os.path.abspath(_KOKA_BRIDGE)
            if not os.path.exists(bridge_path):
                return
            self._proc = subprocess.Popen(
                ["koka", "-e", "-v0", bridge_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Read startup line (30s timeout — Koka compiles on first run)
            ready, _, _ = select.select([self._proc.stdout], [], [], 30.0)
            if not ready:
                self._proc.terminate()
                self._proc = None
                logger.debug("Koka disinhibition startup timeout")
                return
            startup = self._proc.stdout.readline()
            if "started" in startup:
                self._backend = "koka"
                logger.info("Koka disinhibition bridge started")
            else:
                self._proc.terminate()
                self._proc = None
        except Exception:  # noqa: BLE001
            self._proc = None
            logger.debug("Koka disinhibition bridge unavailable, using Python fallback")

    def _call_koka(self, method: str, **kwargs: Any) -> dict[str, Any] | None:
        """Send a request to the Koka bridge."""
        if not self._proc or self._proc.poll() is not None:
            return None
        try:
            request = json.dumps({"method": method, **kwargs})
            self._proc.stdin.write(request + "\n")
            self._proc.stdin.flush()
            ready, _, _ = select.select([self._proc.stdout], [], [], 5.0)
            if not ready:
                return None
            response = self._proc.stdout.readline()
            return json.loads(response)
        except Exception:  # noqa: BLE001
            return None

    def get_state(self) -> dict[str, Any]:
        """Get current state info."""
        with self._lock:
            if self._backend == "koka":
                result = self._call_koka("get_state")
                if result and result.get("status") == "ok":
                    return result
            return self._python_get_state()

    def _python_get_state(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "state": _STATE_NAMES[self._state],
            "state_code": self._state,
            "disinhibition_level": _DISINHIBITION_LEVELS[self._state],
            "weights": _STATE_WEIGHTS[self._state].copy(),
        }

    def transition(self) -> dict[str, Any]:
        """Transition to the next state."""
        with self._lock:
            self._total_transitions += 1
            self._state = _TRANSITIONS.get(self._state, WAKE)
            if self._backend == "koka":
                result = self._call_koka("transition")
                if result and result.get("status") == "ok":
                    return result
            return self._python_get_state()

    def set_state(self, state: int) -> dict[str, Any]:
        """Set the state directly."""
        with self._lock:
            if state not in _STATE_NAMES:
                return {"status": "error", "error": f"Invalid state: {state}"}
            self._state = state
            if self._backend == "koka":
                result = self._call_koka("set_state", state=state)
                if result and result.get("status") == "ok":
                    return result
            return self._python_get_state()

    def get_weights(self) -> dict[str, float]:
        """Get galaxy gating weights for the current state."""
        with self._lock:
            if self._backend == "koka":
                result = self._call_koka("get_weights")
                if result and result.get("status") == "ok":
                    return result.get("weights", {})
            return _STATE_WEIGHTS[self._state].copy()

    def stats(self) -> dict[str, Any]:
        return {
            "state": _STATE_NAMES[self._state],
            "state_code": self._state,
            "backend": self._backend,
            "total_transitions": self._total_transitions,
        }

    def close(self) -> None:
        if self._proc:
            self._proc.terminate()
            self._proc = None


# Singleton
_instance: DisinhibitionModel | None = None
_lock = threading.RLock()


def get_disinhibition() -> DisinhibitionModel:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = DisinhibitionModel()
    return _instance
