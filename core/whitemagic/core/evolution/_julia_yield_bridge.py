"""Python dispatcher for the Julia yield curve bridge.

Tries the Julia JSON stdio bridge first for compute-heavy yield curve operations.
Falls back to pure Python implementations if the bridge is unavailable.

This module is used by yield_curve.py to accelerate value_at, duration,
fit_parameters, portfolio_duration, select_by_horizon, and detect_regime_change.
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
    / "bridges"
    / "julia"
    / "yield_bridge.jl"
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
            ["julia", str(_BRIDGE_PATH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        _proc.stdin.write(
            json.dumps({"command": "value_at", "yield_type": "decaying", "t": 0.0})
            + "\n"
        )
        _proc.stdin.flush()
        line = _proc.stdout.readline()
        if not line:
            _available = False
            return None
        resp = json.loads(line)
        if resp.get("status") == "ok":
            _available = True
            logger.debug("Julia yield curve bridge started")
            return _proc
        else:
            _available = False
            return None
    except Exception as e:
        logger.debug("Julia yield curve bridge unavailable: %s", e)
        _available = False
        return None


def call(command: str, **params) -> dict[str, Any] | None:
    """Call the Julia yield curve bridge.

    Returns the result dict, or None if the bridge is unavailable.
    """
    proc = _ensure_running()
    if proc is None:
        return None

    try:
        req = {"command": command, **params}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            return None
        resp = json.loads(line)
        if resp.get("status") == "ok":
            return resp.get("result", {})
        else:
            logger.debug("Bridge error for %s: %s", command, resp.get("error"))
            return None
    except Exception as e:
        logger.debug("Bridge call failed for %s: %s", command, e)
        return None


def is_available() -> bool:
    """Check if the Julia yield curve bridge is available."""
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
