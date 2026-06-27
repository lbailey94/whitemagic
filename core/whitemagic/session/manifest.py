# ruff: noqa: BLE001
"""
Session Manifest — YAML/JSON state file.

Created at session start, updated throughout, used for handoffs.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


@dataclass
class SessionManifest:
    """Session state manifest for handoffs."""
    session_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    interface: str = "cli"
    goals: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    notes: str = ""
    files_touched: list[str] = field(default_factory=list)
    tests_run: int = 0
    tests_passed: int = 0

    def update(self, **kwargs: Any) -> None:
        """Update manifest fields."""
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def create_manifest(
    session_id: str = "",
    interface: str = "cli",
    goals: list[str] | None = None,
) -> SessionManifest:
    """Create and persist a new session manifest."""
    manifest = SessionManifest(
        session_id=session_id or str(int(time.time())),
        interface=interface,
        goals=goals or [],
    )
    state_root = get_state_root()
    manifest_file = state_root / "session_manifest.json"
    manifest_file.write_text(manifest.to_json())
    return manifest
