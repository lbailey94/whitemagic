# ruff: noqa: BLE001
"""Global Workspace — broadcast architecture for cognitive integration.

Based on "Theater of Mind" Global Workspace Theory for LLMs (arXiv, Jun 2026).
Specialized cognitive modules (spreading activation, galaxy gating, sleep
consolidation, neuromodulation, etc.) compete for access to the global
workspace. The winner is "broadcast" to all other modules, creating
integrated cognitive behavior.

Architecture:
    ┌──────────────────────────────────────────────────────────┐
    │              Global Workspace                            │
    │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐      │
    │   │ Module1 │ │ Module2 │ │ Module3 │ │ ModuleN  │      │
    │   │ (SA)    │ │ (Gate)  │ │ (Sleep) │ │ (Neuro)  │      │
    │   └────┬────┘ └────┬────┘ └────┬────┘ └────┬─────┘      │
    │        │           │           │            │            │
    │        ▼           ▼           ▼            ▼            │
    │   ┌────────────────────────────────────────────────┐    │
    │   │          Competition / Arbitration              │    │
    │   └────────────────────┬───────────────────────────┘    │
    │                        │ broadcast                       │
    │   ┌────────────────────▼───────────────────────────┐    │
    │   │          All Listeners Receive                  │    │
    │   └────────────────────────────────────────────────┘    │
    └──────────────────────────────────────────────────────────┘

Uses GanYingBus for the actual broadcast mechanism.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_GW_DIR: Path = Path(os.environ.get("WM_STATE_ROOT", "/tmp/whitemagic")) / "citta"
_GW_STATE_FILE: Path = _GW_DIR / "workspace_state.json"


@dataclass
class WorkspaceBroadcast:
    """A single broadcast message in the global workspace."""

    source: str
    content: dict[str, Any]
    salience: float
    timestamp: float = field(default_factory=time.time)
    broadcast_id: str = ""

    def __post_init__(self):
        if not self.broadcast_id:
            self.broadcast_id = f"gw_{int(self.timestamp * 1000)}_{id(self)}"


@dataclass
class ModuleRegistration:
    """Registration info for a cognitive module in the workspace."""

    name: str
    handler: Callable[[WorkspaceBroadcast], None]
    salience_fn: Callable[[], float] | None = None
    description: str = ""
    last_broadcast_received: float = 0.0


class GlobalWorkspace:
    """Manages competition between cognitive modules and broadcasts winners.

    The workspace collects "proposals" from registered modules, selects the
    most salient one, and broadcasts it to all other modules. This creates
    integrated cognitive behavior from independent specialized systems.

    Competition model:
        - Proposals accumulate in a competition window
        - High-salience proposals (>= fast_ignite_threshold) ignite immediately
        - Lower-salience proposals compete; the winner ignites after the
          window closes or when ignite() is called explicitly
        - This replaces the original simple threshold with proper GWT ignition
    """

    def __init__(
        self,
        max_history: int = 100,
        competition_window: float = 0.5,
        fast_ignite_threshold: float = 0.8,
        min_ignite_salience: float = 0.3,
    ):
        self._modules: dict[str, ModuleRegistration] = {}
        self._lock = threading.RLock()
        self._history: list[WorkspaceBroadcast] = []
        self._max_history = max_history
        self._total_broadcasts = 0
        self._total_proposals = 0
        self._bus = None
        # Competition state
        self._competition_window = competition_window
        self._fast_ignite_threshold = fast_ignite_threshold
        self._min_ignite_salience = min_ignite_salience
        self._pending: list[WorkspaceBroadcast] = []
        self._window_start: float = 0.0
        self._ignition_count = 0

    def register(
        self,
        name: str,
        handler: Callable[[WorkspaceBroadcast], None],
        salience_fn: Callable[[], float] | None = None,
        description: str = "",
    ) -> None:
        """Register a cognitive module in the workspace."""
        with self._lock:
            self._modules[name] = ModuleRegistration(
                name=name, handler=handler, salience_fn=salience_fn, description=description
            )
        logger.debug("Registered module '%s' in global workspace", name)

    def unregister(self, name: str) -> None:
        """Remove a module from the workspace."""
        with self._lock:
            self._modules.pop(name, None)

    def propose(self, source: str, content: dict[str, Any], salience: float) -> WorkspaceBroadcast | None:
        """Submit a proposal to the global workspace.

        If salience >= fast_ignite_threshold, the proposal ignites immediately
        (fast pathway). Otherwise, it enters the competition window and
        competes with other pending proposals. The winner is selected when
        ignite() is called or when the window expires.

        Returns the broadcast if this proposal ignited, None otherwise.
        """
        self._total_proposals += 1
        broadcast = WorkspaceBroadcast(source=source, content=content, salience=salience)

        # Fast pathway: high-salience proposals ignite immediately
        if salience >= self._fast_ignite_threshold:
            self._broadcast(broadcast)
            self._ignition_count += 1
            self._pending.clear()
            self._window_start = 0.0
            return broadcast

        # Competition pathway: queue for competition
        with self._lock:
            if self._window_start == 0.0:
                self._window_start = time.time()
            self._pending.append(broadcast)

            # Check if window has expired
            if time.time() - self._window_start >= self._competition_window:
                return self._ignite_internal()

        return None

    def ignite(self) -> WorkspaceBroadcast | None:
        """Force ignition of the current competition window.

        Selects the most salient pending proposal and broadcasts it.
        Returns the broadcast if ignition occurred, None if no pending proposals
        or none meet the minimum salience threshold.
        """
        with self._lock:
            return self._ignite_internal()

    def _ignite_internal(self) -> WorkspaceBroadcast | None:
        """Select the winner from pending proposals and broadcast."""
        if not self._pending:
            self._window_start = 0.0
            return None

        # Select the most salient proposal
        winner = max(self._pending, key=lambda b: b.salience)

        # Reset competition window
        self._pending.clear()
        self._window_start = 0.0

        # Only ignite if winner meets minimum salience
        if winner.salience < self._min_ignite_salience:
            return None

        self._broadcast(winner)
        self._ignition_count += 1
        return winner

    def get_pending(self) -> list[dict[str, Any]]:
        """Get currently pending proposals in the competition window."""
        with self._lock:
            return [
                {"source": p.source, "salience": p.salience, "broadcast_id": p.broadcast_id}
                for p in self._pending
            ]

    def _broadcast(self, broadcast: WorkspaceBroadcast) -> None:
        """Broadcast a message to all registered modules."""
        self._total_broadcasts += 1

        # Add to history
        self._history.append(broadcast)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Notify all modules except the source
        with self._lock:
            modules = list(self._modules.values())

        for mod in modules:
            if mod.name == broadcast.source:
                continue
            try:
                mod.handler(broadcast)
                mod.last_broadcast_received = time.time()
            except Exception as e:
                logger.debug("Module '%s' failed to handle broadcast: %s", mod.name, e, exc_info=True)

        # Also emit via GanYingBus if available
        self._emit_to_bus(broadcast)

        # Throttled persistence — every 5 broadcasts
        if self._total_broadcasts % 5 == 0:
            self.persist_state()

    def _emit_to_bus(self, broadcast: WorkspaceBroadcast) -> None:
        """Emit the broadcast as a GanYingBus event for system-wide notification."""
        if self._bus is None:
            try:
                from whitemagic.core.resonance import EventType, get_bus
                self._bus = get_bus()
                self._event_type = EventType
            except Exception:
                self._bus = False
                return
        if self._bus and self._bus is not False:
            try:
                self._bus.emit(
                    self._event_type.INTERNAL_STATE_CHANGED,
                    source="global_workspace",
                    data={
                        "broadcast_id": broadcast.broadcast_id,
                        "source": broadcast.source,
                        "salience": broadcast.salience,
                        "content_keys": list(broadcast.content.keys()),
                    },
                )
            except Exception as e:
                logger.debug("GanYingBus emit failed: %s", e, exc_info=True)

    def get_current_state(self) -> dict[str, Any]:
        """Get the current workspace state (for sensorium/citta integration)."""
        latest = self._history[-1] if self._history else None
        return {
            "total_modules": len(self._modules),
            "total_broadcasts": self._total_broadcasts,
            "total_proposals": self._total_proposals,
            "latest_broadcast": {
                "source": latest.source,
                "salience": latest.salience,
                "broadcast_id": latest.broadcast_id,
            } if latest else None,
            "module_names": list(self._modules.keys()),
            "ignition_count": self._ignition_count,
            "pending_proposals": len(self._pending),
            "competition_active": self._window_start > 0.0,
        }

    def persist_state(self) -> None:
        """Persist workspace state to disk for cross-session continuity."""
        try:
            _GW_DIR.mkdir(parents=True, exist_ok=True)
            state = {
                "total_broadcasts": self._total_broadcasts,
                "total_proposals": self._total_proposals,
                "ignition_count": self._ignition_count,
                "history": [
                    {
                        "source": b.source,
                        "salience": b.salience,
                        "timestamp": b.timestamp,
                        "broadcast_id": b.broadcast_id,
                        "content_keys": list(b.content.keys()),
                    }
                    for b in self._history[-50:]  # Keep last 50
                ],
            }
            _GW_STATE_FILE.write_text(json.dumps(state, indent=2))
        except OSError:
            logger.debug("Failed to persist workspace state", exc_info=True)

    def load_state(self) -> None:
        """Load workspace state from disk on startup."""
        try:
            if not _GW_STATE_FILE.exists():
                return
            state = json.loads(_GW_STATE_FILE.read_text())
            self._total_broadcasts = state.get("total_broadcasts", 0)
            self._total_proposals = state.get("total_proposals", 0)
            self._ignition_count = state.get("ignition_count", 0)
            # Reconstruct lightweight history (without content dicts)
            for h in state.get("history", []):
                self._history.append(WorkspaceBroadcast(
                    source=h["source"],
                    content={},
                    salience=h["salience"],
                    timestamp=h.get("timestamp", 0.0),
                    broadcast_id=h.get("broadcast_id", ""),
                ))
        except (OSError, json.JSONDecodeError, KeyError):
            logger.debug("Failed to load workspace state", exc_info=True)

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent broadcast history."""
        return [
            {
                "source": b.source,
                "salience": b.salience,
                "timestamp": b.timestamp,
                "broadcast_id": b.broadcast_id,
                "content_keys": list(b.content.keys()),
            }
            for b in self._history[-limit:]
        ]

    def stats(self) -> dict[str, Any]:
        """Get workspace statistics."""
        return {
            "total_modules": len(self._modules),
            "total_broadcasts": self._total_broadcasts,
            "total_proposals": self._total_proposals,
            "history_length": len(self._history),
            "broadcast_rate": (
                self._total_broadcasts / max(self._total_proposals, 1)
            ),
            "ignition_count": self._ignition_count,
            "pending_proposals": len(self._pending),
            "competition_active": self._window_start > 0.0,
        }


# Singleton

_workspace: GlobalWorkspace | None = None


def get_global_workspace() -> GlobalWorkspace:
    """Get the singleton GlobalWorkspace instance."""
    global _workspace
    if _workspace is None:
        _workspace = GlobalWorkspace()
        _workspace.load_state()
    return _workspace
