# ruff: noqa: BLE001
"""
Homeostasis System — Self-balancing memory management.

Inspired by biological homeostasis: monitors metrics and applies
corrective feedback to maintain optimal equilibrium.
"""

from __future__ import annotations

from .equilibrium import EquilibriumDetector, get_equilibrium
from .feedback import FeedbackLoop, get_feedback
from .metrics import HomeostasisMetrics, get_metrics

__all__ = [
    "HomeostasisMetrics",
    "get_metrics",
    "FeedbackLoop",
    "get_feedback",
    "EquilibriumDetector",
    "get_equilibrium",
]
