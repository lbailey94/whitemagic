# ruff: noqa: BLE001
"""Python dispatcher for the Rust evolution bridge.

Tries the Rust JSON stdio bridge first for compute-heavy operations.
Falls back to pure Python implementations if the bridge is unavailable.

This module is used by info_theory.py and thermodynamic.py to accelerate
their hot-path computations via the Rust wm-evolution crate.
"""

from __future__ import annotations

import json
import logging
import queue
import subprocess
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BRIDGE_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "polyglot"
    / "whitemagic-rs"
    / "target"
    / "release"
    / "examples"
    / "evolution_bridge"
)

_proc: subprocess.Popen | None = None
_available: bool | None = None


def _readline_timeout(proc: subprocess.Popen, timeout: float = 5.0) -> str | None:
    """Read a line from proc.stdout with a timeout to avoid hangs."""
    if proc.stdout is None:
        return None
    result_q: queue.Queue[str | None] = queue.Queue(maxsize=1)

    def _reader() -> None:
        try:
            result_q.put(proc.stdout.readline())
        except Exception:
            result_q.put(None)

    t = threading.Thread(target=_reader, name="rust-bridge-read", daemon=True)
    t.start()
    try:
        return result_q.get(timeout=timeout)
    except Exception:
        return None


def _ensure_running() -> subprocess.Popen | None:
    """Start or return the bridge subprocess."""
    global _proc, _available

    if _available is False:
        return None

    # Note: WM_SKIP_POLYGLOT does NOT apply here — the Rust evolution bridge
    # is a compiled binary, not a polyglot language runtime (Julia/Elixir/etc).

    if _proc is not None and _proc.poll() is None:
        return _proc

    if not _BRIDGE_PATH.exists():
        _available = False
        return None

    try:
        _proc = subprocess.Popen(
            [str(_BRIDGE_PATH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        _proc.stdin.write(json.dumps({"method": "ping", "params": {}}) + "\n")
        _proc.stdin.flush()
        line = _readline_timeout(_proc, timeout=5.0)
        if not line:
            _available = False
            return None
        resp = json.loads(line)
        if resp.get("status") == "ok":
            _available = True
            logger.debug("Rust evolution bridge started")
            return _proc
        else:
            _available = False
            return None
    except Exception as e:
        logger.debug("Rust evolution bridge unavailable: %s", e)
        _available = False
        return None


def call(method: str, **params) -> dict[str, Any] | None:
    """Call the Rust evolution bridge.

    Returns the result dict, or None if the bridge is unavailable.
    """
    proc = _ensure_running()
    if proc is None:
        return None

    try:
        req = {"method": method, "params": params}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        line = _readline_timeout(proc, timeout=5.0)
        if not line:
            return None
        resp = json.loads(line)
        if resp.get("status") == "ok":
            return resp.get("result", {})
        else:
            logger.debug("Bridge error for %s: %s", method, resp.get("error"))
            return None
    except Exception as e:
        logger.debug("Bridge call failed for %s: %s", method, e)
        return None


def is_available() -> bool:
    """Check if the Rust evolution bridge is available."""
    return _ensure_running() is not None


def close() -> None:
    """Close the bridge subprocess."""
    global _proc, _available
    if _proc is not None:
        try:
            _proc.stdin.close()
            _proc.wait(timeout=5)
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)
        _proc = None
    _available = None
