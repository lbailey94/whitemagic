"""P5.5 — Configured-path violation gate.

Verifies that production code does not hard-code Path.home() / ".whitemagic"
outside of config/paths.py (the sanctioned location). This prevents
regression of the configured-path migration.
"""
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

PRODUCTION_ROOT = Path(__file__).parent.parent.parent / "whitemagic"
ALLOWED_FILES = {
    "config/paths.py",
    "config/__init__.py",
}
EXCLUDE_DIRS = {"__pycache__", ".archive", "_archives", "_archived", "archive", "mesh"}


def _find_hardcoded_paths() -> list[tuple[str, int, str]]:
    """Find Path.home() / ".whitemagic" patterns outside config/paths.py."""
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
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
                continue
            if 'Path.home()' in stripped and '.whitemagic' in stripped:
                violations.append((rel, i, stripped))
    return violations


class TestConfiguredPaths:
    """Verify no hard-coded Path.home() / .whitemagic outside config/paths.py."""

    def test_no_hardcoded_whitemagic_paths(self):
        violations = _find_hardcoded_paths()
        if violations:
            msgs = [f"  {f}:{l}: {s}" for f, l, s in violations]
            pytest.fail(
                f"Found {len(violations)} hard-coded Path.home() / .whitemagic references.\n"
                "Use whitemagic.config.paths.get_state_root() instead.\n"
                + "\n".join(msgs)
            )

    def test_get_state_root_exists(self):
        from whitemagic.config.paths import get_state_root
        assert callable(get_state_root)
        root = get_state_root()
        assert isinstance(root, Path)
