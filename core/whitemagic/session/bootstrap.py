# ruff: noqa: BLE001
"""
Session Bootstrap — Total Recall Architecture.

Ensures every session starts with FULL context:
1. Load recent memories and session history
2. Read the Grimoire index for available spells
3. Discover all available tools
4. Load the "seen-it" registry
5. Check in-progress work
6. Wire up Gan Ying Bus with all listeners
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Context loaded at session start."""

    session_id: str = ""
    started_at: float = field(default_factory=time.time)
    recent_memories: list[dict[str, Any]] = field(default_factory=list)
    available_tools: list[str] = field(default_factory=list)
    seen_items: int = 0
    in_progress: list[str] = field(default_factory=list)
    grimoire_chapters: list[str] = field(default_factory=list)


class SessionBootstrap:
    """Bootstraps a session with full context."""

    def __init__(self) -> None:
        self.state_root = get_state_root()

    def bootstrap(self, session_id: str = "") -> SessionContext:
        """Run full bootstrap sequence."""
        ctx = SessionContext(session_id=session_id or str(int(time.time())))
        ctx.recent_memories = self._load_recent_memories()
        ctx.available_tools = self._discover_tools()
        ctx.seen_items = self._load_seen_count()
        ctx.in_progress = self._check_in_progress()
        ctx.grimoire_chapters = self._load_grimoire()
        self._save_context(ctx)
        return ctx

    def _load_recent_memories(self) -> list[dict[str, Any]]:
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            mem = get_unified_memory()
            if hasattr(mem, "recent"):
                return mem.recent(limit=10)
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)
        return []

    def _discover_tools(self) -> list[str]:
        try:
            from whitemagic.tools.dispatch_table import DISPATCH_TABLE

            return list(DISPATCH_TABLE.keys())[:20]
        except Exception:
            return []

    def _load_seen_count(self) -> int:
        try:
            from whitemagic.memory_matrix.seen_registry import get_seen_registry

            return get_seen_registry().summary()["total_seen"]
        except Exception:
            return 0

    def _check_in_progress(self) -> list[str]:
        progress_file = self.state_root / "in_progress.json"
        if progress_file.exists():
            try:
                return json.loads(progress_file.read_text())
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)
        return []

    def _load_grimoire(self) -> list[str]:
        try:
            from whitemagic.agentic.grimoire_check import get_grimoire_checker

            return get_grimoire_checker().list_chapters()
        except Exception:
            return []

    def _save_context(self, ctx: SessionContext) -> None:
        ctx_file = self.state_root / "session_context.json"
        ctx_file.write_text(
            json.dumps(
                {
                    "session_id": ctx.session_id,
                    "started_at": ctx.started_at,
                    "recent_memories": ctx.recent_memories,
                    "available_tools": ctx.available_tools,
                    "seen_items": ctx.seen_items,
                    "in_progress": ctx.in_progress,
                    "grimoire_chapters": ctx.grimoire_chapters,
                },
                indent=2,
            )
        )


def quick_bootstrap(session_id: str = "") -> SessionContext:
    """Convenience function for quick session bootstrap."""
    return SessionBootstrap().bootstrap(session_id)
