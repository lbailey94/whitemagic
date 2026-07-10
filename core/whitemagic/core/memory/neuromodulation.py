# ruff: noqa: BLE001
"""Neuromodulation — DA/5HT/ACh modulatory signals via Julia bridge.

Computes dopamine (DA), serotonin (5HT), and acetylcholine (ACh) levels
that modulate learning rate, consolidation priority, and attention focus.
Based on research showing distinct neuromodulators reshape memory processing
across brain regions (PLOS Comp Bio, 2025).

The Julia bridge runs as a subprocess with JSON stdio protocol. If the
Julia runtime is unavailable or WM_SKIP_POLYGLOT is set, falls back to
a pure-Python implementation.
"""

from __future__ import annotations

import json
import logging
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
    "polyglot", "bridges", "julia", "neuromodulation.jl",
)
_BRIDGE_PATH = os.path.normpath(_BRIDGE_PATH)

# Parameters (mirrored from Julia)
_DA_BASELINE = 0.5
_DA_NOVELTY_WEIGHT = 0.15
_DA_REWARD_WEIGHT = 0.2
_DA_DECAY = 0.95

_SHT_BASELINE = 0.5
_SHT_STABILITY_WEIGHT = 0.15
_SHT_COHERENCE_WEIGHT = 0.15
_SHT_DECAY = 0.97

_ACH_BASELINE = 0.5
_ACH_FOCUS_WEIGHT = 0.2
_ACH_ACTIVITY_WEIGHT = 0.1
_ACH_DECAY = 0.93


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class _JuliaBridge:
    """Manages a persistent Julia subprocess for neuromodulation."""

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
                ["julia", _BRIDGE_PATH],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            time.sleep(2.0)  # Julia JIT takes time
            if self._proc.poll() is None:
                self._available = True
                return True
            self._available = False
            return False
        except Exception as e:
            logger.debug("Julia neuromodulation bridge unavailable: %s", e, exc_info=True)
            self._available = False
            return False

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            if not self._ensure():
                return {"status": "fallback", "reason": "julia_unavailable"}
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
                logger.debug("Julia bridge call failed: %s", e, exc_info=True)
                self._available = False
                return {"status": "fallback", "reason": str(e)}


# ── Pure Python fallback ──────────────────────────────────────────────────


class _PyNeuromodulator:
    """Pure-Python fallback neuromodulator."""

    def __init__(self):
        self.da = _DA_BASELINE
        self.sht = _SHT_BASELINE
        self.ach = _ACH_BASELINE
        self._total_computations = 0
        self._total_modulations = 0

    def compute(self, params: dict[str, Any]) -> dict[str, Any]:
        novelty = params.get("novelty", 0.5)
        reward = params.get("reward", 0.5)
        stability = params.get("stability", 0.5)
        coherence = params.get("coherence", 0.5)
        focus = params.get("focus", 0.5)
        activity = params.get("activity_level", 0.5)

        da_signal = _DA_NOVELTY_WEIGHT * novelty + _DA_REWARD_WEIGHT * reward
        self.da = _clamp(self.da * _DA_DECAY + da_signal)

        sht_signal = _SHT_STABILITY_WEIGHT * stability + _SHT_COHERENCE_WEIGHT * coherence
        self.sht = _clamp(self.sht * _SHT_DECAY + sht_signal)

        ach_signal = _ACH_FOCUS_WEIGHT * focus + _ACH_ACTIVITY_WEIGHT * activity
        self.ach = _clamp(self.ach * _ACH_DECAY + ach_signal)

        self._total_computations += 1

        return {
            "da": self.da,
            "sht": self.sht,
            "ach": self.ach,
            "da_signal": da_signal,
            "sht_signal": sht_signal,
            "ach_signal": ach_signal,
            "learning_rate_boost": self.da * 0.5,
            "consolidation_priority": self.sht * 0.7,
            "attention_focus": self.ach * 0.8,
            "novelty_seeking": self.da * 0.3,
            "patience_factor": self.sht * 0.4,
        }

    def modulate(self, memories: list[dict[str, Any]], da: float | None = None, sht: float | None = None, ach: float | None = None) -> dict[str, Any]:
        _da = da if da is not None else self.da
        _sht = sht if sht is not None else self.sht
        _ach = ach if ach is not None else self.ach

        modulated = []
        for mem in memories:
            importance = mem.get("importance", 0.5)
            novelty = mem.get("novelty", 0.5)
            is_active = mem.get("is_active", False)

            da_boost = _da * novelty * 0.3
            sht_boost = _sht * importance * 0.2
            ach_boost = _ach * (1.0 if is_active else 0.0) * 0.4
            modulated_importance = _clamp(importance + da_boost + sht_boost + ach_boost)

            modulated.append({
                "memory_id": mem.get("memory_id", ""),
                "original_importance": importance,
                "modulated_importance": modulated_importance,
                "da_boost": da_boost,
                "sht_boost": sht_boost,
                "ach_boost": ach_boost,
            })

        self._total_modulations += 1
        return {"modulated": modulated, "total": len(modulated), "da": _da, "sht": _sht, "ach": _ach}

    def reset(self) -> None:
        self.da = _DA_BASELINE
        self.sht = _SHT_BASELINE
        self.ach = _ACH_BASELINE

    def stats(self) -> dict[str, Any]:
        return {
            "da": self.da,
            "sht": self.sht,
            "ach": self.ach,
            "total_computations": self._total_computations,
            "total_modulations": self._total_modulations,
        }


