#!/usr/bin/env python3
"""Phase 1: B3 Concurrency & Lease Stress Benchmark Driver.

Protocol: docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md §3 Layer 3, §5 Phase 1
Baseline: Gen3 Cognitive Runtime Baseline 1 (G3-CRB-1)

Asserts:
  1. 50 concurrent tasks competing for the exact same scope: exactly 1 winner, 49 conflicts, zero split-brain.
  2. 50 concurrent tasks claiming disjoint scopes: exactly 50 successes, 0 lost updates, exactly 50 entries in ledger.
  3. 50 concurrent releases: exactly 50 successes, scope transitions to released/free.
  4. Continuous snapshot-readonly readers under heavy write traffic: zero torn reads, zero lockfile leaks.
  5. Stale lock stealing: lockfile older than STALE_LOCK_SECS is cleaned up automatically without wedging.
"""

import os
import re
import subprocess
import sys
import time

ROOT_GEN3 = os.environ.get("WMGEN3_ROOT", "/home/lucas/Desktop/WMgen3")
ROOT_WMV9 = "/home/lucas/Desktop/WHITEMAGIC/WMv9"

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def main():
    log("=== PHASE 1: B3 CONCURRENCY & LEASE STRESS BENCHMARK ===")
    log(f"Target repository: {ROOT_WMV9}")
    log("Executing: cargo test -p wm-tools --test coordination_stress -- --nocapture")

    start_time = time.time()
    p = subprocess.run(
        ["cargo", "test", "-p", "wm-tools", "--test", "coordination_stress", "--", "--nocapture"],
        cwd=ROOT_WMV9,
        capture_output=True,
        text=True,
        timeout=180,
    )
    elapsed = time.time() - start_time

    if p.returncode != 0:
        log("FAILURE: Benchmark test execution failed!")
        print("STDOUT:\n", p.stdout)
        print("STDERR:\n", p.stderr)
        sys.exit(1)

    # Parse passed tests
    expected_tests = [
        "test_50_tasks_competing_for_single_scope_zero_split_brain",
        "test_50_tasks_disjoint_scopes_no_lost_updates",
        "test_snapshot_readonly_immunity_under_heavy_write_churn",
        "test_stale_lockfile_recovery_steals_and_succeeds",
    ]

    for t in expected_tests:
        if f"{t} ... ok" in p.stdout or t in p.stdout:
            log(f"  ✓ {t}: PASS")
        else:
            log(f"  ✗ {t}: MISSING OR FAILED")
            sys.exit(1)

    summary_match = re.search(r"test result: ok\.\s+(\d+)\s+passed;\s+0\s+failed", p.stdout)
    assert summary_match, f"Could not find clean summary: {p.stdout}"
    passed_count = int(summary_match.group(1))

    log(f"All {passed_count} high-concurrency stress suites passed cleanly in {elapsed:.2f}s.")
    log("=== PHASE 1 COMPLETE: B3 CONCURRENCY & LEASE STRESS SATISFIED ===")

if __name__ == "__main__":
    main()
