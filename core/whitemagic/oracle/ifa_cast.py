"""Ifa Casting System - Cowrie Shell Divination.

Simulates the traditional cowrie shell casting method (Diloggun/Ifa).
16 cowrie shells are cast; each falls open (mouth up) or closed (mouth down).
The result is divided into two legs of 8 shells each, producing two 4-bit
figures (open shells count as marks, closed as double marks).

Casting methods:
  1. Cowrie shells (16 shells, 2 hands of 8) -- primary method
  2. Opele chain (8 half-pods, single cast) -- fast method
  3. Ikin (16 sacred palm nuts, counted by subtraction) -- traditional

The binary encoding follows Ifa convention:
  - Open mouth (face up) = 0 = single mark |
  - Closed mouth (face down) = 1 = double mark ||
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from whitemagic.oracle.ifa_data import (
    OduAmulu,
    OduMeji,
    PRINCIPAL_ODU,
    get_odu_by_binary,
    ifa_to_iching,
)


@dataclass
class CastResult:
    """Result of an Ifa casting."""

    right_binary: str          # 4-bit right leg (cast first, yang/active)
    left_binary: str           # 4-bit left leg (cast second, yin/receptive)
    full_binary: str           # 8-bit combined
    decimal: int               # 0-255
    odu: OduMeji | OduAmulu    # The Odu object
    is_meji: bool              # True if principal (doubled) Odu
    iching_hexagram: int       # Corresponding I Ching hexagram (King Wen)
    casting_method: str        # "cowrie", "opele", or "ikin"
    shell_results: list[bool]  # Raw shell results (True = open/0, False = closed/1)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    question: str = ""
    context_hash: str = ""

    @property
    def odu_name(self) -> str:
        """Full name of the cast Odu."""
        if isinstance(self.odu, OduMeji):
            return self.odu.name
        return self.odu.name

    @property
    def odu_number(self) -> int:
        """Number of the cast Odu (1-256)."""
        if isinstance(self.odu, OduMeji):
            return self.odu.number
        return self.odu.number

    @property
    def wisdom(self) -> str:
        """Wisdom text for the cast Odu."""
        if isinstance(self.odu, OduMeji):
            return self.odu.wisdom
        return f"{self.odu.right_leg.wisdom} Combined with: {self.odu.left_leg.wisdom}"

    @property
    def marks(self) -> str:
        """Visual representation of the Odu marks."""
        right_marks = " ".join("||" if b == "1" else "|" for b in self.right_binary)
        left_marks = " ".join("||" if b == "1" else "|" for b in self.left_binary)
        return f"{right_marks}\n{left_marks}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "odu_name": self.odu_name,
            "odu_number": self.odu_number,
            "binary": self.full_binary,
            "decimal": self.decimal,
            "is_meji": self.is_meji,
            "iching_hexagram": self.iching_hexagram,
            "casting_method": self.casting_method,
            "right_leg": self.right_binary,
            "left_leg": self.left_binary,
            "marks": self.marks,
            "wisdom": self.wisdom,
            "meaning": self.odu.meaning if isinstance(self.odu, OduMeji) else f"{self.odu.right_leg.meaning} + {self.odu.left_leg.meaning}",
            "element": self.odu.element if isinstance(self.odu, OduMeji) else f"{self.odu.right_leg.element}/{self.odu.left_leg.element}",
            "ire": self.odu.ire if isinstance(self.odu, OduMeji) else f"{self.odu.right_leg.ire} + {self.odu.left_leg.ire}",
            "osogbo": self.odu.osogbo if isinstance(self.odu, OduMeji) else f"{self.odu.right_leg.osogbo} + {self.odu.left_leg.osogbo}",
            "prescriptions": self.odu.prescriptions if isinstance(self.odu, OduMeji) else [*self.odu.right_leg.prescriptions, *self.odu.left_leg.prescriptions],
            "prohibitions": self.odu.prohibitions if isinstance(self.odu, OduMeji) else [*self.odu.right_leg.prohibitions, *self.odu.left_leg.prohibitions],
            "timestamp": self.timestamp,
            "question": self.question,
        }


class IfaCaster:
    """Ifa divination casting system using cowrie shells.

    Supports three casting methods:
    - cowrie: 16 cowrie shells cast in two hands of 8 (primary)
    - opele: 8-pod chain cast once (fast)
    - ikin: 16 palm nuts counted by subtraction (traditional)

    The caster can be seeded for reproducibility or left to entropy.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._seed = seed
        if seed is not None:
            self.rng = random.Random(seed)
        else:
            self.rng = random.SystemRandom()
        self.history: list[CastResult] = []

    def cast_cowrie(self, question: str = "", context: dict[str, Any] | None = None) -> CastResult:
        """Cast 16 cowrie shells to produce an Odu.

        Traditional method: 16 cowrie shells are thrown. Each lands
        open (mouth up = 0) or closed (mouth down = 1). The 16 results
        are split into two legs of 8 shells each. Within each leg,
        the shells are grouped into 4 pairs, and each pair produces
        one binary digit (open pair = 0, closed pair = 1, mixed = 0).

        For simplicity and fidelity to the binary structure, we use
        8 shells per leg, each shell producing one bit directly.
        """
        # Incorporate question and context into entropy
        entropy = self._gather_entropy(question, context)

        # Cast 16 shells (8 per leg)
        shells = []
        for i in range(16):
            # Each shell has ~50% chance of open/closed, modulated by entropy
            bit = self._cast_single_shell(entropy, i)
            shells.append(bit)  # True = open (0), False = closed (1)

        # Split into two legs of 8 shells each
        # Right leg (first 8 shells) -> 4 bits (take every other shell)
        # Left leg (last 8 shells) -> 4 bits (take every other shell)
        right_shells = shells[:8]
        left_shells = shells[8:]

        # Convert 8 shells to 4 bits: pair them up
        right_binary = self._shells_to_binary(right_shells)
        left_binary = self._shells_to_binary(left_shells)

        return self._build_result(
            right_binary, left_binary, "cowrie", shells, question, context
        )

    def cast_opele(self, question: str = "", context: dict[str, Any] | None = None) -> CastResult:
        """Cast the opele chain to produce an Odu.

        The opele is a chain with 8 half-pods. When cast, each pod lands
        open (face up = 0) or closed (face down = 1). The 8 pods directly
        produce the 8 bits of the Odu (4 right + 4 left).
        """
        entropy = self._gather_entropy(question, context)

        # Cast 8 pods directly
        pods = []
        for i in range(8):
            bit = self._cast_single_shell(entropy, i)
            pods.append(bit)

        # First 4 pods = right leg, last 4 = left leg
        right_binary = self._shells_to_binary_direct(pods[:4])
        left_binary = self._shells_to_binary_direct(pods[4:])

        return self._build_result(
            right_binary, left_binary, "opele", pods, question, context
        )

    def cast_ikin(self, question: str = "", context: dict[str, Any] | None = None) -> CastResult:
        """Cast 16 sacred palm nuts (ikin Ifa) to produce an Odu.

        Traditional method: 16 ikin are grabbed in the right hand.
        If 1-2 remain, mark || (closed = 1). If 0 or 3+ remain,
        mark | (open = 0). Repeat 8 times for both legs.
        """
        results = []
        for leg in range(2):  # Two legs
            for i in range(4):  # 4 marks per leg
                # Simulate grabbing 16 nuts and counting remainder
                remainder = self.rng.randint(0, 16)
                # 1-2 remaining = closed (1), else open (0)
                is_closed = 1 <= remainder <= 2
                results.append(not is_closed)  # True = open (0)

        right_binary = self._shells_to_binary_direct(results[:4])
        left_binary = self._shells_to_binary_direct(results[4:])

        return self._build_result(
            right_binary, left_binary, "ikin", results, question, context
        )

    def cast(self, question: str = "", context: dict[str, Any] | None = None,
             method: str = "cowrie") -> CastResult:
        """Cast using the specified method.

        Args:
            question: The question being asked
            context: Additional context for the casting
            method: "cowrie", "opele", or "ikin"
        """
        if method == "opele":
            result = self.cast_opele(question, context)
        elif method == "ikin":
            result = self.cast_ikin(question, context)
        else:
            result = self.cast_cowrie(question, context)

        self.history.append(result)
        return result

    # --- Internal helpers ---

    def _gather_entropy(self, question: str, context: dict[str, Any] | None) -> bytes:
        """Gather entropy from question, context, and system state.

        Seeded mode: deterministic entropy from question+context+seed.
        Unseeded mode: harvests real system entropy via os.urandom and
        CPU timing jitter (inspired by QPP-RNG approach), combined with
        nanosecond timestamps for additional irreducibility.
        """
        import os
        ctx_str = str(context) if context else ""
        if self._seed is not None:
            combined = f"{question}|{ctx_str}|{self._seed}"
        else:
            system_entropy = os.urandom(32).hex()
            time_jitter = str(time.time_ns())
            combined = f"{question}|{ctx_str}|{system_entropy}|{time_jitter}"
        return hashlib.sha256(combined.encode()).digest()

    def _cast_single_shell(self, entropy: bytes, index: int) -> bool:
        """Cast a single shell, modulated by entropy.

        Returns True for open (0), False for closed (1).
        The entropy hash modulates each shell's probability in a range
        centered on 128 (true 50/50), with ±3% variation so the
        question/context meaningfully influences individual shells.
        """
        entropy_byte = entropy[index % len(entropy)]
        threshold = 128 + (entropy_byte % 6) - 3
        return self.rng.randint(0, 255) < threshold

    def _shells_to_binary(self, shells: list[bool]) -> str:
        """Convert 8 shell results to 4 binary digits.

        Pairs of shells: XOR logic — if shells differ, the result is
        determined by the first shell (right leg priority in Ifa).
        If both agree, use that value directly. This produces a fair
        ~50/50 distribution while preserving the pairing tradition.
        """
        bits = []
        for i in range(0, len(shells), 2):
            pair = shells[i:i + 2]
            if len(pair) == 2:
                if pair[0] == pair[1]:
                    # Both agree: use that value
                    bit = "0" if pair[0] else "1"
                else:
                    # Disagreement: first shell (right/active) decides
                    bit = "0" if pair[0] else "1"
            else:
                bit = "0" if pair[0] else "1"
            bits.append(bit)
        return "".join(bits)

    def _shells_to_binary_direct(self, shells: list[bool]) -> str:
        """Convert shell results directly to binary (1 shell = 1 bit)."""
        return "".join("0" if s else "1" for s in shells)

    def _build_result(
        self,
        right_binary: str,
        left_binary: str,
        method: str,
        shell_results: list[bool],
        question: str,
        context: dict[str, Any] | None,
    ) -> CastResult:
        """Build a CastResult from the binary legs."""
        full_binary = right_binary + left_binary
        decimal = int(full_binary, 2)
        odu = get_odu_by_binary(full_binary)
        is_meji = right_binary == left_binary
        iching_num = ifa_to_iching(right_binary, left_binary)

        ctx_str = str(context) if context else ""
        context_hash = hashlib.sha256(ctx_str.encode()).hexdigest()[:16] if ctx_str else ""

        return CastResult(
            right_binary=right_binary,
            left_binary=left_binary,
            full_binary=full_binary,
            decimal=decimal,
            odu=odu or PRINCIPAL_ODU[0],  # Fallback to Eji Ogbe
            is_meji=is_meji,
            iching_hexagram=iching_num,
            casting_method=method,
            shell_results=shell_results,
            question=question,
            context_hash=context_hash,
        )


# Singleton caster
_caster: IfaCaster | None = None


def get_caster(seed: int | None = None) -> IfaCaster:
    """Get the global Ifa caster instance."""
    global _caster
    if _caster is None:
        _caster = IfaCaster(seed=seed)
    return _caster


def cast_ifa(question: str = "", context: dict[str, Any] | None = None,
             method: str = "cowrie") -> CastResult:
    """Convenience function to cast Ifa."""
    return get_caster().cast(question=question, context=context, method=method)
