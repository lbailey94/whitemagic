# ruff: noqa: BLE001
"""
Wisdom Auto-Ingester — Automatically ingest wisdom from interactions.

Scans interactions and memories for wisdom-worthy content,
automatically extracting and storing insights.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class WisdomAutoIngester:
    """Automatically ingests wisdom from system interactions."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "wisdom"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.ingested_file = self.data_dir / "ingested_wisdom.jsonl"
        self.ingested: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.ingested_file.exists():
            for line in self.ingested_file.read_text().splitlines():
                if line.strip():
                    try:
                        self.ingested.append(json.loads(line))
                    except Exception:
                        logger.debug("Swallowed exception", exc_info=True)

    def ingest(
        self, content: str, source: str = "", tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Ingest a piece of wisdom."""
        entry = {
            "content": content,
            "source": source,
            "tags": tags or [],
            "timestamp": time.time(),
        }
        self.ingested.append(entry)
        with open(self.ingested_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def scan_interactions(self) -> list[dict[str, Any]]:
        """Scan recent interactions for wisdom-worthy content."""
        ingested: list[dict[str, Any]] = []
        try:
            from whitemagic.memory_matrix.matrix import get_matrix

            matrix = get_matrix()
            recent = matrix.get_interactions(limit=20)
            for interaction in recent:
                content = interaction.get("target", "")
                if self._is_wisdom_worthy(content):
                    entry = self.ingest(
                        content=content,
                        source=f"interaction:{interaction.get('action', '')}",
                        tags=["auto-ingested"],
                    )
                    ingested.append(entry)
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)
        return ingested

    @staticmethod
    def _is_wisdom_worthy(content: str) -> bool:
        """Heuristic: is this content wisdom-worthy?"""
        wisdom_keywords = ["learned", "realized", "understood", "discovered", "insight"]
        return any(kw in content.lower() for kw in wisdom_keywords)

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search ingested wisdom."""
        query_lower = query.lower()
        results = [
            entry
            for entry in self.ingested
            if query_lower in entry.get("content", "").lower()
        ]
        return results[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_ingested": len(self.ingested),
            "tags": list(set(t for e in self.ingested for t in e.get("tags", []))),
        }


_ingester: WisdomAutoIngester | None = None


def get_ingester() -> WisdomAutoIngester:
    global _ingester
    if _ingester is None:
        _ingester = WisdomAutoIngester()
    return _ingester
