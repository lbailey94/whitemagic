# ruff: noqa: BLE001
"""
Dharmic Bounties — XRPL Escrow-based task management.
=====================================================
Allows agents and humans to create task bounties using XRPL Escrows.
Funds are locked on-chain and only released upon successful completion
and verification of the task.

Philosophy: "Trustless exchange of value for intelligence."
"""

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Bounty:
    """A task bounty backed by an XRPL Escrow."""

    id: str
    task_description: str
    amount: float
    currency: str = "XRP"
    creator: str = ""
    executor: str = ""
    escrow_seq: int | None = None
    tx_hash: str = ""
    status: str = "open"  # open, active, completed, cancelled, expired
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return asdict(self)


class BountyBoard:
    """Manages the lifecycle of Dharmic Bounties."""

    def __init__(self) -> None:
        from whitemagic.config.paths import ECONOMY_DIR

        self._path = ECONOMY_DIR / "bounties.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._bounties: dict[str, Bounty] = {}
        self._load()

    def _load(self) -> None:
        """Load bounties from disk."""
        if not self._path.exists():
            return
        from whitemagic.utils.fast_json import loads as _json_loads

        try:
            with open(self._path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = _json_loads(line)
                        bounty = Bounty(**data)
                        self._bounties[bounty.id] = bounty
        except Exception as e:
            logger.warning("Failed to load bounty board: %s", e, exc_info=True)

    def create_bounty(
        self, task: str, amount: float, expires_in: int = 86400
    ) -> Bounty:
        """Create a new bounty record (link to XRPL Escrow happens later)."""
        import uuid

        bounty_id = str(uuid.uuid4())[:8]
        bounty = Bounty(
            id=bounty_id,
            task_description=task,
            amount=amount,
            expires_at=time.time() + expires_in,
        )
        self._bounties[bounty_id] = bounty
        self._persist(bounty)
        return bounty

    async def link_escrow(self, bounty_id: str, tx_hash: str) -> dict[str, Any]:
        """Verify an XRPL EscrowCreate transaction and link it to a bounty."""
        bounty = self.get_bounty(bounty_id)
        if not bounty:
            return {"status": "error", "message": "Bounty not found"}

        import httpx

        from whitemagic.gratitude.proof import _XRPL_NODES

        payload = {
            "method": "tx",
            "params": [{"transaction": tx_hash, "binary": False}],
        }

        async with httpx.AsyncClient() as client:
            for node in _XRPL_NODES:
                try:
                    resp = await client.post(node, json=payload, timeout=10.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        result = data.get("result", {})
                        if result.get("TransactionType") == "EscrowCreate":
                            # Verify amount and destination
                            from whitemagic.core.economy.wallet_manager import (
                                get_wallet,
                            )

                            wallet = get_wallet()

                            amount_drops = int(result.get("Amount", "0"))
                            if amount_drops / 1_000_000 < bounty.amount:
                                return {
                                    "status": "error",
                                    "message": "Escrow amount too low",
                                }

                            if result.get("Destination") != wallet.public_address:
                                return {
                                    "status": "error",
                                    "message": "Escrow destination mismatch",
                                }

                            bounty.tx_hash = tx_hash
                            bounty.escrow_seq = result.get("Sequence")
                            bounty.creator = result.get("Account")
                            bounty.status = "active"
                            self._persist(bounty)
                            return {"status": "ok", "bounty": bounty.to_dict()}
                except (ImportError, AttributeError):
                    continue

        return {"status": "error", "message": "Escrow transaction not found or invalid"}

    def _persist(self, bounty: Bounty) -> None:
        """Append bounty to the ledger."""
        from whitemagic.utils.fast_json import dumps_str as _json_dumps

        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(_json_dumps(bounty.to_dict()) + "\n")
        except (ImportError, ModuleNotFoundError) as e:
            logger.error("Failed to persist bounty: %s", e, exc_info=True)

    def get_bounty(self, bounty_id: str) -> Bounty | None:
        """
        Get the bounty.

        Args:
            bounty_id: Parameter description.

        Returns:
            Bounty | None
        """
        return self._bounties.get(bounty_id)

    def list_bounties(self, status: str = "open") -> list[Bounty]:
        """
        List the bounties.

        Args:
            status: Parameter description.

        Returns:
            list[Bounty]
        """
        return [b for b in self._bounties.values() if b.status == status]


_board: BountyBoard | None = None


def get_bounty_board() -> BountyBoard:
    """
    Get the bounty board.

    Returns:
        BountyBoard
    """
    global _board
    if _board is None:
        _board = BountyBoard()
    return _board
