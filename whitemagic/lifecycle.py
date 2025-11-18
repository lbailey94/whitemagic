"""Smart memory lifecycle management (Priority 4)."""

from datetime import datetime
from typing import Dict, List


def calculate_importance_score(entry: Dict) -> int:
    """Calculate importance score (0-100)."""
    score = 50  # baseline

    # Frequency: More tags = more important
    score += min(len(entry.get("tags", [])) * 5, 20)

    # Recency: Recently accessed
    if entry.get("last_accessed"):
        days = (datetime.now() - datetime.fromisoformat(entry["last_accessed"])).days
        if days < 7:
            score += 20
        elif days < 30:
            score += 10

    # Relationships
    if entry.get("related_to"):
        score += min(len(entry["related_to"]) * 10, 30)

    return min(score, 100)


def should_promote(entry: Dict, threshold: int = 70) -> bool:
    """Check if short-term memory should be promoted to long-term."""
    if entry["type"] != "short_term":
        return False

    return calculate_importance_score(entry) >= threshold


def get_promotion_candidates(manager) -> List[Dict]:
    """Get short-term memories that should be promoted."""
    candidates = []
    for entry in manager._entries("short_term", include_archived=False):
        if should_promote(entry):
            candidates.append(entry)
    return candidates
