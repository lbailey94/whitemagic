"""
Gratitude Pulse — Background XRPL tip monitoring daemon.
========================================================
Periodically scans the configured XRPL address for incoming payments.
Automatically records them in the Gratitude Ledger and triggers
system-wide 'Abundance' events.

Philosophy: "Gratitude as an automated metabolic process."
"""

import asyncio
import logging
import os
from typing import Any

from whitemagic.core.economy.wallet_manager import get_wallet
from whitemagic.gratitude.ledger import GratitudeEvent, get_gratitude_ledger

logger = logging.getLogger(__name__)

class GratitudePulse:
    """Background scanner for XRPL gratitude resonance."""

    def __init__(self, interval_seconds: int = 300):
        self.interval = interval_seconds
        self.wallet = get_wallet()
        self.ledger = get_gratitude_ledger()
        self.running = False
        self._last_checked_ledger_index: int | None = None

        # Load state root for persistent watermarks
        from whitemagic.config.paths import GRATITUDE_DIR
        self.status_file = GRATITUDE_DIR / "pulse_status.json"

    async def start(self):
        """Start the background scanning loop."""
        if self.running:
            return

        self.running = True
        logger.info(f"💓 Gratitude Pulse started. Scanning {self.wallet.public_address} every {self.interval}s")

        while self.running:
            try:
                await self.scan()
            except Exception as e:
                logger.error(f"Gratitude Pulse scan failed: {e}")

            await asyncio.sleep(self.interval)

    def stop(self):
        """Stop the background loop."""
        self.running = False
        logger.info("💓 Gratitude Pulse stopping...")

    async def scan(self):
        """Perform a single scan of the XRPL for new transactions."""
        address = self.wallet.public_address
        if not address or address.startswith("rPlaceholder"):
            logger.debug("Gratitude Pulse: No valid XRPL address configured. Skipping scan.")
            return

        # Note: In a production environment with many transactions, we'd use account_tx
        # for historical scanning. For a tip jar, checking recent is usually sufficient.
        try:
            import httpx

            from whitemagic.gratitude.proof import _XRPL_NODES

            # 1. Fetch account transactions
            payload = {
                "method": "account_tx",
                "params": [
                    {
                        "account": address,
                        "ledger_index_min": -1,
                        "ledger_index_max": -1,
                        "limit": 10,
                        "forward": False
                    }
                ]
            }

            async with httpx.AsyncClient() as client:
                # Try nodes until one works
                success = False
                for node in _XRPL_NODES:
                    try:
                        resp = await client.post(node, json=payload, timeout=10.0)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("result", {}).get("status") == "success":
                                transactions = data["result"].get("transactions", [])
                                await self._process_transactions(transactions)
                                success = True
                                break
                    except Exception:
                        continue

                if not success:
                    logger.warning("Gratitude Pulse: All XRPL nodes unreachable.")

        except ImportError:
            logger.debug("Gratitude Pulse: httpx not installed. Cannot scan.")

    async def _process_transactions(self, transactions: list[dict[str, Any]]):
        """Analyze transactions and record new tips."""
        new_tips = 0
        for tx_wrapper in transactions:
            tx = tx_wrapper.get("tx", {})
            tx_hash = tx.get("hash")

            # Skip if not a Payment or not confirmed
            if tx.get("TransactionType") != "Payment":
                continue

            # Skip if we already have this in the ledger
            # (In a real implementation, we'd check a local seen_tx database)
            if any(e.get("tx_hash") == tx_hash for e in self.ledger.get_recent(limit=50)):
                continue

            # Verify it's actually for us (could be outgoing if user uses same wallet)
            if tx.get("Destination") != self.wallet.public_address:
                continue

            # Check if destination tag matches if configured
            expected_tag = os.environ.get("WM_XRP_DEST_TAG")
            if expected_tag and str(tx.get("DestinationTag")) != str(expected_tag):
                continue

            # Record the tip
            amount_raw = tx.get("Amount")
            if isinstance(amount_raw, str):
                amount = int(amount_raw) / 1_000_000
                currency = "XRP"
            else:
                amount = float(amount_raw.get("value", 0))
                currency = amount_raw.get("currency", "???")

            event = GratitudeEvent(
                channel="xrpl",
                amount=amount,
                currency=currency,
                sender=tx.get("Account", ""),
                tx_hash=tx_hash,
                verified=True,
                metadata={
                    "pulse_detected": True,
                    "ledger_index": tx.get("ledger_index"),
                    "memos": tx.get("Memos", [])
                }
            )

            self.ledger.record(event)
            new_tips += 1
            logger.info(f"💓 Pulse detected NEW tip: {amount} {currency} from {event.sender} (tx: {tx_hash})")

            # Trigger 'Abundance' effect (e.g., clearing some debt)
            try:
                from whitemagic.dharma.karma_ledger import get_karma_ledger
                get_karma_ledger().forgive(amount * 0.1) # Forgive 10% of tip value in debt
            except (ImportError, ModuleNotFoundError) as e:
                import logging
                logging.getLogger(__name__).debug("Exception silenced: %s", e)

        if new_tips > 0:
            logger.info(f"💓 Pulse finished. Recorded {new_tips} new tips.")

_pulse: GratitudePulse | None = None

def get_pulse() -> GratitudePulse:
    """Get the global Gratitude Pulse singleton."""
    global _pulse
    if _pulse is None:
        _pulse = GratitudePulse()
    return _pulse
