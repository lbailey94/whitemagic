# ruff: noqa: BLE001
"""Python dispatcher for the Elixir actor bridge.

Routes hypothesis actor operations to the BEAM GenServer-based actor system
via JSON stdio. Falls back to pure Python if the Elixir bridge is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BRIDGE_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "polyglot"
    / "bridges"
    / "elixir"
    / "actor_bridge.exs"
)

_ELIXIR_DIR = Path(__file__).parent.parent.parent.parent.parent / "polyglot" / "elixir"

_proc: subprocess.Popen | None = None
_available: bool | None = None


class ElixirActorBridge:
    """Bridge to the Elixir actor system via JSON stdio."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._available: bool | None = None

    def _readline_timeout(self, timeout: float = 5.0) -> str | None:
        """Read a line from stdout with a timeout to avoid hangs."""
        import queue
        import threading

        if self._proc is None or self._proc.stdout is None:
            return None
        result_q: queue.Queue[str | None] = queue.Queue(maxsize=1)

        def _reader() -> None:
            try:
                proc = self._proc
                if proc and proc.stdout:
                    result_q.put(proc.stdout.readline())
                else:
                    result_q.put(None)
            except Exception:
                result_q.put(None)

        t = threading.Thread(target=_reader, name="elixir-bridge-read", daemon=True)
        t.start()
        try:
            return result_q.get(timeout=timeout)
        except Exception:
            return None

    def _ensure_running(self) -> subprocess.Popen | None:
        if self._available is False:
            return None
        if os.environ.get("WM_SKIP_POLYGLOT", ""):
            self._available = False
            return None
        if self._proc is not None and self._proc.poll() is None:
            return self._proc
        if not _BRIDGE_PATH.exists():
            self._available = False
            return None
        try:
            self._proc = subprocess.Popen(
                ["mix", "run", str(_BRIDGE_PATH), "--no-start"],
                cwd=_ELIXIR_DIR,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self._proc.stdin.write(json.dumps({"method": "ping", "params": {}}) + "\n")
            self._proc.stdin.flush()
            line = self._readline_timeout(timeout=5.0)
            if not line:
                self._available = False
                return None
            resp = json.loads(line)
            if resp.get("status") == "ok":
                self._available = True
                logger.debug("Elixir actor bridge started")
                return self._proc
            self._available = False
            return None
        except Exception as e:
            logger.debug("Elixir actor bridge unavailable: %s", e)
            self._available = False
            return None

    def is_available(self) -> bool:
        return self._ensure_running() is not None

    def call(self, method: str, **params) -> dict[str, Any] | None:
        proc = self._ensure_running()
        if proc is None:
            return None
        try:
            req = {"method": method, "params": params}
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()
            line = self._readline_timeout(timeout=5.0)
            if not line:
                return None
            resp = json.loads(line)
            if resp.get("status") == "ok":
                return resp.get("result", {})
            logger.debug("Elixir bridge error for %s: %s", method, resp.get("error"))
            return None
        except Exception as e:
            logger.debug("Elixir bridge call failed for %s: %s", method, e)
            return None

    def close(self) -> None:
        if self._proc is not None:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)
            self._proc = None
        self._available = None
