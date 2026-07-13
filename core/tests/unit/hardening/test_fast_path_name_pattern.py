"""Phase 1 deferred — Document remaining name-pattern inference in fast-path.

The dispatch_table fast-path uses two mechanisms:
1. An explicit frozenset (_FAST_PATH_TOOLS) of tool names — this is fine.
2. A prefix-based pattern match (_FAST_PATH_PREFIXES) for "gana_ghost." —
   this is name-pattern inference that should be replaced with explicit
   registration in Phase 3.

This test file documents the current state so that when the prefix-based
inference is removed, we can verify the migration is complete.
"""
from __future__ import annotations

import pytest


class TestFastPathNamePatternInference:
    """Document the remaining name-pattern inference in dispatch_table fast-path."""

    def test_fast_path_tools_are_explicit(self):
        """_FAST_PATH_TOOLS is an explicit frozenset of tool names."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_TOOLS
        assert isinstance(_FAST_PATH_TOOLS, frozenset)
        # All entries should be valid tool names (dot-notation)
        for name in _FAST_PATH_TOOLS:
            assert isinstance(name, str)
            assert len(name) > 0

    def test_fast_path_prefixes_contains_gana_ghost(self):
        """_FAST_PATH_PREFIXES currently contains 'gana_ghost.' — this is
        the remaining name-pattern inference that should be replaced with
        explicit registration in Phase 3."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_PREFIXES
        assert isinstance(_FAST_PATH_PREFIXES, frozenset)
        # Document the known prefix
        assert "gana_ghost." in _FAST_PATH_PREFIXES

    def test_is_fast_path_matches_explicit_tools(self):
        """Tools in _FAST_PATH_TOOLS are fast-path eligible."""
        from whitemagic.tools.dispatch_table import _is_fast_path, _FAST_PATH_TOOLS
        for tool_name in _FAST_PATH_TOOLS:
            assert _is_fast_path(tool_name), f"{tool_name} should be fast-path eligible"

    def test_is_fast_path_matches_prefix_pattern(self):
        """Tools matching a prefix in _FAST_PATH_PREFIXES are fast-path eligible.
        This is the name-pattern inference that should be migrated to explicit
        registration in Phase 3."""
        from whitemagic.tools.dispatch_table import _is_fast_path
        # gana_ghost. prefix matches
        assert _is_fast_path("gana_ghost.something")
        assert _is_fast_path("gana_ghost.capabilities")
        assert _is_fast_path("gana_ghost.telemetry")

    def test_is_fast_path_rejects_unknown_tools(self):
        """Tools not in the explicit set or matching a prefix are not fast-path."""
        from whitemagic.tools.dispatch_table import _is_fast_path
        assert not _is_fast_path("memory_create")
        assert not _is_fast_path("llama_chat")
        assert not _is_fast_path("some.random.tool")

    def test_prefix_count_is_small(self):
        """There should be at most 1-2 prefix patterns remaining.
        If this count grows, it indicates regression in the migration plan."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_PREFIXES
        assert len(_FAST_PATH_PREFIXES) <= 2, (
            f"Expected at most 2 fast-path prefixes, got {len(_FAST_PATH_PREFIXES)}. "
            f"Prefix-based inference should be shrinking, not growing."
        )

    def test_fast_path_tools_count_reasonable(self):
        """The explicit tool set should be small (only safe read-only tools)."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_TOOLS
        assert len(_FAST_PATH_TOOLS) <= 20, (
            f"Expected at most 20 fast-path tools, got {len(_FAST_PATH_TOOLS)}. "
            f"Fast-path should be limited to safe read-only status tools."
        )
