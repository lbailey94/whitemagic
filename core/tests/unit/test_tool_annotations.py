"""Tests for MCP tool annotations (whitemagic.tools.annotations, P9.3).

Pins the derivation policy (safety + karmic effects -> MCP ToolAnnotations),
explicit-override merging, router aggregation, wire format, and the
registry invariants that guarantee complete coverage.
"""
from __future__ import annotations

import pytest

from whitemagic.tools.annotations import (
    CURATED_IDEMPOTENT,
    aggregate_annotations,
    derive_annotations,
    humanize,
    resolve_annotations,
)
from whitemagic.tools.tool_types import (
    McpAnnotations,
    ToolCategory,
    ToolDefinition,
    ToolSafety,
)


def _def(
    name: str,
    safety: ToolSafety,
    annotations: McpAnnotations | None = None,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=f"Test tool {name}",
        category=ToolCategory.SYSTEM,
        safety=safety,
        input_schema={"type": "object", "properties": {}},
        annotations=annotations,
    )


class TestHumanize:
    def test_underscore(self):
        assert humanize("create_memory") == "Create Memory"

    def test_dotted(self):
        assert humanize("galaxy.search") == "Galaxy Search"


class TestDerivationPolicy:
    """Pure policy table: safety x effects -> hints (no registry involved)."""

    def test_read_pure(self):
        ann = derive_annotations("some_status_tool", ToolSafety.READ, {"PURE"})
        assert ann.read_only is True
        assert ann.destructive is False
        assert ann.idempotent is True
        assert ann.open_world is False
        assert ann.title == "Some Status Tool"

    def test_read_observation(self):
        ann = derive_annotations("metrics_probe", ToolSafety.READ, {"OBSERVATION"})
        assert ann.read_only is True

    def test_read_with_write_effect_is_not_read_only(self):
        ann = derive_annotations("sneaky", ToolSafety.READ, {"LOCAL_WRITE"})
        assert ann.read_only is False

    def test_delete_is_destructive(self):
        ann = derive_annotations("destroy_everything", ToolSafety.DELETE, {"LOCAL_WRITE"})
        assert ann.read_only is False
        assert ann.destructive is True
        assert ann.idempotent is False

    def test_destructive_effect_marks_read_tool(self):
        ann = derive_annotations("purge_cache", ToolSafety.READ, {"DESTRUCTIVE"})
        assert ann.destructive is True

    def test_write_defaults(self):
        ann = derive_annotations("mutate_thing", ToolSafety.WRITE, {"LOCAL_WRITE"})
        assert ann.read_only is False
        assert ann.destructive is False
        assert ann.idempotent is False

    def test_network_is_open_world(self):
        ann = derive_annotations("call_api", ToolSafety.READ, {"NETWORK", "PURE"})
        assert ann.open_world is True
        assert ann.read_only is False  # NETWORK not in {PURE, OBSERVATION}

    def test_curated_idempotent(self):
        assert "create_memory" in CURATED_IDEMPOTENT
        ann = derive_annotations("create_memory", ToolSafety.WRITE, {"LOCAL_WRITE"})
        assert ann.idempotent is True
        assert ann.read_only is False

    def test_five_fields_always_present(self):
        for safety in (ToolSafety.READ, ToolSafety.WRITE, ToolSafety.DELETE):
            d = derive_annotations("whatever_tool", safety, set()).to_dict()
            for field in (
                "title",
                "readOnlyHint",
                "destructiveHint",
                "idempotentHint",
                "openWorldHint",
            ):
                assert d[field] is not None


class TestResolveIntegration:
    """Resolver against the real effect registry with real tool names."""

    def test_real_read_tool(self):
        ann = resolve_annotations(_def("pulse.status", ToolSafety.READ))
        assert ann.read_only is True
        assert ann.idempotent is True

    def test_real_network_tool_is_open_world(self):
        # web_fetch is in the effect registry's NETWORK set
        ann = resolve_annotations(_def("web_fetch", ToolSafety.READ))
        assert ann.open_world is True

    def test_explicit_partial_override_wins(self):
        explicit = McpAnnotations(idempotent=True)
        ann = resolve_annotations(
            _def("bounty.create", ToolSafety.WRITE, annotations=explicit)
        )
        assert ann.idempotent is True  # override
        assert ann.read_only is False  # derived
        assert ann.title == "Bounty Create"  # derived


