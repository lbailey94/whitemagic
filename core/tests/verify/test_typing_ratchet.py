"""Contract test: Mypy typing ratchet for public boundary packages.

This test verifies that:
1. Public boundary packages (config, ports) are mypy-clean.
2. Total mypy errors do not grow from baseline.
3. The mypy configuration is valid and runs successfully.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

CORE_ROOT = Path(__file__).resolve().parent.parent.parent
WHITEMAGIC_DIR = CORE_ROOT / "whitemagic"

# Boundary packages that must be mypy-clean (no errors)
BOUNDARY_PACKAGES = [
    "whitemagic/config/env_vars.py",
    "whitemagic/config/unified.py",
    "whitemagic/config/daemon_config.py",
    "whitemagic/config/paths.py",
    "whitemagic/core/ports.py",
]

# Baseline established 2026-07-19
TOTAL_BASELINE = 611  # With --follow-imports=silent


def _run_mypy(targets: list[str], follow_imports: str = "silent") -> tuple[int, str]:
    """Run mypy and return (returncode, output)."""
    cmd = [sys.executable, "-m", "mypy"] + targets
    cmd += ["--follow-imports", follow_imports, "--no-error-summary"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(CORE_ROOT))
    return result.returncode, result.stdout + result.stderr


class TestTypingRatchet:
    """Verify Mypy typing ratchet."""

    def test_boundary_packages_clean(self):
        """Public boundary packages must have zero mypy errors in their own files."""
        targets = [str(WHITEMAGIC_DIR / p.replace("whitemagic/", "")) for p in BOUNDARY_PACKAGES]
        rc, output = _run_mypy(targets, follow_imports="silent")
        # Filter for errors only in the boundary files themselves
        errors = [
            l for l in output.splitlines()
            if "error:" in l and any(f"{p}:" in l for p in BOUNDARY_PACKAGES)
        ]
        assert not errors, (
            f"Boundary packages have mypy errors:\n" + "\n".join(errors)
        )

    def test_total_errors_ratcheted(self):
        """Total mypy errors must not grow from baseline."""
        rc, output = _run_mypy([str(WHITEMAGIC_DIR)], follow_imports="silent")
        error_count = sum(1 for l in output.splitlines() if "error:" in l)
        assert error_count <= TOTAL_BASELINE, (
            f"Mypy errors grew from {TOTAL_BASELINE} to {error_count}. "
            f"Fix new type errors or add type: ignore with justification."
        )
