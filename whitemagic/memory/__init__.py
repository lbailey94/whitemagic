"""
WhiteMagic Memory system for WhiteMagic.

Provides hierarchical memory management:
- Short-term: Scratchpad, active context
- Long-term: Consolidated learnings
- Meta: Extracted patterns
- Evolution: Self-improvement proposals
"""

from .auto_capture import (
    Action,
    ShortTermMemory,
    MemoryCapture,
    get_capture,
)

from .pattern_engine import (
    Pattern,
    PatternReport,
    PatternEngine,
    get_engine,
)

from .evolution import (
    EvolutionProposal,
    EvolutionReport,
    EvolutionEngine,
    get_evolution_engine,
)

__all__ = [
    "Action",
    "ShortTermMemory",
    "MemoryCapture",
    "get_capture",
    "Pattern",
    "PatternReport",
    "PatternEngine",
    "get_engine",
    "EvolutionProposal",
    "EvolutionReport",
    "EvolutionEngine",
    "get_evolution_engine",
]
