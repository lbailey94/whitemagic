"""Contract test: Ruff ratchet — no new findings, baseline only shrinks.

This test verifies that:
1. Zero F-rule (correctness) findings exist (undefined names, unused imports, etc.).
2. Total non-E501 findings do not exceed the established baseline.
3. BLE001 (blind-except) count does not grow from baseline.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

CORE_ROOT = Path(__file__).resolve().parent.parent.parent
WHITEMAGIC_DIR = CORE_ROOT / "whitemagic"

# Baselines established 2026-07-19 after P7.3 ratchet setup
TOTAL_BASELINE = 670  # Excluding E501 (line-too-long, ignored in config)
BLE001_BASELINE = 627  # Per-line noqa'd broad exception catches


def _run_ruff(select: str, ignore: str = "") -> tuple[int, str]:
    """Run ruff check and return (returncode, output)."""
    cmd = [sys.executable, "-m", "ruff", "check", str(WHITEMAGIC_DIR)]
    cmd += ["--select", select, "--no-cache", "--output-format=concise"]
    if ignore:
        cmd += ["--ignore", ignore]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode, result.stdout + result.stderr


class TestRuffRatchet:
    """Verify Ruff findings ratchet — no growth from baseline."""

    def test_zero_correctness_findings(self):
        """F-rules (undefined names, unused imports, etc.) must be zero."""
        rc, output = _run_ruff("F")
        assert rc == 0, f"F-rule findings exist:\n{output}"

    def test_total_findings_ratcheted(self):
        """Total non-E501 findings must not exceed baseline."""
        rc, output = _run_ruff("E,F,I,W,UP,BLE", "E501")
        # Count findings from concise output
        lines = [l for l in output.splitlines() if ":" in l and "F" in l.split(":")[0]]
        # Actually parse from statistics
        stat_cmd = [sys.executable, "-m", "ruff", "check", str(WHITEMAGIC_DIR)]
        stat_cmd += ["--select", "E,F,I,W,UP,BLE", "--ignore", "E501", "--no-cache", "--statistics"]
        result = subprocess.run(stat_cmd, capture_output=True, text=True, timeout=120)
        # Parse the "Found N errors" line
        for line in result.stdout.splitlines():
            if line.startswith("Found "):
                count = int(line.split()[1])
                assert count <= TOTAL_BASELINE, (
                    f"Ruff findings grew from {TOTAL_BASELINE} to {count}. "
                    f"Fix new findings or add per-line noqa with justification."
                )
                return
        pytest.fail("Could not parse ruff findings count")

    def test_ble001_count_ratcheted(self):
        """BLE001 (blind-except) count must not grow from baseline."""
        stat_cmd = [sys.executable, "-m", "ruff", "check", str(WHITEMAGIC_DIR)]
        stat_cmd += ["--select", "BLE001", "--no-cache", "--statistics"]
        result = subprocess.run(stat_cmd, capture_output=True, text=True, timeout=120)
        for line in result.stdout.splitlines():
            if line.strip().startswith("BLE001"):
                count = int(line.strip().split()[0])
                assert count <= BLE001_BASELINE, (
                    f"BLE001 count grew from {BLE001_BASELINE} to {count}. "
                    f"Use specific exception types instead of `except Exception`."
                )
                return
        # If no BLE001 line found, count is 0 — that's fine
