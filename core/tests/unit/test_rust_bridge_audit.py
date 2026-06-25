# ruff: noqa: BLE001
"""Regression tests for Rust bridge type mismatch fixes (3A)."""
import unittest
from unittest.mock import patch, MagicMock


class TestPolyglotAcceleratorRustBridge(unittest.TestCase):
    """Test that polyglot_accelerator correctly handles Rust FFI types."""

    def test_extract_patterns_returns_list_of_dicts(self):
        """Test that extract_patterns converts Rust 7-tuple to list[dict]."""
        from whitemagic.core.acceleration.polyglot_accelerator import PolyglotAccelerator

        accel = PolyglotAccelerator()
        # Force Rust path
        accel._rust_available = True

        # Mock whitemagic_rs to return the 7-tuple Rust actually returns
        mock_rs = MagicMock()
        mock_rs.extract_patterns_from_content.return_value = (
            10,  # total
            3,  # found
            ["Use caching for repeated queries"],  # solutions
            ["Don't block the event loop"],  # anti_patterns
            ["Cache invalidation by mtime"],  # heuristics
            ["Use SIMD for batch cosine"],  # optimizations
            0.05,  # duration
        )

        with patch.dict("sys.modules", {"whitemagic_rs": mock_rs}):
            result = accel.extract_patterns("some content about caching")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)  # 1 solution + 1 anti + 1 heuristic + 1 opt
        types = {r["type"] for r in result}
        self.assertEqual(types, {"solution", "anti_pattern", "heuristic", "optimization"})
        self.assertTrue(all("description" in r for r in result))

    def test_extract_patterns_accepts_list_input(self):
        """Test that extract_patterns accepts list[str] input."""
        from whitemagic.core.acceleration.polyglot_accelerator import PolyglotAccelerator

        accel = PolyglotAccelerator()
        accel._rust_available = True

        mock_rs = MagicMock()
        mock_rs.extract_patterns_from_content.return_value = (
            3, 2, ["s1"], [], [], [], 0.01,
        )

        with patch.dict("sys.modules", {"whitemagic_rs": mock_rs}):
            result = accel.extract_patterns(["content1", "content2", "content3"])

        # Verify Rust was called with the list directly
        call_args = mock_rs.extract_patterns_from_content.call_args
        self.assertEqual(call_args[0][0], ["content1", "content2", "content3"])
        self.assertIsInstance(result, list)

    def test_search_memories_parses_json_string(self):
        """Test that search_memories parses JSON string from Rust search_query."""
        import json as _json

        from whitemagic.core.acceleration.polyglot_accelerator import PolyglotAccelerator

        accel = PolyglotAccelerator()
        accel._rust_available = True

        mock_rs = MagicMock()
        mock_rs.search_build_index.return_value = (10, 100)  # (doc_count, vocab_size)
        # Rust returns JSON string
        mock_rs.search_query.return_value = _json.dumps([
            {"id": "mem1", "score": 0.95},
            {"id": "mem2", "score": 0.80},
        ])

        with patch.dict("sys.modules", {"whitemagic_rs": mock_rs}):
            result = accel.search_memories(
                "test query",
                [("mem1", "content1"), ("mem2", "content2")],
            )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ("mem1", 0.95))
        self.assertEqual(result[1], ("mem2", 0.80))

        # Verify search_build_index was called with JSON string, not list
        build_call = mock_rs.search_build_index.call_args
        self.assertIsInstance(build_call[0][0], str)  # Should be JSON string

        # Verify search_query was called with 2 args (query, limit), not 3
        query_call = mock_rs.search_query.call_args
        self.assertEqual(len(query_call[0]), 2)  # (query, limit)


class TestRustSearchTypeAnnotations(unittest.TestCase):
    """Test that rust_search.py has correct type annotations."""

    def test_search_build_index_return_type(self):
        """Test that search_build_index is annotated as tuple[int, int] | None."""
        from whitemagic.optimization.rust_search import search_build_index
        # Check the return annotation
        import typing
        hints = typing.get_type_hints(search_build_index)
        # The return type should not be str
        return_hint = str(hints.get("return", ""))
        self.assertIn("tuple", return_hint)
        self.assertNotIn("str", return_hint.replace("tuple", ""))


class TestRustAcceleratorsTypeAnnotations(unittest.TestCase):
    """Test that rust_accelerators.py has correct type annotations."""

    def test_search_build_index_return_type(self):
        """Test that search_build_index is annotated as tuple[int, int] | None."""
        from whitemagic.optimization.rust_accelerators import search_build_index
        import typing
        hints = typing.get_type_hints(search_build_index)
        return_hint = str(hints.get("return", ""))
        self.assertIn("tuple", return_hint)
        self.assertNotIn("str", return_hint.replace("tuple", ""))


if __name__ == "__main__":
    unittest.main()
