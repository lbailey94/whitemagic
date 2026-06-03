"""Tests for PRAT Compressor.

Covers:
- Round-trip compress/decompress
- Gana name encoding (lunar mansion glyphs)
- Nested tool name aliasing
- Arg name aliasing
- Stats calculation
- WM_VECTORIZED env toggle
"""

import os
import pytest
from whitemagic.tools.prat_compressor import (
    PratCompressor,
    get_prat_compressor,
    is_vectorized,
)


class TestPratCompressor:
    def test_level_0_passthrough(self):
        c = PratCompressor(level=0)
        payload = {"tool": "search_memories", "args": {"query": "hello", "limit": 10}}
        assert c.compress(payload) == payload
        assert c.decompress(payload) == payload

    def test_tool_name_alias(self):
        c = PratCompressor(level=1)
        payload = {"tool": "search_memories", "args": {"query": "hello", "limit": 10}}
        comp = c.compress(payload)
        assert comp["槍"] == "sm"  # tool → 枪
        assert comp["a"]["q"] == "hello"
        assert comp["a"]["n"] == 10

        decomp = c.decompress(comp)
        assert decomp["tool"] == "search_memories"
        assert decomp["args"]["query"] == "hello"
        assert decomp["args"]["limit"] == 10

    def test_gana_name_encoding(self):
        c = PratCompressor(level=1)
        gana, tool, args, op = c.compress_gana_call(
            "gana_winnowing_basket", "search_memories", {"query": "x"}, None
        )
        assert gana == "箕"  # winnowing basket glyph
        assert tool == "sm"
        assert args == {"q": "x"}

        dg, dt, da, do = c.decompress_gana_call(gana, tool, args, op)
        assert dg == "gana_winnowing_basket"
        assert dt == "search_memories"
        assert da == {"query": "x"}
        assert do is None

    def test_unknown_tool_passthrough(self):
        c = PratCompressor(level=1)
        payload = {"tool": "unknown_tool_xyz", "args": {"foo": "bar"}}
        comp = c.compress(payload)
        assert comp["槍"] == "unknown_tool_xyz"
        assert comp["a"]["foo"] == "bar"

    def test_nested_dict_compression(self):
        c = PratCompressor(level=1)
        payload = {
            "args": {
                "query": "test",
                "tags": ["a", "b"],
                "nested": {"content": "hello"},
            }
        }
        comp = c.compress(payload)
        assert comp["a"]["q"] == "test"
        assert comp["a"]["t"] == ["a", "b"]
        assert comp["a"]["nested"]["c"] == "hello"

    def test_stats_positive_savings(self):
        c = PratCompressor(level=1)
        orig = {"tool": "search_memories", "args": {"query": "hello", "limit": 10}}
        comp = c.compress(orig)
        stats = c.stats(orig, comp)
        assert stats["chars_saved"] > 0
        assert stats["ratio"] > 1.0
        assert stats["estimated_tokens_saved"] >= 0

    def test_stats_level_0_no_savings(self):
        c = PratCompressor(level=0)
        orig = {"tool": "search_memories", "args": {"query": "hello"}}
        comp = c.compress(orig)
        stats = c.stats(orig, comp)
        assert stats["chars_saved"] == 0
        assert stats["ratio"] == 1.0

    def test_is_vectorized_env_toggle(self):
        old = os.environ.get("WM_VECTORIZED")
        try:
            os.environ["WM_VECTORIZED"] = "1"
            assert is_vectorized() is True
            os.environ["WM_VECTORIZED"] = "true"
            assert is_vectorized() is True
            os.environ["WM_VECTORIZED"] = "0"
            assert is_vectorized() is False
            del os.environ["WM_VECTORIZED"]
            assert is_vectorized() is False
        finally:
            if old is not None:
                os.environ["WM_VECTORIZED"] = old
            elif "WM_VECTORIZED" in os.environ:
                del os.environ["WM_VECTORIZED"]

    def test_get_prat_compressor_singleton(self):
        import whitemagic.tools.prat_compressor as _pc
        old = os.environ.get("WM_VECTORIZED")
        try:
            # Reset singleton so env change is respected
            _pc._compressor = None
            os.environ["WM_VECTORIZED"] = "1"
            c1 = get_prat_compressor()
            c2 = get_prat_compressor()
            assert c1 is c2
            assert c1.level == 1
        finally:
            _pc._compressor = None
            if old is not None:
                os.environ["WM_VECTORIZED"] = old
            elif "WM_VECTORIZED" in os.environ:
                del os.environ["WM_VECTORIZED"]
