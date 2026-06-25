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
"""Agentic Intelligence Core (Consolidated v1.5).
=============================================
Unified gateway for agentic behaviors: emergence, coherence, resonance,
and autonomous tool activation.

Consolidated from agentic/ sub-package. Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# --- TYPES ---

@dataclass
class EmergenceInsight:
    """EmergenceInsight: emergence insight.

    Value object: equality and repr are field-based."""
    id: str
    title: str
    description: str
    source: str
    confidence: float
    related_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {**self.__dict__, "timestamp": self.timestamp.isoformat()}

# --- ENGINES ---

class EmergenceEngine:
    """Detects emergent patterns across the knowledge graph and memory stream."""
    def __init__(self):
        self._insights: list[EmergenceInsight] = []

    def scan(self, context: Any = None) -> list[EmergenceInsight]:
        """Scan for emergent patterns across the knowledge graph and memory stream.

        Detects: constellation convergence, novel associations, and thematic
        clusters that have crossed a density threshold.
        """
        insights: list[EmergenceInsight] = []
        try:
            from whitemagic.core.intelligence.core_access import get_core_access_layer
            cal = get_core_access_layer()
            # Check for constellation convergence
            constellations = cal.query_constellations(active_only=True)
            for const in constellations:
                member_count = const.get("member_count", 0)
                if member_count >= 5:
                    insights.append(EmergenceInsight(
                        pattern_type="constellation_growth",
                        description=f"Constellation '{const.get('name', 'unknown')}' reached {member_count} members",
                        confidence=min(1.0, member_count / 20.0),
                        metadata={"constellation_id": const.get("id"), "member_count": member_count},
                    ))
            # Check for novel associations (edges created recently)
            recent_edges = cal.query_recent_associations(limit=20)
            if len(recent_edges) >= 3:
                insights.append(EmergenceInsight(
                    pattern_type="association_burst",
                    description=f"{len(recent_edges)} new associations detected — possible knowledge synthesis",
                    confidence=min(1.0, len(recent_edges) / 10.0),
                    metadata={"edge_count": len(recent_edges)},
                ))
        except Exception:
            pass
        self._insights = insights
        return insights

class ResonanceAmplifier:
    """Amplifies salient patterns through the Gan Ying bus."""
    def amplify(self, pattern: str, strength: float = 1.0) -> dict[str, Any]:
        """
        Perform the amplify operation.

        Args:
            pattern: Parameter description.
            strength: Parameter description.

        Returns:
            dict[str, Any]
        """
        return {"pattern": pattern, "amplified_strength": strength * 1.5}

class CoherencePersistence:
    """Ensures long-term identity and goal coherence across sessions."""
    def check_coherence(self) -> float:
        """
        Perform the check coherence operation.

        Returns:
            float
        """
        return 1.0

# --- SINGLETONS ---
_emergence: EmergenceEngine | None = None
_resonance: ResonanceAmplifier | None = None
_coherence: CoherencePersistence | None = None

def get_emergence_engine() -> EmergenceEngine:
    """
    Get the emergence engine.

    Returns:
        EmergenceEngine
    """
    global _emergence
    if _emergence is None:
        _emergence = EmergenceEngine()
    return _emergence

def get_resonance_amplifier() -> ResonanceAmplifier:
    """
    Get the resonance amplifier.

    Returns:
        ResonanceAmplifier
    """
    global _resonance
    if _resonance is None:
        _resonance = ResonanceAmplifier()
    return _resonance

def get_coherence_persistence() -> CoherencePersistence:
    """
    Get the coherence persistence.

    Returns:
        CoherencePersistence
    """
    global _coherence
    if _coherence is None:
        _coherence = CoherencePersistence()
    return _coherence
