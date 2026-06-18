"""
Auto-Prompting Supervisor (G004)
================================

The "Supervisor Loop" that handles routine managerial prompts automatically.
Monitors agent state and triggers Standard Operating Procedures (SOPs).
"""
# ruff: noqa: BLE001

import json
import logging
from pathlib import Path
from typing import Any, cast

from whitemagic.core.intelligence.prompt_classifier import PromptClassifier
from whitemagic.core.memory.thought_galaxy import ThoughtGalaxy

logger = logging.getLogger(__name__)

class Supervisor:
    """
    Auto-prompting supervisor that triggers SOPs based on context.
    """

    def __init__(self, sop_dir: str | Path, thought_galaxy: ThoughtGalaxy | None = None):
        self.sop_dir = Path(sop_dir)
        self.classifier = PromptClassifier()
        self.thought_galaxy = thought_galaxy
        self.enabled_sops: dict[str, bool] = {}
        self.sop_cache: dict[str, dict] = {}

        self._load_sops()

    def _load_sops(self):
        """Load SOP definitions from disk."""
        if not self.sop_dir.exists():
            self.sop_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_sops()

        for f in self.sop_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                name = data.get("name")
                if name:
                    self.sop_cache[name] = data
                    # Default to enabled unless explicitly disabled
                    self.enabled_sops[name] = data.get("enabled_by_default", True)
            except Exception as e:
                logger.error(f"Failed to load SOP {f}: {e}")

    def _create_default_sops(self):
        """Create default SOPs if none exist."""
        defaults = [
            {
                "name": "review_code",
                "trigger": "file_change",
                "condition": "changes_count > 0",
                "prompt_template": "Review the changes in {files}. Look for bugs, security issues, and style violations.",
                "enabled_by_default": True
            },
            {
                "name": "session_handoff",
                "trigger": "session_end",
                "condition": "always",
                "prompt_template": "Generate a session handoff summary including accomplished tasks, open loops, and next steps.",
                "enabled_by_default": True
            }
        ]
        for d in defaults:
            p = self.sop_dir / f"{d['name']}.json"
            p.write_text(json.dumps(d, indent=2))

    def suggest_sop(self, context: dict[str, Any]) -> list[str]:
        """
        Suggest SOPs to run based on current context.
        Returns list of SOP names.
        """
        suggestions = []
        trigger = context.get("trigger")

        for name, sop in self.sop_cache.items():
            if not self.enabled_sops.get(name, False):
                continue

            if sop.get("trigger") == trigger:
                # Evaluate condition (simple implementation for now)
                # In a real system, this would be a safer eval or rule engine
                suggestions.append(name)

        return suggestions

    def get_sop_prompt(self, sop_name: str, context: dict[str, Any]) -> str | None:
        """Render the prompt for a specific SOP."""
        sop = self.sop_cache.get(sop_name)
        if not sop:
            return None

        template = sop.get("prompt_template", "")
        try:
            return cast(str, template.format(**context))
        except KeyError:
            return cast(str, template)  # Fallback

    def toggle_sop(self, sop_name: str, enabled: bool):
        """Enable or disable an SOP."""
        if sop_name in self.sop_cache:
            self.enabled_sops[sop_name] = enabled

    def status(self) -> dict[str, Any]:
        """Return supervisor status."""
        return {
            "sops_loaded": len(self.sop_cache),
            "sops_enabled": sum(1 for v in self.enabled_sops.values() if v),
            "sop_list": [
                {"name": k, "enabled": self.enabled_sops.get(k, False)}
                for k in self.sop_cache
            ]
        }
