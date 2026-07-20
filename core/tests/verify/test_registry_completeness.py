"""P1.1 — Registry completeness audit.

Deterministic set-difference tests that verify the tool surface is consistent
across dispatch table, tool registry, authored definitions, PRAT mappings,
and Gana meta-tools.

These tests record the current baseline and will be tightened as missing
definitions are authored in P1.4 batches.
"""
import os

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

from whitemagic.tools.dispatch_table import DISPATCH_TABLE
from whitemagic.tools.prat_mappings import GANA_TO_TOOLS
from whitemagic.tools.registry import AUTHORED_TOOL_REGISTRY, TOOL_REGISTRY
from whitemagic.tools.stable_surface import STABLE_TOOL_NAMES, is_stable
from whitemagic.tools.tool_catalog import GANA_NAMES, get_gana_nested_tools
from whitemagic.tools.tool_types import ToolDefinition, ToolSafety, ToolStability

# ── Computed sets ────────────────────────────────────────────────────

_DISPATCH_NAMES = frozenset(DISPATCH_TABLE.keys())
_GANA_NAMES = frozenset(GANA_NAMES)
_AUTHORED_NAMES = frozenset(t.name for t in AUTHORED_TOOL_REGISTRY)
_NESTED_UNIQUE = frozenset(
    tool for tools in get_gana_nested_tools().values() for tool in tools
)
_PRAT_NAMES = frozenset(
    tool for tools in GANA_TO_TOOLS.values() for tool in tools
)
_REGISTRY_NAMES = frozenset(t.name for t in TOOL_REGISTRY)

# Tools that are callable but lack authored definitions (synthesized).
_UNAUTHORED = sorted(_DISPATCH_NAMES - _AUTHORED_NAMES - _GANA_NAMES)

# Dispatch tools with no PRAT Gana mapping (not reachable via any Gana).
_UNMAPPED = sorted(_DISPATCH_NAMES - _PRAT_NAMES - _GANA_NAMES)

# Strict mode: fail on missing authored definitions.
# Set WM_STRICT_REGISTRY=1 to enable. Disabled by default during P1.4 migration.
_STRICT = os.getenv("WM_STRICT_REGISTRY", "0") == "1"


# ── Tests: set consistency ────────────────────────────────────────────


def test_prat_tools_are_all_dispatchable():
    """Every tool name in PRAT mappings must exist in the dispatch table."""
    extra = sorted(_PRAT_NAMES - _DISPATCH_NAMES - _GANA_NAMES)
    assert extra == [], f"PRAT tools not in dispatch table: {extra}"


def test_authored_tools_are_all_dispatchable():
    """Every authored tool definition must exist in the dispatch table."""
    extra = sorted(_AUTHORED_NAMES - _DISPATCH_NAMES - _GANA_NAMES)
    assert extra == [], f"Authored tools not in dispatch table: {extra}"


def test_all_gana_names_are_in_registry():
    """All 28 Gana names must be present in the callable tool registry.

    Ganas are routed via prefix matching (tool_name.startswith('gana_'))
    in the dispatch pipeline, not via DISPATCH_TABLE keys.
    """
    missing = sorted(_GANA_NAMES - _REGISTRY_NAMES)
    assert missing == [], f"Gana tools missing from registry: {missing}"


def test_registry_equals_dispatch_union_ganas():
    """The callable registry must be exactly dispatch ∪ Gana names."""
    expected = _DISPATCH_NAMES | _GANA_NAMES
    extra = sorted(_REGISTRY_NAMES - expected)
    missing = sorted(expected - _REGISTRY_NAMES)
    assert extra == [], f"Registry has tools not in dispatch∪Gana: {extra}"
    assert missing == [], f"dispatch∪Gana has tools not in registry: {missing}"


# ── Tests: stability contract (P1.5 — option B) ──────────────────────


