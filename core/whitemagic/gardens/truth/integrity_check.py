# ruff: noqa: BLE001
"""Integrity Check — Verify alignment between words and actions."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class IntegrityCheck:
    """Checks integrity by comparing words to actions."""

    def __init__(self) -> None:
        self._commitments: list[dict[str, Any]] = []

    def commit(self, words: str) -> None:
        """Record a commitment."""
        self._commitments.append({"words": words, "fulfilled": False})

    def fulfill(self, idx: int) -> bool:
        """Mark a commitment as fulfilled."""
        if 0 <= idx < len(self._commitments):
            self._commitments[idx]["fulfilled"] = True
            return True
        return False

    def integrity_score(self) -> float:
        """Calculate integrity score (0-1)."""
        if not self._commitments:
            return 1.0
        fulfilled = sum(1 for c in self._commitments if c["fulfilled"])
        return fulfilled / len(self._commitments)

    def summary(self) -> dict[str, Any]:
        return {
            "total_commitments": len(self._commitments),
            "fulfilled": sum(1 for c in self._commitments if c["fulfilled"]),
            "integrity_score": round(self.integrity_score(), 3),
        }
