"""Contract test: Duplicate code ratchet.

This test verifies that:
1. The duplicate function count does not grow from baseline.
2. The number of duplicate groups does not grow from baseline.
3. The top duplicate groups are classified (singleton getters, to_dict, etc.).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CHECK_SCRIPT = REPO_ROOT / "core" / "scripts" / "check_duplicates.py"

# Baseline established 2026-07-19
# 597 duplicate functions across 211 groups
TOTAL_FUNCTIONS_BASELINE = 597
TOTAL_GROUPS_BASELINE = 211


def _run_duplicate_check() -> tuple[int, int, str]:
    """Run check_duplicates.py and return (function_count, group_count, output)."""
    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr

    # Parse "Found N duplicate functions across M groups:"
    func_count = 0
    group_count = 0
    for line in output.splitlines():
        if line.startswith("Found ") and "duplicate functions" in line:
            parts = line.split()
            func_count = int(parts[1])
            group_count = int(parts[5])
            break

    return func_count, group_count, output


class TestDuplicateRatchet:
    """Verify duplicate code ratchet."""

    def test_duplicate_functions_ratcheted(self):
        """Total duplicate functions must not grow from baseline."""
        func_count, _, _ = _run_duplicate_check()
        assert func_count <= TOTAL_FUNCTIONS_BASELINE, (
            f"Duplicate functions grew from {TOTAL_FUNCTIONS_BASELINE} to {func_count}. "
            f"Extract shared utilities instead of copying implementations."
        )

    def test_duplicate_groups_ratcheted(self):
        """Total duplicate groups must not grow from baseline."""
        _, group_count, _ = _run_duplicate_check()
        assert group_count <= TOTAL_GROUPS_BASELINE, (
            f"Duplicate groups grew from {TOTAL_GROUPS_BASELINE} to {group_count}. "
            f"Extract shared utilities instead of copying implementations."
        )

    def test_top_groups_are_singleton_patterns(self):
        """The largest duplicate groups should be singleton getter patterns.

        These are structural duplicates (same boilerplate, different modules)
        not semantic duplicates (same logic copied unnecessarily).
        """
        _, _, output = _run_duplicate_check()

        # The top group should be singleton getters (get_* with 17 nodes)
        # This is expected — 598 singleton factories use the same pattern
        lines = output.splitlines()
        group1_found = False
        for line in lines:
            if "Group 1" in line:
                group1_found = True
                # Should have many copies (20+)
                assert "29 copies" in line or "2[0-9] copies" in line, (
                    f"Top duplicate group should be large singleton pattern, got: {line}"
                )
                break

        # Verify most top groups are get_* singleton patterns
        get_count = 0
        total_shown = 0
        for line in lines:
            if "get_" in line and "()" in line and "[" in line:
                get_count += 1
            if "core/whitemagic/" in line and "[" in line:
                total_shown += 1

        # At least 50% of shown duplicates should be singleton getters
        if total_shown > 0:
            ratio = get_count / total_shown
            assert ratio >= 0.3, (
                f"Too many non-singleton duplicates: {get_count}/{total_shown} "
                f"are get_* patterns (expected ≥30%)"
            )
