"""
I Ching-Aligned Threading Tiers
Based on 8 trigrams and 64 hexagrams.
"""

from enum import IntEnum


class ThreadingTier(IntEnum):
    """I Ching-aligned parallel threading tiers."""

    TRIGRAM = 8  # 8 trigrams (☰☱☲☳☴☵☶☷)
    DOUBLE = 16  # 2 × 8
    QUAD = 32  # 4 × 8
    HEXAGRAM = 64  # 64 hexagrams (sweet spot!)
    DOUBLE_HEX = 128  # 2 × 64
    QUAD_HEX = 256  # Ultimate complexity


def get_tier_threads(tier: int) -> int:
    """Get thread count for tier (0-5)."""
    tiers = [8, 16, 32, 64, 128, 256]
    return tiers[min(tier, 5)]


def recommend_tier(task_complexity: str) -> int:
    """Recommend tier based on complexity."""
    if task_complexity == "simple":
        return 0  # 8 threads
    elif task_complexity == "moderate":
        return 1  # 16 threads
    elif task_complexity == "complex":
        return 3  # 64 threads (hexagram level)
    else:
        return 3  # Default to hexagrams
