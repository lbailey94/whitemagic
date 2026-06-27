# ruff: noqa: BLE001
"""
Automated Consolidation Triggers.

Triggers consolidation at appropriate times:
- Session end
- Version release
- Every N memories
- On schedule (cron-like)
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConsolidationTriggers:
    """Manages when consolidation should be triggered."""

    def __init__(self) -> None:
        self.triggers: dict[str, dict[str, Any]] = {}
        self.last_triggered: dict[str, float] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.triggers = {
            "session_end": {"type": "event", "enabled": True},
            "version_release": {"type": "event", "enabled": True},
            "memory_count": {"type": "threshold", "value": 40, "enabled": True},
            "scheduled": {"type": "interval", "value": 3600, "enabled": False},
        }

    def check_triggers(self) -> list[str]:
        """Check which triggers are currently active."""
        active: list[str] = []
        now = time.time()

        for name, config in self.triggers.items():
            if not config.get("enabled", False):
                continue

            if config["type"] == "interval":
                last = self.last_triggered.get(name, 0)
                if now - last >= config["value"]:
                    active.append(name)

            elif config["type"] == "threshold":
                try:
                    from whitemagic.core.memory.unified import get_unified_memory
                    mem = get_unified_memory()
                    if hasattr(mem, "count") and mem.count() >= config["value"]:
                        active.append(name)
                except Exception:
                    pass

        return active

    def fire_trigger(self, name: str) -> bool:
        """Manually fire a trigger."""
        if name not in self.triggers:
            return False
        self.last_triggered[name] = time.time()
        logger.info("Trigger fired: %s", name)
        return True

    def enable(self, name: str) -> bool:
        if name in self.triggers:
            self.triggers[name]["enabled"] = True
            return True
        return False

    def disable(self, name: str) -> bool:
        if name in self.triggers:
            self.triggers[name]["enabled"] = False
            return True
        return False

    def summary(self) -> dict[str, Any]:
        return {
            "triggers": {n: c.get("enabled", False) for n, c in self.triggers.items()},
            "last_triggered": self.last_triggered,
        }


_triggers: ConsolidationTriggers | None = None


def get_triggers() -> ConsolidationTriggers:
    global _triggers
    if _triggers is None:
        _triggers = ConsolidationTriggers()
    return _triggers
