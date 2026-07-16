"""Hexagram cognitive state machine — 64-state I Ching state tracker.

Each cognitive state is a combination of a lower trigram (inner state)
and an upper trigram (outer action). The 8 trigrams map to 8 cognitive
functions in the 8-Trigram Vectorization architecture:

    ☰ Qián  (Heaven)  → draft generation
    ☳ Zhèn  (Thunder) → event detection
    ☲ Lí    (Fire)    → verify model
    ☴ Xùn   (Wind)    → tool routing
    ☵ Kǎn   (Water)   → dream cycle
    ☶ Gèn   (Mountain)→ heartbeat / stillness
    ☷ Kūn   (Earth)   → memory store
    ☱ Duì   (Lake)    → output formatting

The 64 hexagrams (8 × 8 combinations) represent all possible cognitive
states. Transitions between states are logged for auditability and
fed to the Wu Xing phase controller for thermal management.

Usage::

    from whitemagic.core.consciousness.hexagram_state import HexagramState

    state = HexagramState()
    state.transition(new_lower="Qian", new_upper="Li", reason="speculative decode start")
    print(state.king_wen_number)  # e.g., 14
    print(state.get_active_functions())  # {"draft", "verify"}
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

# Trigram → 3-bit mapping (must match hexagram_vectors.py)
TRIGRAM_BITS: dict[str, int] = {
    "Qian": 0b111,
    "Kun": 0b000,
    "Zhen": 0b001,
    "Xun": 0b110,
    "Kan": 0b010,
    "Li": 0b101,
    "Gen": 0b100,
    "Dui": 0b011,
}

# Trigram → cognitive function mapping
TRIGRAM_FUNCTION: dict[str, str] = {
    "Qian": "draft",
    "Zhen": "event",
    "Li": "verify",
    "Xun": "route",
    "Kan": "dream",
    "Gen": "heartbeat",
    "Kun": "memory",
    "Dui": "output",
}

# Trigram → Wu Xing element mapping
TRIGRAM_ELEMENT: dict[str, str] = {
    "Qian": "fire",
    "Zhen": "wood",
    "Li": "fire",
    "Xun": "wood",
    "Kan": "water",
    "Gen": "earth",
    "Kun": "earth",
    "Dui": "metal",
}

# Trigram → core ID mapping
TRIGRAM_CORE: dict[str, int] = {
    "Qian": 0,
    "Zhen": 0,
    "Li": 1,
    "Xun": 1,
    "Kan": 2,
    "Gen": 2,
    "Kun": 3,
    "Dui": 3,
}

# King Wen → binary lookup (must match hexagram_vectors.py _KING_WEN_TO_BINARY)
_KING_WEN_TO_BINARY: list[int] = [
     2, 24,  7, 19, 15, 36, 46, 11,
    16, 51, 40, 54, 62, 55, 32, 34,
     8,  3, 29, 60, 39, 63, 48,  5,
    45, 17, 47, 58, 31, 49, 28, 43,
    23, 27,  4, 41, 52, 22, 18, 26,
    35, 21, 64, 38, 56, 30, 50, 14,
    20, 42, 59, 61, 53, 37, 57,  9,
    12, 25,  6, 10, 33, 13, 44,  1,
]

# Reverse lookup: binary (0-63) → King Wen number (1-64)
_BINARY_TO_KING_WEN: dict[int, int] = {
    binary: kw for binary, kw in enumerate(_KING_WEN_TO_BINARY)
}

# King Wen number → hexagram name (abbreviated, for logging)
_KING_WEN_NAMES: dict[int, str] = {
    1: "Qián", 2: "Kūn", 3: "Zhūn", 4: "Méng", 5: "Xū", 6: "Sòng",
    7: "Shī", 8: "Bǐ", 9: "Xiǎo Chù", 10: "Lǚ", 11: "Tài", 12: "Pǐ",
    13: "Tóng Rén", 14: "Dà Yǒu", 15: "Qiān", 16: "Yù", 17: "Suí",
    18: "Gū", 19: "Lín", 20: "Guān", 21: "Shì Hé", 22: "Bì", 23: "Bō",
    24: "Fù", 25: "Wú Wàng", 26: "Dà Chù", 27: "Yí", 28: "Dà Guò",
    29: "Kǎn", 30: "Lí", 31: "Xián", 32: "Héng", 33: "Dùn", 34: "Dà Zhuàng",
    35: "Jìn", 36: "Míng Yí", 37: "Jiā Rén", 38: "Kuí", 39: "Jiǎn",
    40: "Xiè", 41: "Sǔn", 42: "Yì", 43: "Guài", 44: "Gòu", 45: "Cuì",
    46: "Shēng", 47: "Kùn", 48: "Jǐng", 49: "Gé", 50: "Dǐng", 51: "Zhèn",
    52: "Gèn", 53: "Jiàn", 54: "Guī Mèi", 55: "Fēng", 56: "Lǚ",
    57: "Xùn", 58: "Duì", 59: "Huàn", 60: "Jié", 61: "Zhōng Fú",
    62: "Xiǎo Guò", 63: "Jì Jì", 64: "Wèi Jì",
}


class HexagramState:
    """64-state cognitive state machine based on I Ching hexagrams.

    Each hexagram is a combination of a lower trigram (inner state)
    and an upper trigram (outer action). State transitions are logged
    and auditable.

    The lower trigram represents the system's internal disposition
    (what it is "feeling"), while the upper trigram represents the
    active external function (what it is "doing").

    Attributes:
        lower: Current lower trigram name (inner state).
        upper: Current upper trigram name (outer action).
    """

    def __init__(self) -> None:
        self._lower: str = "Kun"
        self._upper: str = "Gen"
        self._history: deque[dict[str, Any]] = deque(maxlen=256)
        self._transition_count: int = 0
        self._lock: threading.RLock()
        self._lock = threading.RLock()
        self._creation_time: float = time.time()
        logger.info(
            "HexagramState initialized: %s (King Wen %d)",
            self.hexagram_name,
            self.king_wen_number,
        )

    @property
    def lower(self) -> str:
        """Current lower trigram (inner state)."""
        return self._lower

    @property
    def upper(self) -> str:
        """Current upper trigram (outer action)."""
        return self._upper

    @property
    def king_wen_number(self) -> int:
        """Current hexagram as King Wen number (1-64)."""
        lower_bits = TRIGRAM_BITS[self._lower]
        upper_bits = TRIGRAM_BITS[self._upper]
        binary = (upper_bits << 3) | lower_bits
        return _BINARY_TO_KING_WEN[binary]

    @property
    def hexagram_name(self) -> str:
        """Name of the current hexagram."""
        return _KING_WEN_NAMES.get(self.king_wen_number, f"Hexagram {self.king_wen_number}")

    @property
    def transition_count(self) -> int:
        """Total number of state transitions since creation."""
        return self._transition_count

    def transition(
        self,
        new_lower: str | None = None,
        new_upper: str | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """Transition to a new hexagram state.

        Args:
            new_lower: New lower trigram name. None = keep current.
            new_upper: New upper trigram name. None = keep current.
            reason: Human-readable reason for the transition.

        Returns:
            Transition record dict with from/to hexagram info, timestamp, reason.

        Raises:
            ValueError: If trigram name is not one of the 8 valid trigrams.
        """
        if new_lower is not None and new_lower not in TRIGRAM_BITS:
            raise ValueError(
                f"Invalid trigram '{new_lower}'. Must be one of: {list(TRIGRAM_BITS)}"
            )
        if new_upper is not None and new_upper not in TRIGRAM_BITS:
            raise ValueError(
                f"Invalid trigram '{new_upper}'. Must be one of: {list(TRIGRAM_BITS)}"
            )

        with self._lock:
            old_lower = self._lower
            old_upper = self._upper
            old_kw = self.king_wen_number

            if new_lower is not None:
                self._lower = new_lower
            if new_upper is not None:
                self._upper = new_upper

            new_kw = self.king_wen_number
            self._transition_count += 1

            record: dict[str, Any] = {
                "transition_id": self._transition_count,
                "timestamp": time.time(),
                "from_lower": old_lower,
                "from_upper": old_upper,
                "to_lower": self._lower,
                "to_upper": self._upper,
                "from_king_wen": old_kw,
                "to_king_wen": new_kw,
                "from_name": _KING_WEN_NAMES.get(old_kw, f"Hexagram {old_kw}"),
                "to_name": _KING_WEN_NAMES.get(new_kw, f"Hexagram {new_kw}"),
                "reason": reason,
            }
            self._history.append(record)

            if old_kw != new_kw:
                logger.info(
                    "Hexagram transition: %s (%d) → %s (%d) — %s",
                    record["from_name"],
                    old_kw,
                    record["to_name"],
                    new_kw,
                    reason,
                )

        return record

    def get_active_functions(self) -> set[str]:
        """Return the cognitive functions active in the current state.

        Both the lower and upper trigram map to a cognitive function.
        The returned set contains both (they may overlap if both
        trigrams map to the same function).
        """
        return {
            TRIGRAM_FUNCTION[self._lower],
            TRIGRAM_FUNCTION[self._upper],
        }

    def get_active_elements(self) -> set[str]:
        """Return the Wu Xing elements associated with the current state."""
        return {
            TRIGRAM_ELEMENT[self._lower],
            TRIGRAM_ELEMENT[self._upper],
        }

    def get_active_cores(self) -> set[int]:
        """Return the CPU core IDs associated with the current state."""
        return {
            TRIGRAM_CORE[self._lower],
            TRIGRAM_CORE[self._upper],
        }

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent state transitions for auditing.

        Args:
            limit: Maximum number of transitions to return (most recent first).

        Returns:
            List of transition records, most recent first.
        """
        with self._lock:
            history = list(self._history)
        history.reverse()
        return history[:limit]

    def get_state_vector(self) -> list[float]:
        """Get the HRR vector for the current hexagram.

        Uses HexagramVectors singleton for the 64-dimensional HRR
        representation of the current hexagram.

        Returns:
            64-dimensional unit-normalized float vector.
        """
        from whitemagic.core.intelligence.hexagram_vectors import get_hexagram_vectors

        hv = get_hexagram_vectors()
        return hv.get_vector(self.king_wen_number)

    def get_status(self) -> dict[str, Any]:
        """Return a comprehensive status dict for monitoring."""
        return {
            "lower_trigram": self._lower,
            "upper_trigram": self._upper,
            "king_wen_number": self.king_wen_number,
            "hexagram_name": self.hexagram_name,
            "active_functions": list(self.get_active_functions()),
            "active_elements": list(self.get_active_elements()),
            "active_cores": list(self.get_active_cores()),
            "transition_count": self._transition_count,
            "uptime_seconds": time.time() - self._creation_time,
        }

    def reset(self, reason: str = "reset") -> None:
        """Reset to the default state (Kun/Gen = Earth/Mountain = receptivity/stillness)."""
        self.transition(new_lower="Kun", new_upper="Gen", reason=reason)


# ── Singleton ─────────────────────────────────────────────────────────

_instance: HexagramState | None = None
_instance_lock = threading.Lock()


def get_hexagram_state() -> HexagramState:
    """Get the singleton HexagramState instance."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = HexagramState()
    return _instance
