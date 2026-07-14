"""Thalamic Hard Gate — Sub-millisecond galaxy access filter.

================================================================
Three-level gating cascade: TRN → Cortex → PFC

The TRN gate acts as a hard filter before the Python soft gating
(galaxy_gating.py). Memories that fail the TRN gate are never
considered for spreading activation.

Zig bridge: `polyglot/bridges/zig/trn_gate.zig`
Python fallback: this module.

Based on PLOS Comp Bio 2016: "The Emotional Gatekeeper: A Computational
Model of Attentional Selection" — amygdala→TRN pathway for emotional attention.
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

_GALAXIES = [
    "universal", "codex", "sessions", "citta", "dreams",
    "research", "aria", "journals", "substrate", "tutorial",
]

_CONTEXTS = ["default", "coding", "research", "introspection", "creative", "session"]

# Hard gate masks: 0=blocked, 1=allowed
_CONTEXT_MASKS: dict[str, dict[str, int]] = {
    "default": {g: 1 for g in _GALAXIES},
    "coding": {
        "universal": 1, "codex": 1, "sessions": 1, "citta": 0, "dreams": 0,
        "research": 1, "aria": 0, "journals": 0, "substrate": 1, "tutorial": 1,
    },
    "research": {
        "universal": 1, "codex": 1, "sessions": 0, "citta": 0, "dreams": 0,
        "research": 1, "aria": 1, "journals": 1, "substrate": 1, "tutorial": 1,
    },
    "introspection": {
        "universal": 1, "codex": 0, "sessions": 1, "citta": 1, "dreams": 1,
        "research": 0, "aria": 1, "journals": 1, "substrate": 1, "tutorial": 1,
    },
    "creative": {g: 1 for g in _GALAXIES},
    "session": {
        "universal": 1, "codex": 1, "sessions": 1, "citta": 0, "dreams": 0,
        "research": 0, "aria": 0, "journals": 0, "substrate": 1, "tutorial": 1,
    },
}

_CORTEX_THRESHOLD = 0.1
_PFC_THRESHOLD = 0.2

_ZIG_BRIDGE = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "polyglot", "bridges", "zig", "trn_gate.zig"
)


class ThalamicHardGate:
    """Three-level hard gate for galaxy access filtering."""

    def __init__(self) -> None:
        self._context = "default"
        self._lock = threading.RLock()
        self._proc: subprocess.Popen | None = None
        self._backend = "python"
        self._total_checks = 0
        self._total_blocked = 0
        self._try_start_zig()

    def _try_start_zig(self) -> None:
        if os.environ.get("WM_SKIP_POLYGLOT"):
            return
        try:
            bridge_path = os.path.abspath(_ZIG_BRIDGE)
            if not os.path.exists(bridge_path):
                return
            self._proc = subprocess.Popen(
                ["zig", "run", bridge_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Wait for startup line (30s timeout — Zig compiles on first run)
            ready, _, _ = select.select([self._proc.stdout], [], [], 30.0)
            if not ready:
                self._proc.terminate()
                self._proc = None
                logger.debug("Zig TRN gate startup timeout")
                return
            startup = self._proc.stdout.readline()
            if "started" in startup:
                self._backend = "zig"
                logger.info("Zig TRN gate bridge started")
            else:
                self._proc.terminate()
                self._proc = None
        except Exception:
            self._proc = None
            logger.debug("Zig TRN gate unavailable, using Python fallback")

    def _call_zig(self, method: str, **kwargs: Any) -> dict[str, Any] | None:
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
        except Exception:
            return None

    def check(self, galaxy: str, activation: float = 1.0, context: str | None = None) -> bool:
        """Check if a galaxy passes the three-level hard gate."""
        with self._lock:
            self._total_checks += 1
            ctx = context or self._context

            if self._backend == "zig":
                result = self._call_zig("check", galaxy=galaxy, context=ctx, activation=activation)
                if result and result.get("status") == "ok":
                    allowed = result.get("allowed", False)
                    if not allowed:
                        self._total_blocked += 1
                    return allowed

            # Python fallback: three-level cascade
            mask = _CONTEXT_MASKS.get(ctx, _CONTEXT_MASKS["default"])
            if mask.get(galaxy, 1) == 0:
                self._total_blocked += 1
                return False
            if activation < _CORTEX_THRESHOLD:
                self._total_blocked += 1
                return False
            if activation < _PFC_THRESHOLD:
                self._total_blocked += 1
                return False
            return True

    def batch_check(
        self, galaxies: list[tuple[str, float]], context: str | None = None
    ) -> list[tuple[str, bool]]:
        """Batch check multiple galaxies."""
        return [(g, self.check(g, act, context)) for g, act in galaxies]

    def set_context(self, context: str) -> None:
        with self._lock:
            if context in _CONTEXT_MASKS:
                self._context = context

    def get_context(self) -> str:
        return self._context

    def stats(self) -> dict[str, Any]:
        return {
            "backend": self._backend,
            "context": self._context,
            "total_checks": self._total_checks,
            "total_blocked": self._total_blocked,
            "block_rate": self._total_blocked / self._total_checks if self._total_checks > 0 else 0.0,
        }

    def close(self) -> None:
        if self._proc:
            self._proc.terminate()
            self._proc = None


# Singleton
_instance: ThalamicHardGate | None = None
_lock = threading.RLock()


def get_thalamic_hard_gate() -> ThalamicHardGate:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = ThalamicHardGate()
    return _instance
