"""Tests for multi-galaxy parallel access, sharing, and cross-galaxy search."""

# ruff: noqa: BLE001

import tempfile
import threading

import pytest

from whitemagic.core.memory.galaxy_manager import GalaxyManager


@pytest.fixture
def _clean_galaxy_manager():
    """Create a fresh GalaxyManager with a temp registry."""
    # Reset singleton
    GalaxyManager._instance = None

    # Use temp dir for registry
    from pathlib import Path

    import whitemagic.core.memory.galaxy_manager as gm_mod

    original_registry = gm_mod._REGISTRY_PATH
    tmpdir = tempfile.mkdtemp(prefix="wm_test_galaxy_")
    gm_mod._REGISTRY_PATH = Path(tmpdir) / "galaxies.json"

    # Also set WM_ROOT to temp for galaxy DB creation

    # Create manager
    gm = GalaxyManager.get_instance()

    yield gm

    # Cleanup
    GalaxyManager._instance = None
    gm_mod._REGISTRY_PATH = original_registry


class TestSearchMultiGalaxy:
    """Test parallel multi-galaxy search."""

    def test_search_multi_galaxy_returns_dict(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        result = gm.search_multi_galaxy(query="test", limit=5)
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "success"
        assert "galaxies_searched" in result
        assert "total_results" in result
        assert "results" in result
        assert "per_galaxy" in result

    def test_search_multi_galaxy_with_specific_galaxies(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        result = gm.search_multi_galaxy(
            query="test",
            galaxies=["default"],
            limit=5,
        )
        assert result["status"] == "success"
        assert isinstance(result["galaxies_searched"], int)

    def test_search_multi_galaxy_invalid_galaxy_raises(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        with pytest.raises(ValueError, match="not found"):
            gm.search_multi_galaxy(galaxies=["nonexistent_galaxy"])

    def test_search_multi_galaxy_no_query(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        result = gm.search_multi_galaxy(limit=3)
        assert result["status"] == "success"
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_search_multi_galaxy_errors_field(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        result = gm.search_multi_galaxy(query="test", limit=1)
        # errors should be None if no errors, or dict if errors
        assert "errors" in result
        assert result["errors"] is None or isinstance(result["errors"], dict)

    def test_search_multi_galaxy_results_sorted_by_importance(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        result = gm.search_multi_galaxy(limit=10)
        results = result["results"]
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].get("importance", 0) >= results[i + 1].get("importance", 0)


class TestGetMemoryForGalaxy:
    """Test getting UnifiedMemory for a specific galaxy without switching."""

    def test_get_memory_for_galaxy_returns_object(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        um = gm.get_memory_for_galaxy("default")
        assert um is not None
        assert hasattr(um, "store")
        assert hasattr(um, "search")

    def test_get_memory_for_galaxy_invalid_raises(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        with pytest.raises(ValueError, match="not found"):
            gm.get_memory_for_galaxy("nonexistent")

    def test_get_memory_for_galaxy_doesnt_switch(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        active_before = gm._active_galaxy
        gm.get_memory_for_galaxy("default")
        assert gm._active_galaxy == active_before


class TestShareGalaxy:
    """Test galaxy sharing between users."""

    def test_share_galaxy_creates_entry(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        result = gm.share_galaxy(name="default", target_user_id="alice")
        assert result["status"] == "shared"
        assert result["galaxy"] == "default"
        assert result["shared_with"] == "alice"
        assert "db_path" in result

    def test_share_galaxy_already_shared(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        gm.share_galaxy(name="default", target_user_id="alice")
        result = gm.share_galaxy(name="default", target_user_id="alice")
        assert result["status"] == "already_shared"

    def test_share_galaxy_invalid_name_raises(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        with pytest.raises(ValueError, match="not found"):
            gm.share_galaxy(name="nonexistent", target_user_id="alice")

    def test_shared_galaxy_appears_in_list(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        gm.share_galaxy(name="default", target_user_id="bob")
        shared = gm.list_shared_galaxies(user_id="bob")
        assert len(shared) == 1
        assert shared[0]["name"] == "default"
        assert "shared" in shared[0]["tags"]

    def test_list_shared_galaxies_empty(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        shared = gm.list_shared_galaxies(user_id="nobody")
        assert shared == []


class TestThreadSafety:
    """Test that multi-galaxy operations are thread-safe."""

    def test_concurrent_search_multi_galaxy(self, _clean_galaxy_manager):
        gm = _clean_galaxy_manager
        results = []
        errors = []

        def _search():
            try:
                r = gm.search_multi_galaxy(query="test", limit=5)
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_search) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 4
        for r in results:
            assert r["status"] == "success"
