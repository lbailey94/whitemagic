# ruff: noqa: BLE001
"""Terminal-based scratchpad with auto-finalization to memory."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class TerminalScratchpad:
    """Scratchpad that auto-finalizes content to persistent memory."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "agentic"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.scratch_dir = self.data_dir / "scratch"
        self.scratch_dir.mkdir(parents=True, exist_ok=True)
        self._current: Path | None = None
        self._start_time: float = 0.0

    def open(self, name: str | None = None) -> Path:
        if name is None:
            name = f"scratch_{int(time.time())}"
        self._current = self.scratch_dir / f"{name}.md"
        self._start_time = time.time()
        self._current.touch()
        return self._current

    def write(self, content: str) -> None:
        if self._current is None:
            self.open()
        assert self._current is not None
        with open(self._current, "a") as f:
            f.write(content + "\n")

    def read(self) -> str:
        if self._current is None or not self._current.exists():
            return ""
        return self._current.read_text()

    def finalize(self) -> bool:
        """Move scratchpad content to persistent memory."""
        if self._current is None or not self._current.exists():
            return False
        content = self.read()
        if not content.strip():
            return False
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            mem = get_unified_memory()
            mem.store(
                content=content,
                metadata={
                    "source": "terminal_scratchpad",
                    "file": str(self._current.name),
                    "duration_s": time.time() - self._start_time,
                },
            )
            self._current.unlink()
            self._current = None
            return True
        except Exception as e:
            logger.debug("Failed to finalize scratchpad: %s", e)
            return False

    def discard(self) -> None:
        if self._current is not None and self._current.exists():
            self._current.unlink()
        self._current = None

    def list_scratches(self) -> list[Path]:
        return sorted(self.scratch_dir.glob("*.md"))


_scratchpad: TerminalScratchpad | None = None


def get_scratchpad() -> TerminalScratchpad:
    global _scratchpad
    if _scratchpad is None:
        _scratchpad = TerminalScratchpad()
    return _scratchpad
