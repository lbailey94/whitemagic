#!/usr/bin/env python3
"""WhiteMagic Gen3 v10.6 — P0 Research Archive Benchmark & Certification Suite.

Executes the 4 P0 experiments from `WhiteMagic_Research_Index.json`:
  - P0.1: Evidence/Sufficiency Benchmark (`QEMem` arXiv:2610.22668 / `JointCore`)
  - P0.2: Memory Evolution, Temporal Validity, PACMI Cascade & `ScopeMem` Interference
          (`EvoBelief` arXiv:2610.12789, `TokenWorth` arXiv:2610.26453)
  - P0.3: Continuity Across Brain Replacement (`RunningTab`, `ObligationGuard`, `STEPGATE`)
  - P0.4: `ParetoGate` Independent Verifier Certification & `MemCut` Erasure Audit
          (`Who Verifies the Verifier?`, `MemCut` arXiv:2610.21405)
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_step(title: str, cmd: list[str]) -> tuple[bool, float, str]:
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode == 0, elapsed_ms, output


def main() -> int:
    print("========================================================================")
    print("  WHITEMAGIC GEN3 v10.6 — P0 RESEARCH ARCHIVE BENCHMARK SUITE")
    print("========================================================================")

    steps = [
        (
            "Unit Tests: Present-Belief State & Statutory B4 Calibration (belief.rs)",
            ["cargo", "test", "-p", "wm-gen3-core", "belief::tests", "--", "--nocapture"],
        ),
        (
            "P0.1–P0.4 Integration Battery (QEMem, EvoBelief/PACMI, Brain Swap, ParetoGate/MemCut)",
            [
                "cargo",
                "test",
                "-p",
                "wm-gen3-core",
                "--test",
                "gen3_v10_6_research_synthesis_battery",
                "--features",
                "operator",
                "--",
                "--nocapture",
            ],
        ),
        (
            "Gate 9C Precision & Vector Non-Resurrection Acceptance Suite",
            [
                "cargo",
                "test",
                "-p",
                "wm-gen3-core",
                "--test",
                "gate9c_precision_acceptance",
                "--features",
                "operator",
            ],
        ),
    ]

    results = []
    all_ok = True
    for title, cmd in steps:
        print(f"\n[RUN] {title}")
        ok, ms, out = run_step(title, cmd)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {title} ({ms:.1f} ms)")
        if not ok:
            print(out)
            all_ok = False
        results.append({"title": title, "passed": ok, "elapsed_ms": round(ms, 2)})

    summary = {
        "suite": "gen3_v10_6_p0_research_archive_benchmarks",
        "all_passed": all_ok,
        "steps": results,
    }
    print("\n" + json.dumps(summary, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
