# ruff: noqa: BLE001
"""
Multi-Agent Coordinator — Prevent conflicts between AI instances.

When multiple AI instances work with WhiteMagic simultaneously,
they need coordination to avoid conflicts and race conditions.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class MultiAgentCoordinator:
    """Coordinates multiple AI instances to prevent conflicts."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "defense"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.locks_file = self.data_dir / "agent_locks.json"
        self.locks: dict[str, dict[str, Any]] = {}
        self._load_locks()

    def _load_locks(self) -> None:
        if self.locks_file.exists():
            try:
                self.locks = json.loads(self.locks_file.read_text())
            except Exception:
                logger.debug("Using empty locks")

    def _save_locks(self) -> None:
        self.locks_file.write_text(json.dumps(self.locks, indent=2))

    def acquire_lock(self, resource: str, agent_id: str, ttl: float = 300.0) -> bool:
        """Acquire a lock on a resource."""
        existing = self.locks.get(resource)
        if existing:
            if existing["agent_id"] == agent_id:
                self.locks[resource]["expires"] = time.time() + ttl
                self._save_locks()
                return True
            if existing.get("expires", 0) > time.time():
                return False
        self.locks[resource] = {
            "agent_id": agent_id,
            "acquired": time.time(),
            "expires": time.time() + ttl,
        }
        self._save_locks()
        return True

    def release_lock(self, resource: str, agent_id: str) -> bool:
        """Release a lock on a resource."""
        existing = self.locks.get(resource)
        if existing and existing["agent_id"] == agent_id:
            del self.locks[resource]
            self._save_locks()
            return True
        return False

    def list_locks(self) -> dict[str, Any]:
        """List all active locks."""
        now = time.time()
        return {
            r: {
                "agent_id": d["agent_id"],
                "acquired": d["acquired"],
                "expires": d["expires"],
                "expired": d["expires"] < now,
            }
            for r, d in self.locks.items()
        }

    def cleanup_expired(self) -> int:
        """Remove expired locks."""
        now = time.time()
        expired = [r for r, d in self.locks.items() if d.get("expires", 0) < now]
        for r in expired:
            del self.locks[r]
        if expired:
            self._save_locks()
        return len(expired)


_coordinator: MultiAgentCoordinator | None = None


def get_coordinator() -> MultiAgentCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = MultiAgentCoordinator()
    return _coordinator
