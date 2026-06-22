"""CodeGenome Template Engine — YAML-driven code template library with lineage tracking.

Forked from PromptEngine to support the Vibe Coding God-Kit.
Loads code templates from $WM_STATE_ROOT/codegenome/ and built-in defaults.
Supports variable substitution, tiered variant selection, dependency tracking, and lineage.
"""

from .engine import CodeGenomeEngine, CodeTemplate, get_codegenome_engine
from .vault import GeneseedVault, get_geneseed_vault
from .vibe_parser import VibeParser, get_vibe_parser

__all__ = [
    "CodeGenomeEngine",
    "CodeTemplate",
    "get_codegenome_engine",
    "VibeParser",
    "get_vibe_parser",
    "GeneseedVault",
    "get_geneseed_vault",
]
