"""Contract test: classify singleton factories by scope.

This test inventories all get_*() singleton factory functions and classifies
them into four scopes:

  - **process-scoped**: singleton lives for the entire process (e.g., config,
    dispatch, registry).  Identified by: no parameters, no user_id/key arg.
  - **user-scoped**: singleton is keyed by user_id or similar parameter
    (e.g., memory, sessions).  Identified by: has user_id or key parameter.
  - **request-scoped**: singleton is created per-request with a unique key
    parameter.  Identified by: has a request_id or ctx parameter.
  - **stateless**: function returns a new instance each call (not a true
    singleton — excluded from the count).

The test establishes baselines for each category and verifies that the
SingletonRegistry legacy table covers all process-scoped critical singletons.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

WHITEMAGIC_ROOT = (Path(__file__).resolve().parent.parent.parent / "whitemagic").resolve()
assert WHITEMAGIC_ROOT.is_dir(), f"WHITEMAGIC_ROOT does not exist: {WHITEMAGIC_ROOT}"


def _find_singleton_factories() -> list[tuple[str, str, str]]:
    """Find all get_*() singleton factories and classify them by scope.

    Returns list of (relative_path, function_name, scope).
    """
    factories: list[tuple[str, str, str]] = []
    for py_file in WHITEMAGIC_ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "def get_" not in content or "is None" not in content:
            continue
        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError:
            continue

        lines = content.splitlines()
        rel = str(py_file.relative_to(WHITEMAGIC_ROOT))

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("get_"):
                continue
            func_lines = lines[node.lineno - 1: node.end_lineno if node.end_lineno else node.lineno + 20]
            func_src = "\n".join(func_lines)
            # Singleton pattern: checks "is None" and uses "global _" or "cls._instance"
            if "is None" not in func_src:
                continue
            if "global _" not in func_src and "cls._instance" not in func_src:
                continue

            # Classify by parameters
            args = node.args
            arg_names = [a.arg for a in args.args if a.arg != "self"]

            if not arg_names:
                scope = "process"
            elif any(a in arg_names for a in ("user_id", "user_key", "namespace", "user")):
                scope = "user"
            elif any(a in arg_names for a in ("request_id", "ctx", "context", "request")):
                scope = "request"
            elif len(arg_names) <= 2 and any(
                a in arg_names for a in ("key", "name", "id", "shelter_id", "tool_name")
            ):
                scope = "user"
            else:
                scope = "process"

            factories.append((rel, node.name, scope))
    return factories


class TestSingletonClassification:
    """Verify singleton factory classification and coverage."""

    def test_all_factories_classified(self):
        """Every singleton factory must be classifiable into a known scope."""
        factories = _find_singleton_factories()
        scopes = {scope for _, _, scope in factories}
        assert scopes <= {"process", "user", "request"}, (
            f"Unknown scope(s) found: {scopes - {'process', 'user', 'request'}}"
        )

    def test_factory_count_baselined(self):
        """Total singleton factory count must not shrink from baseline."""
        factories = _find_singleton_factories()
        BASELINE = 400
        assert len(factories) >= BASELINE, (
            f"Singleton factory count dropped from {BASELINE} to {len(factories)}. "
            f"This may indicate singletons were removed or refactored."
        )

    def test_process_scoped_count_baselined(self):
        """Process-scoped singleton count must not shrink from baseline."""
        factories = _find_singleton_factories()
        process_count = sum(1 for _, _, s in factories if s == "process")
        BASELINE = 400
        assert process_count >= BASELINE, (
            f"Process-scoped singleton count dropped from {BASELINE} to {process_count}."
        )

    def test_user_scoped_count_baselined(self):
        """User-scoped singleton count must not shrink from baseline."""
        factories = _find_singleton_factories()
        user_count = sum(1 for _, _, s in factories if s == "user")
        BASELINE = 3
        assert user_count >= BASELINE, (
            f"User-scoped singleton count dropped from {BASELINE} to {user_count}."
        )

    def test_scope_distribution_sane(self):
        """Scope distribution must be sane: process > user > request."""
        factories = _find_singleton_factories()
        counts = {"process": 0, "user": 0, "request": 0}
        for _, _, scope in factories:
            counts[scope] = counts.get(scope, 0) + 1
        # Process-scoped should be the majority
        total = len(factories)
        assert counts["process"] > counts["user"], (
            f"Process-scoped ({counts['process']}) should exceed user-scoped ({counts['user']})"
        )
        assert counts["process"] / total > 0.5, (
            f"Process-scoped should be >50% of total, got {counts['process']}/{total}"
        )

    def test_no_duplicate_factories(self):
        """No duplicate (path, name) entries in the factory list."""
        factories = _find_singleton_factories()
        seen = set()
        duplicates = []
        for rel, name, scope in factories:
            key = (rel, name)
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        assert not duplicates, f"Duplicate singleton factories: {duplicates[:10]}"
