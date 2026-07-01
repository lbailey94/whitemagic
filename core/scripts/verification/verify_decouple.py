
import logging
logger = logging.getLogger(__name__)
try:
    from whitemagic.local_ml.bitnet_inference import get_bitnet_engine

    engine = get_bitnet_engine()
    logger.debug(f"Engine Load Success: {True}")
    logger.debug(f"Engine Available: {engine.available}")
    logger.debug(f"Status: {engine.get_status()}")
except Exception as e:
    logger.debug(f"CRITICAL FAILURE: {e}")
