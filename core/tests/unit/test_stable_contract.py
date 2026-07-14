"""Tests for stable_contract module."""

from whitemagic.tools.stable_contract import (
    STABLE_TOOLS,
    StableTool,
    ToolStability,
    get_deprecated_aliases,
    get_stable_tools,
    is_stable_tool,
)


class TestStableTool:
    def test_dataclass_creation(self):
        st = StableTool(
            name="test_tool",
            description="A test tool",
            stability=ToolStability.STABLE,
            since_version="1.0.0",
            deprecated_aliases=[],
            required_params=["x"],
            optional_params=["y"],
            response_schema={"status": "success"},
        )
        assert st.name == "test_tool"
        assert st.stability == ToolStability.STABLE

    def test_tool_stability_enum(self):
        assert ToolStability.STABLE == "stable"
        assert ToolStability.EXPERIMENTAL == "experimental"
        assert ToolStability.DEPRECATED == "deprecated"


class TestStableToolRegistry:
    def test_stable_tools_not_empty(self):
        assert len(STABLE_TOOLS) > 0

    def test_core_tools_present(self):
        assert "create_memory" in STABLE_TOOLS
        assert "search_memories" in STABLE_TOOLS
        assert "capabilities" in STABLE_TOOLS

    def test_get_stable_tools_returns_copy(self):
        tools = get_stable_tools()
        assert len(tools) == len(STABLE_TOOLS)
        assert "create_memory" in tools

    def test_is_stable_tool(self):
        assert is_stable_tool("create_memory") is True
        assert is_stable_tool("nonexistent_tool_12345") is False

    def test_get_deprecated_aliases(self):
        aliases = get_deprecated_aliases()
        assert isinstance(aliases, dict)
        # Some tools have deprecated aliases
        if aliases:
            assert all(
                isinstance(k, str) and isinstance(v, str) for k, v in aliases.items()
            )

    def test_stable_tool_schemas(self):
        for name, tool in STABLE_TOOLS.items():
            assert tool.name == name
            assert tool.since_version
            assert tool.response_schema
            assert isinstance(tool.required_params, list)
            assert isinstance(tool.optional_params, list)
