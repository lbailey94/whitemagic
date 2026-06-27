# ruff: noqa: BLE001
"""Wisdom — Top-level wisdom system with Wu Xing, I Ching, and auto-ingestion."""

from __future__ import annotations

from .auto_ingester import WisdomAutoIngester, get_ingester
from .i_ching import IChingSystem, get_i_ching
from .i_ching_advisor import IChingAdvisor, get_advisor
from .wu_xing import WuXingSystem, get_wu_xing

__all__ = [
    "WuXingSystem",
    "get_wu_xing",
    "IChingSystem",
    "get_i_ching",
    "IChingAdvisor",
    "get_advisor",
    "WisdomAutoIngester",
    "get_ingester",
]
