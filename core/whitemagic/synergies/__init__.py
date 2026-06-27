# ruff: noqa: BLE001
"""Synergies — Cross-system bridges that connect subsystems."""

from __future__ import annotations

from .cli_suggestion_learner import CLISuggestionLearner, get_suggestion_learner
from .pattern_dream_bridge import PatternDreamBridge, get_pattern_dream_bridge
from .security_homeostasis_link import SecurityHomeostasisLink, get_security_link

__all__ = [
    "PatternDreamBridge",
    "get_pattern_dream_bridge",
    "SecurityHomeostasisLink",
    "get_security_link",
    "CLISuggestionLearner",
    "get_suggestion_learner",
]
