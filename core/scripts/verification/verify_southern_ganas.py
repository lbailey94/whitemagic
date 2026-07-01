import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.abspath("."))

from whitemagic.mcp_api_bridge import (
    gana_ghost,
    gana_willow,
    gana_star,
    gana_extended_net,
    gana_wings,
    gana_chariot,
    gana_abundance,
)

import logging
logger = logging.getLogger(__name__)


async def run_test(name, func, **kwargs):
    logger.debug(f"\nTesting {name}...")
    try:
        result = await func(**kwargs)
        logger.debug(f"✓ {name} Success")
        logger.debug(json.dumps(result, indent=2, default=str))
        return True
    except Exception as e:
        logger.debug(f"✗ {name} Failed: {e}")
        return False


async def main():
    logger.debug("=== Verifying Southern Quadrant Ganas ===")

    # 1. Ghost (Introspection)
    await run_test(
        "Ghost (Metric)",
        gana_ghost,
        task="track_metric",
        metric="test_metric",
        value=100.0,
    )

    # 2. Willow (Flexibility)
    await run_test("Willow (Adapt)", gana_willow, task="adapt_ui")

    # 3. Star (Governance)
    await run_test("Star (Context)", gana_star, task="prat_get_context")

    # 4. Extended Net (Connection)
    await run_test(
        "Extended Net (Monitor)",
        gana_extended_net,
        task="manage_resonance",
        operation="monitor",
    )

    # 5. Wings (Expansion)
    await run_test("Wings (Parallel)", gana_wings, task="check_status")

    # 6. Chariot (Mobility)
    await run_test(
        "Chariot (Scan)",
        gana_chariot,
        task="manage_archaeology",
        operation="scan",
        directory=".",
    )

    # 7. Abundance (Surplus)
    await run_test("Abundance (Check)", gana_abundance, task="check_surplus")

    logger.debug("\n=== Verification Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
