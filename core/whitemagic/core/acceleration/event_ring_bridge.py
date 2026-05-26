"""Event Ring Bridge — minimal stub for acceleration module imports."""

from __future__ import annotations

from typing import Any


class EventRingBridge:
    """Minimal stub for event ring bridge."""

    def __init__(self) -> None:
        pass

    def push(self, event: dict[str, Any]) -> None:
        """Push an event to the ring (no-op stub)."""
        pass

    def pop(self) -> dict[str, Any] | None:
        """Pop an event from the ring (no-op stub)."""
        return None


_bridge: EventRingBridge | None = None


def get_event_ring() -> EventRingBridge:
    """Get or create the global event ring bridge."""
    global _bridge
    if _bridge is None:
        _bridge = EventRingBridge()
    return _bridge
