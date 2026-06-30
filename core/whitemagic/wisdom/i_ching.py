# ruff: noqa: F401
"""I Ching System — Shim module.

Re-exports from the canonical implementation in
whitemagic.core.intelligence.wisdom.i_ching which has all 64 hexagrams,
Rust acceleration, Gan Ying integration, and reading logs.

Consolidated in v23.3.2: the simple 12-hexagram version was replaced
by the complete 64-hexagram implementation.
"""

from __future__ import annotations

from whitemagic.core.intelligence.wisdom.i_ching import (
    Hexagram,
    IChingAdvisor as IChingSystem,
    get_i_ching,
)

__all__ = ["Hexagram", "IChingSystem", "get_i_ching"]
