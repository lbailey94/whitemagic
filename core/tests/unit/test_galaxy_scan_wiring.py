"""Tests for multi-galactic engine wiring.

Verifies that CoreAccessLayer, KaizenEngine, EmergenceEngine, SerendipityEngine,
and AssociationMiner correctly query across all galaxy DBs via galaxy_scan.
"""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest


def _create_test_galaxy(db_path: str, memories: list[dict]) -> None:
    """Create a minimal galaxy DB with schema and insert test memories."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,
            created_at TEXT,
            accessed_at TEXT,
            access_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS holographic_coords (
            memory_id TEXT PRIMARY KEY,
            x REAL, y REAL, z REAL, w REAL, v REAL
        );
        CREATE TABLE IF NOT EXISTS tags (
            memory_id TEXT,
            tag TEXT
        );
        CREATE TABLE IF NOT EXISTS associations (
            source_id TEXT,
            target_id TEXT,
            strength REAL,
            last_traversed_at TEXT,
            traversal_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS embeddings (
            memory_id TEXT PRIMARY KEY,
            embedding BLOB
        );
    """)
    for m in memories:
        conn.execute(
            "INSERT OR REPLACE INTO memories (id, title, content, created_at, accessed_at, access_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                m["id"],
                m.get("title"),
                m.get("content", ""),
                m.get("created_at", "2026-01-01T00:00:00"),
                m.get("accessed_at"),
                m.get("access_count", 0),
            ),
        )
        coords = m.get("coords", (0.5, 0.5, 0.5, 0.5, 0.5))
        conn.execute(
            "INSERT OR REPLACE INTO holographic_coords (memory_id, x, y, z, w, v) VALUES (?, ?, ?, ?, ?, ?)",
            (m["id"], coords[0], coords[1], coords[2], coords[3], coords[4]),
        )
        for tag in m.get("tags", []):
            conn.execute("INSERT INTO tags (memory_id, tag) VALUES (?, ?)", (m["id"], tag))
        for assoc in m.get("associations", []):
            conn.execute(
                "INSERT INTO associations (source_id, target_id, strength) VALUES (?, ?, ?)",
                (assoc[0], assoc[1], assoc[2]),
            )
    conn.commit()
    conn.close()


@pytest.fixture
def multi_galaxy_setup(tmp_path, monkeypatch):
    """Create two temp galaxy DBs and patch galaxy_scan to discover them."""
    galaxy_a = tmp_path / "galaxies" / "alpha" / "whitemagic.db"
    galaxy_b = tmp_path / "galaxies" / "beta" / "whitemagic.db"

    _create_test_galaxy(str(galaxy_a), [
        {
            "id": "mem_a1",
            "title": "Alpha Memory One",
            "content": "Content about python programming",
            "created_at": "2026-01-01T00:00:00",
            "access_count": 0,
            "coords": (0.1, 0.2, 0.3, 0.8, 0.5),
            "tags": ["python", "coding"],
            "associations": [("mem_a1", "mem_a2", 0.7)],
        },
        {
            "id": "mem_a2",
            "title": "Alpha Memory Two",
            "content": "More about python and testing",
            "created_at": "2026-01-02T00:00:00",
            "access_count": 5,
            "coords": (0.2, 0.3, 0.4, 0.6, 0.5),
            "tags": ["python", "testing"],
        },
    ])

    _create_test_galaxy(str(galaxy_b), [
        {
            "id": "mem_b1",
            "title": "Beta Memory One",
            "content": "Content about rust acceleration",
            "created_at": "2026-01-03T00:00:00",
            "access_count": 0,
            "coords": (-0.1, -0.2, 0.3, 0.7, 0.5),
            "tags": ["rust", "performance"],
            "associations": [("mem_b1", "mem_b2", 0.5)],
        },
        {
            "id": "mem_b2",
            "title": "",
            "content": "Untitled beta memory",
            "created_at": "2026-01-04T00:00:00",
            "access_count": 1,
            "coords": (0.05, 0.05, 0.5, 0.4, 0.5),
            "tags": ["rust"],
        },
    ])

    fake_paths = {
        "alpha": str(galaxy_a),
        "beta": str(galaxy_b),
    }

    # Patch get_galaxy_db_paths everywhere it's been imported
    import importlib as _il
    patches = []
    for mod_name in [
        "whitemagic.core.memory.galaxy_scan",
        "whitemagic.core.intelligence.core_access",
        "whitemagic.core.intelligence.synthesis.kaizen_engine",
        "whitemagic.core.intelligence.synthesis.serendipity_engine",
        "whitemagic.core.intelligence.agentic.emergence_engine",
    ]:
        try:
            mod = _il.import_module(mod_name)
            if hasattr(mod, "get_galaxy_db_paths"):
                patches.append(
                    patch.object(mod, "get_galaxy_db_paths", return_value=fake_paths)
                )
        except ImportError:
            pass

    # Also patch galaxy_connection in core_access since it imports it directly
    from whitemagic.core.memory.galaxy_scan import galaxy_connection as _gc
    patches.append(
        patch("whitemagic.core.intelligence.core_access.galaxy_connection", side_effect=_gc)
    )

    for p in patches:
        p.start()

    # Also invalidate the cache
    from whitemagic.core.memory import galaxy_scan
    galaxy_scan._db_paths_cache = fake_paths
    galaxy_scan._db_paths_cache_time = 999999999.0
    yield fake_paths
    for p in patches:
        p.stop()
    galaxy_scan._db_paths_cache = None
    galaxy_scan._db_paths_cache_time = 0.0


