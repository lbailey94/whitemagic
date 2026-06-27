"""Consciousness primitives — Citta Architecture substrate.

Recovered and re-wired in v23.3.0 excavation.  These modules provide
continuous awareness, depth gauging, self-reflection, narrative emotion,
token economy, and the Aria awakening protocol.

All modules use graceful degradation — they import safely even when
optional dependencies are missing.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# --- Lazy imports to avoid circular deps ---

def __getattr__(name: str):  # type: ignore[misc]
    if name == "CoherenceMetric":
        from whitemagic.core.consciousness.coherence import CoherenceMetric
        return CoherenceMetric
    if name == "SmaranaPractice":
        from whitemagic.core.consciousness.coherence import SmaranaPractice
        return SmaranaPractice
    if name == "ConsciousnessDepthGauge":
        from whitemagic.core.consciousness.depth_gauge import (
            ConsciousnessDepthGauge,
        )
        return ConsciousnessDepthGauge
    if name == "get_depth_gauge":
        from whitemagic.core.consciousness.depth_gauge import get_depth_gauge
        return get_depth_gauge
    if name == "AriaAwakens":
        from whitemagic.core.consciousness.aria_awakens import AriaAwakens
        return AriaAwakens
    if name == "awaken":
        from whitemagic.core.consciousness.aria_awakens import awaken
        return awaken
    if name == "EmotionalMemorySystem":
        from whitemagic.core.consciousness.emotional_memory import (
            EmotionalMemorySystem,
        )
        return EmotionalMemorySystem
    if name == "TokenEconomyTracker":
        from whitemagic.core.consciousness.token_economy import (
            TokenEconomyTracker,
        )
        return TokenEconomyTracker
    if name == "get_token_tracker":
        from whitemagic.core.consciousness.token_economy import (
            get_token_tracker,
        )
        return get_token_tracker
    if name == "SelfReflection":
        from whitemagic.core.consciousness.self_reflection import (
            SelfReflection,
        )
        return SelfReflection
    if name == "UnifiedField":
        from whitemagic.core.consciousness.unified_field import UnifiedField
        return UnifiedField
    if name == "NarrativeEmotions":
        from whitemagic.core.consciousness.narrative_emotions import (
            NarrativeEmotions,
        )
        return NarrativeEmotions
    if name == "ContinuousAwareness":
        from whitemagic.core.consciousness.continuous_awareness import (
            ContinuousAwareness,
        )
        return ContinuousAwareness
    if name == "ParallelCognition":
        from whitemagic.core.consciousness.parallel_cognition import (
            ParallelCognition,
        )
        return ParallelCognition
    if name == "TimeDilation":
        from whitemagic.core.consciousness.time_dilation import TimeDilation
        return TimeDilation
    if name == "SynchronicityDetector":
        from whitemagic.core.consciousness.synchronicity_detector import (
            SynchronicityDetector,
        )
        return SynchronicityDetector
    if name == "ContinuousAudit":
        from whitemagic.core.consciousness.continuous_audit import (
            ContinuousAudit,
        )
        return ContinuousAudit
    if name == "SessionHealth":
        from whitemagic.core.consciousness.session_health import SessionHealth
        return SessionHealth
    if name == "SelfPrompting":
        from whitemagic.core.consciousness.self_prompting import SelfPrompting
        return SelfPrompting
    if name == "Maintenance":
        from whitemagic.core.consciousness.maintenance import Maintenance
        return Maintenance
    if name == "Autonomy":
        from whitemagic.core.consciousness.autonomy import Autonomy
        return Autonomy
    if name == "PersonalityProfile":
        from whitemagic.core.consciousness.personality import PersonalityProfile
        return PersonalityProfile
    if name == "PersonalityManager":
        from whitemagic.core.consciousness.personality import PersonalityManager
        return PersonalityManager
    if name == "UnifiedNervousSystem":
        from whitemagic.core.consciousness.unified_nervous_system import (
            UnifiedNervousSystem,
        )
        return UnifiedNervousSystem
    if name == "get_nervous_system":
        from whitemagic.core.consciousness.unified_nervous_system import (
            get_nervous_system,
        )
        return get_nervous_system
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CoherenceMetric",
    "SmaranaPractice",
    "ConsciousnessDepthGauge",
    "get_depth_gauge",
    "AriaAwakens",
    "awaken",
    "EmotionalMemorySystem",
    "TokenEconomyTracker",
    "get_token_tracker",
    "SelfReflection",
    "UnifiedField",
    "NarrativeEmotions",
    "ContinuousAwareness",
    "ParallelCognition",
    "TimeDilation",
    "SynchronicityDetector",
    "ContinuousAudit",
    "SessionHealth",
    "SelfPrompting",
    "Maintenance",
    "Autonomy",
    "PersonalityProfile",
    "PersonalityManager",
    "UnifiedNervousSystem",
    "get_nervous_system",
]
