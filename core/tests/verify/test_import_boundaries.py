"""CI gate: verify no new direct core→tools imports.

This test scans all whitemagic.core.* Python files for direct imports of
whitemagic.tools.* modules. It uses a baseline allowlist of known violations.
Any new direct import will fail the test.

Indirect imports (core → non-tools → tools) are handled by import-linter
(.importlinter config + scripts/check_import_boundaries.sh).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

WHITEMAGIC_ROOT = (Path(__file__).resolve().parent.parent.parent / "whitemagic").resolve()
assert WHITEMAGIC_ROOT.is_dir(), f"WHITEMAGIC_ROOT does not exist: {WHITEMAGIC_ROOT}"
CORE_ROOT = WHITEMAGIC_ROOT / "core"
assert CORE_ROOT.is_dir(), f"CORE_ROOT does not exist: {CORE_ROOT}"

# Baseline of direct core→tools imports as of 2026-07-19.
# All core→tools imports have been migrated to core/ports.py (the designated
# bridge point). This baseline should only contain ports.py entries.
# If new direct imports appear outside ports.py, they must be migrated or
# explicitly added here with justification.
KNOWN_DIRECT_VIOLATIONS: set[tuple[str, str]] = {
    # --- designated bridge point (core/ports.py is the one allowed import site) ---
    ("core/ports.py", "whitemagic.tools.circuit_breaker"),
    ("core/ports.py", "whitemagic.tools.dispatch_table"),
    ("core/ports.py", "whitemagic.tools.handlers.broker"),
    ("core/ports.py", "whitemagic.tools.handlers.llama_tools"),
    ("core/ports.py", "whitemagic.tools.handlers.scratchpad"),
    ("core/ports.py", "whitemagic.tools.handlers.tool_bandit"),
    ("core/ports.py", "whitemagic.tools.middleware"),
    ("core/ports.py", "whitemagic.tools.prat_mappings"),
    ("core/ports.py", "whitemagic.tools.prat_resonance"),
    ("core/ports.py", "whitemagic.tools.prat_router"),
    ("core/ports.py", "whitemagic.tools.registry"),
    ("core/ports.py", "whitemagic.tools.security.contest_pipeline"),
    ("core/ports.py", "whitemagic.tools.security.strata_mitre_map"),
    ("core/ports.py", "whitemagic.tools.strata"),
    ("core/ports.py", "whitemagic.tools.tool_surface"),
    ("core/ports.py", "whitemagic.tools.unified_api"),
}


def _find_direct_tools_imports() -> set[tuple[str, str]]:
    """Scan all core/*.py files for direct imports of whitemagic.tools.*"""
    violations: set[tuple[str, str]] = set()

    for py_file in CORE_ROOT.rglob("*.py"):
        rel = py_file.relative_to(WHITEMAGIC_ROOT)
        rel_str = str(rel)

        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            # import whitemagic.tools.foo
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("whitemagic.tools"):
                        violations.add((rel_str, alias.name))
            # from whitemagic.tools.foo import bar
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("whitemagic.tools"):
                    violations.add((rel_str, node.module))

    return violations


class TestImportBoundaries:
    """Verify no new direct core→tools imports have been added."""

    def test_no_new_direct_core_to_tools_imports(self):
        """Direct imports from whitemagic.core.* to whitemagic.tools.* must be in the baseline."""
        actual = _find_direct_tools_imports()
        known = KNOWN_DIRECT_VIOLATIONS

        new_violations = actual - known
        assert not new_violations, (
            f"{len(new_violations)} new direct core→tools imports found:\n"
            + "\n".join(f"  {src} -> {mod}" for src, mod in sorted(new_violations))
            + "\nAdd them to KNOWN_DIRECT_VIOLATIONS or fix the import."
        )

    def test_baselined_violations_still_exist(self):
        """Verify baselined violations still exist (detects stale entries)."""
        actual = _find_direct_tools_imports()
        known = KNOWN_DIRECT_VIOLATIONS

        stale = known - actual
        # Stale entries are OK — they mean a violation was fixed.
        # Just report them so the baseline can be cleaned up.
        if stale:
            print(f"\n{len(stale)} baselined violations have been fixed (remove from KNOWN_DIRECT_VIOLATIONS):")
            for src, mod in sorted(stale):
                print(f"  ✅ {src} -> {mod}")

    def test_violation_count_no_growth(self):
        """The total direct violation count must not grow from baseline."""
        actual = _find_direct_tools_imports()
        baseline_count = len(KNOWN_DIRECT_VIOLATIONS)
        assert len(actual) <= baseline_count, (
            f"Direct core→tools violations grew from {baseline_count} to {len(actual)}. "
            f"New violations: {actual - KNOWN_DIRECT_VIOLATIONS}"
        )
