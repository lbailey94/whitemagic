"""Tests for PRAT vectorized dispatcher."""

from whitemagic.tools.vectorized import (
    _REVERSE_TOOL,
    _TOOL_CODEBOOK,
    VectorizedDispatcher,
    decode_call,
    encode_call,
    is_vectorized_mode,
)


class TestVectorizedDispatcher:
    def test_encode_known_tool_no_args(self):
        vd = VectorizedDispatcher()
        assert vd.encode("create_memory") == "M+"
        assert vd.encode("gnosis") == "Gg"
        assert vd.encode("health_report") == "Rh"

    def test_encode_unknown_tool_passthrough(self):
        vd = VectorizedDispatcher()
        assert vd.encode("unknown_tool") == "unknown_tool"
        assert vd.encode("unknown_tool", {"x": 1}) == "unknown_tool[x:1]"

    def test_encode_with_args(self):
        vd = VectorizedDispatcher()
        assert vd.encode("search_memories", {"limit": 10}) == "M?[n:10]"
        assert (
            vd.encode("search_memories", {"limit": 10, "query": "test"})
            == "M?[n:10,q:test]"
        )

    def test_encode_bool_and_list(self):
        vd = VectorizedDispatcher()
        assert (
            vd.encode("test", {"compact": True, "tags": ["a", "b"]})
            == "test[C:!t,g:a|b]"
        )

    def test_decode_known_tool(self):
        vd = VectorizedDispatcher()
        tool, args = vd.decode("M+")
        assert tool == "create_memory"
        assert args == {}

    def test_decode_with_args(self):
        vd = VectorizedDispatcher()
        tool, args = vd.decode("M?[n:10,q:test]")
        assert tool == "search_memories"
        assert args == {"limit": 10, "query": "test"}

    def test_decode_bool(self):
        vd = VectorizedDispatcher()
        tool, args = vd.decode("test[C:!t,D:!f]")
        assert args == {"compact": True, "dry_run": False}

    def test_decode_list(self):
        vd = VectorizedDispatcher()
        tool, args = vd.decode("test[g:a|b|c]")
        assert args == {"tags": ["a", "b", "c"]}

    def test_decode_unknown_tool(self):
        vd = VectorizedDispatcher()
        tool, args = vd.decode("unknown")
        assert tool == "unknown"
        assert args == {}

    def test_roundtrip(self):
        vd = VectorizedDispatcher()
        original = ("read_memory", {"id": "abc123", "limit": 5, "compact": True})
        encoded = vd.encode(*original)
        decoded = vd.decode(encoded)
        assert decoded == original

    def test_measure_compression(self):
        vd = VectorizedDispatcher()
        m = vd.measure(
            "search_memories",
            {
                "query": "consciousness",
                "limit": 10,
                "sort_by": "importance",
                "order": "desc",
            },
        )
        assert m["raw_bytes"] > m["encoded_bytes"]
        assert m["ratio"] > 0.3  # expect at least 30% compression

    def test_codebook_coverage(self):
        # Every mapped tool must be reversible
        for tool, glyph in _TOOL_CODEBOOK.items():
            assert _REVERSE_TOOL[glyph] == tool, f"reverse mismatch for {tool}"

    def test_module_level_helpers(self):
        assert encode_call("gnosis") == "Gg"
        assert decode_call("Gg") == ("gnosis", {})
        assert is_vectorized_mode() is False  # env not set by default


class TestVectorizedModeToggle:
    def test_vectorized_mode_on(self, monkeypatch):
        monkeypatch.setenv("WM_VECTORIZED", "1")
        assert is_vectorized_mode() is True

    def test_vectorized_mode_true_string(self, monkeypatch):
        monkeypatch.setenv("WM_VECTORIZED", "true")
        assert is_vectorized_mode() is True

    def test_vectorized_mode_off(self, monkeypatch):
        monkeypatch.setenv("WM_VECTORIZED", "0")
        assert is_vectorized_mode() is False
