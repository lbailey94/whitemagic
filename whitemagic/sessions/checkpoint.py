"""Checkpoint Manager - Session State Snapshots"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


@dataclass
class Checkpoint:
    """Session checkpoint/snapshot."""

    session_id: str
    name: str
    timestamp: str
    context: Dict[str, Any]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CheckpointManager:
    """Manages session checkpoints."""

    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path.home() / ".whitemagic" / "checkpoints"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def create_checkpoint(
        self, session_id: str, name: str, context: Dict[str, Any], metrics: Dict[str, Any]
    ) -> Checkpoint:
        """Create checkpoint."""
        checkpoint = Checkpoint(
            session_id=session_id,
            name=name,
            timestamp=datetime.utcnow().isoformat(),
            context=context,
            metrics=metrics,
        )

        # Save
        path = self.base_dir / session_id / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(checkpoint.to_dict(), indent=2))

        return checkpoint
