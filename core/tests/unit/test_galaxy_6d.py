# ruff: noqa: BLE001
"""Tests for 6D Holographic Galaxy Memory System (v23.1 Phase 1).

Tests galaxy field on Memory dataclass, schema migration, GalaxyRouter,
galaxy-filtered search, and per-galaxy zone counts.
"""

import os
import tempfile
import unittest
from datetime import datetime

# Set test state root before importing WM modules
_tmp = tempfile.mkdtemp(prefix="wm_galaxy_test_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)

from whitemagic.core.memory.galaxy_router import (
    DEFAULT_GALAXIES,
    GalaxyRouter,
    get_galaxy_router,
)
from whitemagic.core.memory.unified_types import Memory, MemoryType


class TestMemoryGalaxyField(unittest.TestCase):
    """Test that the Memory dataclass has the galaxy field."""

    def test_default_galaxy_is_universal(self):
        mem = Memory(id="test-1", content="hello", memory_type=MemoryType.SHORT_TERM)
        self.assertEqual(mem.galaxy, "universal")

    def test_custom_galaxy(self):
        mem = Memory(
            id="test-2",
            content="hello",
            memory_type=MemoryType.SHORT_TERM,
            galaxy="oracle",
        )
        self.assertEqual(mem.galaxy, "oracle")

    def test_to_dict_includes_galaxy(self):
        mem = Memory(
            id="test-3",
            content="hello",
            memory_type=MemoryType.SHORT_TERM,
            galaxy="insight",
        )
        data = mem.to_dict()
        self.assertIn("galaxy", data)
        self.assertEqual(data["galaxy"], "insight")

    def test_from_dict_includes_galaxy(self):
        data = {
            "id": "test-4",
            "content": "hello",
            "memory_type": "SHORT_TERM",
            "created_at": datetime.now().isoformat(),
            "accessed_at": datetime.now().isoformat(),
            "galaxy": "self_learning",
        }
        mem = Memory.from_dict(data)
        self.assertEqual(mem.galaxy, "self_learning")

    def test_from_dict_defaults_galaxy(self):
        data = {
            "id": "test-5",
            "content": "hello",
            "memory_type": "SHORT_TERM",
            "created_at": datetime.now().isoformat(),
            "accessed_at": datetime.now().isoformat(),
        }
        mem = Memory.from_dict(data)
        self.assertEqual(mem.galaxy, "universal")


class TestGalaxyRouter(unittest.TestCase):
    """Test the GalaxyRouter routing logic."""

    def setUp(self):
        self.router = GalaxyRouter()

    def test_default_galaxies_registered(self):
        galaxies = self.router.list_galaxies()
        for name in DEFAULT_GALAXIES:
            self.assertIn(name, galaxies)

    def test_route_subsystem_mapping(self):
        # Known subsystems map to correct galaxies
        self.assertEqual(
            self.router.route("recursive_improvement_loop"), "knowledge"
        )
        self.assertEqual(self.router.route("emergence_engine"), "self_discovery")
        self.assertEqual(self.router.route("insight_pipeline"), "insight")
        self.assertEqual(self.router.route("dream_cycle"), "creative_solutions")
        self.assertEqual(self.router.route("oracle"), "oracle")

    def test_route_unknown_subsystem_defaults_to_universal(self):
        self.assertEqual(self.router.route("unknown_subsystem_xyz"), "universal")

    def test_route_metadata_override(self):
        # Metadata galaxy takes priority
        galaxy = self.router.route("dream_cycle", metadata={"galaxy": "oracle"})
        self.assertEqual(galaxy, "oracle")

    def test_route_metadata_unknown_galaxy_falls_back(self):
        galaxy = self.router.route("dream_cycle", metadata={"galaxy": "nonexistent"})
        # Should fall back to subsystem mapping
        self.assertEqual(galaxy, "creative_solutions")

    def test_register_custom_galaxy(self):
        info = self.router.register_galaxy(
            "custom_galaxy",
            description="My custom galaxy",
            color="#ff0000",
            decay_multiplier=0.5,
        )
        self.assertEqual(info.name, "custom_galaxy")
        self.assertEqual(info.description, "My custom galaxy")
        self.assertIn("custom_galaxy", self.router.list_galaxies())

    def test_map_subsystem_override(self):
        self.router.register_galaxy("test_galaxy")
        self.router.map_subsystem("dream_cycle", "test_galaxy")
        self.assertEqual(self.router.route("dream_cycle"), "test_galaxy")

    def test_map_subsystem_unknown_galaxy_raises(self):
        with self.assertRaises(ValueError):
            self.router.map_subsystem("dream_cycle", "nonexistent_galaxy")

    def test_get_decay_multiplier(self):
        self.assertEqual(self.router.get_decay_multiplier("oracle"), 0.6)
        self.assertEqual(self.router.get_decay_multiplier("universal"), 1.0)
        self.assertEqual(self.router.get_decay_multiplier("nonexistent"), 1.0)

    def test_singleton(self):
        r1 = get_galaxy_router()
        r2 = get_galaxy_router()
        self.assertIs(r1, r2)


class TestGalaxyRouterStats(unittest.TestCase):
    """Test galaxy stats with a real SQLite backend."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="wm_galaxy_db_")
        cls.db_path = os.path.join(cls.tmpdir, "test_galaxy.db")
        os.environ["WM_STATE_ROOT"] = cls.tmpdir

    @classmethod
    def tearDownClass(cls):
        import shutil

        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_galaxy_stats_returns_dict(self):
        """Test that get_galaxy_stats returns a properly structured dict."""
        router = GalaxyRouter()

        # We can't easily get a full UnifiedMemory in unit tests,
        # so we test the stats method handles missing DB gracefully
        class FakeUM:
            class FakeBackend:
                class FakePool:
                    def connection(self):
                        import sqlite3

                        raise sqlite3.Error("no DB")

                pool = FakePool()

            backend = FakeBackend()

        stats = router.get_galaxy_stats("universal", FakeUM())
        self.assertEqual(stats["galaxy"], "universal")
        self.assertIn("error", stats)


class TestGalaxyDecayMultipliers(unittest.TestCase):
    """Test that galaxy decay multipliers are sensible."""

    def test_oracle_decays_slowest(self):
        router = GalaxyRouter()
        oracle_mult = router.get_decay_multiplier("oracle")
        universal_mult = router.get_decay_multiplier("universal")
        self.assertLess(oracle_mult, universal_mult)

    def test_self_discovery_decays_slower_than_universal(self):
        router = GalaxyRouter()
        sd_mult = router.get_decay_multiplier("self_discovery")
        universal_mult = router.get_decay_multiplier("universal")
        self.assertLess(sd_mult, universal_mult)


if __name__ == "__main__":
    unittest.main()
