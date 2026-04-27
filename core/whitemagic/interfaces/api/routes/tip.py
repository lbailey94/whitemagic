"""Tip endpoint — gratitude economy API.

Provides a simple HTTP endpoint for checking tip status and
initiating gratitude flows. Requires WM_XRP_ADDRESS to be set.
"""

from __future__ import annotations

from typing import Any

try:
    from fastapi import APIRouter, HTTPException

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = None  # type: ignore[misc,assignment]

from whitemagic.core.economy.wallet_manager import get_wallet

if HAS_FASTAPI:
    router = APIRouter(prefix="/tip", tags=["economy"])
else:
    router = None


def _build_response(data: dict[str, Any]) -> dict[str, Any]:
    """Stable JSON envelope for all tip responses."""
    return {
        "status": "success",
        "tool": "tip",
        "data": data,
    }


if HAS_FASTAPI and router is not None:

    @router.get("/status")
    async def tip_status() -> dict[str, Any]:
        """Get current wallet status and last known balance."""
        wallet = get_wallet()
        if not wallet.enabled:
            return _build_response({
                "enabled": False,
                "message": "Wallet not configured. Set WM_XRP_ADDRESS to enable.",
            })
        return _build_response({
            "enabled": True,
            "address": wallet.public_address,
            "last_balance": wallet.last_balance,
            "currency": "XRP",
        })

    @router.post("/scan")
    async def tip_scan() -> dict[str, Any]:
        """Scan XRPL for new tips to the configured address."""
        wallet = get_wallet()
        if not wallet.enabled:
            raise HTTPException(status_code=503, detail="Wallet not configured")
        tip = await wallet.check_for_tips()
        if tip is not None and tip > 0:
            return _build_response({
                "tip_detected": True,
                "amount": round(tip, 6),
                "currency": "XRP",
                "message": f"Gratitude resonance detected: {tip} XRP",
            })
        return _build_response({
            "tip_detected": False,
            "amount": 0.0,
            "message": "No new tips detected",
        })

    @router.post("/settle")
    async def tip_settle(amount: float) -> dict[str, Any]:
        """Propose a gratitude settlement split across beneficiaries."""
        wallet = get_wallet()
        if not wallet.enabled:
            raise HTTPException(status_code=503, detail="Wallet not configured")
        proposal = wallet.propose_gratitude_settlement(amount)
        return _build_response(proposal)
