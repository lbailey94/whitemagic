"""Phase 3 §7.3 — Tests verifying fast-path dispatch uses registry metadata.

This test suite verifies the Phase 3 fix for fast-path dispatch:
- _FAST_PATH_TOOLS is an explicit frozenset of tool names (unchanged)
- _FAST_PATH_PREFIXES has been REMOVED — no more name-pattern inference
- Fast-path eligibility is determined by:
  1. Explicit _FAST_PATH_TOOLS set, OR
  2. ToolDefinition.fast_path=True in the registry, OR
  3. Tool belongs to gana_ghost (all introspection/read-only tools)
- ToolDefinition has a fast_path boolean field (defaults False)
"""
from __future__ import annotations

import pytest


class TestFastPathRegistryMetadata:
    """Verify fast-path dispatch uses registry metadata, not name-pattern inference."""

    def test_fast_path_tools_are_explicit(self):
        """_FAST_PATH_TOOLS is an explicit frozenset of tool names."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_TOOLS
        assert isinstance(_FAST_PATH_TOOLS, frozenset)
        for name in _FAST_PATH_TOOLS:
            assert isinstance(name, str)
            assert len(name) > 0

    def test_no_fast_path_prefixes(self):
        """_FAST_PATH_PREFIXES should no longer exist (removed in Phase 3)."""
        import whitemagic.tools.dispatch_table as mod
        assert not hasattr(mod, "_FAST_PATH_PREFIXES"), (
            "_FAST_PATH_PREFIXES should be removed in Phase 3. "
            "Fast-path eligibility should use registry metadata instead."
        )

    def test_is_fast_path_matches_explicit_tools(self):
        """Tools in _FAST_PATH_TOOLS are fast-path eligible."""
        from whitemagic.tools.dispatch_table import _is_fast_path, _FAST_PATH_TOOLS
        for tool_name in _FAST_PATH_TOOLS:
            assert _is_fast_path(tool_name), f"{tool_name} should be fast-path eligible"

    def test_is_fast_path_rejects_unknown_tools(self):
        """Tools not in the explicit set or registry should not be fast-path."""
        from whitemagic.tools.dispatch_table import _is_fast_path
        assert not _is_fast_path("memory_create")
        assert not _is_fast_path("llama_chat")
        assert not _is_fast_path("some.random.tool")

    def test_fast_path_tools_count_reasonable(self):
        """The explicit tool set should be small (only safe read-only tools)."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_TOOLS
        assert len(_FAST_PATH_TOOLS) <= 20, (
            f"Expected at most 20 fast-path tools, got {len(_FAST_PATH_TOOLS)}. "
            f"Fast-path should be limited to safe read-only status tools."
        )

    def test_tool_definition_has_fast_path_field(self):
        """ToolDefinition should have a fast_path boolean field."""
        from whitemagic.tools.tool_types import ToolDefinition, ToolCategory, ToolSafety
        td = ToolDefinition(
            name="test.tool",
            description="test",
            category=ToolCategory.SYSTEM,
            safety=ToolSafety.READ,
            input_schema={},
            fast_path=True,
        )
        assert td.fast_path is True

    def test_tool_definition_fast_path_defaults_false(self):
        """ToolDefinition.fast_path should default to False."""
        from whitemagic.tools.tool_types import ToolDefinition, ToolCategory, ToolSafety
        td = ToolDefinition(
            name="test.tool",
            description="test",
            category=ToolCategory.SYSTEM,
            safety=ToolSafety.READ,
            input_schema={},
        )
        assert td.fast_path is False
