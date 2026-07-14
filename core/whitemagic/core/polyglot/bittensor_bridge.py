# ruff: noqa: BLE001
import asyncio
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class BittensorBridge:
    """Bridge to Bittensor Decentralized Intelligence Network.

    Initial focus: SN51 (lium.io / Datura) for compute resource discovery.
    Philosophy: "Muscle for the Nervous System".
    """

    def __init__(self) -> None:
        self.sn51_api = "https://api.lium.io/v1"  # Example endpoint for SN51 data
        self.last_discovery: datetime | None = None
        self.discovery_cache: dict[str, Any] = {}

    async def discover_resources(self, mining_type: str = "gpu") -> dict[str, Any]:
        """Scan SN51 for available compute resources.

        Attempts a live fetch from the lium.io marketplace API. Falls back
        to cached/default data when the endpoint is unreachable.
        """
        import aiohttp

        logger.info("🔍 Scanning Bittensor SN51 for %s resources...", mining_type)

        # Try live API fetch
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.sn51_api}/marketplace/status",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        data["subnet"] = 51
                        data["timestamp"] = datetime.now().isoformat()
                        self.discovery_cache = data
                        self.last_discovery = datetime.now()
                        return data
        except (TimeoutError, aiohttp.ClientError, OSError) as e:
            logger.debug("SN51 API unreachable, using fallback: %s", e)

        # Fallback when API is unreachable
        fallback_data = {
            "subnet": 51,
            "name": "Datura / lium.io",
            "available_instances": 0,
            "pricing": {
                "h100": "0.12 TAO/hr",
                "a100_80gb": "0.08 TAO/hr",
                "rtx_4090": "0.02 TAO/hr",
            },
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "fallback": True,
        }

        self.discovery_cache = fallback_data
        self.last_discovery = datetime.now()
        return fallback_data

    def get_resource_quote(self, requirement: str) -> dict[str, Any] | None:
        """Return a pricing quote for a specific requirement based on cache."""
        if not self.discovery_cache:
            return None

        pricing = self.discovery_cache.get("pricing", {})
        if "heavy" in requirement.lower() or "llm" in requirement.lower():
            return {"type": "h100", "price": pricing.get("h100")}
        return {"type": "rtx_4090", "price": pricing.get("rtx_4090")}


_bridge: BittensorBridge | None = None


def get_bittensor_bridge() -> BittensorBridge:
    """
    Get the bittensor bridge.

    Returns:
        BittensorBridge
    """
    global _bridge
    if _bridge is None:
        _bridge = BittensorBridge()
    return _bridge


if __name__ == "__main__":
    bridge = get_bittensor_bridge()
    asyncio.run(bridge.discover_resources())
    print(f"Bittensor Status: {bridge.discovery_cache['status']}")
    quote = bridge.get_resource_quote("heavy llm training")
    if quote is not None:
        print(f"H100 Price: {quote.get('price')}")
