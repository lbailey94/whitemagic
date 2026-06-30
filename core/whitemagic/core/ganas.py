# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Ganas Subsystem (Consolidated v1.9).
====================================
Unified gateway for the 28 Ganas (Lunar Mansions), providing tool invocation,
karma tracking, and resonant sequence execution (chains).

Consolidated from ganas/ sub-package. Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LunarMansion(Enum):
    """LunarMansion: lunar mansion.

    Enumeration.

    Members:
        HORN
        NECK
        ROOT
        ROOM
        HEART
        TAIL
        BASKET
        GHOST
        WILLOW
        STAR
        NET_EXT
        WINGS
        CHARIOT
        ABUNDANCE
        STRADDLING
        MOUND
        STOMACH
        HAIRY
        NET
        TURTLE
        THREE_STARS
        DIPPER
        OX
        GIRL
        VOID
        ROOF
        ENCAMPMENT
        WALL"""

    HORN = "horn"
    NECK = "neck"
    ROOT = "root"
    ROOM = "room"
    HEART = "heart"
    TAIL = "tail"
    BASKET = "basket"
    GHOST = "ghost"
    WILLOW = "willow"
    STAR = "star"
    NET_EXT = "net_ext"
    WINGS = "wings"
    CHARIOT = "chariot"
    ABUNDANCE = "abundance"
    STRADDLING = "straddling"
    MOUND = "mound"
    STOMACH = "stomach"
    HAIRY = "hairy"
    NET = "net"
    TURTLE = "turtle"
    THREE_STARS = "three_stars"
    DIPPER = "dipper"
    OX = "ox"
    GIRL = "girl"
    VOID = "void"
    ROOF = "roof"
    ENCAMPMENT = "encampment"
    WALL = "wall"


@dataclass
class GanaCall:
    """GanaCall: gana call.

    Value object: equality and repr are field-based."""

    task: str
    state_vector: dict[str, Any] = field(default_factory=dict)
    resonance_hints: Any = None


@dataclass
class GanaResult:
    """GanaResult: gana result.

    Value object: equality and repr are field-based."""

    mansion: LunarMansion
    output: Any
    successor_hint: str | None = None
    karma_trace: dict[str, Any] = field(default_factory=dict)


class BaseGana:
    """Base class for all lunar mansions (Ganas)."""

    def __init__(self, mansion: LunarMansion):
        self.mansion = mansion
        self.stats = {"invocations": 0}

    async def invoke(self, call: GanaCall) -> GanaResult:
        """
        Perform the invoke operation.

        Args:
            call: Parameter description.

        Returns:
            GanaResult
        """
        self.stats["invocations"] += 1
        return GanaResult(mansion=self.mansion, output="Execution simulated")


class EasternGana(BaseGana):
    """Eastern quadrant gana (placeholder stub pending consolidation into GanaChain)."""

    pass


class SouthernGana(BaseGana):
    """Southern quadrant gana (placeholder stub pending consolidation into GanaChain)."""

    pass


class WesternGana(BaseGana):
    """Western quadrant gana (placeholder stub pending consolidation into GanaChain)."""

    pass


class NorthernGana(BaseGana):
    """Northern quadrant gana (placeholder stub pending consolidation into GanaChain)."""

    pass


class GanaChain:
    """Executes sequences of Gana calls with resonance."""

    async def execute_chain(
        self, mansions: list[LunarMansion], task: str
    ) -> list[GanaResult]:
        """
        Run the chain operation.

        Args:
            mansions: Parameter description.
            task: Parameter description.

        Returns:
            list[GanaResult]
        """
        return [await get_gana(m).invoke(GanaCall(task=task)) for m in mansions]


_registry: dict[LunarMansion, BaseGana] = {}


def get_gana(mansion: LunarMansion) -> BaseGana:
    """
    Get the gana.

    Args:
        mansion: Parameter description.

    Returns:
        BaseGana
    """
    if mansion not in _registry:
        _registry[mansion] = BaseGana(mansion)
    return _registry[mansion]


def get_chain() -> GanaChain:
    """
    Get the chain.

    Returns:
        GanaChain
    """
    return GanaChain()
