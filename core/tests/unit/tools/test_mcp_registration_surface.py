import pytest

# Skip tests for deprecated hydrated MCP server (v22.0.0 replaced with lean server)
pytestmark = pytest.mark.skip(reason="Tests deprecated hydrated MCP server; replaced by run_mcp_lean with 28 Gana meta-tools")

try:
    from whitemagic.run_mcp import _register_prat_tools, get_registered_tool_definitions
except ImportError:
    pytest.skip("Tests deprecated hydrated MCP server", allow_module_level=True)

from whitemagic.tools.tool_surface import GANA_NAMES, get_surface_counts


def test_classic_registration_matches_callable_surface():
    counts = get_surface_counts()
    tool_defs = get_registered_tool_definitions(lite_mode=False)
    assert len(tool_defs) == counts["callable_tools"]


def test_lite_registration_is_filtered_subset_with_required_tools():
    counts = get_surface_counts()
    lite_defs = get_registered_tool_definitions(lite_mode=True)
    lite_names = {tool.name for tool in lite_defs}
    assert 0 < len(lite_defs) < counts["callable_tools"]
    for expected in ["gnosis", "capabilities", "manifest", "health_report", "search_memories"]:
        assert expected in lite_names


def test_prat_registration_count_matches_gana_contract():
    count = _register_prat_tools("")
    assert count == len(GANA_NAMES) == 28
