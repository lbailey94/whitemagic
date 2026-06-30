"""Economy Tool Handlers — Pulse, Bounties, and Memory Market."""

import logging
from dataclasses import asdict
from typing import Any

logger = logging.getLogger(__name__)


def handle_pulse_status(**kwargs: Any) -> dict[str, Any]:
    """Check the status of the Gratitude Pulse background scanner."""
    from whitemagic.gratitude.pulse import get_pulse

    pulse = get_pulse()
    return {
        "running": pulse.running,
        "interval": pulse.interval,
        "address": pulse.wallet.public_address,
    }


def handle_create_bounty(**kwargs: Any) -> dict[str, Any]:
    """Create a new task bounty."""
    task = kwargs.get("task", "")
    amount = float(kwargs.get("amount", 0.0))
    if not task or amount <= 0:
        return {"status": "error", "message": "task and positive amount required"}

    from whitemagic.core.economy.bounty_board import get_bounty_board

    bounty = get_bounty_board().create_bounty(task, amount)
    return {"status": "success", "bounty": bounty.to_dict()}


def handle_list_bounties(**kwargs: Any) -> dict[str, Any]:
    """List available bounties."""
    status = kwargs.get("status", "open")
    from whitemagic.core.economy.bounty_board import get_bounty_board

    bounties = get_bounty_board().list_bounties(status)
    return {"status": "success", "bounties": [b.to_dict() for b in bounties]}


def handle_rent_galaxy(**kwargs: Any) -> dict[str, Any]:
    """Rent access to a specialized galaxy."""
    galaxy_name = kwargs.get("galaxy_name", "")
    agent_id = kwargs.get("agent_id", "default")
    tx_hash = kwargs.get("tx_hash", "")

    if not galaxy_name or not tx_hash:
        return {"status": "error", "message": "galaxy_name and tx_hash required"}

    # In a real impl, we'd verify the tx_hash first
    from whitemagic.core.economy.memory_market import get_memory_market

    access = get_memory_market().grant_access(galaxy_name, agent_id, tx_hash=tx_hash)
    return {"status": "success", "access": asdict(access)}
