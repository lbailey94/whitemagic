"""
Verification: Phase 3 Unification (Stats)
=========================================
Tests if QuantumIChing correctly inherits from BaseMonitor and reports unified stats.
"""

import sys
import os

# Ensure we can import from staging/core_system
sys.path.append(os.getcwd())

from newmagic.core.oracle.quantum_iching import QuantumIChing

import logging
logger = logging.getLogger(__name__)


def verify():
    logger.debug("🔍 Testing QuantumIChing Unification...")

    # 1. Instantiate
    oracle = QuantumIChing()
    logger.debug("✅ Instantiation successful.")

    # 2. Run Operation (Should trigger latencies)
    logger.debug("🔮 Running consultation...")
    result = oracle.consult("Test unified stats?")
    logger.debug(f"✅ Result: Hexagram #{result.primary_hexagram}")

    # 3. Check Stats
    stats = oracle.get_statistics()
    logger.debug("📊 Statistics:")
    logger.debug(stats)

    # 4. Assertions
    assert "uptime_sec" in stats, "Missing 'uptime_sec' from BaseMonitor"
    assert "metrics" in stats, "Missing 'metrics' from BaseMonitor"
    assert "consultation_time" in stats["metrics"], "Missing 'consultation_time' metric"
    assert stats["metrics"]["consultation_time"]["count"] == 1, "Metric count mismatch"
    assert "specific" in stats, "Missing 'specific' component stats"

    logger.debug("\n✅ VERIFICATION PASSED: Unification successful.")


if __name__ == "__main__":
    verify()
