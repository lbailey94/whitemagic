"""Tests for Warps — declarative, stackable agent presets."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp())
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")

import pytest

from whitemagic.agents.warps import Warp, WarpManager, get_warp_manager


@pytest.fixture
def manager():
    """Get a fresh WarpManager instance."""
    return get_warp_manager()


class TestWarpDataclass:
    def test_creation(self):
        warp = Warp(name="test_warp", description="Test preset")
        assert warp.name == "test_warp"
        assert warp.tools_allowed is None
        assert warp.tools_denied == []
        assert warp.research_domains == []

    def test_to_dict(self):
        warp = Warp(
            name="dict_test",
            description="Dict test",
            tools_allowed=["tool1", "tool2"],
            dharma_profile="strict",
            inference_tier="edge",
            galaxies_accessible=["universal"],
            execution_mode="autonomous",
        )
        d = warp.to_dict()
        assert d["name"] == "dict_test"
        assert d["tools_allowed"] == ["tool1", "tool2"]
        assert d["dharma_profile"] == "strict"
        assert d["inference_tier"] == "edge"

    def test_from_dict(self):
        data = {
            "name": "from_dict_test",
            "description": "From dict",
            "tools_allowed": ["tool_a"],
            "dharma_profile": "research",
            "inference_tier": "local_large",
            "galaxies_accessible": ["codex"],
            "execution_mode": "dream",
            "research_domains": ["cognitive"],
        }
        warp = Warp.from_dict(data)
        assert warp.name == "from_dict_test"
        assert warp.tools_allowed == ["tool_a"]
        assert warp.execution_mode == "dream"


class TestWarpManager:
    def test_builtin_warps_loaded(self, manager):
        assert "researcher" in manager._warps
        assert "archivist" in manager._warps
        assert "sentinel" in manager._warps
        assert "oracle" in manager._warps
        assert "diplomat" in manager._warps
        assert "evolutionist" in manager._warps

    def test_load_warp(self, manager):
        warp = manager.load_warp("researcher")
        assert warp is not None
        assert warp.name == "researcher"
        assert warp.execution_mode == "autonomous"

    def test_load_nonexistent_warp(self, manager):
        warp = manager.load_warp("nonexistent_warp_12345")
        assert warp is None

    def test_list_warps(self, manager):
        warps = manager.list_warps()
        assert len(warps) >= 6  # At least the built-ins
        names = [w["name"] for w in warps]
        assert "researcher" in names
        assert "sentinel" in names

    def test_stack_warps(self, manager):
        stacked = manager.stack_warps(["researcher", "sentinel"])
        assert stacked is not None
        # Sentinel should override execution mode
        assert stacked.name == "researcher+sentinel"
        # Sentinel's tools_allowed should override researcher's None
        assert stacked.tools_allowed is not None
        # Sentinel's denied tools should be included
        assert "memory.store" in stacked.tools_denied

    def test_stack_single_warp(self, manager):
        stacked = manager.stack_warps(["oracle"])
        assert stacked is not None
        assert stacked.name == "oracle"
        assert stacked.execution_mode == "dream"

    def test_stack_empty(self, manager):
        assert manager.stack_warps([]) is None

    def test_stack_with_nonexistent(self, manager):
        stacked = manager.stack_warps(["researcher", "nonexistent_warp"])
        assert stacked is not None
        # Should still work, just skipping the nonexistent one
        assert "researcher" in stacked.name

    def test_create_custom_warp(self, manager):
        warp = Warp(
            name="custom_test_warp",
            description="Custom test",
            tools_allowed=["tool1"],
            execution_mode="interactive",
        )
        result = manager.create_warp(warp, persist=False)
        assert result["status"] == "success"
        assert result["persisted"] is False

        # Should be loadable
        loaded = manager.load_warp("custom_test_warp")
        assert loaded is not None
        assert loaded.name == "custom_test_warp"

    def test_delete_custom_warp(self, manager):
        warp = Warp(name="deletable_warp", description="To be deleted")
        manager.create_warp(warp, persist=False)
        result = manager.delete_warp("deletable_warp")
        assert result["status"] == "success"
        assert manager.load_warp("deletable_warp") is None

    def test_delete_builtin_warp_fails(self, manager):
        result = manager.delete_warp("researcher")
        assert result["status"] == "error"

    def test_get_status(self, manager):
        status = manager.get_status()
        assert "builtin_warps" in status
        assert "custom_warps" in status
        assert "warp_names" in status
        assert status["builtin_warps"] >= 6

    def test_researcher_warp_config(self, manager):
        warp = manager.load_warp("researcher")
        assert warp.dharma_profile == "research"
        assert warp.inference_tier == "local_large"
        assert "codex" in warp.galaxies_accessible
        assert warp.shelter_template == "research"

    def test_sentinel_warp_config(self, manager):
        warp = manager.load_warp("sentinel")
        assert warp.dharma_profile == "strict"
        assert warp.inference_tier == "edge"
        assert "memory.store" in warp.tools_denied
        assert warp.shelter_template == "secure"

    def test_diplomat_warp_config(self, manager):
        warp = manager.load_warp("diplomat")
        assert "mesh.connect" in warp.tools_allowed
        assert "galaxy.export" in warp.tools_allowed
        assert warp.shelter_template == "production"

    def test_evolutionist_warp_config(self, manager):
        warp = manager.load_warp("evolutionist")
        assert warp.metadata.get("autoswarm_enabled") is True
        assert "evolution" in warp.research_domains
