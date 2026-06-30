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


def verify():
    print("🔍 Testing QuantumIChing Unification...")

    # 1. Instantiate
    oracle = QuantumIChing()
    print("✅ Instantiation successful.")

    # 2. Run Operation (Should trigger latencies)
    print("🔮 Running consultation...")
    result = oracle.consult("Test unified stats?")
    print(f"✅ Result: Hexagram #{result.primary_hexagram}")

    # 3. Check Stats
    stats = oracle.get_statistics()
    print("📊 Statistics:")
    print(stats)

    # 4. Assertions
    assert "uptime_sec" in stats, "Missing 'uptime_sec' from BaseMonitor"
    assert "metrics" in stats, "Missing 'metrics' from BaseMonitor"
    assert "consultation_time" in stats["metrics"], "Missing 'consultation_time' metric"
    assert stats["metrics"]["consultation_time"]["count"] == 1, "Metric count mismatch"
    assert "specific" in stats, "Missing 'specific' component stats"

    print("\n✅ VERIFICATION PASSED: Unification successful.")


if __name__ == "__main__":
    verify()
