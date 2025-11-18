"""
Art of War Strategic Planning Framework
Sun Tzu's principles for AI task planning.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class TaskTerrain(Enum):
    """Sun Tzu's six terrains for tasks."""

    ACCESSIBLE = "accessible"  # Straightforward
    ENTANGLING = "entangling"  # Has dependencies
    TEMPORIZING = "temporizing"  # Need more info
    NARROW = "narrow"  # Must be sequential
    PRECIPITOUS = "precipitous"  # High risk
    DISTANT = "distant"  # Long duration


class Factor(Enum):
    """Sun Tzu's Five Factors (五事)."""

    DAO = "dao"  # Alignment with principles
    HEAVEN = "heaven"  # Timing
    EARTH = "earth"  # Resources
    GENERAL = "general"  # Strategy
    LAW = "law"  # Discipline


@dataclass
class TerrainAnalysis:
    """Task terrain analysis."""

    terrain_type: TaskTerrain
    difficulty: str  # easy/medium/hard/extreme
    parallelizable: bool
    estimated_tokens: int
    recommended_approach: str
    warnings: List[str]


@dataclass
class FiveFactorsAssessment:
    """Five factors check."""

    dao_aligned: bool
    heaven_favorable: bool
    earth_prepared: bool
    general_ready: bool
    law_followed: bool

    @property
    def score(self) -> float:
        """Score 0.0 to 1.0"""
        return (
            sum(
                [
                    self.dao_aligned,
                    self.heaven_favorable,
                    self.earth_prepared,
                    self.general_ready,
                    self.law_followed,
                ]
            )
            / 5.0
        )

    @property
    def recommendation(self) -> str:
        """Strategic recommendation."""
        if self.score >= 0.8:
            return "PROCEED"
        elif self.score >= 0.6:
            return "PROCEED_WITH_CAUTION"
        else:
            return "PREPARE_MORE"
