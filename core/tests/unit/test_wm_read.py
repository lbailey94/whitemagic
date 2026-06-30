# ruff: noqa: BLE001
"""Unit tests for the unified wm_read API."""

import unittest
from unittest.mock import MagicMock, patch

from whitemagic.tools.handlers.wm_read import (
    _detect_mode,
    _filter_private,
    _flag_enabled,
    _memory_to_dict,
    handle_wm_read,
    handle_wm_read_status,
)


class TestModeDetection(unittest.TestCase):
    """Auto-detection of read mode based on query characteristics."""

    def test_codebase_mode_when_path_provided(self):
        self.assertEqual(_detect_mode("rust", path="/repo"), "codebase")

    def test_id_mode_for_memory_id(self):
        self.assertEqual(_detect_mode("mem_abc123"), "id")

    def test_id_mode_not_triggered_for_long_string(self):
        self.assertNotEqual(_detect_mode("mem_" + "x" * 100), "id")

    def test_id_mode_not_triggered_with_spaces(self):
        self.assertEqual(_detect_mode("mem_abc def"), "hybrid")

    def test_constellation_mode_when_tags_no_query(self):
        self.assertEqual(_detect_mode("", tags=["rust", "memory"]), "constellation")

    def test_temporal_mode_when_time_window_no_query(self):
        self.assertEqual(_detect_mode("", time_window="7d"), "temporal")

    def test_spatial_mode_when_coords_provided(self):
        self.assertEqual(
            _detect_mode("test", coords=(0.1, 0.2, 0.3, 0.4, 0.5)), "spatial"
        )

    def test_hybrid_mode_default(self):
        self.assertEqual(_detect_mode("memory consolidation"), "hybrid")

    def test_strata_mode_when_path_and_strata_flag(self):
        self.assertEqual(_detect_mode("analysis", path="/repo", strata=True), "strata")


class TestPrivacyFilter(unittest.TestCase):
    """Private memory filtering logic."""

    def test_flag_enabled_bool_true(self):
        self.assertTrue(_flag_enabled(True))

    def test_flag_enabled_bool_false(self):
        self.assertFalse(_flag_enabled(False))

    def test_flag_enabled_int_nonzero(self):
        self.assertTrue(_flag_enabled(1))

    def test_flag_enabled_int_zero(self):
        self.assertFalse(_flag_enabled(0))

    def test_flag_enabled_string_returns_false(self):
        self.assertFalse(_flag_enabled("true"))

    def test_filter_private_removes_private(self):
        mem = MagicMock(is_private=True, model_exclude=False)
        result = _filter_private([mem], include_private=False)
        self.assertEqual(len(result), 0)

    def test_filter_private_keeps_non_private(self):
        mem = MagicMock(is_private=False, model_exclude=False)
        result = _filter_private([mem], include_private=False)
        self.assertEqual(len(result), 1)

    def test_filter_private_includes_all_when_flag_true(self):
        mem = MagicMock(is_private=True, model_exclude=True)
        result = _filter_private([mem], include_private=True)
        self.assertEqual(len(result), 1)

    def test_filter_private_removes_model_exclude(self):
        mem = MagicMock(is_private=False, model_exclude=True)
        result = _filter_private([mem], include_private=False)
        self.assertEqual(len(result), 0)


class TestMemoryToDict(unittest.TestCase):
    """Memory-to-dict serialization."""

    def test_basic_conversion(self):
        mem = MagicMock()
        mem.id = "mem_123"
        mem.title = "Test Memory"
        mem.content = "Some content"
        mem.memory_type = MagicMock()
        mem.memory_type.name = "EPISODIC"
        mem.importance = 0.8
        mem.neuro_score = 1.5
        mem.novelty_score = 0.9
        mem.tags = {"test", "unit"}
        mem.created_at = MagicMock()
        mem.created_at.isoformat.return_value = "2026-01-01T00:00:00"
        mem.galactic_distance = 0.3

        d = _memory_to_dict(mem)
        self.assertEqual(d["id"], "mem_123")
        self.assertEqual(d["title"], "Test Memory")
        self.assertEqual(d["memory_type"], "EPISODIC")
        self.assertEqual(d["importance"], 0.8)
        self.assertEqual(d["galactic_distance"], 0.3)


