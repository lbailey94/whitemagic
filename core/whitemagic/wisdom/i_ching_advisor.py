# ruff: noqa: BLE001
"""
I Ching Advisor — Decision support using I Ching oracle.

Wraps the I Ching system with advisory context, translating
hexagram interpretations into actionable guidance.
"""

from __future__ import annotations

import logging
from typing import Any

from whitemagic.core.intelligence.wisdom.i_ching import IChingAdvisor as _CanonicalIChing

logger = logging.getLogger(__name__)


class IChingAdvisor:
    """Advises decisions using I Ching oracle."""

    def __init__(self) -> None:
        self.i_ching = _CanonicalIChing()
        self.consultations: list[dict[str, Any]] = []

    def advise(self, question: str) -> dict[str, Any]:
        """Get I Ching advice for a question."""
        hexagram = self.i_ching.cast_hexagram(question)
        consultation = {
            "question": question,
            "number": hexagram.number,
            "name": hexagram.name,
            "chinese": hexagram.chinese,
            "judgment": hexagram.judgment,
            "image": hexagram.image,
            "guidance": hexagram.guidance,
        }
        advice = self._generate_advice(consultation)
        consultation["advice"] = advice
        self.consultations.append(consultation)
        return consultation

    def _generate_advice(self, consultation: dict[str, Any]) -> str:
        """Generate actionable advice from hexagram interpretation."""
        name = consultation.get("name", "")
        number = consultation.get("number", 0)

        advice_map: dict[int, str] = {
            1: "Take initiative. The time is right for creative action.",
            2: "Be receptive. Listen more than you speak. Patience will be rewarded.",
            3: "Face difficulties with patience. Don't force things.",
            4: "Seek guidance from experience. Don't act impulsively.",
            5: "Wait for the right moment. Nourish yourself while waiting.",
            6: "Avoid conflict. Seek mediation. Compromise is not weakness.",
            7: "Organize and discipline. Leadership requires structure.",
            8: "Build alliances. Unity brings strength.",
            11: "Harmony prevails. Proceed with confidence.",
            12: "Things are blocked. Be patient and conserve energy.",
            63: "A cycle is completing. Prepare for the next phase.",
            64: "You are on the verge of completion. Don't rush.",
        }

        base_advice = advice_map.get(number, f"Reflect on the meaning of {name}.")
        return base_advice

    def history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent consultations."""
        return self.consultations[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_consultations": len(self.consultations),
        }


_advisor: IChingAdvisor | None = None


def get_advisor() -> IChingAdvisor:
    global _advisor
    if _advisor is None:
        _advisor = IChingAdvisor()
    return _advisor