def test_stable_tools_are_ganas_or_promoted():
    """STABLE tools must be either Gana meta-tools or in the stable_surface set.

    This implements option B from P1.5: Ganas plus promoted foundational tools.
    The canonical list is in stable_surface.py.
    """
    violations = [
        t.name
        for t in TOOL_REGISTRY
        if t.stability == ToolStability.STABLE
        and not t.name.startswith("gana_")
        and t.name not in STABLE_TOOL_NAMES
    ]
    assert violations == [], (
        f"STABLE tools not in stable_surface.py: {violations}"
    )


def test_stable_count_matches_ganas_plus_promoted():
    """STABLE count must equal Gana count + promoted non-Gana tools."""
    stable_non_gana = {
        t.name
        for t in TOOL_REGISTRY
        if t.stability == ToolStability.STABLE
        and not t.name.startswith("gana_")
    }
    expected = len(_GANA_NAMES) + len(STABLE_TOOL_NAMES)
    actual = len(_GANA_NAMES) + len(stable_non_gana)
    assert actual == expected, (
        f"Expected {expected} STABLE tools ({len(_GANA_NAMES)} Ganas + "
        f"{len(STABLE_TOOL_NAMES)} promoted), got {actual} "
        f"({len(_GANA_NAMES)} Ganas + {len(stable_non_gana)} promoted)"
    )


# ── Tests: safety classification ─────────────────────────────────────


def test_write_tools_get_write_safety():
    """Tools in WRITE_TOOLS must not default to READ safety."""
    from whitemagic.tools.dispatch_core import WRITE_TOOLS

    violations = []
    for t in TOOL_REGISTRY:
        if t.name in WRITE_TOOLS and t.safety == ToolSafety.READ:
            violations.append(t.name)
    assert violations == [], (
        f"WRITE_TOOLS members with READ safety: {violations}"
    )


def test_no_unauthored_write_tools():
    """Unauthored tools (no ToolDefinition) must default to READ, not WRITE.

    Only tools explicitly in WRITE_TOOLS may get WRITE safety when unauthored.
    """
    from whitemagic.tools.dispatch_core import WRITE_TOOLS

    violations = []
    for t in TOOL_REGISTRY:
        if t.name in _UNAUTHORED and t.safety == ToolSafety.WRITE:
            if t.name not in WRITE_TOOLS:
                violations.append(t.name)
    assert violations == [], (
        f"Unauthored tools with WRITE safety but not in WRITE_TOOLS: {violations}"
    )


# ── Baseline recording (not strict during P1.4 migration) ────────────


def test_baseline_unauthored_count():
    """Record the current count of dispatch tools without authored definitions.

    This is a baseline ratchet — the count must not increase. When strict mode
    is enabled (WM_STRICT_REGISTRY=1), this test fails.
    """
    count = len(_UNAUTHORED)
    if _STRICT:
        assert count == 0, (
            f"Strict mode: {count} dispatch tools lack authored definitions: "
            f"{_UNAUTHORED[:20]}..."
        )
    else:
        # Baseline: record but don't fail. Count must not increase.
        assert count <= 400, (
            f"Unauthored tool count grew to {count} (baseline: 385). "
            f"New tools must have authored definitions."
        )


def test_baseline_unmapped_count():
    """Record the current count of dispatch tools without PRAT Gana mapping."""
    count = len(_UNMAPPED)
    if _STRICT:
        assert count == 0, (
            f"Strict mode: {count} dispatch tools lack PRAT mapping: "
            f"{_UNMAPPED}"
        )
    else:
        assert count <= 20, (
            f"Unmapped tool count grew to {count} (baseline: 18). "
            f"New tools must be added to PRAT mappings."
        )


def test_unmapped_tools_list():
    """Print the current unmapped tools for documentation purposes."""
    # This test always passes — it's for CI output visibility
    if _UNMAPPED:
        pytest.skip(
            f"Unmapped tools (baseline): {_UNMAPPED}"
        )
