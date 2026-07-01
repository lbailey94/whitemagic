"""Ram's Horn Scratchpad — Phase 26 Autonomy.
=========================================
A terminal-based ephemeral workspace for active sessions.
Automatically finalizes "thoughts" into long-term memories on close.
"""

import json
import os
import time
from datetime import datetime

from whitemagic.config.paths import WM_ROOT
from whitemagic.core.memory.unified import remember

import logging
logger = logging.getLogger(__name__)


class Scratchpad:
    """Ephemeral session storage that auto-commits to long-term memory."""

    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id or f"session_{int(time.time())}"
        self.base_dir = WM_ROOT / "scratchpad"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.base_dir / f"{self.session_id}.json"
        self.entries = self._load()

    def _load(self) -> list[dict]:
        if self.file_path.exists():
            try:
                with open(self.file_path) as f:
                    return json.load(f)  # type: ignore[no-any-return]
            except (OSError, FileNotFoundError, PermissionError):
                return []
        return []

    def _save(self) -> None:
        with open(self.file_path, "w") as f:
            json.dump(self.entries, f, indent=2)

    def add_entry(self, text: str, tags: list[str] | None = None) -> None:
        """Add a thought or directive to the scratchpad."""
        entry = {
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "tags": tags or [],
        }
        self.entries.append(entry)
        self._save()
        logger.debug("  [Scratchpad] Entry added to %s.", self.session_id)

    def finalize(self) -> None:
        """Commit all entries to Unified Memory and clear the scratchpad."""
        if not self.entries:
            return

        logger.debug(
            "  [Scratchpad] Finalizing %d entries for %s...",
            len(self.entries),
            self.session_id,
        )

        # Coherence boost for session closure (Phase 26)
        try:
            from whitemagic.core.intelligence.agentic.coherence_persistence import (
                get_coherence,
            )

            get_coherence().boost(
                len(self.entries), f"Scratchpad finalization: {self.session_id}"
            )
        except (ImportError, ModuleNotFoundError):
            pass

        # Combine all entries into one "Session Summary" or "Insight Block"
        combined_text = f"# Session Scratchpad: {self.session_id}\n"
        combined_text += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"

        all_tags = {"scratchpad", "session_coherence", self.session_id}

        for entry in self.entries:
            combined_text += f"[{entry['timestamp']}] {entry['text']}\n"
            for t in entry["tags"]:
                all_tags.add(t)

        remember(
            content=combined_text,
            title=f"Scratchpad Finalization: {self.session_id}",
            tags=all_tags,
            importance=0.7,
        )

        self.entries = []
        if self.file_path.exists():
            self.file_path.unlink()

        logger.debug("  [Scratchpad] Memory persisted. Session cleared.")

    def list_entries(self) -> None:
        """List current entries."""
        if not self.entries:
            logger.debug("  [Scratchpad] Empty.")
            return

        for i, entry in enumerate(self.entries):
            logger.debug("  %s. [%s] %s...", i + 1, entry['timestamp'], entry['text'][:50])


def get_active_scratchpad() -> Scratchpad:
    """Gets or creates a scratchpad for the current session."""
    # We can use an environment variable to track the session, or default to a daily one
    session_id = (
        os.getenv("WM_SESSION_ID") or f"day_{datetime.now().strftime('%Y%m%d')}"
    )
    return Scratchpad(session_id)
