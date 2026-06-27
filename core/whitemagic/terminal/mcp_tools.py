# ruff: noqa: BLE001
"""MCP tools for terminal execution."""

from __future__ import annotations

import logging
from typing import Any

from .allowlist import Allowlist, Profile
from .audit import AuditLogger
from .executor import Executor

logger = logging.getLogger(__name__)


class TerminalMCPTools:
    """MCP tool wrappers for terminal operations."""

    def __init__(
        self,
        executor: Executor | None = None,
        allowlist: Allowlist | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self.executor = executor or Executor()
        self.allowlist = allowlist or Allowlist(Profile.STANDARD)
        self.audit = audit or AuditLogger()

    def run_command(self, command: str) -> dict[str, Any]:
        """Run a command with safety checks and audit logging."""
        if not self.allowlist.is_allowed(command):
            return {
                "status": "error",
                "error": "Command not in allowlist",
                "command": command,
            }

        result = self.executor.execute(command)
        self.audit.log(
            command=command,
            exit_code=result.exit_code,
            duration_s=result.duration_s,
            output_preview=result.stdout[:200],
        )

        return {
            "status": "success" if result.exit_code == 0 else "error",
            "exit_code": result.exit_code,
            "stdout": result.stdout[:1000],
            "stderr": result.stderr[:500],
            "duration_s": result.duration_s,
        }

    def list_allowed(self) -> dict[str, Any]:
        """List allowed commands."""
        return self.allowlist.summary()

    def summary(self) -> dict[str, Any]:
        return {
            "allowlist": self.allowlist.summary(),
            "audit": self.audit.summary(),
        }


TOOLS = [
    {"name": "run_command", "description": "Run a terminal command"},
    {"name": "list_allowed", "description": "List allowed commands"},
]
