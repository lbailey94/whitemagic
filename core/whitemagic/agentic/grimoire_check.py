# ruff: noqa: BLE001
"""Brain Upgrade #3: Grimoire Auto-Check — Never forget available spells."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_project_root

logger = logging.getLogger(__name__)


class GrimoireChecker:
    """Scans the grimoire and reports available tools/spells."""

    def __init__(self, grimoire_dir: Path | None = None) -> None:
        if grimoire_dir is None:
            grimoire_dir = get_project_root() / "grimoire"
        self.grimoire_dir = Path(grimoire_dir)

    def list_chapters(self) -> list[str]:
        """List all grimoire chapters."""
        if not self.grimoire_dir.exists():
            return []
        return sorted(
            f.stem
            for f in self.grimoire_dir.glob("*.md")
            if not f.name.startswith("00_")
        )

    def list_tools(self) -> list[dict[str, str]]:
        """Extract tool definitions from grimoire."""
        tools: list[dict[str, str]] = []
        for chapter in self.grimoire_dir.glob("*.md"):
            if chapter.name.startswith("00_"):
                continue
            try:
                content = chapter.read_text()
                for match in re.finditer(r"###\s+(.+)", content):
                    tools.append(
                        {
                            "chapter": chapter.stem,
                            "section": match.group(1).strip(),
                        }
                    )
            except Exception:
                pass
        return tools

    def check_available(self) -> dict[str, Any]:
        """Check which grimoire tools are currently available."""
        chapters = self.list_chapters()
        tools = self.list_tools()
        return {
            "total_chapters": len(chapters),
            "chapters": chapters,
            "total_sections": len(tools),
            "sections": tools[:20],
        }


_checker: GrimoireChecker | None = None


def get_grimoire_checker() -> GrimoireChecker:
    global _checker
    if _checker is None:
        _checker = GrimoireChecker()
    return _checker
