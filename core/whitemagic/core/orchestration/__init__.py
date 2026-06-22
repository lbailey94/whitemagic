"""🎭 Orchestration Module

Unified system orchestration that wires together:
- 7 Biological Subsystems (Unified Nervous System)
- 28 Ganas → 17 Gardens (Sangha, Wonder, Joy, Love, Truth, Wisdom, etc.)
- Identity Continuity (Self-Naming, Phylogenetics)
- Memory Metabolism (Reconsolidation, Narrative Compression)
- Synthesis Engine (Resonance fields, emergence detection)

This module provides the bootstrap point and public API for the unified
orchestration system.
"""

from whitemagic.core.orchestration.session_startup import (
    SessionStartupOrchestrator,
    session_status,
    start_session,
)
from whitemagic.core.orchestration.session_startup import (
    get_orchestrator as get_session_orchestrator,
)
from whitemagic.core.orchestration.unified_orchestrator import (
    OrchestrationEvent,
    SystemHealth,
    SystemState,
    UnifiedOrchestrator,
    awaken_unified_system,
    get_orchestrator,
    get_system_health,
)
from whitemagic.core.orchestration.zodiacal_procession import (
    ZodiacalProcession,
    ZodiacCore,
    ZodiacSign,
    get_procession,
)

__all__ = [
    # Session startup
    "start_session",
    "session_status",
    "get_session_orchestrator",
    "SessionStartupOrchestrator",
    # Unified orchestration
    "get_orchestrator",
    "awaken_unified_system",
    "get_system_health",
    "UnifiedOrchestrator",
    "SystemState",
    "SystemHealth",
    "OrchestrationEvent",
    # Zodiacal procession
    "ZodiacalProcession",
    "ZodiacSign",
    "ZodiacCore",
    "get_procession",
]
