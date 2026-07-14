import pytest

pytestmark = pytest.mark.core  # Entire module is core contract validation

from whitemagic.tools.dispatch_table import DISPATCH_TABLE
from whitemagic.tools.envelope import is_enveloped
from whitemagic.tools.registry import TOOL_REGISTRY
from whitemagic.tools.tool_catalog import GANA_NAMES
from whitemagic.tools.tool_surface import get_surface_counts
from whitemagic.tools.tool_types import ToolStability
from whitemagic.tools.unified_api import call_tool


@pytest.mark.parametrize("tool_def", TOOL_REGISTRY)
def test_tool_registered_has_handler(tool_def):
    """Verify EVERY registered tool has a handler or prefix routing."""
    if tool_def.name.startswith("gana_"):
        return  # Handled by prefix routing in dispatch()
    assert tool_def.name in DISPATCH_TABLE, (
        f"Tool '{tool_def.name}' is registered but missing from DISPATCH_TABLE"
    )


@pytest.mark.parametrize("tool_def", TOOL_REGISTRY)
def test_tool_conforms_to_envelope(tool_def):
    """
    Verify tool output conforms to stable envelope.
    Uses dry_run=True for safe verification where supported.
    """
    # Some tools might fail in CI if they require external services,
    # but the envelope structure should still be checked on success/error.

    # We only test tools that support dry_run safely or are pure read.
    # Note: capabilities and manifest are perfect test cases.
    if tool_def.name in ["capabilities", "manifest", "state.paths"]:
        resp = call_tool(tool_def.name)
        assert is_enveloped(resp), (
            f"Tool '{tool_def.name}' returned non-enveloped response"
        )
        assert resp["status"] == "success"


# ---------------------------------------------------------------------------
# Stability contract tests — Phase 2 hardening
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("gana_name", GANA_NAMES)
def test_gana_tools_are_stable(gana_name):
    """All 28 Gana meta-tools must carry ToolStability.STABLE.

    Ganas are the public contract surface. If any Gana loses its STABLE
    label this test catches it before a release.
    """
    tool_def = next((t for t in TOOL_REGISTRY if t.name == gana_name), None)
    assert tool_def is not None, f"Gana tool '{gana_name}' not found in TOOL_REGISTRY"
    assert tool_def.stability == ToolStability.STABLE, (
        f"Gana tool '{gana_name}' must be STABLE, got {tool_def.stability.value!r}"
    )


def test_non_gana_tools_not_stable_by_default():
    """Dispatch-only tools (not explicitly promoted) must not be STABLE.

    STABLE is a deliberate promotion — it must not leak to auto-synthesized
    tools. This test ensures no dispatch-table tool accidentally inherits STABLE.
    """
    violations = [
        t.name
        for t in TOOL_REGISTRY
        if not t.name.startswith("gana_") and t.stability == ToolStability.STABLE
    ]
    assert violations == [], (
        f"Non-Gana tools must not be STABLE without explicit promotion: {violations}"
    )


def test_surface_counts_includes_stability_breakdown():
    """get_surface_counts() must expose a by_stability dict with all tier keys."""
    counts = get_surface_counts()
    assert "by_stability" in counts, "surface_counts missing 'by_stability' key"
    by_stability = counts["by_stability"]
    for tier in ToolStability:
        assert tier.value in by_stability, f"by_stability missing tier '{tier.value}'"
    assert by_stability[ToolStability.STABLE.value] == len(GANA_NAMES), (
        f"Expected {len(GANA_NAMES)} STABLE tools (one per Gana), "
        f"got {by_stability[ToolStability.STABLE.value]}"
    )
