import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.abspath("."))

from whitemagic.mcp_api_bridge import (
    gana_horn,
    gana_neck,
    gana_root,
    gana_room,
    gana_heart,
    gana_tail,
    gana_winnowing_basket,
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
    logger.debug("=== Verifying Eastern Quadrant Ganas ===")

    # 1. Horn
    await run_test(
        "Horn (Init)", gana_horn, task="session_init", session_name="Test Session"
    )

    # 2. Neck
    await run_test(
        "Neck (Memory)",
        gana_neck,
        task="memory_create",
        title="Test Memory",
        content="This is a test.",
    )

    # 3. Root
    await run_test("Root (Health)", gana_root, task="check_system_health")

    # 4. Room
    await run_test(
        "Room (Locks)",
        gana_room,
        task="manage_resource_locks",
        operation="acquire",
        resource_id="test_lock",
    )

    # 5. Heart
    await run_test("Heart (Context)", gana_heart, task="session_get_context")

    # 6. Tail
    await run_test("Tail (Acceleration)", gana_tail, task="check_acceleration")

    # 7. Winnowing Basket
    await run_test(
        "Winnowing Basket (Wisdom)", gana_winnowing_basket, task="extract_wisdom"
    )

    logger.debug("\n=== Verification Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
