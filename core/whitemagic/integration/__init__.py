"""🔗 INTEGRATION - The Grand Unified Interface

This module provides integration utilities for connecting WhiteMagic subsystems.
Currently contains garden weaving functionality.

Usage:
    from whitemagic.integration import garden_weaver
"""

from .garden_weaver import (
    get_garden_weaver,
    weave_gardens,
)

__all__ = ["weave_gardens", "get_garden_weaver"]