# ── Unified interface ─────────────────────────────────────────────────────

_bridge: _JuliaBridge | None = None
_fallback: _PyNeuromodulator | None = None
_use_julia: bool | None = None


def _get_bridge() -> _JuliaBridge:
    global _bridge
    if _bridge is None:
        _bridge = _JuliaBridge()
    return _bridge


def _get_fallback() -> _PyNeuromodulator:
    global _fallback
    if _fallback is None:
        _fallback = _PyNeuromodulator()
    return _fallback


def _try_julia() -> bool:
    global _use_julia
    if _use_julia is None:
        _use_julia = _get_bridge()._ensure()
    return _use_julia


def compute(
    novelty: float = 0.5,
    reward: float = 0.5,
    stability: float = 0.5,
    coherence: float = 0.5,
    focus: float = 0.5,
    activity_level: float = 0.5,
) -> dict[str, Any]:
    """Compute neuromodulator levels from activity signals."""
    params = {
        "novelty": novelty, "reward": reward, "stability": stability,
        "coherence": coherence, "focus": focus, "activity_level": activity_level,
    }
    if _try_julia():
        result = _get_bridge().call("compute", params)
        if result.get("status") == "ok":
            return result
    return _get_fallback().compute(params)


def modulate(memories: list[dict[str, Any]], da: float | None = None, sht: float | None = None, ach: float | None = None) -> dict[str, Any]:
    """Apply neuromodulation to a list of memories."""
    params = {"memories": memories}
    if da is not None:
        params["da"] = da
    if sht is not None:
        params["sht"] = sht
    if ach is not None:
        params["ach"] = ach
    if _try_julia():
        result = _get_bridge().call("modulate", params)
        if result.get("status") == "ok":
            return result
    return _get_fallback().modulate(memories, da, sht, ach)


def reset() -> dict[str, Any]:
    """Reset neuromodulator levels to baseline."""
    if _try_julia():
        result = _get_bridge().call("reset", {})
        if result.get("status") == "ok":
            return result
    _get_fallback().reset()
    return {"status": "success", "message": "Neuromodulator levels reset"}


def stats() -> dict[str, Any]:
    """Get neuromodulation statistics."""
    if _try_julia():
        result = _get_bridge().call("stats", {})
        if result.get("status") == "ok":
            result["backend"] = "julia"
            return result
    s = _get_fallback().stats()
    s["backend"] = "python"
    return s
