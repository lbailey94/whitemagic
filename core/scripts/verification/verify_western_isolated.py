import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.abspath("."))

from whitemagic.core.ganas.base import GanaCall
from whitemagic.core.ganas.western_quadrant import (
    StraddlingLegsGana,
    MoundGana,
    StomachGana,
    HairyHeadGana,
    NetGana,
    TurtleBeakGana,
    ThreeStarsGana,
)

import logging
logger = logging.getLogger(__name__)


async def test_gana(name, gana_class, task, **kwargs):
    logger.debug(f"\nTesting {name}...")
    try:
        gana = gana_class()
        call = GanaCall(task=task, state_vector=kwargs)
        result = await gana.invoke(call)
        logger.debug(f"✓ {name} Success")
        logger.debug(
            json.dumps(
                {
                    "mansion": result.mansion.name,
                    "garden": result.garden,
                    "result": result.output,
                },
                indent=2,
                default=str,
            )
        )
        return True
    except Exception as e:
        logger.debug(f"✗ {name} Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    logger.debug("=== Verifying Western Quadrant Ganas (Isolated) ===", flush=True)

    # 1. Legs
    logger.debug(">> Testing Legs...", flush=True)
    await test_gana("Legs", StraddlingLegsGana, "check_balance")
    logger.debug("<< Legs Done", flush=True)

    # 2. Mound
    logger.debug(">> Testing Mound...", flush=True)
    await test_gana("Mound", MoundGana, "check_storage")
    logger.debug("<< Mound Done", flush=True)

    # 3. Stomach
    logger.debug(">> Testing Stomach...", flush=True)
    await test_gana("Stomach", StomachGana, "check_energy")
    logger.debug("<< Stomach Done", flush=True)

    # 4. Hairy Head
    logger.debug(">> Testing Hairy Head...", flush=True)
    await test_gana("Hairy Head", HairyHeadGana, "validate_integrations")
    logger.debug("<< Hairy Head Done", flush=True)

    # 5. Net
    logger.debug(">> Testing Net...", flush=True)
    from unittest.mock import MagicMock, patch

    # Mock the pattern API to avoid heavy DB calls and Rust issues
    mock_api = MagicMock()
    mock_api.get_stats.return_value = {"total_patterns": 42, "status": "mocked"}
    mock_api.search.return_value = []

    with patch(
        "whitemagic.intelligence.synthesis.unified_patterns.get_pattern_api",
        return_value=mock_api,
    ):
        await test_gana("Net", NetGana, "detect_patterns")

    logger.debug("<< Net Done", flush=True)

    # 6. Turtle Beak
    logger.debug(">> Testing Turtle Beak...", flush=True)
    await test_gana("Turtle Beak", TurtleBeakGana, "validate_command", command="ls -la")
    logger.debug("<< Turtle Beak Done", flush=True)

    # 7. Three Stars
    logger.debug(">> Testing Three Stars...", flush=True)
    await test_gana(
        "Three Stars",
        ThreeStarsGana,
        "consult_wisdom_council",
        question="Test question",
    )
    logger.debug("<< Three Stars Done", flush=True)

    logger.debug("\n=== Verification Complete ===", flush=True)


if __name__ == "__main__":
    logger.debug("Starting main execution...", flush=True)
    try:
        asyncio.run(main())
        logger.debug("Main execution finished.", flush=True)
    except Exception as e:
        logger.debug(f"CRASHED: {e}", flush=True)
