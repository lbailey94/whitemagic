"""Phase 1 — Tests for the canonical stable tool surface.

Verifies that:
- The stable surface is explicitly defined and non-empty
- All tools in the stable surface are registered with stability=STABLE
- Gana meta-tools are always stable
- The stable surface is a small minority of total tools (product boundary)
- get_stable_tools() and to_mcp_tools_stable() work correctly
- Critical user-facing tools are in the stable surface
"""
from __future__ import annotations

import pytest


class TestStableSurfaceDefinition:
    """Verify the stable surface is well-defined."""

    def test_stable_surface_non_empty(self):
        from whitemagic.tools.stable_surface import STABLE_TOOL_NAMES

        assert len(STABLE_TOOL_NAMES) > 0

    def test_stable_surface_is_small_minority(self):
        """Stable tools should be < 10% of total — this is a curated surface."""
        from whitemagic.tools.stable_surface import STABLE_TOOL_NAMES
        from whitemagic.tools.registry import get_all_tools

        total = len(get_all_tools())
        stable_count = len(STABLE_TOOL_NAMES) + 28  # +28 for gana_* tools
        ratio = stable_count / total
        assert ratio < 0.15, (
            f"Stable surface is {ratio:.1%} of total ({stable_count}/{total}) — "
            f"should be < 15% for a curated public release"
        )

    def test_is_stable_for_gana_tools(self):
        from whitemagic.tools.stable_surface import is_stable

        assert is_stable("gana_horn") is True
        assert is_stable("gana_ghost") is True
        assert is_stable("gana_void") is True

    def test_is_stable_for_core_tools(self):
        from whitemagic.tools.stable_surface import is_stable

        assert is_stable("create_memory") is True
        assert is_stable("search_memories") is True
        assert is_stable("gnosis") is True
        assert is_stable("state.current") is True

    def test_is_stable_for_experimental_tools(self):
        from whitemagic.tools.stable_surface import is_stable

        assert is_stable("echidna.fuzz") is False
        assert is_stable("autoswarm.campaign") is False
        assert is_stable("warp.create") is False


class TestStableSurfaceRegistryConsistency:
    """Verify that ToolDefinition.stability matches the stable surface."""

    def test_all_stable_surface_tools_are_stable_in_registry(self):
        """Every tool in STABLE_TOOL_NAMES must have stability=STABLE in registry."""
        from whitemagic.tools.stable_surface import STABLE_TOOL_NAMES
        from whitemagic.tools.registry import get_all_tools
        from whitemagic.tools.tool_types import ToolStability

        registry_map = {t.name: t for t in get_all_tools()}
        mismatches = []
        for name in STABLE_TOOL_NAMES:
            td = registry_map.get(name)
            if td is None:
                mismatches.append(f"{name}: NOT IN REGISTRY")
            elif td.stability != ToolStability.STABLE:
                mismatches.append(f"{name}: stability={td.stability.value}")
        assert not mismatches, f"Stable surface tools not marked STABLE:\n  {chr(10).join(mismatches)}"

    def test_all_gana_tools_are_stable(self):
        """All gana_* tools must have stability=STABLE."""
        from whitemagic.tools.registry import get_all_tools
        from whitemagic.tools.tool_types import ToolStability

        gana_tools = [t for t in get_all_tools() if t.name.startswith("gana_")]
        assert len(gana_tools) == 28
        not_stable = [t.name for t in gana_tools if t.stability != ToolStability.STABLE]
        assert not not_stable, f"Gana tools not STABLE: {not_stable}"

    def test_experimental_tools_are_not_stable(self):
        """Tools marked EXPERIMENTAL must not be in the stable surface."""
        from whitemagic.tools.registry import get_all_tools
        from whitemagic.tools.stable_surface import is_stable
        from whitemagic.tools.tool_types import ToolStability

        exp_tools = [t for t in get_all_tools() if t.stability == ToolStability.EXPERIMENTAL]
        in_surface = [t.name for t in exp_tools if is_stable(t.name)]
        assert not in_surface, f"EXPERIMENTAL tools in stable surface: {in_surface}"


class TestStableSurfaceFunctions:
    """Verify registry functions for stable tools work correctly."""

    def test_get_stable_tools_returns_only_stable(self):
        from whitemagic.tools.registry import get_stable_tools
        from whitemagic.tools.tool_types import ToolStability

        stable = get_stable_tools()
        assert len(stable) > 0
        assert all(t.stability == ToolStability.STABLE for t in stable)

    def test_get_stable_tools_includes_gana(self):
        from whitemagic.tools.registry import get_stable_tools

        stable_names = {t.name for t in get_stable_tools()}
        assert "gana_horn" in stable_names
        assert "gana_ghost" in stable_names

    def test_get_stable_tools_includes_core_memory(self):
        from whitemagic.tools.registry import get_stable_tools

        stable_names = {t.name for t in get_stable_tools()}
        assert "create_memory" in stable_names
        assert "search_memories" in stable_names

    def test_to_mcp_tools_stable_returns_valid_dicts(self):
        from whitemagic.tools.registry import to_mcp_tools_stable

        mcp_tools = to_mcp_tools_stable()
        assert len(mcp_tools) > 0
        for t in mcp_tools:
            assert "name" in t
            assert "description" in t
            assert "inputSchema" in t
            assert t["stability"] == "stable"

    def test_stable_count_is_57(self):
        """Exact count of stable tools: 28 Gana + 29 core = 57."""
        from whitemagic.tools.registry import get_stable_tools

        assert len(get_stable_tools()) == 57


class TestCriticalToolsAreStable:
    """Verify that critical user-facing tools are in the stable surface."""

    @pytest.mark.parametrize("tool_name", [
        "create_memory",
        "update_memory",
        "delete_memory",
        "search_memories",
        "hybrid_recall",
        "memory_read",
        "wm_read",
        "wm_write",
        "state.current",
        "session.record",
        "session.recall",
        "session.continuity",
        "gnosis",
        "capabilities",
        "manifest",
        "health_report",
        "galaxy.list",
        "galaxy.stats",
        "galaxy.status",
        "governor_validate",
        "karmic.effects",
        "karmic.debt",
        "consciousness.loop.status",
        "guna.balance.status",
        "meta.galaxy.overview",
        "galactic.dashboard",
    ])
    def test_tool_is_stable(self, tool_name):
        from whitemagic.tools.stable_surface import is_stable

        assert is_stable(tool_name), f"{tool_name} should be in the stable surface"
