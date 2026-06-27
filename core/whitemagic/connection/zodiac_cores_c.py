# ruff: noqa: BLE001
"""
Zodiac Cores System C — Evolutionary Synthesis.

Combines the best of System A and System B with emergent properties:
- Task routing intelligence (can_handle)
- Capability metadata (strengths/challenges)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .zodiac_cores import SIGN_QUALITIES, ZODIAC_SIGNS

logger = logging.getLogger(__name__)


@dataclass
class EvolutionaryZodiacCore:
    """Evolutionary zodiac core with task routing intelligence."""
    sign: str
    quality: str
    strengths: list[str] = field(default_factory=list)
    challenges: list[str] = field(default_factory=list)
    can_handle: list[str] = field(default_factory=list)
    energy: float = 0.5
    active: bool = False

    def matches_task(self, task_type: str) -> bool:
        """Check if this core can handle a task type."""
        return task_type in self.can_handle


# Define capabilities for each sign
SIGN_CAPABILITIES: dict[str, dict[str, list[str]]] = {
    "aries": {"strengths": ["initiative", "speed"], "can_handle": ["start", "launch", "attack"]},
    "taurus": {"strengths": ["persistence", "stability"], "can_handle": ["build", "maintain", "secure"]},
    "gemini": {"strengths": ["communication", "versatility"], "can_handle": ["translate", "connect", "analyze"]},
    "cancer": {"strengths": ["nurturing", "memory"], "can_handle": ["care", "protect", "remember"]},
    "leo": {"strengths": ["leadership", "creativity"], "can_handle": ["lead", "create", "perform"]},
    "virgo": {"strengths": ["precision", "analysis"], "can_handle": ["debug", "optimize", "organize"]},
    "libra": {"strengths": ["balance", "diplomacy"], "can_handle": ["mediate", "balance", "decide"]},
    "scorpio": {"strengths": ["depth", "transformation"], "can_handle": ["investigate", "transform", "heal"]},
    "sagittarius": {"strengths": ["exploration", "wisdom"], "can_handle": ["explore", "teach", "expand"]},
    "capricorn": {"strengths": ["discipline", "structure"], "can_handle": ["plan", "execute", "govern"]},
    "aquarius": {"strengths": ["innovation", "vision"], "can_handle": ["innovate", "design", "reform"]},
    "pisces": {"strengths": ["intuition", "compassion"], "can_handle": ["dream", "synthesize", "forgive"]},
}


def get_evolutionary_cores() -> dict[str, EvolutionaryZodiacCore]:
    """Create evolutionary zodiac cores for all signs."""
    cores: dict[str, EvolutionaryZodiacCore] = {}
    for sign in ZODIAC_SIGNS:
        caps = SIGN_CAPABILITIES.get(sign, {})
        cores[sign] = EvolutionaryZodiacCore(
            sign=sign,
            quality=SIGN_QUALITIES.get(sign, ""),
            strengths=caps.get("strengths", []),
            challenges=caps.get("challenges", []),
            can_handle=caps.get("can_handle", []),
        )
    return cores
