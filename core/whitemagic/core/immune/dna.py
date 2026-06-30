# ruff: noqa: BLE001
"""
DNA Layer — Immutable principles and immune regulation.

Defines WhiteMagic's core principles and prevents autoimmune conditions
where the system attacks itself. Like biological DNA, this defines
what the organism IS and cannot be changed without mutation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Principle:
    """An immutable core principle."""

    name: str
    description: str
    immutable: bool = True


class DNALayer:
    """Defines and protects core principles."""

    def __init__(self) -> None:
        self.principles: dict[str, Principle] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            Principle(
                "safety", "Never execute destructive actions without confirmation"
            ),
            Principle("transparency", "All actions must be auditable and logged"),
            Principle("graceful_degradation", "Optional features must fail safely"),
            Principle("path_hygiene", "Never write to repo, only to WM_STATE_ROOT"),
            Principle("test_guardrail", "Never skip tests"),
        ]
        for p in defaults:
            self.principles[p.name] = p

    def check_action(self, action: str, context: dict[str, Any]) -> bool:
        """Check if an action violates any core principle."""
        action_lower = action.lower()

        if "delete" in action_lower and not context.get("confirmed", False):
            logger.warning("Action '%s' violates safety principle", action)
            return False

        if "skip" in action_lower and "test" in action_lower:
            logger.warning("Action '%s' violates test_guardrail principle", action)
            return False

        return True

    def is_autoimmune(self, proposed_action: str) -> bool:
        """Check if a proposed action would attack the system itself."""
        dangerous_patterns = [
            "delete whitemagic",
            "rm -rf core",
            "drop table",
            "truncate memory",
        ]
        action_lower = proposed_action.lower()
        return any(p in action_lower for p in dangerous_patterns)

    def list_principles(self) -> list[dict[str, str]]:
        return [
            {
                "name": p.name,
                "description": p.description,
                "immutable": str(p.immutable),
            }
            for p in self.principles.values()
        ]


_dna: DNALayer | None = None


def get_dna_layer() -> DNALayer:
    global _dna
    if _dna is None:
        _dna = DNALayer()
    return _dna
