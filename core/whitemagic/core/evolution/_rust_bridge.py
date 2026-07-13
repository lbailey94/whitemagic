# ruff: noqa: BLE001
"""Python dispatcher for the Rust evolution bridge.

Tries the Rust JSON stdio bridge first for compute-heavy operations.
Falls back to pure Python implementations if the bridge is unavailable.

This module is used by info_theory.py and thermodynamic.py to accelerate
their hot-path computations via the Rust wm-evolution crate.

Phase 5: Migrated to ProcessSupervisor for bounded, observable, supervised I/O.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from whitemagic.core.acceleration.process_supervisor import (
    ProcessSupervisor,
    register,
)

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

_supervisor: ProcessSupervisor | None = None


def _get_supervisor() -> ProcessSupervisor:
    global _supervisor
    if _supervisor is None:
        _supervisor = ProcessSupervisor(
            name="rust-evolution",
            cmd=[str(_BRIDGE_PATH)],
            binary_path=str(_BRIDGE_PATH),
            startup_timeout=5.0,
            call_timeout=5.0,
        )
        register(_supervisor)
    return _supervisor


def call(method: str, **params) -> dict[str, Any] | None:
    """Call the Rust evolution bridge.

    Returns the result dict, or None if the bridge is unavailable.
    """
    sup = _get_supervisor()
    result = sup.call({"method": method, "params": params})
    if result.ok and result.data:
        if result.data.get("status") == "ok":
            return result.data.get("result", {})
        logger.debug("Bridge error for %s: %s", method, result.data.get("error"))
        return None
    return None


def is_available() -> bool:
    """Check if the Rust evolution bridge is available."""
    return _get_supervisor().is_available()


def close() -> None:
    """Close the bridge subprocess."""
    global _supervisor
    if _supervisor is not None:
        _supervisor.close()
        _supervisor = None


def health_check() -> dict[str, Any]:
    """Return health check dict for the bridge."""
    return _get_supervisor().health_check()
