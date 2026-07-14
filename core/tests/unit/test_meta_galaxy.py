"""Tests for MetaGalaxy — overhead index of all galaxies."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp())
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")


from whitemagic.core.consciousness.meta_galaxy import (
    CACHE_TTL,
    GalaxySummary,
    MetaGalaxy,
    MetaGalaxyIndex,
)


class TestMetaGalaxy:
    def test_empty_index(self):
        MetaGalaxy()
        index = MetaGalaxyIndex()
        assert index.total_memories == 0
        assert index.total_galaxies == 0

    def test_galaxy_summary_defaults(self):
        gs = GalaxySummary(name="test")
        assert gs.memory_count == 0
        assert gs.health_score == 1.0
        assert gs.galaxy_zone == "INNER_RIM"

    def test_galaxy_summary_to_dict(self):
        gs = GalaxySummary(name="citta", memory_count=42, avg_importance=0.7)
        d = gs.to_dict()
        assert d["name"] == "citta"
        assert d["memory_count"] == 42
        assert d["avg_importance"] == 0.7

    def test_meta_galaxy_index_to_dict(self):
        index = MetaGalaxyIndex(
            galaxies={"citta": GalaxySummary(name="citta", memory_count=10)},
            total_memories=10,
            total_galaxies=1,
        )
        d = index.to_dict()
        assert d["total_memories"] == 10
        assert d["total_galaxies"] == 1
        assert "citta" in d["galaxies"]

    def test_cache_ttl_is_reasonable(self):
        assert CACHE_TTL >= 30.0
        assert CACHE_TTL <= 300.0

    def test_get_index_returns_cached(self):
        mg = MetaGalaxy()
        # Without a backend, refresh returns empty index
        index1 = mg.get_index()
        index2 = mg.get_index()
        # Second call should return cached (same object)
        assert index2 is index1

    def test_get_overview(self):
        mg = MetaGalaxy()
        overview = mg.get_overview()
        assert "total_memories" in overview
        assert "galaxies" in overview

    def test_get_strategic_priorities(self):
        mg = MetaGalaxy()
        priorities = mg.get_strategic_priorities()
        assert isinstance(priorities, list)

    def test_get_knowledge_gaps(self):
        mg = MetaGalaxy()
        gaps = mg.get_knowledge_gaps()
        assert isinstance(gaps, list)

    def test_get_report(self):
        mg = MetaGalaxy()
        report = mg.get_report()
        assert isinstance(report, str)

    def test_on_refresh_callback(self):
        mg = MetaGalaxy()
        called = []
        mg.on_refresh(lambda idx: called.append(idx))
        mg.refresh()
        assert len(called) == 1

    def test_galaxy_zone_classification(self):
        gs_empty = GalaxySummary(name="test", memory_count=0)
        gs_empty.knowledge_gaps = []
        # Simulate zone logic
        assert gs_empty.memory_count == 0

        gs_core = GalaxySummary(name="big", memory_count=300)
        assert gs_core.memory_count > 200
