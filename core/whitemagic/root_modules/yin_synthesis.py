# ruff: noqa: BLE001
"""
Yin Phase Synthesis — Deep pattern analysis.

Deep synthesis using dream-state logic to understand project state
and generate insights.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class YinSynthesis:
    """Deep Yin analysis for pattern synthesis."""

    def __init__(self) -> None:
        self.observations: list[dict[str, Any]] = []
        self.syntheses: list[dict[str, Any]] = []

    def observe(self, subject: str, observation: str) -> None:
        """Record an observation without judgment."""
        self.observations.append({
            "subject": subject,
            "observation": observation,
        })

    def synthesize(self) -> dict[str, Any]:
        """Synthesize observations into insights."""
        by_subject: dict[str, list[str]] = {}
        for obs in self.observations:
            by_subject.setdefault(obs["subject"], []).append(obs["observation"])

        insights: list[str] = []
        for subject, obs_list in by_subject.items():
            if len(obs_list) >= 3:
                insights.append(f"{subject}: Pattern detected ({len(obs_list)} observations)")
            if len(obs_list) >= 5:
                insights.append(f"{subject}: Strong signal — investigate further")

        synthesis = {
            "total_observations": len(self.observations),
            "subjects": len(by_subject),
            "insights": insights,
        }
        self.syntheses.append(synthesis)
        return synthesis

    def summary(self) -> dict[str, Any]:
        return {
            "total_observations": len(self.observations),
            "total_syntheses": len(self.syntheses),
            "last_synthesis": self.syntheses[-1] if self.syntheses else None,
        }


_synthesis: YinSynthesis | None = None


def get_yin_synthesis() -> YinSynthesis:
    global _synthesis
    if _synthesis is None:
        _synthesis = YinSynthesis()
    return _synthesis
