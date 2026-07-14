"""Phase 3 §7.3 — Tests verifying mechanical enforcement of fast-path safety declarations.

Verifies that:
- FastPathSafety dataclass exists with all 5 safety constraints
- ToolDefinition.fast_path_eligible property enforces safety=READ + fast_path_safety
- Tools with fast_path=True but safety=WRITE are NOT eligible
- Tools with fast_path=True but no fast_path_safety are NOT eligible
- Tools with fast_path_safety but any constraint False are NOT eligible
- _ensure_fast_path_registry skips ineligible tools with a warning
"""
from __future__ import annotations

import pytest


class TestFastPathSafetyDataclass:
    """Verify FastPathSafety dataclass structure and defaults."""

    def test_fast_path_safety_exists(self):
        from whitemagic.tools.tool_types import FastPathSafety
        fps = FastPathSafety()
        assert fps is not None

    def test_all_defaults_true(self):
        from whitemagic.tools.tool_types import FastPathSafety
        fps = FastPathSafety()
        assert fps.no_writes is True
        assert fps.no_network is True
        assert fps.no_secrets is True
        assert fps.no_user_sensitive_output is True
        assert fps.no_policy_dependent_behavior is True

    def test_all_satisfied_property(self):
        from whitemagic.tools.tool_types import FastPathSafety
        assert FastPathSafety().all_satisfied is True
        assert FastPathSafety(no_writes=False).all_satisfied is False
        assert FastPathSafety(no_network=False).all_satisfied is False
        assert FastPathSafety(no_secrets=False).all_satisfied is False
        assert FastPathSafety(no_user_sensitive_output=False).all_satisfied is False
        assert FastPathSafety(no_policy_dependent_behavior=False).all_satisfied is False

    def test_is_frozen(self):
        from whitemagic.tools.tool_types import FastPathSafety
        fps = FastPathSafety()
        with pytest.raises((AttributeError, Exception)):
            fps.no_writes = False  # type: ignore[misc]


class TestFastPathEligibleProperty:
    """Verify ToolDefinition.fast_path_eligible mechanically enforces safety."""

    def _make_td(self, **kwargs):
        from whitemagic.tools.tool_types import (
            ToolCategory,
            ToolDefinition,
            ToolSafety,
        )
        defaults = dict(
            name="test.tool",
            description="test",
            category=ToolCategory.INTROSPECTION,
            safety=ToolSafety.READ,
            input_schema={},
        )
        defaults.update(kwargs)
        return ToolDefinition(**defaults)

    def test_fast_path_false_not_eligible(self):
        td = self._make_td(fast_path=False)
        assert td.fast_path_eligible is False

    def test_fast_path_true_no_safety_not_eligible(self):
        """fast_path=True but no fast_path_safety → NOT eligible."""
        td = self._make_td(fast_path=True, fast_path_safety=None)
        assert td.fast_path_eligible is False

    def test_fast_path_true_write_safety_not_eligible(self):
        """fast_path=True but safety=WRITE → NOT eligible."""
        from whitemagic.tools.tool_types import FastPathSafety, ToolSafety
        td = self._make_td(
            fast_path=True,
            safety=ToolSafety.WRITE,
            fast_path_safety=FastPathSafety(),
        )
        assert td.fast_path_eligible is False

    def test_fast_path_true_delete_safety_not_eligible(self):
        """fast_path=True but safety=DELETE → NOT eligible."""
        from whitemagic.tools.tool_types import FastPathSafety, ToolSafety
        td = self._make_td(
            fast_path=True,
            safety=ToolSafety.DELETE,
            fast_path_safety=FastPathSafety(),
        )
        assert td.fast_path_eligible is False

    def test_fast_path_true_read_with_safety_eligible(self):
        """fast_path=True, safety=READ, fast_path_safety all satisfied → eligible."""
        from whitemagic.tools.tool_types import FastPathSafety, ToolSafety
        td = self._make_td(
            fast_path=True,
            safety=ToolSafety.READ,
            fast_path_safety=FastPathSafety(),
        )
        assert td.fast_path_eligible is True

    def test_fast_path_true_safety_constraint_false_not_eligible(self):
        """fast_path=True, safety=READ, but one constraint False → NOT eligible."""
        from whitemagic.tools.tool_types import FastPathSafety, ToolSafety
        td = self._make_td(
            fast_path=True,
            safety=ToolSafety.READ,
            fast_path_safety=FastPathSafety(no_writes=False),
        )
        assert td.fast_path_eligible is False

    def test_to_dict_includes_fast_path_fields(self):
        from whitemagic.tools.tool_types import FastPathSafety
        td = self._make_td(
            fast_path=True,
            fast_path_safety=FastPathSafety(),
        )
        d = td.to_dict()
        assert "fast_path" in d
        assert "fast_path_eligible" in d
        assert d["fast_path"] is True
        assert d["fast_path_eligible"] is True


