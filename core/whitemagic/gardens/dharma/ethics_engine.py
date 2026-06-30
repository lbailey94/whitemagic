# ruff: noqa: BLE001
"""Ethics Engine - Strategic Ethics + Developmental Maturity.

Fuses:
  - ArtOfWarEngine: Sun Tzu's 13 chapters for terrain assessment, campaign planning,
    and strategic wisdom applied to software engineering.
  - MaturityEngine: Developmental milestone gates (Seed → Bicameral → Reflective →
    Radiant → Collective → Logos) that unlock capabilities only after safety gates pass.

The EthicsEngine provides a unified facade for strategic ethical evaluation,
terrain assessment, campaign planning, and maturity-gated capability checks.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EthicsEngine:
    """Unified strategic ethics and developmental maturity engine.

    Combines Art of War strategic planning with maturity-gated capability
    unlocking to ensure the system only uses advanced features after
    foundational layers are verified.
    """

    _art_of_war_instance: Any = None
    _maturity_engine_instance: Any = None

    def _get_art_of_war(self):
        """Lazy accessor for the ArtOfWarEngine."""
        if self._art_of_war_instance is None:
            from whitemagic.core.intelligence.wisdom.art_of_war import get_war_engine

            self._art_of_war_instance = get_war_engine()
        return self._art_of_war_instance

    def assess_terrain(self, objective: str) -> Any:
        """Assess the 'terrain' of a given objective using Sun Tzu's framework."""
        return self._get_art_of_war().assess_terrain(objective)

    def plan_campaign(self, objective: str) -> Any:
        """Generate a full campaign plan for an objective."""
        return self._get_art_of_war().plan_campaign(objective)

    def consult_chapter(self, chapter: int) -> list[Any]:
        """Get all principles from a specific Art of War chapter (1-13)."""
        return self._get_art_of_war().consult_chapter(chapter)

    def get_war_wisdom(self, situation: str) -> Any:
        """Get the most relevant Art of War wisdom for a situation."""
        return self._get_art_of_war().get_war_wisdom(situation)

    def list_campaigns(self, limit: int = 10) -> list[dict[str, Any]]:
        """List recent campaigns."""
        return self._get_art_of_war().list_campaigns(limit)

    def _get_maturity_engine(self):
        """Lazy accessor for the MaturityEngine."""
        if self._maturity_engine_instance is None:
            from whitemagic.core.governance.maturity_gates import get_maturity_engine

            self._maturity_engine_instance = get_maturity_engine()
        return self._maturity_engine_instance

    def assess_maturity(self) -> Any:
        """Run all gate checks and determine current maturity stage."""
        return self._get_maturity_engine().assess()

    def is_capable(self, capability: str) -> bool:
        """Check if a specific capability is unlocked at the current maturity."""
        return self._get_maturity_engine().is_capable(capability)

    def require_stage(self, minimum: Any) -> bool:
        """Check if the system has reached at least the given stage."""
        return self._get_maturity_engine().require_stage(minimum)

    def get_maturity_stats(self) -> dict[str, Any]:
        """Get maturity engine statistics."""
        return self._get_maturity_engine().get_stats()


_ethics_engine: EthicsEngine | None = None


def get_ethics_engine() -> EthicsEngine:
    """Get the global EthicsEngine singleton."""
    global _ethics_engine
    if _ethics_engine is None:
        _ethics_engine = EthicsEngine()
    return _ethics_engine
