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
"""Multispectral Reasoning Subsystem (Consolidated v1.5).
======================================================
Unified gateway for wisdom-based perspective analysis and scratchpad synthesis.
Contains the MultiSpectralReasoner and Scratchpad Analysis logic.

Consolidated from multi_spectral_reasoning.py and multi_spectral_scratchpad.py.
Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from whitemagic.config.paths import WM_ROOT

logger = logging.getLogger(__name__)

# --- TYPES & ENUMS ---

class ReasoningLens(Enum):
    """ReasoningLens: reasoning lens.

    Enumeration.

    Members:
        OBJ_RECOVERY
        WU_XING
        ART_OF_WAR
        STOICISM
        FIRST_PRINCIPLES
        S026_COHERENCE"""
    OBJ_RECOVERY = "objective_recovery"
    WU_XING = "wu_xing"
    ART_OF_WAR = "art_of_war"
    STOICISM = "stoicism"
    FIRST_PRINCIPLES = "first_principles"
    S026_COHERENCE = "s026_coherence"

@dataclass
class ReasoningContext:
    """ReasoningContext: reasoning context.

    Value object: equality and repr are field-based."""
    question: str
    task_type: str = "analysis"
    stakes: str = "medium"
    complexity: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class LensPerspective:
    """LensPerspective: lens perspective.

    Value object: equality and repr are field-based."""
    lens: ReasoningLens
    analysis: str
    guidance: str
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)

@dataclass
class ReasoningResult:
    """ReasoningResult: reasoning result.

    Value object: equality and repr are field-based."""
    question: str
    perspectives: list[LensPerspective]
    synthesis: str
    recommendation: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    reasoning_chain: list[str] = field(default_factory=list)
    patterns_matched: list[dict[str, Any]] = field(default_factory=list)

@dataclass(frozen=True)
class ScratchpadAnalysis:
    """ScratchpadAnalysis: scratchpad analysis.

    Value object: equality and repr are field-based."""
    synthesis: str
    wisdom: str
    confidence: float
    perspectives: list[dict[str, Any]]
    patterns_matched: int
    reasoning_chain: list[str]
    timestamp: datetime

# --- CORE REASONER (delegates to real multi_spectral_reasoning.py) ---

class MultiSpectralReasoner:
    """Orchestrates multiple wisdom-based reasoning perspectives.

    This is a compatibility wrapper that delegates to the real
    MultiSpectralReasoner in multi_spectral_reasoning.py.
    """

    def __init__(self, base_dir: Path | None = None):
        from whitemagic.core.intelligence.multi_spectral_reasoning import (
            MultiSpectralReasoner as _RealReasoner,
        )
        self._real = _RealReasoner(base_dir=base_dir or WM_ROOT)
        self.reasoning_history: list[ReasoningResult] = []

    def reason(self, question: str, lenses: Sequence[ReasoningLens] | None = None, context: ReasoningContext | None = None) -> ReasoningResult:
        from whitemagic.core.intelligence.multi_spectral_reasoning import (
            ReasoningContext as _RealContext,
        )
        from whitemagic.core.intelligence.multi_spectral_reasoning import (
            ReasoningLens as _RealLens,
        )

        # Map stub lenses to real lenses where possible
        lens_map = {
            ReasoningLens.WU_XING: _RealLens.WU_XING,
            ReasoningLens.ART_OF_WAR: _RealLens.ART_OF_WAR,
        }
        real_lenses = None
        if lenses:
            mapped = [lens_map[l] for l in lenses if l in lens_map]
            if mapped:
                real_lenses = mapped

        # Map context
        real_ctx = None
        if context:
            real_ctx = _RealContext(
                question=context.question,
                task_type=context.task_type,
                stakes=context.stakes,
                complexity=context.complexity,
            )

        real_result = self._real.reason(question=question, lenses=real_lenses, context=real_ctx)

        # Wrap back to stub types
        perspectives = []
        for p in real_result.perspectives:
            perspectives.append(LensPerspective(
                lens=ReasoningLens.WU_XING,
                analysis=p.analysis,
                guidance=p.guidance,
                confidence=p.confidence,
                details=p.details,
            ))

        result = ReasoningResult(
            question=question,
            perspectives=perspectives,
            synthesis=real_result.synthesis,
            recommendation=real_result.recommendation,
            confidence=real_result.confidence,
        )
        self.reasoning_history.append(result)
        return result

# --- SCRATCHPAD INTEGRATION ---

def analyze_scratchpad(scratchpad_content: dict[str, str], question: str | None = None, lenses: Sequence[ReasoningLens] | None = None) -> ScratchpadAnalysis:
    """
    Perform the analyze scratchpad operation.

    Args:
        scratchpad_content: Parameter description.
        question: Parameter description.
        lenses: Parameter description.

    Returns:
        ScratchpadAnalysis
    """
    if question is None:
        question = scratchpad_content.get("current_focus") or "What should I focus on next?"

    reasoner = MultiSpectralReasoner()
    result = reasoner.reason(question=question, lenses=lenses)

    return ScratchpadAnalysis(
        synthesis=result.synthesis,
        wisdom=result.recommendation,
        confidence=result.confidence,
        perspectives=[{"lens": p.lens.value, "guidance": p.guidance} for p in result.perspectives],
        patterns_matched=0,
        reasoning_chain=[],
        timestamp=result.timestamp,
    )

def serialize_scratchpad_with_analysis(scratchpad_content: dict[str, str], analysis: ScratchpadAnalysis, title: str = "Scratchpad") -> str:
    """
    Perform the serialize scratchpad with analysis operation.

    Args:
        scratchpad_content: Parameter description.
        analysis: Parameter description.
        title: Parameter description.

    Returns:
        str
    """
    lines = [f"# {title}", "", "## Analysis", f"Confidence: {analysis.confidence:.2%}", "", "### Synthesis", analysis.synthesis, "", "### Recommendation", analysis.wisdom, ""]
    lines.append("## Scratchpad")
    for section, content in scratchpad_content.items():
        lines.extend([f"### {section.replace('_', ' ').title()}", content, ""])
    return "\n".join(lines)

# --- SINGLETON ---
_reasoner: MultiSpectralReasoner | None = None

def get_reasoner() -> MultiSpectralReasoner:
    """
    Get the reasoner.

    Returns:
        MultiSpectralReasoner
    """
    global _reasoner
    if _reasoner is None:
        _reasoner = MultiSpectralReasoner()
    return _reasoner
