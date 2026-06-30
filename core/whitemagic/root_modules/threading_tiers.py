# ruff: noqa: BLE001
"""
I Ching-Aligned Threading Tiers.

Based on 8 trigrams and 64 hexagrams.
"""

from __future__ import annotations

from enum import IntEnum


class ThreadingTier(IntEnum):
    """Threading tiers aligned with I Ching trigrams."""

    QIAN = 1  # Heaven — single thread, max focus
    KUN = 2  # Earth — dual thread, balanced
    ZHEN = 4  # Thunder — 4 threads, rapid
    KAN = 8  # Water — 8 threads, flowing
    GEN = 16  # Mountain — 16 threads, heavy
    XUN = 32  # Wind — 32 threads, distributed
    LI = 64  # Fire — 64 threads, max parallel
    DUI = 128  # Lake — 128 threads, extreme


TIER_NAMES: dict[ThreadingTier, str] = {
    ThreadingTier.QIAN: "Heaven (focused single-thread)",
    ThreadingTier.KUN: "Earth (balanced dual-thread)",
    ThreadingTier.ZHEN: "Thunder (rapid 4-thread)",
    ThreadingTier.KAN: "Water (flowing 8-thread)",
    ThreadingTier.GEN: "Mountain (heavy 16-thread)",
    ThreadingTier.XUN: "Wind (distributed 32-thread)",
    ThreadingTier.LI: "Fire (max parallel 64-thread)",
    ThreadingTier.DUI: "Lake (extreme 128-thread)",
}


def recommend_tier(task_complexity: int, io_bound: bool = False) -> ThreadingTier:
    """Recommend a threading tier based on task complexity."""
    if io_bound:
        return ThreadingTier.KAN if task_complexity < 5 else ThreadingTier.LI
    if task_complexity <= 1:
        return ThreadingTier.QIAN
    elif task_complexity <= 2:
        return ThreadingTier.KUN
    elif task_complexity <= 4:
        return ThreadingTier.ZHEN
    elif task_complexity <= 8:
        return ThreadingTier.KAN
    elif task_complexity <= 16:
        return ThreadingTier.GEN
    elif task_complexity <= 32:
        return ThreadingTier.XUN
    else:
        return ThreadingTier.LI
