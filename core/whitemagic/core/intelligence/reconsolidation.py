# ruff: noqa: BLE001
"""Memory Reconsolidation — Backward-compat shim.

Fused into ConsolidationEngine (slot 1, Neck 亢) as of v23.1.
All reconsolidation logic now lives in whitemagic.core.memory.consolidation.

This module re-exports the fused classes and functions for backward
compatibility with existing imports.
"""

from __future__ import annotations

from whitemagic.core.memory.consolidation import (
    DEFAULT_LABILE_WINDOW,
    MAX_LABILE,
    LabileMemory,
    MemoryConsolidator as ReconsolidationEngine,
    get_consolidator as get_reconsolidation_engine,
)

# Backward-compat alias (some code references MemoryReconsolidator)
MemoryReconsolidator = ReconsolidationEngine

__all__ = [
    "DEFAULT_LABILE_WINDOW",
    "MAX_LABILE",
    "LabileMemory",
    "ReconsolidationEngine",
    "MemoryReconsolidator",
    "get_reconsolidation_engine",
]
