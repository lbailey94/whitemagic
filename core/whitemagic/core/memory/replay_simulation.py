# ruff: noqa: BLE001
"""Replay Simulation — Memory sequence replay with STDP via Haskell bridge.

Traverses memory sequences during the dream cycle, applies spike-timing-
dependent plasticity (STDP) to strengthen sequential associations, and
detects replay trajectories. Based on research showing replay overrepresents
reward-associated locations and STDP controls replay duration (bioRxiv, Jan 2026).

The Haskell bridge runs as a subprocess with JSON stdio protocol. If the
Haskell runtime is unavailable or WM_SKIP_POLYGLOT is set, falls back to
a pure-Python implementation.
"""

from __future__ import annotations

import json
import logging
import math
import os
import select
import subprocess
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_SKIP_POLYGLOT = os.environ.get("WM_SKIP_POLYGLOT", "0") == "1"

_BRIDGE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..",
    "polyglot", "bridges", "haskell", "replay_sim.hs",
)
_BRIDGE_PATH = os.path.normpath(_BRIDGE_PATH)

_STDP_WINDOW = 20.0  # ms
_STDP_LTP = 1.0      # long-term potentiation amplitude
_STDP_LTD = -0.5     # long-term depression amplitude


class _HaskellBridge:
    """Manages a persistent Haskell subprocess for replay simulation."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._available = False

    def _ensure(self) -> bool:
        if _SKIP_POLYGLOT:
            return False
        if self._proc and self._proc.poll() is None:
            return True
        try:
            self._proc = subprocess.Popen(
                ["runhaskell", _BRIDGE_PATH],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            time.sleep(1.0)  # Haskell takes longer to start
            if self._proc.poll() is None:
                self._available = True
                return True
            self._available = False
            return False
        except Exception as e:
            logger.debug("Haskell replay bridge unavailable: %s", e, exc_info=True)
            self._available = False
            return False

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            if not self._ensure():
                return {"status": "fallback", "reason": "haskell_unavailable"}
            req = json.dumps({"method": method, "params": params or {}})
            try:
                self._proc.stdin.write(req + "\n")
                self._proc.stdin.flush()
                # Wait up to 5s for response — prevents infinite hang
                ready, _, _ = select.select([self._proc.stdout], [], [], 5.0)
                if not ready:
                    self._available = False
                    return {"status": "fallback", "reason": "timeout"}
                line = self._proc.stdout.readline()
                if not line:
                    self._available = False
                    return {"status": "fallback", "reason": "no_response"}
                return json.loads(line)
            except Exception as e:
                logger.debug("Haskell bridge call failed: %s", e, exc_info=True)
                self._available = False
                return {"status": "fallback", "reason": str(e)}


# ── Pure Python fallback ──────────────────────────────────────────────────


class _PyReplayEngine:
    """Pure-Python fallback replay engine with STDP."""

    def __init__(self):
        self._stats = {"total_replays": 0, "total_sequences": 0, "avg_strength": 0.0, "trajectories_detected": 0}

    def replay(self, sequence: list[dict[str, Any]]) -> dict[str, Any]:
        if not sequence:
            return {"replayed": [], "trajectories": [], "trajectory_count": 0, "avg_strength": 0.0, "total_items": 0}

        replayed = []
        for i, item in enumerate(sequence):
            mid = item.get("memory_id", "")
            ts = item.get("timestamp", 0.0)
            imp = item.get("importance", 0.5)
            gal = item.get("galaxy", "universal")

            prev_stdp = 0.0
            if i > 0:
                prev_ts = sequence[i - 1].get("timestamp", 0.0)
                dt = ts - prev_ts
                if 0 < dt < _STDP_WINDOW:
                    prev_stdp = _STDP_LTP * math.exp(-dt / _STDP_WINDOW)

            next_stdp = 0.0
            if i < len(sequence) - 1:
                next_ts = sequence[i + 1].get("timestamp", 0.0)
                dt = next_ts - ts
                if 0 < dt < _STDP_WINDOW:
                    next_stdp = _STDP_LTP * math.exp(-dt / _STDP_WINDOW)

            strength = max(0.0, imp + prev_stdp + next_stdp)
            replayed.append({
                "memory_id": mid,
                "timestamp": ts,
                "importance": imp,
                "galaxy": gal,
                "replay_strength": strength,
            })

        trajectories = self._detect_trajectories(replayed)
        avg_strength = sum(r["replay_strength"] for r in replayed) / len(replayed) if replayed else 0.0

        self._stats["total_replays"] += 1
        self._stats["total_sequences"] += len(sequence)
        self._stats["avg_strength"] = avg_strength
        self._stats["trajectories_detected"] += len(trajectories)

        return {
            "replayed": replayed,
            "trajectories": trajectories,
            "trajectory_count": len(trajectories),
            "avg_strength": avg_strength,
            "total_items": len(replayed),
        }

    def _detect_trajectories(self, replayed: list[dict[str, Any]]) -> list[list[str]]:
        trajectories = []
        current: list[str] = []
        for i, item in enumerate(replayed):
            if item["replay_strength"] > 0.5:
                current.append(item["memory_id"])
            else:
                if len(current) >= 2:
                    trajectories.append(current)
                current = []
            if i > 0:
                dt = abs(item["timestamp"] - replayed[i - 1]["timestamp"])
                if dt >= _STDP_WINDOW and len(current) >= 2:
                    trajectories.append(current)
                    current = []
        if len(current) >= 2:
            trajectories.append(current)
        return trajectories

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)


# ── Unified interface ─────────────────────────────────────────────────────

_bridge: _HaskellBridge | None = None
_fallback: _PyReplayEngine | None = None
_use_haskell: bool | None = None


def _get_bridge() -> _HaskellBridge:
    global _bridge
    if _bridge is None:
        _bridge = _HaskellBridge()
    return _bridge


def _get_fallback() -> _PyReplayEngine:
    global _fallback
    if _fallback is None:
        _fallback = _PyReplayEngine()
    return _fallback


def _try_haskell() -> bool:
    global _use_haskell
    if _use_haskell is None:
        _use_haskell = _get_bridge()._ensure()
    return _use_haskell


def replay(sequence: list[dict[str, Any]]) -> dict[str, Any]:
    """Replay a memory sequence with STDP strengthening."""
    if _try_haskell():
        result = _get_bridge().call("replay", {"sequence": sequence})
        if result.get("status") == "ok":
            return result
    return _get_fallback().replay(sequence)


def batch_replay(batches: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """Replay multiple sequences."""
    if _try_haskell():
        result = _get_bridge().call("batch_replay", {"batches": [{"sequence": b} for b in batches]})
        if result.get("status") == "ok":
            return result
    results = [_get_fallback().replay(b) for b in batches]
    return {"status": "success", "results": results, "total": len(results)}


def stats() -> dict[str, Any]:
    """Get replay engine statistics."""
    if _try_haskell():
        result = _get_bridge().call("stats", {})
        if result.get("status") == "ok":
            result["backend"] = "haskell"
            return result
    s = _get_fallback().stats()
    s["backend"] = "python"
    return s
