"""Contract test: Oversized module ratchet.

This test verifies that:
1. No production module exceeds the critical threshold (3000 lines).
2. The number of modules over 1000 lines does not grow from baseline.
3. The top 10 largest modules are tracked for future splitting.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

WHITEMAGIC_DIR = Path(__file__).resolve().parent.parent.parent / "whitemagic"

# Thresholds
CRITICAL_THRESHOLD = 3000  # Modules over this MUST be split
LARGE_THRESHOLD = 1000  # Modules over this are tracked

# Baseline established 2026-07-19
# 25 modules over 1000 lines
LARGE_MODULE_BASELINE = 25


def _count_lines(filepath: Path) -> int:
    """Count non-blank, non-comment lines in a Python file."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    count = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def _get_module_sizes() -> list[tuple[str, int]]:
    """Get all Python module sizes sorted by size descending."""
    sizes = []
    for py_file in WHITEMAGIC_DIR.rglob("*.py"):
        rel = str(py_file.relative_to(WHITEMAGIC_DIR))
        if "__pycache__" in rel or "_archived" in rel:
            continue
        line_count = _count_lines(py_file)
        if line_count > 0:
            sizes.append((rel, line_count))
    return sorted(sizes, key=lambda x: -x[1])


class TestModuleSizeRatchet:
    """Verify oversized module ratchet."""

    def test_no_module_exceeds_critical_threshold(self):
        """No module should exceed 3000 lines (critical threshold)."""
        sizes = _get_module_sizes()
        critical = [(name, count) for name, count in sizes if count > CRITICAL_THRESHOLD]
        assert not critical, (
            f"Critical modules over {CRITICAL_THRESHOLD} lines:\n"
            + "\n".join(f"  {name}: {count} lines" for name, count in critical)
        )

    def test_large_module_count_ratcheted(self):
        """Number of modules over 1000 lines must not grow from baseline."""
        sizes = _get_module_sizes()
        large_count = sum(1 for _, count in sizes if count > LARGE_THRESHOLD)
        assert large_count <= LARGE_MODULE_BASELINE, (
            f"Large module count grew from {LARGE_MODULE_BASELINE} to {large_count}. "
            f"Split new modules before they exceed {LARGE_THRESHOLD} lines."
        )

    def test_top_10_modules_tracked(self):
        """Top 10 largest modules are identified for future splitting."""
        sizes = _get_module_sizes()
        top_10 = sizes[:10]

        # All top 10 should be over 1000 lines
        for name, count in top_10:
            assert count > 1000, (
                f"Module {name} in top 10 but only {count} lines"
            )

        # Known largest modules (baseline 2026-07-19)
        known_large = {
            "tools/middleware.py",
            "tools/handlers/meta_tool.py",
            "archaeology/session_miner.py",
            "run_mcp_lean.py",
            "core/memory/sqlite_backend.py",
            "core/evolution/recursive_loop.py",
            "core/dreaming/dream_cycle.py",
        }
        top_names = {name for name, _ in top_10}
        overlap = top_names & known_large
        assert len(overlap) >= 5, (
            f"Expected ≥5 known large modules in top 10, got {len(overlap)}: {overlap}"
        )
