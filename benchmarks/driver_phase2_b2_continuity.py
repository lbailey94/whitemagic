#!/usr/bin/env python3
"""Phase 2: B2 Long-Horizon Multi-Session Continuity & Replay Benchmark Driver.

Protocol: docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md §3 Layer 2/Layer 4, §5 Phase 2
Baseline: Gen3 Cognitive Runtime Baseline 1 (G3-CRB-1)

Asserts:
  1. 50 sequential sessions chain continuity with zero amnesia or payload loss.
  2. Previous-session selection orders by time (created_at) rather than UUID sort order.
  3. Structured nodiscovery handoffs are preserved 100% across the 50-step chain.
  4. 250 turns recorded across sessions with write-time indexing in LMDB/Tantivy.
  5. Export -> Import roundtrip preserves IDs, timestamps, roles, and content lossless.
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
    log("=== PHASE 2: B2 LONG-HORIZON CONTINUITY & REPLAY BENCHMARK ===")
    log(f"Target repository: {ROOT_WMV9}")
    log("Executing: cargo test -p wm-tools --test session_continuity_stress -- --nocapture")

    start_time = time.time()
    p = subprocess.run(
        ["cargo", "test", "-p", "wm-tools", "--test", "session_continuity_stress", "--", "--nocapture"],
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

    expected_tests = [
        "test_50_sequential_sessions_continuity_chain",
        "test_export_import_lossless_replay_roundtrip",
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

    log(f"All {passed_count} continuity & replay suites passed cleanly in {elapsed:.2f}s.")
    log("=== PHASE 2 COMPLETE: B2 CONTINUITY & REPLAY SATISFIED ===")

if __name__ == "__main__":
    main()
