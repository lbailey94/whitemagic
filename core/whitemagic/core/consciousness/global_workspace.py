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

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


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
    """

    def __init__(self, max_history: int = 100):
        self._modules: dict[str, ModuleRegistration] = {}
        self._lock = threading.Lock()
        self._history: list[WorkspaceBroadcast] = []
        self._max_history = max_history
        self._total_broadcasts = 0
        self._total_proposals = 0
        self._bus = None  # Lazy GanYingBus connection

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

        If this proposal has the highest salience in the current cycle,
        it will be broadcast to all other modules.
        """
        self._total_proposals += 1
        broadcast = WorkspaceBroadcast(source=source, content=content, salience=salience)

        # Check if this is more salient than recent proposals
        # Simple competition: broadcast if salience > threshold
        if salience >= 0.5:
            self._broadcast(broadcast)
            return broadcast
        return None

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

    def _emit_to_bus(self, broadcast: WorkspaceBroadcast) -> None:
        """Emit the broadcast as a GanYingBus event for system-wide notification."""
        if self._bus is None:
            try:
                from whitemagic.core.resonance import get_bus, EventType
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
        }

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
        }


# Singleton

_workspace: GlobalWorkspace | None = None


def get_global_workspace() -> GlobalWorkspace:
    """Get the singleton GlobalWorkspace instance."""
    global _workspace
    if _workspace is None:
        _workspace = GlobalWorkspace()
    return _workspace
