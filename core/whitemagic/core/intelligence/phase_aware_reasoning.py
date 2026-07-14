"""Phase-Aware Reasoning Enhancement

Integrates Zodiacal Procession's Yin/Yang cycle into multi-spectral reasoning
to adapt approach based on current cosmic phase.

Philosophy:
- Yin Phase: Receptive, analytical, reflective
- Yang Phase: Creative, active, expressive
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class PhaseGuidance(Enum):
    """Reasoning guidance based on phase"""

    YIN_RECEPTIVE = "yin_receptive"
    YANG_CREATIVE = "yang_creative"


@dataclass
class PhaseContext:
    """Current phase context from Zodiacal Procession"""

    phase: str  # "yin" or "yang"
    sign: str  # Current zodiac sign
    element: str  # Current element
    is_fixed: bool  # Is this a fixed sign (hub)?
    cycle: int  # Current cycle number


class PhaseAwareReasoner:
    """Enhances reasoning with Yin/Yang phase awareness"""

    def __init__(self):
        self.procession = None
        self._connect_to_procession()

    def _connect_to_procession(self):
        """Connect to Zodiacal Procession"""
        try:
            from whitemagic.core.orchestration.zodiacal_procession import get_procession

            self.procession = get_procession()
        except ImportError:
            logger.debug("Ignored ImportError in phase_aware_reasoning.py:50")

    def get_phase_context(self) -> PhaseContext | None:
        """Get current phase context"""
        if not self.procession:
            return None

        state = self.procession.state
        return PhaseContext(
            phase=state.current_phase.value,
            sign=state.current_sign.name_str,
            element=state.current_sign.element,
            is_fixed=state.current_sign.is_fixed,
            cycle=state.cycle_count,
        )

    def adapt_reasoning_strategy(self, phase_context: PhaseContext) -> dict[str, Any]:
        """Adapt reasoning strategy based on phase"""

        if phase_context.phase == "yin":
            # YIN: Receptive, analytical, reflective
            return {
                "approach": "receptive_analysis",
                "emphasis": {
                    "wu_xing": "water",  # Reflection, flow
                    "zodiac_signs": ["cancer", "scorpio", "pisces"],  # Water signs
                    "i_ching_type": "receptive",  # Kun hexagrams
                },
                "strategy": {
                    "sequential_thinking": True,  # Allow deep branching
                    "pattern_matching": "semantic",  # Contextual
                    "lens_priority": ["i_ching", "wu_xing", "zodiac", "art_of_war"],
                },
                "guidance": "Receive, analyze, integrate. Let patterns emerge naturally.",
            }
        else:
            # YANG: Creative, active, expressive
            return {
                "approach": "creative_action",
                "emphasis": {
                    "wu_xing": "fire",  # Action, transformation
                    "zodiac_signs": ["aries", "leo", "sagittarius"],  # Fire signs
                    "i_ching_type": "creative",  # Qian hexagrams
                },
                "strategy": {
                    "sequential_thinking": False,  # Direct answers
                    "pattern_matching": "exact",  # Precise
                    "lens_priority": ["art_of_war", "wu_xing", "zodiac", "i_ching"],
                },
                "guidance": "Create, express, manifest. Transform insight into action.",
            }

    def consult_fixed_sign_wisdom(self, sign: str) -> str | None:
        """Get wisdom from fixed signs (stability points)"""
        fixed_wisdom = {
            "taurus": "Build foundations that endure. Value stability and resources.",
            "leo": "Express authentically and boldly. Lead with heart and creativity.",
            "scorpio": "Embrace deep transformation. Go to the depths for truth.",
            "aquarius": "Think radically, serve collectively. Innovate for the future.",
        }
        return fixed_wisdom.get(sign.lower())

    def enhance_reasoning(self, question: str, base_result: Any) -> dict[str, Any]:
        """Enhance reasoning result with phase awareness"""

        phase_context = self.get_phase_context()
        if not phase_context:
            return {
                "phase_enhancement": None,
                "reason": "Zodiacal Procession not available",
            }

        strategy = self.adapt_reasoning_strategy(phase_context)

        enhancement = {
            "phase_context": {
                "phase": phase_context.phase,
                "sign": phase_context.sign,
                "element": phase_context.element,
                "is_fixed_hub": phase_context.is_fixed,
                "cycle": phase_context.cycle,
            },
            "adapted_strategy": strategy,
            "phase_guidance": strategy["guidance"],
        }

        if phase_context.is_fixed:
            wisdom = self.consult_fixed_sign_wisdom(phase_context.sign)
            if wisdom:
                enhancement["fixed_sign_wisdom"] = wisdom

        return enhancement


# Singleton instance
_phase_aware_reasoner = None


def get_phase_aware_reasoner() -> PhaseAwareReasoner:
    """Get global phase-aware reasoner"""
    global _phase_aware_reasoner
    if _phase_aware_reasoner is None:
        _phase_aware_reasoner = PhaseAwareReasoner()
    return _phase_aware_reasoner
