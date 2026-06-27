#!/usr/bin/env python3
"""
Layer 2 Verification Script: Parallel Magic
===========================================
Tests the "Parallel Magic" components:
1. whitemagic-rs (Rust bridge)
2. Mojo Bridge
3. AdaptiveParallelExecutor (Python)
"""

import time
import asyncio
import logging

# Setup paths - rely on installed package
# ROOT_DIR = Path(__file__).parent.parent.parent
# sys.path.append(str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BridgeVerifier")

def test_rust_bridge():
    logger.info("--- Testing Rust Bridge (whitemagic-rs) ---")
    try:
        import whitemagic_rs
        logger.info("✅ whitemagic_rs imported successfully!")
        if hasattr(whitemagic_rs, 'SpatialIndex'):
             logger.info("✅ SpatialIndex class found.")
        else:
             logger.warning("⚠️ whitemagic_rs imported but SpatialIndex missing.")
    except ImportError as e:
        logger.warning(f"⚠️ whitemagic_rs import failed: {e}")
        logger.info("ℹ️ Note: This is expected if binaries are missing. Fallbacks should handle this.")

def test_mojo_bridge():
    """Mojo bridge removed in v23.2 — kept as no-op for backward compat."""
    logger.info("\n--- Mojo Bridge: skipped (removed in v23.2) ---")

async def test_parallel_executor():
    logger.info("\n--- Testing AdaptiveParallelExecutor ---")
    try:
        from whitemagic.cascade.advanced_parallel import AdaptiveParallelExecutor, ParallelTask, ParallelTier
        
        executor = AdaptiveParallelExecutor()
        logger.info("✅ AdaptiveParallelExecutor initialized.")
        
        # Define a simple task
        def dummy_task(x):
            time.sleep(0.01)
            return x * x
            
        tasks = [ParallelTask(id=str(i), func=dummy_task, args=(i,)) for i in range(10)]
        logger.info(f"   Created {len(tasks)} dummy tasks.")
        
        # Run them
        start = time.time()
        results = await executor.execute_parallel(tasks, tier=ParallelTier.TIER_0_TRIGRAMS)
        duration = time.time() - start
        
        logger.info(f"✅ Execution complete. Results: {results[:5]}...")
        logger.info(f"   Duration: {duration:.4f}s")
        
    except ImportError as e:
        logger.error(f"❌ Could not import AdaptiveParallelExecutor: {e}")
    except Exception as e:
        logger.error(f"❌ Parallel execution failed: {e}")

if __name__ == "__main__":
    import multiprocessing
    # Ensure safe multiprocessing start method
    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        pass
        
    test_rust_bridge()
    test_mojo_bridge()  # no-op since v23.2
    
    # Add timeout to async execution
    try:
        asyncio.run(asyncio.wait_for(test_parallel_executor(), timeout=10.0))
    except asyncio.TimeoutError:
        logger.error("❌ Parallel execution timed out!")
    except Exception as e:
        logger.error(f"❌ Execution failed: {e}")
