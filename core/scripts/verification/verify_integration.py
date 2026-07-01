import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)

# Make sure we can import whitemagic
import sys
import os
logger = logging.getLogger(__name__)

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # Auto-fixed path

try:
    from whitemagic.core.ganas.base import GanaCall
    from whitemagic.core.ganas.western_quadrant import NetGana
    from whitemagic.core.ganas.southern_quadrant import ExtendedNetGana
except ImportError as e:
    logger.debug(f"ImportError: {e}")
    sys.exit(1)


async def test_integration():
    logger.debug("=== Testing Integration (Async DB Access) ===")

    # 1. Test NetGana (West) - Global Stats
    logger.debug("\n[1] Testing NetGana (West)...")
    net = NetGana()
    call = GanaCall(task="detect_patterns", state_vector={})

    # This should NOT hang if the fix works
    result = await net.invoke(call)
    logger.debug("✓ NetGana returned successfully")
    logger.debug(f"Result keys: {result.output.keys()}")

    # 2. Test ExtendedNetGana (South) - Search
    logger.debug("\n[2] Testing ExtendedNetGana (South)...")
    extended = ExtendedNetGana()
    # Ensure Pattern API is instantiated inside
    try:
        call_search = GanaCall(
            task="search_all_patterns",
            state_vector={"query": "test", "min_confidence": 0.0},
        )
        result_search = await extended.invoke(call_search)
        logger.debug("✓ ExtendedNetGana returned successfully")
        logger.debug(f"Patterns found: {result_search.output.get('pattern_count', 0)}")
    except Exception as e:
        logger.debug(f"ExtNet Error: {e}")

    logger.debug("\n=== Integration Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_integration())
