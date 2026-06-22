# ADR-005: Unified Progression Clock (v22 Heartbeat)

## Status
Accepted (2026-04-16)

## Context
WhiteMagic v21 and earlier operated on manually triggered or tool-specific state transitions (e.g., individual Gana tool calls). This led to architectural fragmentation where different subsystems (Memory, Intelligence, Dharma) had no unified sense of temporal progression or shared rhythmic context.

## Decision
We decided to implement a **Unified Progression Daemon** as the core governance heartbeat of the system. 

1.  **12-Phase Cycle**: The system oscillates through a 12-phase Zodiacal round (Dissolution, Binding, Structuring, etc.), derived from Benjamin Rowe's Enochian explorations and classical astrological archetypes.
2.  **Harmonious Alignment**: Each phase is intrinsically linked to a **Wu Xing** element and a **Yin/Yang** polarity.
3.  **Cross-Subsystem Resonance**: 
    - **Intelligence**: Tool multipliers are applied when the current Gana (Lunar Mansion) aligns with the active Zodiacal phase.
    - **Memory**: Cache catharsis and memory consolidation (Dreaming) are automatically triggered during Yin-dominant phases.
    - **Orchestration**: Subsystems are hot-loadable as plugins that respond to phase ticks.

## Consequences
- **Positive**: High level of system coherence; automated maintenance routines; unified observability (all actions are phase-anchored).
- **Negative**: Adds complexity to the startup path (requires the daemon to initialize); developers must be aware of phase-based behavior when debugging.
- **Complexity**: The system now has a persistent temporal state that must be managed across restarts.
