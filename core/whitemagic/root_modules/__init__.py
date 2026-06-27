# ruff: noqa: BLE001
"""
Root Modules — Recovered root-level Windsurf modules.

These modules were at the root of the Windsurf-era codebase and have been
adapted for v23. They provide standalone functionality that doesn't fit
neatly into existing v23 packages.
"""

from __future__ import annotations

from .backup_system import BackupSystem, get_backup_system
from .comprehensive_review import ComprehensiveReview, run_review
from .concept_map import ConceptMap, get_concept_map
from .delta_tracking import DeltaTracker, get_delta_tracker
from .lazy_memory_loader import LazyMemoryLoader, get_lazy_loader
from .lifecycle import MemoryLifecycle, calculate_importance_score
from .pattern_discovery_enhanced import EnhancedPatternDiscovery, get_enhanced_discovery
from .session_templates import SessionTemplates, get_session_templates
from .session_types import SessionType, detect_session_type
from .symbolic import SymbolicEngine, get_symbolic_engine
from .symbolic_memory import SymbolicMemory, get_symbolic_memory
from .threading_tiers import ThreadingTier
from .workflow_patterns import WorkflowPatterns, get_workflow_patterns
from .workspace_loader import WorkspaceLoader, get_workspace_loader
from .yin_synthesis import YinSynthesis, get_yin_synthesis

__all__ = [
    "SessionType",
    "detect_session_type",
    "DeltaTracker",
    "get_delta_tracker",
    "SymbolicEngine",
    "get_symbolic_engine",
    "WorkflowPatterns",
    "get_workflow_patterns",
    "ConceptMap",
    "get_concept_map",
    "SymbolicMemory",
    "get_symbolic_memory",
    "LazyMemoryLoader",
    "get_lazy_loader",
    "SessionTemplates",
    "get_session_templates",
    "ComprehensiveReview",
    "run_review",
    "WorkspaceLoader",
    "get_workspace_loader",
    "BackupSystem",
    "get_backup_system",
    "MemoryLifecycle",
    "calculate_importance_score",
    "ThreadingTier",
    "EnhancedPatternDiscovery",
    "get_enhanced_discovery",
    "YinSynthesis",
    "get_yin_synthesis",
]
