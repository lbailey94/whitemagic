# ruff: noqa: BLE001
"""
Synastry Governor — Conflict resolution through harmony.

When cores disagree, synastry finds the harmonious path.
Not compromise, but synthesis. Not averaging, but transcendence.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SynastryGovernor:
    """Resolves conflicts between zodiac cores through synastry."""

    def __init__(self) -> None:
        self.resolutions: list[dict[str, Any]] = []

    def resolve(self, core_a: str, core_b: str, issue: str) -> dict[str, Any]:
        """Resolve a conflict between two cores."""
        # Synastry logic: find the harmonious path
        complementary = {
            ("aries", "libra"),
            ("taurus", "scorpio"),
            ("gemini", "sagittarius"),
            ("cancer", "capricorn"),
            ("leo", "aquarius"),
            ("virgo", "pisces"),
        }
        pair = (core_a.lower(), core_b.lower())
        is_complementary = pair in complementary or pair[::-1] in complementary

        if is_complementary:
            resolution = (
                f"Complementary pair: {core_a} and {core_b} naturally balance. "
            )
            resolution += (
                f"Use {core_a}'s energy to address {core_b}'s concern about {issue}."
            )
            strategy = "complementary"
        else:
            resolution = (
                f"Find the higher ground between {core_a} and {core_b} on {issue}. "
            )
            resolution += (
                "Both perspectives have value — synthesize rather than compromise."
            )
            strategy = "synthesis"

        result = {
            "core_a": core_a,
            "core_b": core_b,
            "issue": issue,
            "resolution": resolution,
            "strategy": strategy,
            "is_complementary": is_complementary,
        }
        self.resolutions.append(result)
        return result

    def history(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.resolutions[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_resolutions": len(self.resolutions),
            "complementary": sum(1 for r in self.resolutions if r["is_complementary"]),
            "synthesis": sum(1 for r in self.resolutions if not r["is_complementary"]),
        }


_governor: SynastryGovernor | None = None


def get_synastry_governor() -> SynastryGovernor:
    global _governor
    if _governor is None:
        _governor = SynastryGovernor()
    return _governor
