"""Grimoire Audit — Brain Upgrade #3.
================================
Self-auditing system for tools and capabilities.
Scans grimoire/ and core/ for executable "spells".
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Spell:
    """An executable tool or script found in the grimoire or core."""

    id: str
    name: str
    path: Path
    category: str  # infrastructure, intelligence, archaeology, etc.
    is_executable: bool = True


class GrimoireAuditor:
    """Audits the system for available tools and scripts."""

    def __init__(self, project_root: Path | None = None) -> None:
        if project_root is None:
            self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        else:
            self.project_root = project_root

        self.grimoire_path = self.project_root / "grimoire"
        self.core_path = self.project_root / "whitemagic" / "core"

    def audit(self) -> list[Spell]:
        """Perform a full audit of available spells."""
        spells: list[Spell] = []

        # 1. Count actual registered MCP tools from the dispatch table
        try:
            from whitemagic.core.ports import get_dispatch_table

            for tool_name in get_dispatch_table():
                category = self._categorize_tool(tool_name)
                spells.append(
                    Spell(
                        id=f"tool_{tool_name}",
                        name=tool_name.replace("_", " ").title(),
                        path=self.project_root / "whitemagic" / "tools",
                        category=category,
                    )
                )
        except Exception as e:  # noqa: BLE001
            logger.debug("Could not load dispatch table: %s", e)

        # 2. Scan scripts/ for executable Python files
        scripts_path = self.project_root / "scripts"
        if scripts_path.exists():
            for script_path in scripts_path.iterdir():
                if script_path.is_file() and script_path.name.endswith(".py"):
                    spells.append(
                        Spell(
                            id=f"script_{script_path.stem}",
                            name=script_path.stem.replace("_", " ").title(),
                            path=script_path,
                            category="automation",
                        )
                    )

        # 3. Scan grimoire/ for spell definitions
        if self.grimoire_path.exists():
            for root, _, files in os.walk(self.grimoire_path):
                for file in files:
                    if file.endswith(".py") and file != "__init__.py":
                        spells.append(
                            Spell(
                                id=f"grimoire_{Path(file).stem}",
                                name=Path(file).stem.replace("_", " ").title(),
                                path=Path(root) / file,
                                category="grimoire",
                            )
                        )

        logger.info("Grimoire Audit complete: Found %s potential spells.", len(spells))
        return spells

    @staticmethod
    def _categorize_tool(tool_name: str) -> str:
        """Categorize a tool by its name prefix."""
        if tool_name.startswith("memory"):
            return "memory"
        if tool_name.startswith("galaxy"):
            return "memory"
        if tool_name.startswith("session"):
            return "session"
        if tool_name.startswith("gana_"):
            return "gana"
        if tool_name.startswith("security") or tool_name.startswith("vuln"):
            return "security"
        if tool_name.startswith("strata"):
            return "archaeology"
        if tool_name.startswith("dharma") or tool_name.startswith("governor"):
            return "governance"
        if tool_name.startswith("karmic") or tool_name.startswith("mandala"):
            return "governance"
        if tool_name.startswith("effect"):
            return "governance"
        if tool_name.startswith("agent"):
            return "agent"
        if tool_name.startswith("edge") or tool_name.startswith("bitnet"):
            return "inference"
        if tool_name.startswith("llama"):
            return "inference"
        if tool_name.startswith("cache"):
            return "metrics"
        if tool_name.startswith("health") or tool_name.startswith("rust"):
            return "system"
        if tool_name.startswith("state"):
            return "session"
        if tool_name.startswith("ambient"):
            return "consciousness"
        if tool_name.startswith("bounty"):
            return "agent"
        if tool_name.startswith("contest"):
            return "security"
        if tool_name.startswith("foundry") or tool_name.startswith("abi"):
            return "security"
        if tool_name.startswith("oss"):
            return "security"
        if tool_name.startswith("model"):
            return "inference"
        if tool_name.startswith("network_state"):
            return "governance"
        if tool_name.startswith("genetic"):
            return "evolution"
        if tool_name.startswith("tx_"):
            return "security"
        if tool_name.startswith("engagement"):
            return "security"
        return "tools"

    def generate_capability_report(self) -> dict[str, Any]:
        """Generate a structured report for the AI Contract or CLI."""
        spells = self.audit()
        return {
            "total_spells": len(spells),
            "categories": {
                cat: len([s for s in spells if s.category == cat])
                for cat in set(s.category for s in spells)
            },
            "spells": [asdict(s) for s in spells],
        }


def asdict(obj: Any) -> dict[str, Any]:
    """Helper to convert dataclass to dict."""
    return {k: str(v) if isinstance(v, Path) else v for k, v in obj.__dict__.items()}


# Singleton
_auditor = None


def get_auditor() -> GrimoireAuditor:
    """
    Get the auditor.

    Returns:
        GrimoireAuditor
    """
    global _auditor
    if _auditor is None:
        _auditor = GrimoireAuditor()
    return _auditor
