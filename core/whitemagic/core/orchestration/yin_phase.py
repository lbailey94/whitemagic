# ruff: noqa: BLE001
"""
Yin Phase — Deep receptive analysis.

坤 (Kūn) — The Receptive Earth:
- Observe everything
- Judge nothing
- Learn deeply
- Consolidate memory
- Self-correct
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class YinPhase:
    """Deep receptive analysis phase."""

    def __init__(self) -> None:
        self.observations: list[dict[str, Any]] = []
        self.insights: list[str] = []
        self.active = False

    def enter(self) -> None:
        """Enter the yin phase."""
        self.active = True
        logger.info("Entering Yin Phase — receptive observation")

    def observe(self, subject: str, observation: str) -> None:
        """Record an observation without judgment."""
        entry = {
            "subject": subject,
            "observation": observation,
            "timestamp": time.time(),
        }
        self.observations.append(entry)

    def consolidate(self) -> list[str]:
        """Consolidate observations into insights."""
        self.insights = []

        # Group observations by subject
        by_subject: dict[str, list[str]] = {}
        for obs in self.observations:
            by_subject.setdefault(obs["subject"], []).append(obs["observation"])

        # Simple insight extraction
        for subject, obs_list in by_subject.items():
            if len(obs_list) >= 3:
                self.insights.append(
                    f"{subject}: {len(obs_list)} observations suggest a pattern"
                )

        return self.insights

    def exit(self) -> dict[str, Any]:
        """Exit the yin phase with consolidated insights."""
        insights = self.consolidate()
        result = {
            "observations": len(self.observations),
            "insights": insights,
            "subjects": list(set(o["subject"] for o in self.observations)),
        }
        self.active = False
        logger.info("Exiting Yin Phase — %d insights", len(insights))
        return result

    def status(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "observations": len(self.observations),
            "insights": len(self.insights),
        }


_yin: YinPhase | None = None


def get_yin_phase() -> YinPhase:
    global _yin
    if _yin is None:
        _yin = YinPhase()
    return _yin
