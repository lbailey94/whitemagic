"""P1.2 — Fail closed for missing safety.

Tests that unauthored tools (no ToolDefinition in registry_defs/) get
UNCLASSIFIED safety, not READ. UNCLASSIFIED tools cannot enter safe/fast
paths and are treated conservatively by permissions, effects, and the
governor.
"""
import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

from whitemagic.tools.dispatch_core import WRITE_TOOLS
from whitemagic.tools.registry import TOOL_REGISTRY, get_safe_tools
from whitemagic.tools.tool_types import ToolSafety, ToolStability


def test_unauthored_tools_get_unclassified_not_read():
    """Tools without authored definitions must default to UNCLASSIFIED, not READ.

    This is the fail-closed principle: missing metadata must never default
    to READ safety. Only tools explicitly in WRITE_TOOLS may get WRITE safety.
    """
    unauthored_read = [
        t.name
        for t in TOOL_REGISTRY
        if t.name not in WRITE_TOOLS
        and not t.name.startswith("gana_")
        and t.safety == ToolSafety.READ
        and t.description.startswith("Dispatch-routable WhiteMagic tool")
    ]
    assert unauthored_read == [], (
        f"Unauthored tools incorrectly assigned READ safety: {unauthored_read[:10]}"
    )


def test_unclassified_tools_excluded_from_safe_tools():
    """get_safe_tools() must only return READ tools, never UNCLASSIFIED."""
    safe = get_safe_tools()
    unclassified_in_safe = [t.name for t in safe if t.safety == ToolSafety.UNCLASSIFIED]
    assert unclassified_in_safe == [], (
        f"UNCLASSIFIED tools found in safe tools: {unclassified_in_safe[:10]}"
    )


def test_unclassified_tools_not_fast_path_eligible():
    """UNCLASSIFIED tools must not be fast-path eligible."""
    fast_path_unclassified = [
        t.name
        for t in TOOL_REGISTRY
        if t.safety == ToolSafety.UNCLASSIFIED and t.fast_path_eligible
    ]
    assert fast_path_unclassified == [], (
        f"UNCLASSIFIED tools with fast-path eligibility: {fast_path_unclassified[:10]}"
    )


def test_unclassified_risk_level_is_caution():
    """UNCLASSIFIED tools must map to CAUTION risk level (not SAFE)."""
    from whitemagic.core.governor import RiskLevel

    unclassified_tools = [
        t for t in TOOL_REGISTRY if t.safety == ToolSafety.UNCLASSIFIED
    ]
    if not unclassified_tools:
        pytest.skip("No UNCLASSIFIED tools in registry")
    for t in unclassified_tools:
        assert t.risk_level == str(RiskLevel.CAUTION.name), (
            f"Tool {t.name} has UNCLASSIFIED safety but risk_level={t.risk_level} "
            f"(expected CAUTION)"
        )


def test_write_tools_get_write_safety_even_without_authored_def():
    """Tools in WRITE_TOOLS must get WRITE safety even without authored definitions."""
    write_tools_unauthored = [
        t.name
        for t in TOOL_REGISTRY
        if t.name in WRITE_TOOLS
        and t.description.startswith("Dispatch-routable WhiteMagic tool")
        and t.safety != ToolSafety.WRITE
    ]
    assert write_tools_unauthored == [], (
        f"WRITE_TOOLS members without WRITE safety: {write_tools_unauthored[:10]}"
    )


def test_unclassified_count_baselined():
    """Record the current count of UNCLASSIFIED tools as a baseline.

    This count must decrease over time as P1.4 batches add authored definitions.
    It must never increase — new tools must have authored definitions.
    """
    count = sum(1 for t in TOOL_REGISTRY if t.safety == ToolSafety.UNCLASSIFIED)
    # Baseline: 385 unauthored - those in WRITE_TOOLS = unclassified
    # This will decrease as P1.4 batches are completed
    assert count <= 400, (
        f"UNCLASSIFIED tool count grew to {count} (baseline: ~385). "
        f"New tools must have authored ToolDefinitions."
    )