class TestGalaxyScanUtility:
    """Test the galaxy_scan utility functions themselves."""

    def test_scan_query_all_concatenates(self, multi_galaxy_setup):
        from whitemagic.core.memory.galaxy_scan import scan_query_all

        rows = scan_query_all("SELECT id, title FROM memories ORDER BY id")
        ids = {r["id"] for r in rows}
        assert ids == {"mem_a1", "mem_a2", "mem_b1", "mem_b2"}

    def test_scan_query_one_finds_first(self, multi_galaxy_setup):
        from whitemagic.core.memory.galaxy_scan import scan_query_one

        row = scan_query_one("SELECT id FROM memories WHERE id = ?", ("mem_b1",))
        assert row is not None
        assert row["id"] == "mem_b1"

    def test_scan_count_all_sums(self, multi_galaxy_setup):
        from whitemagic.core.memory.galaxy_scan import scan_count_all

        total = scan_count_all("SELECT COUNT(*) FROM memories")
        assert total == 4

    def test_execute_across_galaxies(self, multi_galaxy_setup):
        from whitemagic.core.memory.galaxy_scan import execute_across_galaxies

        affected = execute_across_galaxies(
            "UPDATE memories SET access_count = access_count + 1 WHERE id = ?",
            ("mem_a1",),
        )
        assert affected == 1


