# ruff: noqa: BLE001
"""Terminal multiplexing — manage multiple named scratchpad channels."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class TerminalMultiplexer:
    """Manage multiple named scratchpad channels for parallel work."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "agentic"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.channels_file = self.data_dir / "channels.json"
        self.channels: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        if self.channels_file.exists():
            try:
                self.channels = json.loads(self.channels_file.read_text())
            except Exception:
                logger.debug("Using empty channels")

    def _save(self) -> None:
        self.channels_file.write_text(json.dumps(self.channels, indent=2))

    def create_channel(self, name: str) -> None:
        if name not in self.channels:
            self.channels[name] = []
            self._save()

    def write(self, channel: str, content: str) -> None:
        self.create_channel(channel)
        self.channels[channel].append(content)
        self._save()

    def read(self, channel: str) -> list[str]:
        return self.channels.get(channel, [])

    def list_channels(self) -> list[str]:
        return list(self.channels.keys())

    def close_channel(self, name: str) -> list[str]:
        return self.channels.pop(name, [])

    def flush_to_memory(self, channel: str) -> bool:
        """Flush a channel's content to unified memory."""
        content = self.read(channel)
        if not content:
            return False
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            mem = get_unified_memory()
            mem.store(
                content="\n".join(content),
                metadata={"channel": channel, "source": "terminal_multiplexer"},
            )
            self.channels[channel] = []
            self._save()
            return True
        except Exception as e:
            logger.debug("Failed to flush channel %s: %s", channel, e)
            return False


_multiplexer: TerminalMultiplexer | None = None


def get_multiplexer() -> TerminalMultiplexer:
    global _multiplexer
    if _multiplexer is None:
        _multiplexer = TerminalMultiplexer()
    return _multiplexer
