# ruff: noqa: BLE001
"""Holographic Encoder Bridge (Python-only since v23.2).
=========================================================

Previously bridged to Mojo for 4D coordinate encoding.
Now uses the Python CoordinateEncoder directly.

Kept as a thin wrapper for backward compat with engine.py imports.
"""

import logging
from typing import Any

from whitemagic.core.intelligence.hologram.encoder import (
    CoordinateEncoder as PythonEncoder,
)
from whitemagic.core.intelligence.hologram.encoder import HolographicCoordinate

logger = logging.getLogger(__name__)


class EncoderBridge:
    """Encoder bridge — Python CoordinateEncoder (Mojo removed in v23.2)."""

    def __init__(self) -> None:
        self.python_fallback = PythonEncoder()

    def encode(self, memory: dict[str, Any]) -> HolographicCoordinate:
        """Encode memory using Python CoordinateEncoder."""
        return self.python_fallback.encode(memory)


# Backward compat alias
MojoEncoderBridge = EncoderBridge


def get_encoder() -> Any:
    """Singleton getter for the encoder bridge."""
    global _encoder_bridge
    if "_encoder_bridge" not in globals():
        globals()["_encoder_bridge"] = EncoderBridge()
    return globals()["_encoder_bridge"]


# Backward compat alias
get_mojo_encoder = get_encoder
