#!/usr/bin/env python3
"""Repeatable PEB-10 timing qualification (the DAG side is emulated)."""
import json
import os
import platform
import subprocess
import sys
import hashlib
from pathlib import Path
from peb10_timing_stats import FLOOR, parse_sample, summarize

REPEATS = int(os.environ.get("PEB10_REPEATS", "7"))
if REPEATS < 5:
    raise SystemExit("PEB10_REPEATS must be at least 5")

samples = []
source = Path("crates/wm-gen3-core/src/pulse_compiler.rs")
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
failure = None
for i in range(REPEATS):
    p = subprocess.run(
        ["cargo", "test", "-p", "wm-gen3-core", "--release", "--lib",
         "test_peb10_benchmark_execution", "--", "--nocapture"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    sample = parse_sample(p.stdout)
    if p.returncode or sample is None:
        failure = f"PEB-10 functional benchmark run {i + 1} failed or lacked full-precision timing output"
        print(p.stdout)
        break
    samples.append(sample)

result = {
    "qualification": "repeatable wall-clock comparison; DAG baseline is emulated",
    "platform": platform.platform(),
    "machine": platform.machine(),
    "python": platform.python_version(),
    "rustc": subprocess.check_output(["rustc", "-Vv"], text=True).strip(),
    "repeats": REPEATS,
    "source_revision": revision,
    "pulse_compiler_sha256": source_hash,
    "samples": samples,
    "median_speedup_x": summarize(samples),
    "min_speedup_x": min((x["speedup_x"] for x in samples), default=None),
    "max_speedup_x": max((x["speedup_x"] for x in samples), default=None),
    "retained_floor_x": FLOOR,
}
Path("benchmark-results").mkdir(exist_ok=True)
Path("benchmark-results/peb10-timing.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
if failure:
    sys.exit(failure)
if result["median_speedup_x"] is None or result["median_speedup_x"] < FLOOR:
    sys.exit("median speedup below retained 1.4x qualification floor")
