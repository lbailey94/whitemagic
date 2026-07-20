"""Contract test: verify the tool execution entrypoint hierarchy.

The canonical execution path is:
  ToolRuntime.execute() → call_tool() → _dispatch_tool_with_timeout() → dispatch()
    → _pipeline.execute() or _fast_path_dispatch()

Lightweight tools bypass dispatch() entirely via _dispatch_lightweight_tool().
Fast-path tools bypass the middleware pipeline via _fast_path_dispatch().

This test verifies:
1. The entrypoint hierarchy is intact (no orphaned entrypoints)
2. Lightweight and fast-path tool sets don't conflict
3. ToolRuntime delegates to call_tool (not dispatch directly)
4. call_tool delegates to dispatch (not handlers directly)
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]


class TestEntrypointHierarchy:
    """Verify the tool execution entrypoint hierarchy is intact."""

    def test_call_tool_exists_and_is_callable(self):
        """call_tool must be the canonical external entrypoint."""
        from whitemagic.tools.unified_api import call_tool

        assert callable(call_tool)

    def test_dispatch_exists_and_is_callable(self):
        """dispatch must be the middleware pipeline entrypoint."""
        from whitemagic.tools.dispatch_table import dispatch

        assert callable(dispatch)

    def test_tool_runtime_delegates_to_call_tool(self):
        """ToolRuntime._execute_full must call call_tool, not dispatch directly."""
        import inspect

        from whitemagic.tools.runtime import ToolRuntime

        source = inspect.getsource(ToolRuntime._execute_full)
        assert "call_tool" in source, (
            "ToolRuntime._execute_full must delegate to call_tool(), not dispatch directly"
        )

    def test_call_tool_delegates_to_dispatch(self):
        """call_tool must delegate to dispatch via _dispatch_tool_with_timeout."""
        import inspect

        from whitemagic.tools.unified_api import call_tool

        source = inspect.getsource(call_tool)
        assert "_dispatch_tool" in source, (
            "call_tool must delegate to _dispatch_tool/_dispatch_tool_with_timeout"
        )

    def test_lightweight_and_fast_path_no_conflict(self):
        """Lightweight tools bypass dispatch; fast-path tools bypass middleware.
        A tool should not be in both sets (it would never reach fast-path)."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_TOOLS
        from whitemagic.tools.timeouts import LIGHTWEIGHT_STATUS_TOOLS

        overlap = _FAST_PATH_TOOLS & LIGHTWEIGHT_STATUS_TOOLS
        # capabilities and manifest are in both — lightweight intercepts first in call_tool
        # This is intentional: lightweight handles them before dispatch is called
        assert overlap <= {"capabilities", "manifest"}, (
            f"Unexpected overlap between LIGHTWEIGHT_STATUS_TOOLS and _FAST_PATH_TOOLS: {overlap}"
        )

    def test_fast_path_dispatch_bypasses_pipeline(self):
        """_fast_path_dispatch must not call _pipeline.execute."""
        import inspect

        from whitemagic.tools.dispatch_table import _fast_path_dispatch

        source = inspect.getsource(_fast_path_dispatch)
        # Strip docstring and comments for accurate check
        assert "_pipeline.execute" not in source, (
            "_fast_path_dispatch must not call _pipeline.execute (it bypasses middleware)"
        )

    def test_dispatch_uses_pipeline(self):
        """dispatch must use _pipeline.execute for non-fast-path tools."""
        import inspect

        from whitemagic.tools.dispatch_table import dispatch

        source = inspect.getsource(dispatch)
        assert "_pipeline" in source, (
            "dispatch must use _pipeline.execute for non-fast-path tools"
        )

    def test_no_recursive_call_tool_from_core(self):
        """Core modules must not call call_tool (prevents recursive public transport)."""
        import ast
        from pathlib import Path

        whitemagic_root = Path(__file__).parent.parent.parent.parent / "whitemagic"
        core_root = whitemagic_root / "core"

        violations = []
        for py_file in core_root.rglob("*.py"):
            rel = py_file.relative_to(whitemagic_root)
            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                tree = ast.parse(content, filename=str(py_file))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "unified_api" in node.module:
                        for alias in node.names:
                            if alias.name == "call_tool":
                                violations.append(str(rel))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "unified_api" in alias.name and "call_tool" in alias.name:
                            violations.append(str(rel))

        # These are known baseline violations
        KNOWN = set()
        new_violations = set(violations) - KNOWN
        assert not new_violations, (
            f"Core modules must not import call_tool (prevents recursive public transport): {new_violations}"
        )
