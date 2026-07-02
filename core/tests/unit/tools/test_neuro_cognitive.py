"""Unit tests for neuro-cognitive MCP tool handlers."""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Set WM_STATE_ROOT to temp dir for test isolation
_tmp = tempfile.mkdtemp(prefix="wm_test_neuro_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


@pytest.fixture
def _mock_galaxy_dbs():
    """Create temporary galaxy DBs with memories and associations."""
    tmpdir = Path(tempfile.mkdtemp(prefix="wm_galaxy_"))
    db_paths = {}

    for galaxy in ["universal", "codex", "sessions", "citta", "dreams", "research", "aria"]:
        db_path = tmpdir / f"{galaxy}.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                importance REAL DEFAULT 0.5,
                neuro_score REAL DEFAULT 1.0,
                recall_count INTEGER DEFAULT 0,
                content_hash TEXT,
                created_at TEXT,
                updated_at TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS associations (
                source_id TEXT,
                target_id TEXT,
                strength REAL,
                direction TEXT,
                relation_type TEXT,
                edge_type TEXT,
                created_at TEXT,
                ingestion_time TEXT
            )"""
        )
        # Insert a test memory
        conn.execute(
            "INSERT OR IGNORE INTO memories (id, title, content, importance) VALUES (?, ?, ?, ?)",
            (f"mem-{galaxy}-1", f"Test {galaxy}", f"Content {galaxy}", 0.8),
        )
        conn.commit()
        conn.close()
        db_paths[galaxy] = str(db_path)

    # Add cross-galaxy association
    conn = sqlite3.connect(db_paths["universal"])
    conn.execute(
        "INSERT INTO associations (source_id, target_id, strength, direction) VALUES (?, ?, ?, ?)",
        ("mem-universal-1", "mem-codex-1", 0.8, "forward"),
    )
    conn.execute(
        "INSERT INTO associations (source_id, target_id, strength, direction) VALUES (?, ?, ?, ?)",
        ("mem-universal-1", "mem-sessions-1", 0.6, "forward"),
    )
    conn.commit()
    conn.close()

    return db_paths


# ═══════════════════════════════════════════════════════════════════════
# Spreading Activation Handlers
# ═══════════════════════════════════════════════════════════════════════


class TestActivationSpread:
    def test_missing_seed_ids(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_activation_spread

        result = handle_activation_spread()
        assert result["status"] == "error"
        assert "seed_ids" in result["error"]

    def test_empty_seed_ids(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_activation_spread

        result = handle_activation_spread(seed_ids=[])
        assert result["status"] == "error"

    def test_string_seed_ids_split(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_activation_spread

        with patch(
            "whitemagic.tools.handlers.neuro_cognitive._resolve_galaxy_db_paths",
            return_value={},
        ):
            result = handle_activation_spread(seed_ids="mem-1, mem-2")
            assert result["status"] == "success"
            assert "seed_ids" in result
            assert "total_activated" in result

    def test_spread_with_mock_dbs(self, _mock_galaxy_dbs):
        from whitemagic.tools.handlers.neuro_cognitive import handle_activation_spread

        with patch(
            "whitemagic.tools.handlers.neuro_cognitive._resolve_galaxy_db_paths",
            return_value=_mock_galaxy_dbs,
        ):
            result = handle_activation_spread(
                seed_ids=["mem-universal-1"],
                max_hops=2,
                decay=0.7,
            )
            assert result["status"] == "success"
            assert result["seed_ids"] == ["mem-universal-1"]
            assert "total_activated" in result
            assert "primed" in result
            assert "galaxies_reached" in result

    def test_spread_with_priming(self, _mock_galaxy_dbs):
        from whitemagic.tools.handlers.neuro_cognitive import handle_activation_spread

        with patch(
            "whitemagic.tools.handlers.neuro_cognitive._resolve_galaxy_db_paths",
            return_value=_mock_galaxy_dbs,
        ):
            result = handle_activation_spread(
                seed_ids=["mem-universal-1"],
                apply_priming=True,
            )
            assert result["status"] == "success"
            assert result["primed_applied"] is not None


class TestActivationStats:
    def test_stats(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_activation_stats

        result = handle_activation_stats()
        assert result["status"] == "success"
        assert "total_spreads" in result
        assert "decay" in result


# ═══════════════════════════════════════════════════════════════════════
# Galaxy Gating Handlers
# ═══════════════════════════════════════════════════════════════════════


class TestGatingSetContext:
    def test_missing_context(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_set_context

        result = handle_gating_set_context()
        assert result["status"] == "error"

    def test_set_valid_context(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_set_context

        result = handle_gating_set_context(context="coding")
        assert result["status"] == "success"
        assert result["context"] == "coding"

    def test_set_unknown_context_falls_back(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_set_context

        result = handle_gating_set_context(context="nonexistent")
        assert result["status"] == "success"
        assert result["context"] == "default"


class TestGatingDetect:
    def test_missing_query(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_detect

        result = handle_gating_detect()
        assert result["status"] == "error"

    def test_detect_coding(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_detect

        result = handle_gating_detect(query="debug this python function")
        assert result["status"] == "success"
        assert result["detected_context"] == "coding"
        assert "weights" in result

    def test_detect_research(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_detect

        result = handle_gating_detect(query="research the literature on neural networks")
        assert result["status"] == "success"
        assert result["detected_context"] == "research"

    def test_detect_default(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_detect

        result = handle_gating_detect(query="hello world")
        assert result["status"] == "success"
        assert result["detected_context"] == "default"


class TestGatingMask:
    def test_get_mask_default(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_mask

        result = handle_gating_mask()
        assert result["status"] == "success"
        assert "context" in result
        assert "weights" in result

    def test_get_mask_specific(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_mask

        result = handle_gating_mask(context="introspection")
        assert result["status"] == "success"
        assert result["context"] == "introspection"
        assert "citta" in result["weights"]


class TestGatingList:
    def test_list(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_list

        result = handle_gating_list()
        assert result["status"] == "success"
        assert "current_context" in result
        assert "contexts" in result
        assert isinstance(result["contexts"], list)
        assert len(result["contexts"]) >= 5


class TestGatingStats:
    def test_stats(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_gating_stats

        result = handle_gating_stats()
        assert result["status"] == "success"
        assert "current_context" in result
        assert "context_count" in result


# ═══════════════════════════════════════════════════════════════════════
# Sleep Consolidation Handlers
# ═══════════════════════════════════════════════════════════════════════


class TestConsolidationRun:
    def test_no_galaxies(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_consolidation_run

        with patch(
            "whitemagic.tools.handlers.neuro_cognitive._resolve_galaxy_db_paths",
            return_value={},
        ):
            result = handle_consolidation_run()
            assert result["status"] == "error"

    def test_dry_run(self, _mock_galaxy_dbs):
        from whitemagic.tools.handlers.neuro_cognitive import handle_consolidation_run

        with patch(
            "whitemagic.tools.handlers.neuro_cognitive._resolve_galaxy_db_paths",
            return_value=_mock_galaxy_dbs,
        ):
            result = handle_consolidation_run(dry_run=True)
            assert result["status"] == "success"
            assert "total_transfers" in result
            assert "transfers" in result
            assert "pruned" in result
            assert "strengthened" in result

    def test_real_run(self, _mock_galaxy_dbs):
        from whitemagic.tools.handlers.neuro_cognitive import handle_consolidation_run

        with patch(
            "whitemagic.tools.handlers.neuro_cognitive._resolve_galaxy_db_paths",
            return_value=_mock_galaxy_dbs,
        ):
            result = handle_consolidation_run(dry_run=False)
            assert result["status"] == "success"
            assert "duration_ms" in result


class TestConsolidationStats:
    def test_stats(self):
        from whitemagic.tools.handlers.neuro_cognitive import (
            handle_consolidation_stats,
        )

        result = handle_consolidation_stats()
        assert result["status"] == "success"
        assert "total_cycles" in result
        assert "min_importance_transfer" in result
