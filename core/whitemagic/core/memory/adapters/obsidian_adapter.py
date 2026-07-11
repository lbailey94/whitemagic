"""Obsidian vault sync adapter — bidirectional sync between WhiteMagic and Obsidian.

Installation:
    pip install wm-memory

Usage:
    from wm_memory.adapters import ObsidianAdapter

    adapter = ObsidianAdapter(vault_path="/path/to/vault")
    adapter.export_memories(limit=100)       # WM → Obsidian
    adapter.import_notes()                    # Obsidian → WM
    adapter.sync()                            # Bidirectional

Each WhiteMagic memory becomes a Markdown note with YAML frontmatter:

    ---
    id: "abc-123"
    type: LONG_TERM
    importance: 0.8
    tags: [api, rate-limit]
    galaxy: universal
    neuro_score: 0.92
    created_at: 2026-07-10T12:00:00
    ---

    # API X has rate limit 100/min

    API X has rate limit 100/min
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.core.memory.adapters.agent_memory import AgentMemory
from whitemagic.core.memory.unified_types import Memory, MemoryType

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


class ObsidianAdapter:
    """Bidirectional sync between WhiteMagic memories and Obsidian vault.

    Converts WM memories to/from Obsidian Markdown notes with YAML frontmatter.
    Supports selective export by galaxy, tags, or importance threshold.

    Args:
        vault_path: Path to the Obsidian vault directory.
        agent_memory: Optional pre-configured AgentMemory.
        folder: Subfolder within vault for WM notes (default: "whitemagic").
    """

    def __init__(
        self,
        vault_path: str | Path,
        agent_memory: AgentMemory | None = None,
        folder: str = "whitemagic",
    ) -> None:
        self.vault_path = Path(vault_path)
        self.folder = folder
        self._am = agent_memory or AgentMemory()
        self._sync_dir = self.vault_path / folder
        self._sync_dir.mkdir(parents=True, exist_ok=True)

    def export_memories(
        self,
        limit: int = 100,
        galaxy: str | None = None,
        tags: set[str] | None = None,
        min_importance: float = 0.0,
    ) -> int:
        """Export WhiteMagic memories to Obsidian as Markdown notes.

        Args:
            limit: Maximum memories to export.
            galaxy: Filter by galaxy.
            tags: Filter by tags.
            min_importance: Minimum importance threshold.

        Returns:
            Number of notes written.
        """
        results = self._am.long_term.search(
            tags=tags,
            min_importance=min_importance,
            limit=limit,
            galaxy=galaxy,
        )

        count = 0
        for mem_dict in results:
            note_path = self._sync_dir / f"{self._slugify(mem_dict.get('title', mem_dict['id']))}.md"
            content = self._memory_to_markdown(mem_dict)
            note_path.write_text(content, encoding="utf-8")
            count += 1

        logger.info("Exported %d memories to %s", count, self._sync_dir)
        return count

    def import_notes(self, folder: str | None = None) -> int:
        """Import Obsidian notes into WhiteMagic as long-term memories.

        Scans for Markdown files with WM frontmatter and imports them.
        Notes without frontmatter are imported with default metadata.

        Args:
            folder: Subfolder to scan (default: self.folder).

        Returns:
            Number of notes imported.
        """
        scan_dir = self.vault_path / (folder or self.folder) if folder else self._sync_dir
        if not scan_dir.exists():
            logger.warning("Directory does not exist: %s", scan_dir)
            return 0

        count = 0
        for md_file in scan_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            mem_data = self._markdown_to_memory(content)
            if mem_data:
                self._am.long_term.store(
                    content=mem_data["content"],
                    title=mem_data.get("title", md_file.stem),
                    tags=mem_data.get("tags", set()),
                    importance=mem_data.get("importance", 0.5),
                    galaxy=mem_data.get("galaxy", "universal"),
                    metadata={"source": "obsidian", "file": str(md_file)},
                )
                count += 1

        logger.info("Imported %d notes from %s", count, scan_dir)
        return count

    def sync(self, **kwargs: Any) -> dict[str, int]:
        """Bidirectional sync: export WM → Obsidian, then import Obsidian → WM.

        Args:
            **kwargs: Passed to export_memories().

        Returns:
            Dict with 'exported' and 'imported' counts.
        """
        exported = self.export_memories(**kwargs)
        imported = self.import_notes()
        return {"exported": exported, "imported": imported}

    def _memory_to_markdown(self, mem: dict[str, Any]) -> str:
        """Convert a memory dict to Obsidian Markdown with frontmatter."""
        tags = mem.get("tags", [])
        if isinstance(tags, list):
            tag_str = ", ".join(f'"{t}"' for t in tags)
        else:
            tag_str = str(tags)

        frontmatter = f"""---
id: "{mem.get('id', '')}"
type: {mem.get('memory_type', 'LONG_TERM')}
importance: {mem.get('importance', 0.5)}
tags: [{tag_str}]
galaxy: {mem.get('galaxy', 'universal')}
neuro_score: {mem.get('neuro_score', 1.0)}
created_at: {mem.get('created_at', datetime.now().isoformat())}
---

"""
        title = mem.get("title", mem.get("id", "Untitled"))
        content = str(mem.get("content", ""))
        body = f"# {title}\n\n{content}\n"
        return frontmatter + body

    def _markdown_to_memory(self, content: str) -> dict[str, Any] | None:
        """Parse Obsidian Markdown with frontmatter into memory data."""
        match = _FRONTMATTER_RE.match(content)
        if not match:
            return {"content": content.strip(), "title": "Untitled"}

        frontmatter_text, body = match.groups()
        data: dict[str, Any] = {}

        for line in frontmatter_text.strip().split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if key == "tags":
                    tags = re.findall(r'"([^"]+)"', value)
                    data["tags"] = set(tags)
                elif key == "importance":
                    try:
                        data["importance"] = float(value)
                    except ValueError:
                        pass
                elif key == "galaxy":
                    data["galaxy"] = value
                elif key == "type":
                    data["memory_type"] = value

        title_match = re.match(r"^#\s+(.+)$", body.strip(), re.MULTILINE)
        if title_match:
            data["title"] = title_match.group(1)
            body = body[title_match.end():].strip()

        data["content"] = body
        return data

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to a filesystem-safe slug."""
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[-\s]+", "-", slug).strip("-_")
        return slug[:80] or "untitled"
