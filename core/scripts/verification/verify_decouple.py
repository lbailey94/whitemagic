try:
    from whitemagic.local_ml.bitnet_inference import get_bitnet_engine

    engine = get_bitnet_engine()
    print(f"Engine Load Success: {True}")
    print(f"Engine Available: {engine.available}")
    print(f"Status: {engine.get_status()}")
except Exception as e:
    print(f"CRITICAL FAILURE: {e}")
