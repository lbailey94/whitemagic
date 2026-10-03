#!/usr/bin/env python3
"""Phase 6: Emergent Expressibility & The Recipe Challenge Benchmark Driver.

Protocol: docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md §3 Layer 6, §5 Phase 6
Baseline: Gen3 Cognitive Runtime Baseline 1 (G3-CRB-1)

Tests the 4 Autonomous Workflows using ONLY existing G3-CRB-1 primitives:
  - Workflow A: Multi-Step Defect Diagnosis & Patch Verification
  - Workflow B: Distributed Multi-Agent Handoff via Leases & Continuity
  - Workflow C: Epistemic Hypothesis Registration & Empirical Validation
  - Workflow D: The Intentionally Awful Workflow (Spec change + SIGKILL + Expired lease + Falsification + Recovery)

Goal:
  Determine whether higher-order orchestration (W2_05: Recipe Layer) is strictly necessary,
  or whether the Minimal Cognitive Runtime substrate already provides complete autonomous expressibility.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT_GEN3 = os.environ.get("WMGEN3_ROOT", "/home/lucas/Desktop/WMgen3")
ROOT_WMV9 = "/home/lucas/Desktop/WHITEMAGIC/WMv9"

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def run_recipe_challenge_tests():
    log("=== PHASE 6: EMERGENT EXPRESSIBILITY & THE RECIPE CHALLENGE ===")
    log(f"Target repository: {ROOT_WMV9}")
    log("Executing: cargo test -p wm-tools --test recipe_expressibility_challenge -- --nocapture")

    start_time = time.time()
    p = subprocess.run(
        ["cargo", "test", "-p", "wm-tools", "--test", "recipe_expressibility_challenge", "--", "--nocapture"],
        cwd=ROOT_WMV9,
        capture_output=True,
        text=True,
        timeout=180,
    )
    elapsed = time.time() - start_time

    if p.returncode != 0:
        log("FAILURE: Recipe challenge benchmark failed!")
        print("STDOUT:\n", p.stdout)
        print("STDERR:\n", p.stderr)
        sys.exit(1)

    expected = [
        "test_workflow_a_defect_diagnosis_and_verification",
        "test_workflow_b_multi_agent_distributed_handoff",
        "test_workflow_c_epistemic_hypothesis_validation_loop",
        "test_workflow_d_the_intentionally_awful_workflow",
    ]
    for t in expected:
        if t in p.stdout:
            log(f"  ✓ {t}: PASS")
        else:
            log(f"  ✗ {t}: MISSING OR FAILED")
            sys.exit(1)

    log(f"\nAll 4 autonomous workflows executed and verified cleanly in {elapsed:.2f}s.")
    log("=== PHASE 6 COMPLETE: RECIPE EXPRESSIBILITY SATISFIED WITHOUT W2_05 BLOAT ===")

if __name__ == "__main__":
    run_recipe_challenge_tests()
