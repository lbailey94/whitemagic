import sys
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

# Ensure whitemagic is in path
sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    from whitemagic.archaeology import get_archaeologist, mark_read
    from whitemagic.tools.handlers.archaeology import handle_archaeology

    logger.debug("--- Archaeology Verification ---")

    arch = get_archaeologist()
    logger.debug(f"Archaeologist instance: {arch}")

    res = mark_read("/tmp/test_file.txt", context="Verification", note="Testing bridge")
    logger.debug(f"Mark Read result: {res}")

    handler_res = handle_archaeology(action="stats")
    logger.debug(f"Handler stats result: {handler_res}")

    logger.debug("\n✅ Archaeology bridge is functional.")

except Exception as e:
    logger.debug(f"\n❌ Archaeology verification failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