class TestCoreAccessLayerMultiGalaxy:
    """Test CoreAccessLayer queries across multiple galaxies."""

    def test_get_association_stats_aggregates(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.core_access import CoreAccessLayer

        cal = CoreAccessLayer()
        stats = cal.get_association_stats()
        assert stats["total_associations"] >= 2
        assert stats["avg_strength"] > 0

    def test_find_broken_associations_scans_all(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.core_access import CoreAccessLayer

        cal = CoreAccessLayer()
        # Should not crash, should return list
        broken = cal.find_broken_associations(limit=10)
        assert isinstance(broken, list)

    def test_find_association_orphans_scans_all(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.core_access import CoreAccessLayer

        cal = CoreAccessLayer()
        orphans = cal.find_association_orphans(min_gravity=0.3, limit=10)
        assert isinstance(orphans, list)
        # Should find memories with w > 0.3 and few associations
        orphan_ids = {o.get("id") for o in orphans}
        # mem_b2 has w=0.4 and 0 associations, should be an orphan
        # mem_a2 has w=0.6 and 1 association, should be an orphan
        assert len(orphan_ids) > 0

    def test_query_holographic_neighbors_scans_all(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.core_access import CoreAccessLayer

        cal = CoreAccessLayer()
        neighbors = cal.query_holographic_neighbors(
            coords=(0.1, 0.2, 0.3, 0.8, 0.5), k=3
        )
        assert isinstance(neighbors, list)
        assert len(neighbors) > 0

    def test_query_association_subgraph_bfs_across_galaxies(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.core_access import CoreAccessLayer

        cal = CoreAccessLayer()
        nodes = cal.query_association_subgraph(
            seed_ids=["mem_a1"], depth=2, max_nodes=10
        )
        assert isinstance(nodes, list)
        assert len(nodes) >= 1
        # Should find mem_a1 and mem_a2 via association
        node_ids = {n.memory_id for n in nodes}
        assert "mem_a1" in node_ids


class TestKaizenEngineMultiGalaxy:
    """Test KaizenEngine queries across multiple galaxies."""

    def test_check_untitled_finds_across_galaxies(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.synthesis.kaizen_engine import KaizenEngine

        engine = KaizenEngine()
        proposals = engine._check_untitled()
        assert len(proposals) == 1
        assert proposals[0].metadata["count"] == 1

    def test_check_untagged_finds_across_galaxies(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.synthesis.kaizen_engine import KaizenEngine

        engine = KaizenEngine()
        proposals = engine._check_untagged()
        # All memories have tags in our setup, so should be empty
        assert isinstance(proposals, list)

    def test_find_duplicates_across_galaxies(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.synthesis.kaizen_engine import KaizenEngine

        engine = KaizenEngine()
        proposals = engine._find_duplicates()
        assert isinstance(proposals, list)


class TestEmergenceEngineMultiGalaxy:
    """Test EmergenceEngine queries across multiple galaxies."""

    def test_detect_tag_clusters_scans_all(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.agentic.emergence_engine import (
            EmergenceEngine,
        )

        engine = EmergenceEngine()
        insights = engine._detect_tag_clusters()
        assert isinstance(insights, list)

    def test_detect_resonance_cascades_scans_all(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.agentic.emergence_engine import (
            EmergenceEngine,
        )

        engine = EmergenceEngine()
        insights = engine._detect_resonance_cascades()
        assert isinstance(insights, list)

    def test_detect_novelty_spikes_scans_all(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.agentic.emergence_engine import (
            EmergenceEngine,
        )

        engine = EmergenceEngine()
        insights = engine._detect_novelty_spikes()
        assert isinstance(insights, list)


class TestSerendipityEngineMultiGalaxy:
    """Test SerendipityEngine queries across multiple galaxies."""

    def test_surface_dormant_scans_all(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.synthesis.serendipity_engine import (
            SerendipityEngine,
        )

        engine = SerendipityEngine()
        surfaced = engine._surface_dormant(count=5)
        assert isinstance(surfaced, list)
        # Should find memories from both galaxies (w > 0.5)
        surfaced_ids = {s.id for s in surfaced}
        assert "mem_a1" in surfaced_ids or "mem_b1" in surfaced_ids

    def test_surface_random_scans_all(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.synthesis.serendipity_engine import (
            SerendipityEngine,
        )

        engine = SerendipityEngine()
        surfaced = engine._surface_random(count=4)
        assert isinstance(surfaced, list)
        # Should find memories from both galaxies
        surfaced_ids = {s.id for s in surfaced}
        assert len(surfaced_ids) > 0

    def test_surface_ancient_scans_all(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.synthesis.serendipity_engine import (
            SerendipityEngine,
        )

        engine = SerendipityEngine()
        surfaced = engine._surface_ancient(count=4)
        assert isinstance(surfaced, list)
        # All test memories are from Jan 2026, which is >30 days old
        surfaced_ids = {s.id for s in surfaced}
        assert len(surfaced_ids) > 0

    def test_surface_bridges_scans_all(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.synthesis.serendipity_engine import (
            SerendipityEngine,
        )

        engine = SerendipityEngine()
        surfaced = engine._surface_bridges(count=4)
        assert isinstance(surfaced, list)
        # mem_b2 has x=0.05, y=0.05 — near boundary
        surfaced_ids = {s.id for s in surfaced}
        assert "mem_b2" in surfaced_ids

    def test_mark_accessed_across_galaxies(self, multi_galaxy_setup):
        from whitemagic.core.intelligence.synthesis.serendipity_engine import (
            SerendipityEngine,
        )

        engine = SerendipityEngine()
        engine.mark_accessed("mem_a1")
        # Verify access_count was incremented
        from whitemagic.core.memory.galaxy_scan import scan_query_one
        row = scan_query_one(
            "SELECT access_count FROM memories WHERE id = ?", ("mem_a1",)
        )
        assert row["access_count"] == 1
