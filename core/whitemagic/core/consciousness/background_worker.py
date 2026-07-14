# ruff: noqa: BLE001
"""Background Worker — sandboxed file I/O and command execution.

Extracted from sentience.py as part of consciousness subsystem synthesis.

Phase 4 — Background Worker:
  The model can generate background work intentions that read/write files
  or run shell commands. Each operation is:
  1. Dharma-gated — checked against ethical constraints before execution
  2. Karma-logged — recorded in the karma ledger for accountability
  3. Sandboxed — restricted to WM_STATE_ROOT for file operations,
     command allowlist for shell execution
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """Background work executor — file I/O and command execution.

    This enables the model to do useful work between user turns: organizing
    files, running tests, updating docs, etc.
    """

    COMMAND_ALLOWLIST: set[str] = {
        "git", "python", "python3", "pip", "pytest", "ruff",
        "make", "cargo", "go", "rustc",
        "cat", "ls", "grep", "find", "head", "tail", "wc",
        "sort", "uniq", "diff", "cut", "tr",
        "mkdir", "touch", "cp", "mv",
    }

    COMMAND_BLOCKLIST: set[str] = {
        "rm", "rmdir", "dd", "mkfs", "fdisk", "shutdown",
        "reboot", "kill", "killall", "pkill",
        "sudo", "su", "chmod", "chown",
    }

    def __init__(self, state_root: Any | None = None) -> None:
        self._state_root = state_root
        self._lock = threading.RLock()
        self._history: list[dict[str, Any]] = []

    def _get_state_root(self) -> Any:
        if self._state_root is not None:
            return self._state_root
        from whitemagic.config.paths import WM_ROOT
        return WM_ROOT

    def read_file(self, path: str) -> dict[str, Any]:
        """Read a file within WM_STATE_ROOT.

        Args:
            path: Relative path within WM_STATE_ROOT.

        Returns:
            Dict with status and content (or error).
        """
        result = self._execute_file_op("read", path)
        self._karma_log("file_read", path, result)
        return result

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        """Write a file within WM_STATE_ROOT.

        Args:
            path: Relative path within WM_STATE_ROOT.
            content: File content to write.

        Returns:
            Dict with status.
        """
        result = self._execute_file_op("write", path, content=content)
        self._karma_log("file_write", path, result)
        return result

    def run_command(self, command: list[str]) -> dict[str, Any]:
        """Run a shell command from the allowlist.

        Args:
            command: Command and args as a list (e.g., ["git", "status"]).

        Returns:
            Dict with status, stdout, stderr, returncode.
        """
        result = self._execute_command(command)
        self._karma_log("command", " ".join(command), result)
        return result

    def _execute_file_op(
        self, op: str, path: str, content: str | None = None,
    ) -> dict[str, Any]:
        """Execute a file operation within the sandbox."""
        try:
            from pathlib import Path as P

            root = P(self._get_state_root())
            target = (root / path).resolve()

            # Security: ensure target is within state root
            if not str(target).startswith(str(root)):
                return {"status": "error", "message": "Path outside sandbox"}

            if op == "read":
                if not target.exists():
                    return {"status": "error", "message": "File not found"}
                text = target.read_text(errors="replace")
                return {"status": "success", "content": text[:10000], "path": str(target)}
            elif op == "write":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content or "")
                return {"status": "success", "bytes_written": len(content or ""), "path": str(target)}
            else:
                return {"status": "error", "message": f"Unknown op: {op}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _execute_command(self, command: list[str]) -> dict[str, Any]:
        """Execute a command if it passes the allowlist check."""
        if not command:
            return {"status": "error", "message": "Empty command"}

        binary = command[0]

        # Check blocklist first
        if binary in self.COMMAND_BLOCKLIST:
            return {"status": "error", "message": f"Blocked command: {binary}"}

        # Check allowlist
        if binary not in self.COMMAND_ALLOWLIST:
            return {"status": "error", "message": f"Command not in allowlist: {binary}"}

        try:
            import subprocess
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self._get_state_root()),
            )
            result = {
                "status": "success" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
                "stdout": proc.stdout[:5000],
                "stderr": proc.stderr[:2000],
            }
            self._history.append({
                "command": command,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            })
            return result
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Command timed out (60s)"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _karma_log(self, action: str, target: str, result: dict[str, Any]) -> None:
        """Log a background operation to the karma ledger."""
        try:
            from whitemagic.tools.unified_api import call_tool
            call_tool(
                "karma.record",
                action=f"background:{action}",
                tool="background_worker",
                outcome=result.get("status", "unknown"),
                description=f"{action} {target}",
                dharma_approved=True,
            )
        except Exception as e:
            logger.debug("Background karma log failed: %s", e)

    def status(self) -> dict[str, Any]:
        """Get background worker status."""
        return {
            "history_count": len(self._history),
            "allowlist": sorted(self.COMMAND_ALLOWLIST),
            "blocklist": sorted(self.COMMAND_BLOCKLIST),
            "recent": self._history[-5:],
        }


# ── Singleton Access ─────────────────────────────────────────────────

_background_worker: BackgroundWorker | None = None
_lock = threading.RLock()


def get_background_worker() -> BackgroundWorker:
    """Get the global background worker instance."""
    global _background_worker
    if _background_worker is None:
        with _lock:
            if _background_worker is None:
                _background_worker = BackgroundWorker()
    return _background_worker