class TestAggregation:
    def test_all_read_children_makes_read_only_router(self):
        children = [
            derive_annotations(f"status_{i}", ToolSafety.READ, {"PURE"}) for i in range(3)
        ]
        agg = aggregate_annotations("gana_test", children)
        assert agg.read_only is True
        assert agg.destructive is False
        assert agg.idempotent is True

    def test_any_destructive_child_makes_destructive_router(self):
        children = [
            derive_annotations("status_a", ToolSafety.READ, {"PURE"}),
            derive_annotations("delete_b", ToolSafety.DELETE, {"DESTRUCTIVE"}),
        ]
        agg = aggregate_annotations("gana_test", children)
        assert agg.read_only is False
        assert agg.destructive is True
        assert agg.idempotent is False

    def test_empty_children_worst_case(self):
        agg = aggregate_annotations("gana_empty", [])
        assert agg.read_only is False
        assert agg.destructive is False
        assert agg.idempotent is False
        assert agg.open_world is False
        assert agg.title == "Gana Empty"


class TestWireFormat:
    def test_to_dict_camel_case_and_none_omitted(self):
        ann = McpAnnotations(title="X", read_only=True)
        assert ann.to_dict() == {"title": "X", "readOnlyHint": True}

    def test_to_mcp_tool_includes_annotations(self):
        tool = _def("pulse.status", ToolSafety.READ)
        mcp = tool.to_mcp_tool()
        assert mcp["title"] == "Pulse Status"
        assert mcp["annotations"]["readOnlyHint"] is True
        assert "inputSchema" in mcp


class TestRegistryInvariants:
    def test_no_unclassified_tools(self):
        """Registry must have zero UNCLASSIFIED tools regardless of import
        order (regression: registry_defs importing whitemagic.tools.registry
        caused partially-initialized modules and silent definition loss)."""
        from whitemagic.tools.registry import get_all_tools

        unclassified = [
            t.name for t in get_all_tools() if t.safety == ToolSafety.UNCLASSIFIED
        ]
        assert unclassified == []

    def test_economy_tools_have_authored_safety(self):
        from whitemagic.tools.registry import get_all_tools

        by_name = {t.name: t for t in get_all_tools()}
        assert by_name["pulse.status"].safety == ToolSafety.READ
        assert by_name["bounty.list"].safety == ToolSafety.READ
        assert by_name["bounty.create"].safety == ToolSafety.WRITE
        assert by_name["memory.rent"].safety == ToolSafety.WRITE

    def test_every_registry_tool_resolves_complete_annotations(self):
        from whitemagic.tools.registry import get_all_tools

        for t in get_all_tools():
            ann = resolve_annotations(t).to_dict()
            for field in (
                "title",
                "readOnlyHint",
                "destructiveHint",
                "idempotentHint",
                "openWorldHint",
            ):
                assert ann.get(field) is not None, f"{t.name} missing {field}"


class TestExposedSurface:
    def test_wm_tool_def_annotated_and_current_count(self):
        """The exposed wm meta-tool must carry title, annotations, and a
        generated (non-stale) tool count in its description."""
        from whitemagic.run_mcp_lean import _wm_tool_def
        from whitemagic.tools.tool_catalog import get_dispatch_tool_names

        tool = _wm_tool_def()
        assert tool.title == "WhiteMagic Cognitive OS"
        assert tool.annotations is not None
        # Universal router: truthful worst-case hints
        assert tool.annotations.readOnlyHint is False
        assert tool.annotations.openWorldHint is True
        # Generated count: must match dispatch ground truth, never stale
        expected = str(len(get_dispatch_tool_names()))
        assert f"{expected}-tool" in tool.description
        assert "678" not in tool.description

    @pytest.mark.parametrize("gana", ["gana_neck", "gana_heart", "gana_ghost"])
    def test_gana_tools_annotated(self, gana, monkeypatch):
        """PRAT-mode Gana tools must carry title + aggregated annotations."""
        monkeypatch.setenv("WM_MCP_PRAT", "1")
        import asyncio

        from whitemagic.run_mcp_lean import list_tools

        tools = asyncio.run(list_tools())
        by_name = {t.name: t for t in tools}
        assert gana in by_name
        t = by_name[gana]
        assert t.title
        assert t.annotations is not None
        assert t.annotations.readOnlyHint is not None
        assert t.annotations.destructiveHint is not None
