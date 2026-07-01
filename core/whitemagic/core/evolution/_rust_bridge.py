"""Python dispatcher for the Rust evolution bridge.

Tries the Rust JSON stdio bridge first for compute-heavy operations.
Falls back to pure Python implementations if the bridge is unavailable.

This module is used by info_theory.py and thermodynamic.py to accelerate
their hot-path computations via the Rust wm-evolution crate.
"""

from __future__ import annotations

import json
import logging
import subprocess
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


def _ensure_running() -> subprocess.Popen | None:
    """Start or return the bridge subprocess."""
    global _proc, _available

    if _available is False:
        return None

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
        line = _proc.stdout.readline()
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
        line = proc.stdout.readline()
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
            pass
        _proc = None
    _available = None
