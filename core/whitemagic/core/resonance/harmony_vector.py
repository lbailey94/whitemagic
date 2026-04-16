"""Harmony Vector — Redirect to whitemagic.harmony.vector.

This module was incorrectly placed in resonance. The correct location is
whitemagic.harmony.vector.
"""

import warnings

from whitemagic.harmony.vector import get_harmony_vector

warnings.warn(
    "whitemagic.core.resonance.harmony_vector is deprecated. "
    "Use 'from whitemagic.harmony.vector import get_harmony_vector' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["get_harmony_vector"]
