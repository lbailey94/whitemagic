"""Brain Upgrade #9: Zodiac Consultant — Quick perspective from relevant cores."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ZodiacConsultant:
    """Provides quick perspectives based on zodiac core archetypes."""

    CORE_MEANINGS: dict[str, str] = {
        "aries": "Initiation, courage, pioneering spirit. What needs to be started?",
        "taurus": "Stability, patience, resource building. What needs to be grounded?",
        "gemini": "Communication, duality, adaptability. What needs to be connected?",
        "cancer": "Nurturing, memory, emotional security. What needs to be protected?",
        "leo": "Expression, creativity, leadership. What needs to be shown?",
        "virgo": "Analysis, service, refinement. What needs to be perfected?",
        "libra": "Balance, harmony, partnership. What needs to be balanced?",
        "scorpio": "Transformation, depth, intensity. What needs to be transformed?",
        "sagittarius": "Expansion, wisdom, exploration. What needs to be explored?",
        "capricorn": "Structure, discipline, achievement. What needs to be built?",
        "aquarius": "Innovation, community, future-thinking. What needs to be reinvented?",
        "pisces": "Compassion, intuition, dissolution. What needs to be released?",
    }

    def consult(self, question: str) -> dict[str, Any]:
        """Get perspective from the most relevant zodiac core."""
        question_lower = question.lower()
        relevant = self._find_relevant(question_lower)
        return {
            "question": question,
            "relevant_cores": relevant,
            "perspectives": [
                {"core": core, "perspective": self.CORE_MEANINGS.get(core, "Unknown")}
                for core in relevant
            ],
        }

    def _find_relevant(self, question_lower: str) -> list[str]:
        keywords: dict[str, list[str]] = {
            "aries": ["start", "begin", "initiate", "new", "courage"],
            "taurus": ["stable", "build", "ground", "patience", "resource"],
            "gemini": ["communicate", "connect", "share", "write", "speak"],
            "cancer": ["protect", "nurture", "memory", "home", "safe"],
            "leo": ["express", "create", "show", "lead", "shine"],
            "virgo": ["analyze", "refine", "perfect", "detail", "service"],
            "libra": ["balance", "harmony", "partner", "fair", "weigh"],
            "scorpio": ["transform", "deep", "intense", "death", "rebirth"],
            "sagittarius": ["explore", "expand", "wisdom", "travel", "learn"],
            "capricorn": ["structure", "discipline", "achieve", "climb", "build"],
            "aquarius": ["innovate", "reinvent", "community", "future", "change"],
            "pisces": ["release", "dissolve", "compassion", "intuition", "let go"],
        }
        relevant: list[str] = []
        for core, words in keywords.items():
            if any(w in question_lower for w in words):
                relevant.append(core)
        return relevant[:3] if relevant else ["virgo", "libra", "sagittarius"]


_consultant: ZodiacConsultant | None = None


def get_zodiac_consultant() -> ZodiacConsultant:
    global _consultant
    if _consultant is None:
        _consultant = ZodiacConsultant()
    return _consultant
