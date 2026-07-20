"""P5.2 — Backend boundary CI gate.

Verifies that production code does not use raw sqlite3.connect() outside
of db_manager.py (the safe_connect provider). This prevents regression
of the backend boundary migration.
"""
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

PRODUCTION_ROOT = Path(__file__).parent.parent.parent / "whitemagic"
ALLOWED_FILES = {
    # db_manager.py is the safe_connect provider — it must use sqlite3.connect
    "core/memory/db_manager.py",
}
EXCLUDE_DIRS = {"__pycache__", ".archive", "_archives", "_archived", "archive"}


def _find_raw_connects() -> list[tuple[str, int, str]]:
    """Find all raw sqlite3.connect() calls in production code."""
    violations: list[tuple[str, int, str]] = []
    for py_file in PRODUCTION_ROOT.rglob("*.py"):
        rel = py_file.relative_to(PRODUCTION_ROOT).as_posix()
        if any(ex in rel for ex in EXCLUDE_DIRS):
            continue
        if rel in ALLOWED_FILES:
            continue
        try:
            content = py_file.read_text()
        except Exception:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "sqlite3.connect(" in stripped and "safe_connect" not in stripped:
                if "patch(" in stripped or "side_effect" in stripped:
                    continue
                violations.append((rel, i, stripped))
    return violations


class TestBackendBoundary:
    """Verify no raw sqlite3.connect() outside db_manager.py."""

    def test_no_raw_sqlite_connect_in_production(self):
        violations = _find_raw_connects()
        if violations:
            msgs = [f"  {f}:{l}: {s}" for f, l, s in violations]
            pytest.fail(
                f"Found {len(violations)} raw sqlite3.connect() calls outside db_manager.py.\n"
                "Use safe_connect() from whitemagic.core.memory.db_manager instead.\n"
                + "\n".join(msgs)
            )

    def test_safe_connect_exists(self):
        from whitemagic.core.memory.db_manager import safe_connect
        assert callable(safe_connect)
