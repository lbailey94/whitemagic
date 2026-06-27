# ruff: noqa: BLE001
"""Smart memory lifecycle management."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def calculate_importance_score(entry: dict[str, Any]) -> int:
    """Calculate importance score (0-100)."""
    score = 50  # baseline

    # Recency bonus
    created = entry.get("created")
    if created:
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created)
            except ValueError:
                created = None
        if isinstance(created, datetime):
            days_old = (datetime.now() - created).days
            if days_old < 1:
                score += 20
            elif days_old < 7:
                score += 10
            elif days_old > 180:
                score -= 30
            elif days_old > 90:
                score -= 20

    # Access frequency
    access_count = entry.get("access_count", 0)
    score += min(access_count * 5, 20)

    # Tagged bonus
    tags = entry.get("tags", [])
    if tags:
        score += min(len(tags) * 2, 10)

    return max(0, min(100, score))


class MemoryLifecycle:
    """Manages memory lifecycle: creation, retention, decay."""

    def __init__(self) -> None:
        self.retention_days = 90
        self.decay_threshold = 30

    def should_retain(self, entry: dict[str, Any]) -> bool:
        """Determine if a memory should be retained."""
        score = calculate_importance_score(entry)
        return score >= self.decay_threshold

    def should_archive(self, entry: dict[str, Any]) -> bool:
        """Determine if a memory should be archived."""
        score = calculate_importance_score(entry)
        return score < self.decay_threshold and score > 10

    def should_delete(self, entry: dict[str, Any]) -> bool:
        """Determine if a memory should be deleted."""
        score = calculate_importance_score(entry)
        return score <= 10

    def summary(self) -> dict[str, Any]:
        return {
            "retention_days": self.retention_days,
            "decay_threshold": self.decay_threshold,
        }
