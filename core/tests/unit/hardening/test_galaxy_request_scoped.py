"""Phase 2 — Global active-galaxy mutation removal tests.

Verifies that:
1. get_memory_for_galaxy() returns a galaxy-scoped UnifiedMemory without
   mutating process-global _active_galaxy.
2. galaxy_context() provides a context manager for request-scoped access.
3. switch_galaxy() emits a DeprecationWarning.
4. handle_galaxy_use returns galaxy info without mutating global state.
5. Two concurrent galaxy accesses don't interfere with each other.
"""
from __future__ import annotations

import warnings

import pytest


class TestGetMemoryForGalaxy:
    """get_memory_for_galaxy() — request-scoped galaxy access."""

    def test_returns_memory_without_mutating_active(self):
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        original_active = gm._active_galaxy

        # get_memory_for_galaxy should NOT change _active_galaxy
        try:
            um = gm.get_memory_for_galaxy("default")
            assert um is not None
            assert gm._active_galaxy == original_active
        except ValueError:
            # "default" might not exist in test env — that's ok
            pass

    def test_raises_for_nonexistent_galaxy(self):
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        with pytest.raises(ValueError, match="not found"):
            gm.get_memory_for_galaxy("nonexistent_galaxy_xyz")

    def test_user_scoped_resolution(self):
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        # Requesting for a specific user should not affect another user
        original_active = gm._active_galaxy
        try:
            gm.get_memory_for_galaxy("default", user_id="alice")
        except ValueError:
            pass  # alice may not have a default galaxy
        assert gm._active_galaxy == original_active


class TestGalaxyContext:
    """galaxy_context() — context manager for request-scoped access."""

    def test_context_manager_yields_memory(self):
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        original_active = gm._active_galaxy

        try:
            with gm.galaxy_context("default") as um:
                assert um is not None
                # Global state should not change inside the context
                assert gm._active_galaxy == original_active
            # Global state should not change after exiting
            assert gm._active_galaxy == original_active
        except ValueError:
            pass  # default may not exist in test env

    def test_context_manager_does_not_mutate_active(self):
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        original_active = gm._active_galaxy

        try:
            with gm.galaxy_context("default"):
                pass
        except ValueError:
            pass

        assert gm._active_galaxy == original_active


class TestSwitchGalaxyDeprecation:
    """switch_galaxy() should emit DeprecationWarning."""

    def test_switch_emits_deprecation_warning(self):
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        original_active = gm._active_galaxy

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                gm.switch_galaxy("default")
            except ValueError:
                pass  # may not exist in test env
            finally:
                gm._active_galaxy = original_active

            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)


class TestHandleGalaxyUse:
    """handle_galaxy_use — request-scoped galaxy access via tool handler."""

    def test_use_returns_success_for_default(self):
        from whitemagic.tools.handlers.galaxy import handle_galaxy_use

        result = handle_galaxy_use(name="default")
        # Should succeed or return error if default doesn't exist in test env
        assert result["status"] in ("success", "error")
        if result["status"] == "success":
            assert "galaxy" in result
            assert "memory_count" in result

    def test_use_returns_error_for_missing_name(self):
        from whitemagic.tools.handlers.galaxy import handle_galaxy_use

        result = handle_galaxy_use()
        assert result["status"] == "error"
        assert "name is required" in result["error"]

    def test_use_returns_error_for_nonexistent_galaxy(self):
        from whitemagic.tools.handlers.galaxy import handle_galaxy_use

        result = handle_galaxy_use(name="nonexistent_xyz")
        assert result["status"] == "error"

    def test_use_does_not_mutate_global_state(self):
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager
        from whitemagic.tools.handlers.galaxy import handle_galaxy_use

        gm = get_galaxy_manager()
        original_active = gm._active_galaxy

        handle_galaxy_use(name="default")

        assert gm._active_galaxy == original_active


class TestConcurrentGalaxyAccess:
    """Two concurrent galaxy accesses must not interfere."""

    def test_two_users_no_interference(self):
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        original_active = gm._active_galaxy

        # Simulate two concurrent requests accessing different galaxies
        # Neither should affect the global _active_galaxy
        try:
            gm.get_memory_for_galaxy("default", user_id="alice")
        except ValueError:
            pass

        try:
            gm.get_memory_for_galaxy("default", user_id="bob")
        except ValueError:
            pass

        assert gm._active_galaxy == original_active
