# ruff: noqa: BLE001
"""Haskell Divination Bridge — wraps the FFI-based haskell_bridge.py."""

import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("haskell_bridge")

# The FFI bridge lives at haskell/haskell_bridge.py (project root)
_HASKELL_DIR = Path(__file__).resolve().parents[3] / "haskell"

# Canonical King Wen table: binary index (0-63) → King Wen number (1-64).
# Binary: bit 0 = bottom line, bit 5 = top line. 1=Yang, 0=Yin.
# Cross-referenced with Wikibooks "I Ching/The 64 Hexagrams".
_KING_WEN_TABLE = [
    2,
    24,
    7,
    19,
    15,
    36,
    46,
    11,
    16,
    51,
    40,
    54,
    62,
    55,
    32,
    34,
    8,
    3,
    29,
    60,
    39,
    63,
    48,
    5,
    45,
    17,
    47,
    58,
    31,
    49,
    28,
    43,
    23,
    27,
    4,
    41,
    52,
    22,
    18,
    26,
    35,
    21,
    64,
    38,
    56,
    30,
    50,
    14,
    20,
    42,
    59,
    61,
    53,
    37,
    57,
    9,
    12,
    25,
    6,
    10,
    33,
    13,
    44,
    1,
]


def _binary_to_king_wen(lines: list[int]) -> int:
    """Convert 6 binary line values (0=Yin, 1=Yang) to King Wen number."""
    binary = 0
    for i, line in enumerate(lines):
        if line:
            binary |= 1 << i
    return _KING_WEN_TABLE[binary]


class HaskellBridge:
    """High-level interface to the Haskell divination library."""

    def __init__(self) -> None:
        self._divination = None
        self._available = False
        self._init()

    def _init(self) -> None:
        try:
            # Add haskell/ to path so we can import haskell_bridge
            haskell_dir = str(_HASKELL_DIR)
            if haskell_dir not in sys.path:
                sys.path.insert(0, haskell_dir)
            from haskell_bridge import (
                HaskellDivination,  # type: ignore[import-not-found]
            )

            self._divination = HaskellDivination()
            self._available = True
            logger.info("Haskell divination bridge initialized")
        except (FileNotFoundError, OSError, ImportError) as e:
            logger.warning("Haskell bridge unavailable: %s", e, exc_info=True)
            self._available = False

    @property
    def available(self) -> bool:
        """
        Perform the available operation.

        Returns:
            bool
        """
        return bool(self._available)

    def cast_hexagram(self, lines: list[int] | None = None) -> dict[str, Any]:
        """Cast a hexagram from 6 line values (0=Yin, 1=Yang).

        If lines is None, generates random lines.
        Returns dict with king_wen_number, is_balanced, lines.
        """
        if lines is None:
            import random

            lines = [random.randint(0, 1) for _ in range(6)]

        if not self._available:
            logger.warning("Haskell bridge not available, returning simulated result")
            return {
                "status": "SIMULATED",
                "lines": lines,
                "king_wen_number": _binary_to_king_wen(lines),
                "is_balanced": lines.count(0) == lines.count(1),
            }

        try:
            assert self._divination is not None
            result: dict[str, Any] = self._divination.create_and_query(lines)
            result["status"] = "OK"
            return result
        except Exception as e:
            logger.error("Haskell bridge error: %s", e, exc_info=True)
            return {
                "status": "ERROR",
                "error": str(e),
                "lines": lines,
            }

    def check_availability(self) -> bool:
        """
        Perform the check availability operation.

        Returns:
            bool
        """
        return bool(self._available)


if __name__ == "__main__":
    bridge = HaskellBridge()
    print(f"Available: {bridge.available}")
    print(bridge.cast_hexagram([1, 1, 1, 1, 1, 1]))
    print(bridge.cast_hexagram([0, 0, 0, 0, 0, 0]))
    print(bridge.cast_hexagram())  # random
