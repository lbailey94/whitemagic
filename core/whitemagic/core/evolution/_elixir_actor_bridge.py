# ruff: noqa: BLE001
"""Python dispatcher for the Elixir actor bridge.

Routes hypothesis actor operations to the BEAM GenServer-based actor system
via JSON stdio. Falls back to pure Python if the Elixir bridge is unavailable.

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
    / "bridges"
    / "elixir"
    / "actor_bridge.exs"
)

_ELIXIR_DIR = Path(__file__).parent.parent.parent.parent.parent / "polyglot" / "elixir"


class ElixirActorBridge:
    """Bridge to the Elixir actor system via JSON stdio."""

    def __init__(self) -> None:
        self._supervisor: ProcessSupervisor | None = None

    def _get_supervisor(self) -> ProcessSupervisor:
        if self._supervisor is None:
            self._supervisor = ProcessSupervisor(
                name="elixir-actor",
                cmd=["mix", "run", str(_BRIDGE_PATH), "--no-start"],
                binary_path=str(_BRIDGE_PATH),
                startup_timeout=30.0,
                call_timeout=5.0,
                skip_polyglot=True,
                cwd=_ELIXIR_DIR,
            )
            register(self._supervisor)
        return self._supervisor

    def is_available(self) -> bool:
        return self._get_supervisor().is_available()

    def call(self, method: str, **params) -> dict[str, Any] | None:
        sup = self._get_supervisor()
        result = sup.call({"method": method, "params": params})
        if result.ok and result.data:
            if result.data.get("status") == "ok":
                return result.data.get("result", {})
            logger.debug("Elixir bridge error for %s: %s", method, result.data.get("error"))
            return None
        return None

    def close(self) -> None:
        if self._supervisor is not None:
            self._supervisor.close()
            self._supervisor = None

    def health_check(self) -> dict[str, Any]:
        return self._get_supervisor().health_check()
