# ruff: noqa: BLE001
"""Ripple Tagging — Co-activation memory tagging via Elixir bridge.

Tags memories that co-activate within a time window with ripple markers.
Ripple-tagged memories get stronger consolidation priority during sleep,
based on research showing sleep ripples elicit stronger reactivation than
wake ripples (bioRxiv, Mar 2026).

The Elixir bridge runs as a subprocess with JSON stdio protocol. If the
Elixir runtime is unavailable or WM_SKIP_POLYGLOT is set, falls back to
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
    "polyglot", "bridges", "elixir", "ripple_tagging.exs",
)
_BRIDGE_PATH = os.path.normpath(_BRIDGE_PATH)


class _ElixirBridge:
    """Manages a persistent Elixir subprocess for ripple tagging."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.RLock()
        self._available = False

    def _ensure(self) -> bool:
        """Start the Elixir process if not running."""
        if _SKIP_POLYGLOT:
            return False
        if self._proc and self._proc.poll() is None:
            return True
        try:
            self._proc = subprocess.Popen(
                ["elixir", _BRIDGE_PATH],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            time.sleep(0.5)  # allow Elixir VM to initialize
            if self._proc.poll() is None:
                self._available = True
                return True
            self._available = False
            return False
        except Exception as e:
            logger.debug("Elixir ripple bridge unavailable: %s", e, exc_info=True)
            self._available = False
            return False

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON request and return the response."""
        with self._lock:
            if not self._ensure():
                return {"status": "fallback", "reason": "elixir_unavailable"}
            req = json.dumps({"method": method, "params": params or {}})
            try:
                self._proc.stdin.write(req + "\n")
                self._proc.stdin.flush()
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
                logger.debug("Elixir bridge call failed: %s", e, exc_info=True)
                self._available = False
                return {"status": "fallback", "reason": str(e)}


# ── Pure Python fallback ──────────────────────────────────────────────────

_PyTag = dict  # type alias


class _PyRippleTagger:
    """Pure-Python fallback ripple tagger."""

    def __init__(self):
        self._tags: dict[str, list[_PyTag]] = {}
        self._stats = {"total_tags": 0, "total_events": 0, "ripples_detected": 0}

    def tag_ripple(
        self,
        memory_ids: list[str],
        timestamp: float,
        galaxy: str = "universal",
        emotional_weight: float = 1.0,
    ) -> dict[str, Any]:
        if len(memory_ids) < 2:
            return {"tagged": False, "reason": "insufficient_co_activation"}

        import math
        strength = min(0.8 * (1.0 + math.log(len(memory_ids)) * 0.2) * emotional_weight, 1.0)
        ripple_id = f"ripple_{int(timestamp)}_{id(self)}_{len(self._tags)}"

        tag = {
            "ripple_id": ripple_id,
            "timestamp": timestamp,
            "galaxy": galaxy,
            "strength": strength,
            "co_activation_count": len(memory_ids),
            "emotional_weight": emotional_weight,
        }

        for mid in memory_ids:
            self._tags.setdefault(mid, []).append(tag)

        self._stats["total_tags"] += len(memory_ids)
        self._stats["total_events"] += 1
        self._stats["ripples_detected"] += 1

        return {
            "tagged": True,
            "ripple_id": ripple_id,
            "strength": strength,
            "tagged_count": len(memory_ids),
        }

    def get_tags(self, memory_ids: list[str]) -> list[dict[str, Any]]:
        return [
            {"memory_id": mid, "ripple_count": len(self._tags.get(mid, [])), "tags": self._tags.get(mid, [])}
            for mid in memory_ids
        ]

    def decay_tags(self, hours: float) -> int:
        factor = 1.0 - (0.05 * hours)
        count = sum(len(v) for v in self._tags.values())
        for mid in list(self._tags.keys()):
            self._tags[mid] = [
                {**t, "strength": t["strength"] * factor}
                for t in self._tags[mid]
                if t["strength"] * factor > 0.05
            ]
            if not self._tags[mid]:
                del self._tags[mid]
        return count

    def stats(self) -> dict[str, Any]:
        return {**self._stats, "tagged_memories": len(self._tags)}


# ── Unified interface ─────────────────────────────────────────────────────

_bridge: _ElixirBridge | None = None
_fallback: _PyRippleTagger | None = None
_use_elixir: bool | None = None


def _get_bridge() -> _ElixirBridge:
    global _bridge
    if _bridge is None:
        _bridge = _ElixirBridge()
    return _bridge


def _get_fallback() -> _PyRippleTagger:
    global _fallback
    if _fallback is None:
        _fallback = _PyRippleTagger()
    return _fallback


def _try_elixir() -> bool:
    """Check if Elixir bridge is available (cached)."""
    global _use_elixir
    if _use_elixir is None:
        _use_elixir = _get_bridge()._ensure()
    return _use_elixir


def tag_ripple(
    memory_ids: list[str],
    timestamp: float | None = None,
    galaxy: str = "universal",
    emotional_weight: float = 1.0,
) -> dict[str, Any]:
    """Tag memories with a ripple marker from a co-activation event."""
    ts = timestamp or time.time() * 1000
    if _try_elixir():
        result = _get_bridge().call("tag_ripple", {
            "memory_ids": memory_ids,
            "timestamp": ts,
            "galaxy": galaxy,
            "emotional_weight": emotional_weight,
        })
        if result.get("status") == "ok":
            return result["result"]
    return _get_fallback().tag_ripple(memory_ids, ts, galaxy, emotional_weight)


def batch_tag(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Process multiple co-activation events."""
    if _try_elixir():
        result = _get_bridge().call("batch_tag", {"events": events})
        if result.get("status") == "ok":
            return result
    results = []
    for ev in events:
        results.append(_get_fallback().tag_ripple(
            ev.get("memory_ids", []),
            ev.get("timestamp", time.time() * 1000),
            ev.get("galaxy", "universal"),
            ev.get("emotional_weight", 1.0),
        ))
    return {"status": "ok", "results": results, "total": len(results)}


def get_tags(memory_ids: list[str]) -> list[dict[str, Any]]:
    """Get ripple tags for given memory IDs."""
    if _try_elixir():
        result = _get_bridge().call("get_tags", {"memory_ids": memory_ids})
        if result.get("status") == "ok":
            return result["tags"]
    return _get_fallback().get_tags(memory_ids)


def decay_tags(hours: float = 1.0) -> int:
    """Decay all ripple tag strengths by time-based factor."""
    if _try_elixir():
        result = _get_bridge().call("decay_tags", {"hours": hours})
        if result.get("status") == "ok":
            return result["decayed_count"]
    return _get_fallback().decay_tags(hours)


def stats() -> dict[str, Any]:
    """Get ripple tagging statistics."""
    if _try_elixir():
        result = _get_bridge().call("stats", {})
        if result.get("status") == "ok":
            return {**result["stats"], "tagged_memories": result["tagged_memories"], "backend": "elixir"}
    s = _get_fallback().stats()
    s["backend"] = "python"
    return s
