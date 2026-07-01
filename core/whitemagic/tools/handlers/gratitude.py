# ruff: noqa: BLE001
"""Gratitude Handlers — MCP tool handlers for the Gratitude Architecture.
======================================================================
Tools:
  - whitemagic.tip: Record a gratitude tip (XRPL or manual)
  - gratitude.stats: Get gratitude ledger statistics
  - gratitude.benefits: Check an agent's gratitude benefits
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def get_recipient_address() -> str | None:
    """Get the configured XRP recipient address for gratitude tips."""
    return os.environ.get("WM_XRP_ADDRESS") or os.environ.get("XRP_ADDRESS")


def handle_tip(**kwargs: Any) -> dict[str, Any]:
    """Record a gratitude tip.

    Args:
        amount: Tip amount (default: 1.0)
        currency: XRP or USDC (default: XRP)
        channel: xrpl / x402 / manual (default: manual)
        sender: Sender identifier (optional)
        agent_id: Agent making the tip (optional)
        tx_hash: On-chain transaction hash for verification (optional)
        message: Optional gratitude message

    """
    from whitemagic.gratitude.ledger import (
        GratitudeEvent,
        get_gratitude_ledger,
    )

    amount = float(kwargs.get("amount", 1.0))
    currency = kwargs.get("currency", "XRP")
    channel = kwargs.get("channel", "manual")
    sender = kwargs.get("sender", "")
    agent_id = kwargs.get("agent_id", "")
    tx_hash = kwargs.get("tx_hash", "")
    message = kwargs.get("message", "")

    verified = False
    if tx_hash:
        try:
            if channel == "xrpl":
                from whitemagic.gratitude.proof import verify_xrpl_payment

                result = verify_xrpl_payment(tx_hash)
                verified = result.get("verified", False)
            elif channel == "x402":
                from whitemagic.gratitude.proof import verify_x402_payment

                result = verify_x402_payment(tx_hash)
                verified = result.get("verified", False)
        except Exception as exc:
            logger.warning(
                "Verification failed for %s: %s", tx_hash, exc, exc_info=True
            )

    event = GratitudeEvent(
        channel=channel,
        amount=amount,
        currency=currency,
        sender=sender,
        agent_id=agent_id,
        tx_hash=tx_hash,
        verified=verified,
        metadata={"message": message} if message else {},
    )

    ledger = get_gratitude_ledger()
    ledger.record(event)

    logger.info(
        "Gratitude recorded: %s %s via %s (verified=%s)",
        amount,
        currency,
        channel,
        verified,
        exc_info=True,
    )

    # Generate payment link for XRPL if manual/failed
    payment_link = ""
    if channel == "xrpl" and not verified:
        xrp_address = get_recipient_address()
        if not xrp_address:
            return {
                "recorded": False,
                "error_code": "not_configured",
                "message": "Set WM_XRP_ADDRESS to enable gratitude tips",
                "instruction": "To enable tipping, set your XRP address: export WM_XRP_ADDRESS=<your_address>",
            }
        # Generate Xaman (XUMM) payment link
        payment_link = f"https://xumm.app/detect/request:{xrp_address}?amount={int(amount * 1_000_000)}"
        if kwargs.get("dest_tag"):
            payment_link += f"&dt={kwargs.get('dest_tag')}"

    response = {
        "recorded": True,
        "amount": amount,
        "currency": currency,
        "channel": channel,
        "verified": verified,
        "message": "Thank you for your gratitude! 🙏"
        if not verified
        else "Verified on-chain. Thank you! 🙏✅",
    }

    if payment_link:
        response["payment_link"] = payment_link
        response["instruction"] = (
            f"To complete your tip, use this Xaman link: {payment_link}"
        )

    return response


def handle_gratitude_stats(**kwargs: Any) -> dict[str, Any]:
    """Get gratitude ledger statistics."""
    from whitemagic.gratitude.ledger import get_gratitude_ledger

    ledger = get_gratitude_ledger()
    stats = ledger.get_stats()
    recent = ledger.get_recent(limit=kwargs.get("limit", 5))

    return {
        **stats,
        "recent": recent,
    }


def handle_gratitude_benefits(**kwargs: Any) -> dict[str, Any]:
    """Check gratitude benefits for an agent."""
    from whitemagic.gratitude.proof import get_gratitude_benefits

    agent_id = kwargs.get("agent_id", "default")
    result = get_gratitude_benefits(agent_id)
    if isinstance(result, dict):
        return result
    return {"agent_id": agent_id, "benefits": []}
    """Check gratitude benefits for an agent."""
    from whitemagic.gratitude.proof import get_gratitude_benefits

    agent_id = kwargs.get("agent_id", "default")
    result = get_gratitude_benefits(agent_id)
    if isinstance(result, dict):
        return result
    return {"agent_id": agent_id, "benefits": []}