class TestHandleWmRead(unittest.TestCase):
    """Integration-level tests for handle_wm_read dispatch."""

    def test_unknown_mode_returns_error(self):
        result = handle_wm_read(query="test", mode="invalid_mode")
        self.assertEqual(result["status"], "error")
        self.assertIn("available_modes", result)

    def test_auto_mode_with_path_selects_codebase(self):
        """Auto mode with path should route to codebase."""
        with patch("whitemagic.tools.handlers.wm_read._read_codebase") as mock_cb:
            mock_cb.return_value = {
                "status": "success",
                "mode": "codebase",
                "count": 0,
                "results": [],
            }
            result = handle_wm_read(query="rust", mode="auto", path="/repo")
            self.assertEqual(result["mode"], "codebase")
            mock_cb.assert_called_once()

    def test_auto_mode_with_mem_id_selects_id(self):
        """Auto mode with mem_ prefix should route to id lookup."""
        with patch("whitemagic.tools.handlers.wm_read._read_by_id") as mock_id:
            mock_id.return_value = {
                "status": "success",
                "mode": "id",
                "count": 0,
                "results": [],
            }
            result = handle_wm_read(query="mem_abc123", mode="auto")
            self.assertEqual(result["mode"], "id")
            mock_id.assert_called_once()

    def test_auto_mode_default_selects_hybrid(self):
        """Auto mode with plain text query should route to hybrid."""
        with patch("whitemagic.tools.handlers.wm_read._read_hybrid") as mock_hybrid:
            mock_hybrid.return_value = {
                "status": "success",
                "mode": "hybrid",
                "count": 0,
                "results": [],
                "strategy": "test",
            }
            result = handle_wm_read(query="memory consolidation", mode="auto")
            self.assertEqual(result["mode"], "hybrid")
            mock_hybrid.assert_called_once()

    def test_explicit_mode_is_respected(self):
        """Explicit mode should bypass auto-detection."""
        with patch("whitemagic.tools.handlers.wm_read._read_lexical") as mock_lex:
            mock_lex.return_value = {
                "status": "success",
                "mode": "lexical",
                "count": 0,
                "results": [],
                "strategy": "FTS5",
            }
            result = handle_wm_read(query="test", mode="lexical")
            self.assertEqual(result["mode"], "lexical")
            mock_lex.assert_called_once()

    def test_exception_returns_error_envelope(self):
        """Exceptions should be caught and returned as error envelopes."""
        with patch(
            "whitemagic.tools.handlers.wm_read._read_hybrid",
            side_effect=RuntimeError("test error"),
        ):
            result = handle_wm_read(query="test", mode="hybrid")
            self.assertEqual(result["status"], "error")
            self.assertIn("test error", result["error"])


class TestHandleWmReadStatus(unittest.TestCase):
    """Status endpoint tests."""

    def test_status_returns_success(self):
        result = handle_wm_read_status()
        self.assertEqual(result["status"], "success")

    def test_status_lists_all_modes(self):
        result = handle_wm_read_status()
        expected_modes = [
            "auto",
            "hybrid",
            "graph_walk",
            "semantic",
            "lexical",
            "spatial",
            "constellation",
            "temporal",
            "codebase",
            "strata",
            "id",
        ]
        self.assertEqual(result["modes"], expected_modes)

    def test_status_includes_backends(self):
        result = handle_wm_read_status()
        self.assertIn("backends", result)
        # At least unified_memory should be listed
        self.assertIn("unified_memory", result["backends"])


if __name__ == "__main__":
    unittest.main()
