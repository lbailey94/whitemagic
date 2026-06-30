# ruff: noqa: BLE001
"""
Token Optimizer — Shim re-exporting canonical implementation.

Canonical implementation: whitemagic.core.intelligence.agentic.token_optimizer
"""

from __future__ import annotations

from whitemagic.core.intelligence.agentic.token_optimizer import (
    CachedResult as CachedQuery,
)
from whitemagic.core.intelligence.agentic.token_optimizer import (
    ContextCompressor,
    QueryCache,
    TokenBudget,
    TokenOptimizer,
    get_token_optimizer,
    optimize_for_ai,
)

__all__ = [
    "CachedQuery",
    "ContextCompressor",
    "QueryCache",
    "TokenBudget",
    "TokenOptimizer",
    "get_token_optimizer",
    "optimize_for_ai",
]
