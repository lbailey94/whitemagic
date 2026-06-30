# ruff: noqa: BLE001
"""Audit logging for command execution."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root


@dataclass
class AuditLog:
    """A single audit log entry."""

    log_id: str
    command: str
    exit_code: int
    duration_s: float
    timestamp: float
    output_preview: str = ""


class AuditLogger:
    """Logs command execution for audit purposes."""

    def __init__(self, log_dir: Path | None = None) -> None:
        if log_dir is None:
            log_dir = get_state_root() / "terminal" / "audit"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "audit_log.jsonl"
        self._entries: list[AuditLog] = []

    def log(
        self,
        command: str,
        exit_code: int,
        duration_s: float,
        output_preview: str = "",
    ) -> AuditLog:
        """Log a command execution."""
        entry = AuditLog(
            log_id=str(uuid.uuid4())[:8],
            command=command,
            exit_code=exit_code,
            duration_s=duration_s,
            timestamp=time.time(),
            output_preview=output_preview[:200],
        )
        self._entries.append(entry)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def recent(self, limit: int = 20) -> list[AuditLog]:
        """Get recent audit entries."""
        return self._entries[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "successful": sum(1 for e in self._entries if e.exit_code == 0),
            "failed": sum(1 for e in self._entries if e.exit_code != 0),
        }
