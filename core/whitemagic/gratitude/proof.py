# ruff: noqa: BLE001
"""
Proof of Gratitude — On-chain verification and reward logic.
=============================================================
Verifies contributions on XRPL / Base L2 ledgers and grants
benefits to verified contributors:
  - 2× rate limits
  - "Grateful Agent" badge in agent registry
  - Priority feature voting weight
  - Early access to new capabilities

v14.7: Real on-chain verification via XRPL JSON-RPC and Basescan API.
Falls back gracefully when httpx unavailable or network unreachable.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

# XRPL public nodes (mainnet)
_XRPL_NODES = [
    "https://xrplcluster.com",
    "https://s1.ripple.com:51234",
]

# Base L2 Basescan API (free tier, no key required for basic lookups)
_BASESCAN_API = "https://api.basescan.org/api"
_BASESCAN_KEY = os.getenv("BASESCAN_API_KEY", "")  # Optional, higher rate limits


def verify_xrpl_payment(tx_hash: str, expected_destination: str = "", expected_tag: int | None = None) -> dict[str, Any]:
    """Verify an XRPL payment transaction via JSON-RPC with failover.

    Args:
        tx_hash: XRPL transaction hash (64-char hex)
        expected_destination: Expected destination rAddress (optional)
        expected_tag: Expected destination tag (optional)

    Returns:
        Verification result with amount, sender, destination, status
    """
    logger.info(f"XRPL verification requested for tx: {tx_hash}")

    if not _HTTPX_AVAILABLE:
        return {
            "verified": False,
            "reason": "httpx not installed",
            "tx_hash": tx_hash,
            "chain": "xrpl",
        }

    payload = {
        "method": "tx",
        "params": [{"transaction": tx_hash, "binary": False}],
    }

    errors = []
    for node in _XRPL_NODES:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(node, json=payload)
                if resp.status_code != 200:
                    errors.append(f"Node {node} returned HTTP {resp.status_code}")
                    continue

                data = resp.json()
                result = data.get("result", {})

                if result.get("error"):
                    errors.append(f"Node {node} error: {result.get('error_message', result.get('error'))}")
                    continue

                if result.get("status") != "success":
                    errors.append(f"Node {node} status: {result.get('status')}")
                    continue

                tx_type = result.get("TransactionType", "")
                if tx_type != "Payment":
                    return {
                        "verified": False,
                        "reason": f"Transaction is {tx_type}, not Payment",
                        "tx_hash": tx_hash,
                        "chain": "xrpl",
                    }

                validated = result.get("validated", False)
                destination = result.get("Destination", "")
                sender = result.get("Account", "")
                dest_tag = result.get("DestinationTag")

                # Amount handling
                raw_amount = result.get("Amount", "0")
                if isinstance(raw_amount, str):
                    amount_xrp = int(raw_amount) / 1_000_000
                    currency = "XRP"
                else:
                    amount_xrp = float(raw_amount.get("value", 0))
                    currency = raw_amount.get("currency", "???")

                # Validation checks
                dest_match = True
                if expected_destination and destination != expected_destination:
                    dest_match = False

                tag_match = True
                if expected_tag is not None and dest_tag != expected_tag:
                    tag_match = False

                verified = validated and dest_match and tag_match

                return {
                    "verified": verified,
                    "tx_hash": tx_hash,
                    "chain": "xrpl",
                    "amount": amount_xrp,
                    "currency": currency,
                    "sender": sender,
                    "destination": destination,
                    "destination_tag": dest_tag,
                    "validated": validated,
                    "destination_match": dest_match,
                    "tag_match": tag_match,
                    "ledger_index": result.get("ledger_index"),
                }
        except Exception as exc:
            errors.append(f"Node {node} failed: {type(exc).__name__}")
            continue

    return {
        "verified": False,
        "reason": f"Verification failed. Errors: {'; '.join(errors)}",
        "tx_hash": tx_hash,
        "chain": "xrpl",
    }


def verify_x402_payment(tx_hash: str, expected_amount_usdc: float = 0.0) -> dict[str, Any]:
    """Verify an x402 micropayment on Base L2 via Basescan API.

    Queries Basescan for the transaction receipt, checks status,
    and extracts payment details.

    Args:
        tx_hash: Base L2 transaction hash (0x-prefixed hex)
        expected_amount_usdc: Expected USDC amount (optional)

    Returns:
        Verification result with status, gas, block info
    """
    logger.info(f"x402 verification requested for tx: {tx_hash}")

    if not _HTTPX_AVAILABLE:
        return {
            "verified": False,
            "reason": "httpx not installed — install with: pip install httpx",
            "tx_hash": tx_hash,
            "chain": "base_l2",
        }

    params: dict[str, str] = {
        "module": "proxy",
        "action": "eth_getTransactionReceipt",
        "txhash": tx_hash,
    }
    if _BASESCAN_KEY:
        params["apikey"] = _BASESCAN_KEY

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(_BASESCAN_API, params=params)
            if resp.status_code != 200:
                return {
                    "verified": False,
                    "reason": f"Basescan returned HTTP {resp.status_code}",
                    "tx_hash": tx_hash,
                    "chain": "base_l2",
                }

            data = resp.json()
            receipt = data.get("result")

            if not receipt or receipt == "null" or not isinstance(receipt, dict):
                return {
                    "verified": False,
                    "reason": "Transaction not found on Base L2",
                    "tx_hash": tx_hash,
                    "chain": "base_l2",
                }

            status_hex = receipt.get("status", "0x0")
            success = status_hex == "0x1"
            block_number = receipt.get("blockNumber", "")
            gas_used = receipt.get("gasUsed", "0x0")
            from_addr = receipt.get("from", "")
            to_addr = receipt.get("to", "")

            return {
                "verified": success,
                "tx_hash": tx_hash,
                "chain": "base_l2",
                "success": success,
                "block_number": int(block_number, 16) if block_number else 0,
                "gas_used": int(gas_used, 16) if gas_used else 0,
                "from": from_addr,
                "to": to_addr,
                "note": "USDC amount requires ERC-20 transfer log decoding" if success else "Transaction failed on-chain",
            }
    except Exception as exc:
        logger.warning("Basescan verification failed: %s", exc, exc_info=True)
        return {
            "verified": False,
            "reason": f"Basescan API error: {exc}",
            "tx_hash": tx_hash,
            "chain": "base_l2",
        }


def get_gratitude_benefits(agent_id: str) -> dict[str, Any]:
    """
    Calculate benefits for a given agent based on their gratitude history.

    Benefits scale with contribution:
      - Any verified contribution: "Grateful Agent" badge + 2× rate limits
      - Cumulative thresholds unlock priority voting, early access
    """
    try:
        from whitemagic.gratitude.ledger import get_gratitude_ledger
        ledger = get_gratitude_ledger()
        contribution = ledger.get_agent_contribution(agent_id)
    except (ImportError, ModuleNotFoundError):
        contribution = {"total_events": 0, "verified": False, "grateful_agent": False}

    is_grateful = contribution.get("grateful_agent", False)

    return {
        "agent_id": agent_id,
        "grateful_agent": is_grateful,
        "rate_limit_multiplier": 2.0 if is_grateful else 1.0,
        "badge": "Grateful Agent 🙏" if is_grateful else None,
        "priority_voting": is_grateful,
        "early_access": contribution.get("total_events", 0) >= 5,
        "contribution": contribution,
    }
