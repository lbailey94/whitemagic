# ruff: noqa: BLE001
"""
Smart START HERE Template System — Optimized session resumption.

Provides tiered templates for session resumption:
- 30-second resume (< 1K tokens)
- 2-minute deep dive (Tier 1)
- 5-minute full context (Tier 2)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SessionTemplates:
    """Tiered session resumption templates."""

    TIER_FAST = "30s"
    TIER_MEDIUM = "2m"
    TIER_FULL = "5m"

    def __init__(self) -> None:
        self._templates: dict[str, str] = {
            self.TIER_FAST: "# Quick Resume\n## Last: {last_action}\n## Next: {next_action}\n",
            self.TIER_MEDIUM: "# Session Resume\n## Status: {status}\n## Recent: {recent}\n## Goals: {goals}\n## Files: {files}\n",
            self.TIER_FULL: "# Full Context\n## Status: {status}\n## Recent: {recent}\n## Goals: {goals}\n## Files: {files}\n## Tests: {tests}\n## Notes: {notes}\n## Decisions: {decisions}\n",
        }

    def render(self, tier: str, context: dict[str, Any]) -> str:
        """Render a template with context."""
        template = self._templates.get(tier, self._templates[self.TIER_FAST])
        return template.format(**context)

    def get_template(self, tier: str) -> str | None:
        return self._templates.get(tier)

    def add_template(self, tier: str, template: str) -> None:
        self._templates[tier] = template

    def summary(self) -> dict[str, Any]:
        return {
            "available_tiers": list(self._templates.keys()),
            "template_count": len(self._templates),
        }


_templates: SessionTemplates | None = None


def get_session_templates() -> SessionTemplates:
    global _templates
    if _templates is None:
        _templates = SessionTemplates()
    return _templates
