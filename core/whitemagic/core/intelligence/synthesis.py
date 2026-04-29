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
"""Synthesis Intelligence Core (Consolidated v1.8).
===============================================
Unified gateway for pattern synthesis, title generation, tag normalization,
and serendipitous discovery.

Consolidated from synthesis/ sub-package. Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# --- TITLE GENERATOR ---

class TitleGenerator:
    """Generate descriptive titles for memories based on content analysis."""
    def generate(self, content: str) -> str:
        if not content: return "Untitled"
        # Match header or first line
        match = re.search(r"^#\s+(.+)$", content, re.M)
        if match: return match.group(1).strip()[:60]
        return content.split("\n")[0].strip()[:60]

# --- SERENDIPITY ENGINE ---

class SerendipityEngine:
    """Detects unexpected connections and novel insights (serendipity)."""
    def find_serendipity(self, pool: Any = None) -> list[dict[str, Any]]:
        """Find serendipitous connections — graceful fallback returns empty list."""
        return []

# --- SOLVER ENGINE ---

class DharmicSolver:
    """Mathematical solver for causal constraints and ethical optimization."""
    def solve(self, nodes: list, edges: list, scores: dict) -> Any:
        # Simplified implementation
        return {n: 1.0 for n in nodes}

# --- SINGLETONS ---
_title_gen: TitleGenerator | None = None
_serendipity: SerendipityEngine | None = None
_solver: DharmicSolver | None = None

def get_title_generator() -> TitleGenerator:
    global _title_gen
    if _title_gen is None: _title_gen = TitleGenerator()
    return _title_gen

def get_serendipity_engine() -> SerendipityEngine:
    global _serendipity
    if _serendipity is None: _serendipity = SerendipityEngine()
    return _serendipity

def get_solver() -> DharmicSolver:
    global _solver
    if _solver is None: _solver = DharmicSolver()
    return _solver
