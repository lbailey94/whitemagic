# ruff: noqa: BLE001
"""
Security-Homeostasis Link — Connect immune threats to homeostatic loop.

When the immune system detects threats, they feed into the homeostatic
loop as corrective actions, creating a self-healing feedback cycle.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SecurityHomeostasisLink:
    """Links immune system threats to homeostatic loop actions."""

    def __init__(self) -> None:
        self.linked_threats: list[dict[str, Any]] = []

    def process_threats(self) -> list[dict[str, Any]]:
        """Process current immune threats into homeostatic actions."""
        actions: list[dict[str, Any]] = []

        try:
            from whitemagic.core.immune.detector import get_detector

            detector = get_detector()
            threats = detector.detected_threats

            for threat in threats:
                action = {
                    "dimension": "security",
                    "level": threat.level.value,
                    "description": threat.description,
                    "source": "immune_system",
                    "antigen": threat.antigen,
                }
                actions.append(action)
                self.linked_threats.append(action)
        except Exception:
            logger.debug("Immune system not available for linking")

        return actions

    def summary(self) -> dict[str, Any]:
        return {
            "total_linked": len(self.linked_threats),
            "recent": len(self.linked_threats[-10:]),
        }


_link: SecurityHomeostasisLink | None = None


def get_security_link() -> SecurityHomeostasisLink:
    global _link
    if _link is None:
        _link = SecurityHomeostasisLink()
    return _link
