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
"""Evolution Subsystem (Consolidated v2.1).
=========================================
Unified gateway for continuous evolution, adaptive integration,
and recursive meta-learning (Thought Galaxy).

Consolidated from evolution/ sub-package. Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# --- ADAPTIVE SYSTEM ---

@dataclass
class AdaptiveRules:
    """AdaptiveRules: adaptive rules.

    Value object: equality and repr are field-based."""
    enabled: bool = False
    min_confidence: float = 0.8
    min_frequency: int = 5
    max_impact_score: float = 0.3
    require_approval: bool = True

class AdaptiveSystem:
    """Core logic for system-wide adaptations and self-optimization."""
    def __init__(self, rules: AdaptiveRules | None = None):
        self.rules = rules or AdaptiveRules()
        self.applied_adaptations = []
        self.pending_approvals = []

    def enable(self, require_approval: bool = True):
        """
        Perform the enable operation.

        Args:
            require_approval: Parameter description.
        """
        self.rules.enabled = True
        self.rules.require_approval = require_approval

# --- THOUGHT GALAXY ---

class ThoughtGalaxy:
    """Stores and mines emergent meta-patterns and 'thoughts'."""
    def __init__(self):
        self._patterns = []

    def mine_patterns(self) -> list[dict[str, Any]]:
        """Mine emergent patterns from stored thoughts.

        Analyzes the internal pattern list for recurring themes,
        frequency clusters, and meta-patterns.
        """
        if not self._patterns:
            return []
        # Group patterns by type and count frequency
        type_counts: dict[str, int] = {}
        for p in self._patterns:
            ptype = p.get("type", "unknown") if isinstance(p, dict) else "unknown"
            type_counts[ptype] = type_counts.get(ptype, 0) + 1
        # Return patterns sorted by frequency
        results = [
            {"type": t, "frequency": c, "dominance": c / len(self._patterns)}
            for t, c in sorted(type_counts.items(), key=lambda x: -x[1])
        ]
        return results

# --- SINGLETONS ---
_adaptive: AdaptiveSystem | None = None
_galaxy: ThoughtGalaxy | None = None

def get_adaptive_system() -> AdaptiveSystem:
    """
    Get the adaptive system.

    Returns:
        AdaptiveSystem
    """
    global _adaptive
    if _adaptive is None:
        _adaptive = AdaptiveSystem()
    return _adaptive

def get_thought_galaxy() -> ThoughtGalaxy:
    """
    Get the thought galaxy.

    Returns:
        ThoughtGalaxy
    """
    global _galaxy
    if _galaxy is None:
        _galaxy = ThoughtGalaxy()
    return _galaxy

def enable_full_recursion(require_approval: bool = True):
    """
    Perform the enable full recursion operation.

    Args:
        require_approval: Parameter description.
    """
    get_adaptive_system().enable(require_approval=require_approval)
    logger.warning("⚠️ FULL RECURSIVE EVOLUTION ENABLED")
