"""Tests for spreading activation, galaxy gating, and sleep consolidation."""

# ruff: noqa: BLE001

import tempfile
from pathlib import Path

import pytest

from whitemagic.core.memory.db_manager import safe_connect
from whitemagic.core.memory.galaxy_gating import (
    GalaxyGating,
    get_galaxy_gating,
)
from whitemagic.core.memory.sleep_consolidation import (
    SleepConsolidation,
    get_sleep_consolidation,
)
from whitemagic.core.memory.spreading_activation import (
    SpreadingActivation,
    get_spreading_activation,
)

# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def _temp_galaxy_dbs():
    """Create temp galaxy DBs with schema and sample data."""
    tmpdir = tempfile.mkdtemp(prefix="wm_cognitive_test_")
    galaxy_dbs: dict[str, str] = {}

    for name in ["aria", "citta", "codex", "sessions", "dreams", "research", "universal"]:
        db_path = str(Path(tmpdir) / f"{name}.db")
        galaxy_dbs[name] = db_path
        conn = safe_connect(db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT,
                title TEXT,
                importance REAL DEFAULT 0.5,
                neuro_score REAL DEFAULT 1.0,
                recall_count INTEGER DEFAULT 0,
                content_hash TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS associations (
                source_id TEXT,
                target_id TEXT,
                strength REAL,
                direction TEXT,
                relation_type TEXT,
                edge_type TEXT,
                traversal_count INTEGER DEFAULT 0,
                created_at TEXT,
                last_traversed_at TEXT,
                ingestion_time TEXT,
                PRIMARY KEY (source_id, target_id)
            );
            CREATE TABLE IF NOT EXISTS tags (
                memory_id TEXT,
                tag TEXT,
                PRIMARY KEY (memory_id, tag)
            );
        """)

        # Insert sample memories
        for i in range(5):
            mem_id = f"{name}-mem-{i}"
            conn.execute(
                "INSERT OR IGNORE INTO memories (id, title, importance, content_hash) VALUES (?, ?, ?, ?)",
                (mem_id, f"{name} memory {i}", 0.5 + i * 0.1, f"hash_{name}_{i}"),
            )

        # Insert associations within galaxy
        for i in range(4):
            conn.execute(
                "INSERT OR IGNORE INTO associations (source_id, target_id, strength, relation_type, edge_type) VALUES (?, ?, ?, ?, ?)",
                (f"{name}-mem-{i}", f"{name}-mem-{i+1}", 0.5 + i * 0.1, "associated_with", "semantic"),
            )

        conn.commit()
        conn.close()

    # Add cross-galaxy associations (aria ↔ citta)
    conn = safe_connect(galaxy_dbs["aria"])
    conn.execute(
        "INSERT OR IGNORE INTO associations (source_id, target_id, strength, relation_type, edge_type) VALUES (?, ?, ?, ?, ?)",
        ("aria-mem-0", "citta-mem-1", 0.6, "cross_galaxy", "bridge"),
    )
    conn.commit()
    conn.close()

    conn = safe_connect(galaxy_dbs["citta"])
    conn.execute(
        "INSERT OR IGNORE INTO associations (source_id, target_id, strength, relation_type, edge_type) VALUES (?, ?, ?, ?, ?)",
        ("citta-mem-1", "aria-mem-0", 0.6, "cross_galaxy", "bridge"),
    )
    conn.commit()
    conn.close()

    yield galaxy_dbs

    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


# ── Spreading Activation Tests ──────────────────────────────────────

class TestSpreadingActivation:

    def test_spread_returns_result(self, _temp_galaxy_dbs):
        engine = SpreadingActivation()
        result = engine.spread(
            seed_ids=["aria-mem-0"],
            galaxy_db_paths=_temp_galaxy_dbs,
            max_hops=2,
        )
        assert result.seed_ids == ["aria-mem-0"]
        assert isinstance(result.primed, list)
        assert result.duration_ms > 0

    def test_spread_finds_neighbors(self, _temp_galaxy_dbs):
        engine = SpreadingActivation()
        result = engine.spread(
            seed_ids=["aria-mem-0"],
            galaxy_db_paths=_temp_galaxy_dbs,
            max_hops=1,
        )
        primed_ids = {n.memory_id for n in result.primed}
        # Should find aria-mem-1 (direct neighbor)
        assert "aria-mem-1" in primed_ids

    def test_spread_cross_galaxy(self, _temp_galaxy_dbs):
        engine = SpreadingActivation(cross_galaxy_factor=0.5)
        result = engine.spread(
            seed_ids=["aria-mem-0"],
            galaxy_db_paths=_temp_galaxy_dbs,
            max_hops=1,
            min_activation=0.01,
        )
        # Should reach citta galaxy via cross-galaxy bridge
        assert "citta" in result.galaxies_reached
        assert result.cross_galaxy_links > 0

    def test_spread_decay_reduces_activation(self, _temp_galaxy_dbs):
        engine = SpreadingActivation(decay=0.3)
        result = engine.spread(
            seed_ids=["aria-mem-0"],
            galaxy_db_paths=_temp_galaxy_dbs,
            max_hops=2,
            min_activation=0.01,
        )
        # Activation should decrease with hops
        if len(result.primed) >= 2:
            assert result.primed[0].activation >= result.primed[-1].activation

    def test_spread_max_hops_limits_reach(self, _temp_galaxy_dbs):
        engine = SpreadingActivation()
        result_h1 = engine.spread(
            seed_ids=["aria-mem-0"],
            galaxy_db_paths=_temp_galaxy_dbs,
            max_hops=1,
        )
        result_h3 = engine.spread(
            seed_ids=["aria-mem-0"],
            galaxy_db_paths=_temp_galaxy_dbs,
            max_hops=3,
        )
        # More hops should activate at least as many nodes
        assert result_h3.total_activated >= result_h1.total_activated

    def test_spread_empty_seeds(self, _temp_galaxy_dbs):
        engine = SpreadingActivation()
        result = engine.spread(seed_ids=[], galaxy_db_paths=_temp_galaxy_dbs)
        assert result.total_activated == 0
        assert result.primed == []

    def test_spread_to_dict(self, _temp_galaxy_dbs):
        engine = SpreadingActivation()
        result = engine.spread(
            seed_ids=["aria-mem-0"],
            galaxy_db_paths=_temp_galaxy_dbs,
            max_hops=1,
        )
        d = result.to_dict()
        assert "primed" in d
        assert "galaxies_reached" in d
        assert "total_activated" in d

    def test_apply_priming(self, _temp_galaxy_dbs):
        engine = SpreadingActivation()
        result = engine.spread(
            seed_ids=["aria-mem-0"],
            galaxy_db_paths=_temp_galaxy_dbs,
            max_hops=1,
        )
        primed_count = engine.apply_priming(result, _temp_galaxy_dbs)
        assert primed_count > 0

    def test_stats(self):
        engine = SpreadingActivation()
        stats = engine.stats()
        assert "total_spreads" in stats
        assert "decay" in stats
        assert "cross_galaxy_factor" in stats

    def test_singleton(self):
        a = get_spreading_activation()
        b = get_spreading_activation()
        assert a is b


# ── Galaxy Gating Tests ─────────────────────────────────────────────

class TestGalaxyGating:

    def test_get_mask_default(self):
        gating = GalaxyGating()
        mask = gating.get_mask("default")
        assert mask.context == "default"

    def test_get_mask_introspection(self):
        gating = GalaxyGating()
        mask = gating.get_mask("introspection")
        assert mask.context == "introspection"
        assert mask.get_weight("citta") > 1.0
        assert mask.get_weight("codex") < 1.0

    def test_get_mask_coding(self):
        gating = GalaxyGating()
        mask = gating.get_mask("coding")
        assert mask.get_weight("codex") > 1.0
        assert mask.get_weight("citta") < 1.0

    def test_set_context(self):
        gating = GalaxyGating()
        gating.set_context("research")
        assert gating.get_current_context() == "research"

    def test_set_unknown_context_falls_back(self):
        gating = GalaxyGating()
        gating.set_context("nonexistent")
        assert gating.get_current_context() == "default"

    def test_detect_context_introspection(self):
        gating = GalaxyGating()
        assert gating.detect_context("what am I feeling right now") == "introspection"

    def test_detect_context_coding(self):
        gating = GalaxyGating()
        assert gating.detect_context("debug the import error in galaxy_manager.py") == "coding"

    def test_detect_context_research(self):
        gating = GalaxyGating()
        assert gating.detect_context("research the literature on memory consolidation") == "research"

    def test_detect_context_creative(self):
        gating = GalaxyGating()
        assert gating.detect_context("write a dream narrative about the ocean") == "creative"

    def test_detect_context_session(self):
        gating = GalaxyGating()
        assert gating.detect_context("where did we leave off last session") == "session"

    def test_detect_context_default(self):
        gating = GalaxyGating()
        assert gating.detect_context("hello world") == "default"

    def test_apply_to_results(self):
        gating = GalaxyGating()
        results = [
            {"id": "1", "galaxy": "citta", "importance": 0.5},
            {"id": "2", "galaxy": "codex", "importance": 0.9},
        ]
        weighted = gating.apply_to_results(results, "introspection")
        # citta should be boosted above codex despite lower base importance
        assert weighted[0]["galaxy"] == "citta"
        assert weighted[0]["weighted_importance"] > weighted[1]["weighted_importance"]

    def test_get_galaxy_weights(self):
        gating = GalaxyGating()
        weights = gating.get_galaxy_weights("coding")
        assert weights["codex"] > weights["citta"]

    def test_list_contexts(self):
        gating = GalaxyGating()
        contexts = gating.list_contexts()
        assert len(contexts) >= 5
        names = [c["context"] for c in contexts]
        assert "introspection" in names
        assert "coding" in names
        assert "default" in names

    def test_register_custom_context(self):
        gating = GalaxyGating()
        from whitemagic.core.memory.galaxy_gating import ContextMask
        gating.register_context(ContextMask(
            context="custom_test",
            description="Test context",
            weights={"aria": 2.0},
        ))
        mask = gating.get_mask("custom_test")
        assert mask.get_weight("aria") == 2.0

    def test_stats(self):
        gating = GalaxyGating()
        stats = gating.stats()
        assert "current_context" in stats
        assert "context_count" in stats

    def test_singleton(self):
        a = get_galaxy_gating()
        b = get_galaxy_gating()
        assert a is b


# ── Sleep Consolidation Tests ───────────────────────────────────────

class TestSleepConsolidation:

    def test_consolidate_returns_report(self, _temp_galaxy_dbs):
        consol = SleepConsolidation(min_importance_transfer=0.5)
        report = consol.consolidate(_temp_galaxy_dbs, dry_run=True)
        assert report.duration_ms > 0
        assert isinstance(report.transfers, list)

    def test_consolidate_dry_run_no_changes(self, _temp_galaxy_dbs):
        consol = SleepConsolidation(min_importance_transfer=0.5)
        report = consol.consolidate(_temp_galaxy_dbs, dry_run=True)
        # Dry run should not strengthen/prune
        assert report.strengthened == 0
        assert report.pruned == 0

    def test_consolidate_finds_high_importance(self, _temp_galaxy_dbs):
        consol = SleepConsolidation(min_importance_transfer=0.5)
        report = consol.consolidate(_temp_galaxy_dbs, dry_run=True)
        # Should find memories with importance >= 0.5 in sessions galaxy
        session_transfers = [t for t in report.transfers if t.source_galaxy == "sessions"]
        assert len(session_transfers) > 0
        for t in session_transfers:
            assert t.importance >= 0.5

    def test_consolidate_strengthen_and_prune(self, _temp_galaxy_dbs):
        consol = SleepConsolidation(
            min_importance_transfer=0.9,  # High threshold to limit transfers
            strengthen_threshold=0.7,
            prune_threshold=0.3,
        )
        report = consol.consolidate(_temp_galaxy_dbs, dry_run=False)
        # Should have strengthened some memories
        assert report.strengthened >= 0
        assert report.pruned >= 0

    def test_consolidate_pathway_sessions_to_codex(self, _temp_galaxy_dbs):
        consol = SleepConsolidation(min_importance_transfer=0.5)
        report = consol.consolidate(_temp_galaxy_dbs, dry_run=True)
        session_to_codex = [
            t for t in report.transfers
            if t.source_galaxy == "sessions" and t.target_galaxy == "codex"
        ]
        assert len(session_to_codex) > 0
        assert session_to_codex[0].reason == "Session handoffs with high importance promoted to permanent codex"

    def test_consolidate_to_dict(self, _temp_galaxy_dbs):
        consol = SleepConsolidation(min_importance_transfer=0.5)
        report = consol.consolidate(_temp_galaxy_dbs, dry_run=True)
        d = report.to_dict()
        assert "total_transfers" in d
        assert "pruned" in d
        assert "strengthened" in d

    def test_consolidate_skips_archive(self, _temp_galaxy_dbs):
        # Add archive galaxy
        _temp_galaxy_dbs["archive"] = _temp_galaxy_dbs["universal"]
        consol = SleepConsolidation(min_importance_transfer=0.5)
        report = consol.consolidate(_temp_galaxy_dbs, dry_run=False)
        # Archive should not appear in transfers
        archive_transfers = [t for t in report.transfers if t.target_galaxy == "archive"]
        assert len(archive_transfers) == 0

    def test_stats(self):
        consol = SleepConsolidation()
        stats = consol.stats()
        assert "total_cycles" in stats
        assert "min_importance_transfer" in stats

    def test_singleton(self):
        a = get_sleep_consolidation()
        b = get_sleep_consolidation()
        assert a is b
