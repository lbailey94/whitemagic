"""I Ching wisdom engine — re-exports from core.intelligence.wisdom.i_ching.

This file previously contained a duplicate implementation. It now delegates
to the canonical version in core/intelligence/wisdom/i_ching.py which has
better logging and error handling.
"""

from whitemagic.core.intelligence.wisdom.i_ching import (
    Hexagram,
    IChingAdvisor,
    get_i_ching,
)

__all__ = ["Hexagram", "IChingAdvisor", "get_i_ching"]
