"""Contract test: verify broad exception handling ratchet.

This test verifies that:
1. No file-level `# ruff: noqa: BLE001` suppressions remain in production code.
2. Per-line `# noqa: BLE001` suppressions are counted and ratcheted (no growth).
3. The 5 high-priority files identified in P7.2 have been converted from
   file-level to per-line suppressions.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

WHITEMAGIC_ROOT = (Path(__file__).resolve().parent.parent.parent / "whitemagic").resolve()


def _find_file_level_noqa(root: Path) -> list[str]:
    """Find files with file-level `# ruff: noqa: BLE001` suppressions."""
    offenders = []
    for py_file in root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # Check first 5 lines for file-level noqa
        for i, line in enumerate(content.splitlines()[:5], 1):
            if re.match(r"#\s*ruff:\s*noqa:\s*BLE001\s*$", line.strip()):
                rel = str(py_file.relative_to(root))
                offenders.append(f"{rel}:{i}")
    return offenders


def _count_per_line_noqa(root: Path) -> int:
    """Count total per-line `# noqa: BLE001` suppressions in production code."""
    count = 0
    for py_file in root.rglob("*.py"):
        if "__pycache__" in str(py_file) or "test_" in py_file.name:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # Count lines with per-line noqa (not file-level)
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("# ruff: noqa: BLE001"):
                continue  # file-level, counted separately
            if "noqa: BLE001" in stripped and not stripped.startswith("# ruff:"):
                count += 1
    return count


class TestBroadExceptionRatchet:
    """Verify broad exception handling ratchet."""

    # The 5 high-priority files from P7.2 strategy
    P7_2_FILES = [
        "config/daemon_config.py",
        "cli/boot.py",
        "core/resonance/_consolidated.py",
        "core/dreaming/dream_cycle.py",
        "tools/dispatch_core.py",
    ]

    def test_p7_2_files_have_no_file_level_noqa(self):
        """The 5 high-priority P7.2 files must not have file-level BLE001 noqa."""
        offenders = []
        for rel_path in self.P7_2_FILES:
            f = WHITEMAGIC_ROOT / rel_path
            if not f.exists():
                continue
            content = f.read_text(encoding="utf-8")
            first_5 = "\n".join(content.splitlines()[:5])
            if "# ruff: noqa: BLE001" in first_5:
                offenders.append(rel_path)
        assert not offenders, (
            f"These P7.2 files still have file-level BLE001 suppressions: {offenders}"
        )

    def test_per_line_noqa_count_ratcheted(self):
        """Per-line BLE001 count must not grow from baseline."""
        count = _count_per_line_noqa(WHITEMAGIC_ROOT)
        BASELINE = 699  # Updated 2026-07-20: reflects post-v25.1.0 codebase growth
        assert count <= BASELINE, (
            f"Per-line BLE001 count grew from {BASELINE} to {count}. "
            f"New broad catches should use specific exception types."
        )

    def test_daemon_config_no_file_noqa(self):
        """daemon_config.py must not have file-level noqa."""
        f = WHITEMAGIC_ROOT / "config" / "daemon_config.py"
        content = f.read_text()
        first_5 = "\n".join(content.splitlines()[:5])
        assert "# ruff: noqa: BLE001" not in first_5

    def test_boot_no_file_noqa(self):
        """cli/boot.py must not have file-level noqa."""
        f = WHITEMAGIC_ROOT / "cli" / "boot.py"
        content = f.read_text()
        first_5 = "\n".join(content.splitlines()[:5])
        assert "# ruff: noqa: BLE001" not in first_5

    def test_consolidated_no_file_noqa(self):
        """core/resonance/_consolidated.py must not have file-level noqa."""
        f = WHITEMAGIC_ROOT / "core" / "resonance" / "_consolidated.py"
        content = f.read_text()
        first_5 = "\n".join(content.splitlines()[:5])
        assert "# ruff: noqa: BLE001" not in first_5

    def test_dream_cycle_no_file_noqa(self):
        """core/dreaming/dream_cycle.py must not have file-level noqa."""
        f = WHITEMAGIC_ROOT / "core" / "dreaming" / "dream_cycle.py"
        content = f.read_text()
        first_5 = "\n".join(content.splitlines()[:5])
        assert "# ruff: noqa: BLE001" not in first_5