class TestEnsureFastPathRegistryEnforcement:
    """Verify _ensure_fast_path_registry skips ineligible tools."""

    def test_ineligible_tool_not_added_to_registry(self):
        """A tool with fast_path=True but no fast_path_safety should not be in _FAST_PATH_FROM_REGISTRY."""
        from whitemagic.tools.dispatch_table import (
            _FAST_PATH_FROM_REGISTRY,
            _ensure_fast_path_registry,
        )
        # Clear and rebuild
        _FAST_PATH_FROM_REGISTRY.clear()
        _ensure_fast_path_registry()
        # All tools in the registry should be either gana_ghost or fast_path_eligible
        # We can't easily check each one, but we can verify the set is populated
        # and doesn't contain obviously ineligible tools
        if _FAST_PATH_FROM_REGISTRY:  # Only check if registry loaded
            # "memory_create" is a WRITE tool — should never be fast-path
            assert "memory_create" not in _FAST_PATH_FROM_REGISTRY
            assert "memory_delete" not in _FAST_PATH_FROM_REGISTRY

    def test_registry_cleared_and_rebuilt(self):
        """_ensure_fast_path_registry should be idempotent (only builds once)."""
        from whitemagic.tools.dispatch_table import (
            _FAST_PATH_FROM_REGISTRY,
            _ensure_fast_path_registry,
        )
        _FAST_PATH_FROM_REGISTRY.clear()
        _ensure_fast_path_registry()
        first = set(_FAST_PATH_FROM_REGISTRY)
        _ensure_fast_path_registry()  # Should be no-op
        second = set(_FAST_PATH_FROM_REGISTRY)
        assert first == second


class TestExplicitFastPathUnification:
    """Verify that every explicit _FAST_PATH_TOOLS entry has registry metadata."""

    def test_all_explicit_tools_have_registry_definitions(self):
        """Every tool in _FAST_PATH_TOOLS must have an authored ToolDefinition."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_TOOLS
        from whitemagic.tools.registry import get_all_tools

        registry_map = {td.name: td for td in get_all_tools()}
        missing = [n for n in _FAST_PATH_TOOLS if n not in registry_map]
        assert not missing, f"Explicit fast-path tools lacking registry defs: {missing}"

    def test_all_explicit_tools_have_fast_path_true(self):
        """Every tool in _FAST_PATH_TOOLS must have fast_path=True in registry."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_TOOLS
        from whitemagic.tools.registry import get_all_tools

        registry_map = {td.name: td for td in get_all_tools()}
        no_fp = [
            n for n in _FAST_PATH_TOOLS
            if n in registry_map and not registry_map[n].fast_path
        ]
        assert not no_fp, f"Explicit fast-path tools lacking fast_path=True: {no_fp}"

    def test_all_explicit_tools_are_eligible(self):
        """Every tool in _FAST_PATH_TOOLS must pass fast_path_eligible check."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_TOOLS
        from whitemagic.tools.registry import get_all_tools

        registry_map = {td.name: td for td in get_all_tools()}
        ineligible = [
            n for n in _FAST_PATH_TOOLS
            if n in registry_map and not registry_map[n].fast_path_eligible
        ]
        assert not ineligible, f"Ineligible explicit fast-path tools: {ineligible}"

    def test_unsafe_tools_excluded_from_fast_path(self):
        """Tools with write/side-effect behavior must NOT be in _FAST_PATH_TOOLS."""
        from whitemagic.tools.dispatch_table import _FAST_PATH_TOOLS

        excluded = {
            "consciousness.mode",    # Can set mode (write)
            "session_bootstrap",     # Starts daemons (side effects)
            "health.check",          # Dead entry (no handler)
            "system.status",         # Dead entry (no handler)
        }
        present = excluded & _FAST_PATH_TOOLS
        assert not present, f"Unsafe tools still in fast-path: {present}"

    def test_verify_explicit_fast_path_runs_clean(self):
        """_verify_explicit_fast_path should not raise for current tool set."""
        from whitemagic.tools.dispatch_table import _verify_explicit_fast_path
        _verify_explicit_fast_path()  # Should complete without error
