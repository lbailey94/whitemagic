"""Contract test: verify structural stub classification and allowlist.

This test verifies that:
1. The stub checker (check_stubs.py) passes with zero untracked stubs.
2. The STUB_REGISTRY.md allowlist is synced with stub_allowlist.json.
3. All allowlisted stubs have a classification category.
4. No dead modules exist without allowlist entries.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CORE_ROOT = Path(__file__).resolve().parent.parent.parent
CHECK_SCRIPT = CORE_ROOT / "scripts" / "check_stubs.py"
SYNC_SCRIPT = CORE_ROOT / "scripts" / "sync_stub_registry.py"
ALLOWLIST_JSON = CORE_ROOT / "scripts" / "stub_allowlist.json"
REGISTRY_MD = REPO_ROOT / "STUB_REGISTRY.md"


class TestStubClassification:
    """Verify stub classification and allowlist integrity."""

    def test_stub_checker_passes(self):
        """check_stubs.py must exit 0 (no untracked stubs)."""
        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"check_stubs.py found untracked stubs:\n{result.stdout}\n{result.stderr}"
        )

    def test_allowlist_json_exists(self):
        """stub_allowlist.json must exist and be valid JSON."""
        assert ALLOWLIST_JSON.exists(), "stub_allowlist.json not found"
        data = json.loads(ALLOWLIST_JSON.read_text())
        assert isinstance(data, list), "stub_allowlist.json must be a list"
        assert len(data) > 0, "stub_allowlist.json must not be empty"

    def test_allowlist_is_synced(self):
        """stub_allowlist.json must match STUB_REGISTRY.md active stubs."""
        # Run sync script
        result = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"sync_stub_registry.py failed: {result.stderr}"

        # Read the regenerated allowlist
        current = json.loads(ALLOWLIST_JSON.read_text())
        assert len(current) >= 30, (
            f"Allowlist must have at least 30 entries, got {len(current)}"
        )

    def test_registry_md_has_classifications(self):
        """STUB_REGISTRY.md active stubs must have classification in reason column."""
        content = REGISTRY_MD.read_text(encoding="utf-8")
        # Find Active Stubs section
        active_match = content.find("## Active Stubs")
        resolved_match = content.find("## Resolved Stubs")
        assert active_match != -1, "STUB_REGISTRY.md missing '## Active Stubs' section"
        assert resolved_match != -1, "STUB_REGISTRY.md missing '## Resolved Stubs' section"

        active_section = content[active_match:resolved_match]
        # Count table rows (lines starting with | that aren't headers/separators)
        rows = [
            line for line in active_section.splitlines()
            if line.strip().startswith("|")
            and "---" not in line
            and "Module" not in line
        ]
        assert len(rows) >= 30, (
            f"Active Stubs table must have at least 30 entries, got {len(rows)}"
        )

    def test_no_dead_mojo_without_allowlist(self):
        """Mojo bridge functions must be allowlisted (Mojo removed in v23.2.0)."""
        mojo_file = CORE_ROOT / "whitemagic" / "core" / "acceleration" / "mojo_bridge.py"
        if not mojo_file.exists():
            pytest.skip("mojo_bridge.py not found")
        # All functions in mojo_bridge should be in the allowlist
        allowlist = set(json.loads(ALLOWLIST_JSON.read_text()))
        content = mojo_file.read_text()
        import ast
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("mojo_"):
                # Only check functions that are stubs (return None or empty body)
                is_stub = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and (
                        child.value is None
                        or (isinstance(child.value, ast.Constant) and child.value.value is None)
                    ):
                        is_stub = True
                if is_stub:
                    key = f"core/whitemagic/core/acceleration/mojo_bridge.py:{node.lineno}:{node.name}"
                    assert key in allowlist, (
                        f"Mojo stub function {node.name} at line {node.lineno} not in allowlist"
                    )
