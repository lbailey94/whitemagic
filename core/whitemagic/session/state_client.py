# ruff: noqa: BLE001
"""
State Server Client — For Windsurf/Cascade integration.

Syncs session state with the state server, enabling continuity
across all interfaces.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class StateClient:
    """Client for syncing session state across interfaces."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "session"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "state.json"
        self._state: dict[str, Any] = {}
        self._interfaces: list[str] = []
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self._state = data.get("state", {})
                self._interfaces = data.get("interfaces", [])
            except Exception:
                pass

    def _save(self) -> None:
        self.state_file.write_text(
            json.dumps(
                {
                    "state": self._state,
                    "interfaces": self._interfaces,
                },
                indent=2,
            )
        )

    def register_interface(self, name: str) -> None:
        if name not in self._interfaces:
            self._interfaces.append(name)
            self._save()

    def sync_state(self, key: str, value: Any) -> None:
        """Sync a state value."""
        self._state[key] = {"value": value, "synced_at": time.time()}
        self._save()

    def get_state(self, key: str) -> Any | None:
        entry = self._state.get(key)
        return entry["value"] if entry else None

    def summary(self) -> dict[str, Any]:
        return {
            "interfaces": self._interfaces,
            "state_keys": list(self._state.keys()),
        }


_client: StateClient | None = None


def get_state_client() -> StateClient:
    global _client
    if _client is None:
        _client = StateClient()
    return _client
