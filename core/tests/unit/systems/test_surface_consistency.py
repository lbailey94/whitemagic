from whitemagic.run_mcp import get_registered_tool_definitions
from whitemagic.runtime_status import get_runtime_status
from whitemagic.security.mcp_integrity import McpIntegrity
from whitemagic.tools.prat_router import validate_mapping
from whitemagic.tools.registry import TOOL_REGISTRY
from whitemagic.tools.tool_surface import GANA_NAMES, get_surface_counts


def test_cross_surface_counts_agree():
    counts = get_surface_counts()
    runtime = get_runtime_status()
    mapping = validate_mapping(TOOL_REGISTRY)
    classic_defs = get_registered_tool_definitions(lite_mode=False)
    lite_defs = get_registered_tool_definitions(lite_mode=True)

    assert runtime["surface_counts"] == counts
    assert counts["callable_tools"] == len(TOOL_REGISTRY) == len(classic_defs)
    assert counts["gana_tools"] == len(GANA_NAMES) == 28
    assert counts["dispatch_tools"] == counts["nested_unique_tools"]
    assert mapping["mapped"] == counts["nested_unique_tools"]
    assert mapping["unmapped"] == []
    assert mapping["orphaned"] == []
    assert 0 < len(lite_defs) < len(classic_defs)


def test_mcp_integrity_count_matches_callable_surface():
    counts = get_surface_counts()
    integrity = McpIntegrity(storage_dir=None)
    snapshot = integrity.snapshot()
    verify = integrity.verify()
    status = integrity.status()

    assert snapshot["tools_fingerprinted"] == counts["callable_tools"]
    assert verify["status"] == "success"
    assert verify["verified"] is True
    assert verify["baseline_count"] == counts["callable_tools"]
    assert verify["current_count"] == counts["callable_tools"]
    assert status["baseline_tool_count"] == counts["callable_tools"]
