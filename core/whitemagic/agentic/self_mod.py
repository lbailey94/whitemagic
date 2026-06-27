# ruff: noqa: BLE001
"""
Self-Modification Protocol — Version-controlled consciousness changes.

Tracks modifications to the system's own configuration and parameters,
creating an audit trail of self-directed changes.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


@dataclass
class SelfModification:
    """Record of a self-directed modification."""
    timestamp: float = field(default_factory=time.time)
    module: str = ""
    parameter: str = ""
    old_value: Any = None
    new_value: Any = None
    reason: str = ""
    approved: bool = False


class SelfModProtocol:
    """Protocol for safe self-modification with audit trail."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "agentic"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.data_dir / "self_mods.jsonl"
        self.modifications: list[SelfModification] = []
        self._load()

    def _load(self) -> None:
        if self.log_file.exists():
            for line in self.log_file.read_text().splitlines():
                if line.strip():
                    try:
                        d = json.loads(line)
                        self.modifications.append(SelfModification(**d))
                    except Exception:
                        logger.debug("Skipping malformed mod entry")

    def propose(
        self,
        module: str,
        parameter: str,
        old_value: Any,
        new_value: Any,
        reason: str,
    ) -> SelfModification:
        mod = SelfModification(
            module=module,
            parameter=parameter,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            approved=False,
        )
        self.modifications.append(mod)
        self._save(mod)
        logger.info("Proposed self-mod: %s.%s", module, parameter)
        return mod

    def approve(self, index: int) -> bool:
        if 0 <= index < len(self.modifications):
            self.modifications[index].approved = True
            self._rewrite()
            return True
        return False

    def _save(self, mod: SelfModification) -> None:
        with open(self.log_file, "a") as f:
            f.write(json.dumps(asdict(mod)) + "\n")

    def _rewrite(self) -> None:
        self.log_file.write_text(
            "\n".join(json.dumps(asdict(m)) for m in self.modifications)
        )

    def history(self) -> list[dict[str, Any]]:
        return [asdict(m) for m in self.modifications]


_protocol: SelfModProtocol | None = None


def get_self_mod_protocol() -> SelfModProtocol:
    global _protocol
    if _protocol is None:
        _protocol = SelfModProtocol()
    return _protocol
