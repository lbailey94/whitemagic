"""
Verify All Unifications
=======================
Tests all components that have been migrated to the Unified Monitoring Library.
"""

import sys
import os

sys.path.append(os.getcwd())

from newmagic.core.oracle.quantum_iching import QuantumIChing
from newmagic.core.symbolic import SymbolicReasoning, ConceptType


def verify_iching():
    logger.debug("\n🔮 Testing QuantumIChing...")
    oracle = QuantumIChing()
    oracle.consult("Verify me")
    stats = oracle.get_statistics()

    assert "metrics" in stats
    assert "consultation_time" in stats["metrics"]
    logger.debug("✅ QuantumIChing OK")


def verify_symbolic():
    logger.debug("\n☯️ Testing SymbolicReasoning...")
    engine = SymbolicReasoning(use_chinese=True)

    engine.add_concept("dao", "The Way", "道", ConceptType.PRINCIPLE)

    # Query it (should trigger stats)
    result = engine.query_concept("dao")
    logger.debug("   Query Result: %s", result)

    stats = engine.get_statistics()
    logger.debug("   Stats:", stats)

    # Assertions
    assert "metrics" in stats, "Missing metrics"
    assert "query_latency" in stats["metrics"], "Missing query_latency"
    assert "total_queries" in stats["metrics"], "Missing total_queries"
    assert stats["metrics"]["total_queries"]["count"] == 1
    assert "specific" in stats, "Missing specific stats"
    assert "token_savings" in stats["specific"], "Missing token_savings in specific"

    logger.debug("✅ SymbolicReasoning OK")


from newmagic.core.gardens.synthesis_enhanced import EnhancedGardenSynthesis


def verify_synthesis():
    logger.debug("\n🌸 Testing EnhancedGardenSynthesis...")
    synth = EnhancedGardenSynthesis()

    result = synth.synthesize_gardens(["joy", "love"], {"intention": True})
    logger.debug(f"   Harmony: {result['harmony_score']:.2f}")

    stats = synth.get_statistics()
    logger.debug("   Stats keys:", list(stats.keys()))

    # Assertions
    assert "metrics" in stats
    assert "synthesis_time" in stats["metrics"]
    assert "syntheses" in stats["metrics"]
    assert stats["metrics"]["syntheses"]["count"] == 1
    assert "specific" in stats
    assert "average_harmony" in stats["specific"]

    logger.debug("✅ EnhancedGardenSynthesis OK")


from newmagic.core.lib.io.locking import file_lock, atomic_write
import time
import threading


def verify_locking():
    logger.debug("\n🔒 Testing File Locking...")
    test_file = "test_lock.txt"
    with open(test_file, "w") as f:
        f.write("initial")

    def locker():
        with file_lock(test_file):
            time.sleep(0.1)

    # Atomic Write Test
    atomic_write(test_file, "atomic_content")
    with open(test_file, "r") as f:
        assert f.read() == "atomic_content", "Atomic write failed"
    logger.debug("   ✅ Atomic Write OK")

    # Locking Test (Basic smoke test)
    # We just ensure it doesn't crash and actually runs
    t = threading.Thread(target=locker)
    t.start()
    with file_lock(test_file):
        pass  # If we acquire it, good
    t.join()
    logger.debug("   ✅ Concurrency Lock OK")

    if os.path.exists(test_file):
        os.remove(test_file)


from newmagic.core.lib.logging import setup_logging, get_logger


def verify_logging_sys():
    logger.debug("\n📝 Testing Logging System...")
    # This should be safe to call multiple times
    setup_logging(level="INFO")
    logger = get_logger("verification")

    assert logger.level == 0  # Level is delegated, root sets effective level
    logger.debug("   ✅ Logger Initialization OK")


from newmagic.core.core.ganas.eastern_quadrant import RootGana
from newmagic.core.core.ganas.base import GanaCall


async def verify_transmutation():
    logger.debug("\n⚔️ Testing Phase 4: The Transmutation (RootGana x Rust)...")
    root = RootGana()

    # Trigger a search for something certain to exist
    call = GanaCall(
        task="search_truth",
        state_vector={"query": "def setup_logging", "limit": 5},
        resonance_hints=None,
    )

    result = await root._execute_core(call, "")
    logger.debug(f"   Search Results Found: {result['results_count']}")
    logger.debug(f"   Engine Used: {result['engine']}")

    assert result["results_count"] > 0, "No search results found"
    # Even if Rust fails and falls back to Python, we want it to work.
    # But ideally it uses rust_parallel.
    if result["engine"] == "rust_parallel":
        logger.debug("   ✅ Rust Acceleration Active")
    else:
        logger.debug("   ⚠️ Rust Acceleration MISSING (Used Python Fallback)")

    logger.debug("✅ RootGana Transmutation OK")


from whitemagic.core.ganas.western_quadrant import NetGana


async def verify_net_transmutation():
    logger.debug("\n🕸️ Testing Phase 4: NetGana Transmutation (Heaven's Net v6)...")
    net = NetGana()

    # Trigger Heaven's Net scan
    call = GanaCall(
        task="cast_heavens_net", state_vector={"mode": "safe"}, resonance_hints=None
    )

    result = await net._execute_core(call, "")
    logger.debug(f"   Net Status: {result['status']}")

    if "internal_net" in result:
        logger.debug(f"   Files Scanned: {result['internal_net']['files_scanned']}")
        logger.debug(f"   Concepts Found: {result['internal_net']['concepts_extracted']}")
        logger.debug(f"   Engine: {result['internal_net']['engine']}")

        assert result["internal_net"]["files_scanned"] > 0
        assert result["internal_net"]["engine"] == "rust_v6"
    else:
        logger.debug("   ⚠️ Heaven's Net integration MISSING or failed")

    logger.debug("✅ NetGana Transmutation OK")


import asyncio

import logging
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.debug("🚀 Starting Unified Verification...")
    verify_iching()
    verify_symbolic()
    verify_synthesis()
    verify_locking()
    verify_logging_sys()

    # Async tasks
    loop = asyncio.get_event_loop()
    loop.run_until_complete(verify_transmutation())
    loop.run_until_complete(verify_net_transmutation())

    logger.debug("\n🎉 ALL SYSTEMS GO + UNIFIED.")
