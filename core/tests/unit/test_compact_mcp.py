"""Tests for MCP compact response mode and vectorized dispatch compression."""

import json
import os
from typing import Any

import pytest

from whitemagic.tools.compact_response import _summarize, compact
from whitemagic.tools.prat_compressor import PratCompressor
from whitemagic.tools.vectorized import (
    VectorizedDispatcher,
    decode_call,
    encode_call,
    is_vectorized_mode,
)


# ── compact_response.py tests ──


class TestCompactResponse:
    def test_compact_preserves_essential_fields(self):
        result = {"status": "success", "error_code": None, "tool": "test"}
        out = compact(result)
        assert out["status"] == "success"
        assert out["tool"] == "test"

    def test_compact_truncates_long_strings(self):
        result = {"status": "success", "details": {"content": "A" * 500}}
        out = compact(result)
        content = out["details"]["content"]
        assert len(content) <= 203  # 200 + "..."
        assert content.endswith("...")

    def test_compact_truncates_lists(self):
        result = {"status": "success", "items": list(range(10))}
        out = compact(result)
        items = out["items"]
        assert len(items) == 4  # 3 items + "...and 7 more"
        assert "7 more" in items[-1]

    def test_compact_preserves_short_strings(self):
        result = {"status": "success", "message": "ok"}
        out = compact(result)
        assert out["message"] == "ok"

    def test_compact_handles_nested_dicts(self):
        result = {
            "status": "success",
            "details": {
                "inner": {"deep_key": "deep_value", "another": "val"},
            },
        }
        out = compact(result)
        assert "details" in out
        assert "inner" in out["details"]

    def test_compact_handles_empty_structures(self):
        result = {"status": "success", "empty_list": [], "empty_dict": {}}
        out = compact(result)
        assert out["empty_list"] == []
        assert out["empty_dict"] == {}

    def test_compact_non_dict_passthrough(self):
        assert compact("string") == "string"
        assert compact(42) == 42
        assert compact(None) is None

    def test_summarize_dict(self):
        d = {"a": 1, "b": 2, "c": 3}
        result = _summarize(d)
        assert "3 keys" in result

    def test_summarize_list(self):
        result = _summarize([1, 2, 3, 4, 5])
        assert "5 items" in result

    def test_summarize_long_string(self):
        result = _summarize("A" * 100)
        assert len(result) <= 53
        assert result.endswith("...")


# ── Middleware compact wiring test ──


class TestMiddlewareCompactWiring:
    def test_compact_fn_is_loaded(self):
        import whitemagic.tools.middleware as mw

        # Force re-initialization in case a prior import cached None
        mw._cached = False
        mw._compact_fn = None
        mw._ensure_cached()
        assert mw._compact_fn is not None, (
            "compact_fn should be loaded from compact_response.compact"
        )

    def test_compact_fn_works_via_middleware(self):
        import whitemagic.tools.middleware as mw

        mw._cached = False
        mw._compact_fn = None
        mw._ensure_cached()
        if mw._compact_fn is None:
            pytest.skip("compact_fn not available")
        result = {"status": "ok", "data": "A" * 500}
        out = mw._compact_fn(result)
        assert out["status"] == "ok"
        assert len(out["data"]) <= 203


# ── Vectorized dispatcher tests ──


class TestVectorizedDispatcher:
    def test_encode_tool_only(self):
        vd = VectorizedDispatcher()
        assert vd.encode("search_memories") == "M?"

    def test_encode_with_args(self):
        vd = VectorizedDispatcher()
        result = vd.encode("search_memories", {"query": "test", "limit": 5})
        assert result.startswith("M?[")
        assert "q:test" in result
        assert "n:5" in result

    def test_decode_roundtrip(self):
        vd = VectorizedDispatcher()
        encoded = vd.encode("create_memory", {"title": "Test", "content": "Hello"})
        tool, args = vd.decode(encoded)
        assert tool == "create_memory"
        assert args["title"] == "Test"
        assert args["content"] == "Hello"

    def test_decode_roundtrip_with_bool(self):
        vd = VectorizedDispatcher()
        encoded = vd.encode("search_memories", {"compact": True, "limit": 10})
        tool, args = vd.decode(encoded)
        assert tool == "search_memories"
        assert args["compact"] is True
        assert args["limit"] == 10

    def test_decode_roundtrip_with_list(self):
        vd = VectorizedDispatcher()
        encoded = vd.encode("create_memory", {"tags": ["a", "b", "c"]})
        tool, args = vd.decode(encoded)
        assert args["tags"] == ["a", "b", "c"]

    def test_measure_compression(self):
        vd = VectorizedDispatcher()
        m = vd.measure("search_memories", {"query": "consciousness", "limit": 10})
        assert m["raw_bytes"] > m["encoded_bytes"]
        assert m["ratio"] > 0.3
        assert m["saved"] > 0

    def test_unknown_tool_passthrough(self):
        vd = VectorizedDispatcher()
        assert vd.encode("unknown_tool") == "unknown_tool"

    def test_encode_call_convenience(self):
        result = encode_call("gnosis")
        assert result == "Gg"

    def test_decode_call_convenience(self):
        tool, args = decode_call("Gg")
        assert tool == "gnosis"

    def test_is_vectorized_mode_default_off(self):
        old = os.environ.pop("WM_VECTORIZED", None)
        try:
            assert is_vectorized_mode() is False
        finally:
            if old is not None:
                os.environ["WM_VECTORIZED"] = old

    def test_is_vectorized_mode_on(self):
        old = os.environ.get("WM_VECTORIZED")
        os.environ["WM_VECTORIZED"] = "1"
        try:
            assert is_vectorized_mode() is True
        finally:
            if old is not None:
                os.environ["WM_VECTORIZED"] = old
            else:
                os.environ.pop("WM_VECTORIZED", None)


# ── PRAT compressor tests ──


class TestPratCompressor:
    def test_gana_codes_cover_all_28(self):
        assert len(_get_gana_codes()) == 28

    def test_compress_gana_name(self):
        comp = PratCompressor(level=1)
        assert comp._gana["gana_horn"] == "角"
        assert comp._gana["gana_winnowing_basket"] == "箕"
        assert comp._gana["gana_wall"] == "壁"

    def test_compress_decompress_roundtrip(self):
        comp = PratCompressor(level=1)
        payload = {"tool": "search_memories", "args": {"query": "test", "limit": 5}}
        compressed = comp.compress(payload)
        decompressed = comp.decompress(compressed)
        assert decompressed == payload

    def test_compress_gana_call_roundtrip(self):
        comp = PratCompressor(level=1)
        cg, ct, ca, co = comp.compress_gana_call(
            "gana_winnowing_basket", "search_memories", {"query": "x"}, "search"
        )
        assert cg == "箕"
        dg, dt, da, do = comp.decompress_gana_call(cg, ct, ca, co)
        assert dg == "gana_winnowing_basket"
        assert dt == "search_memories"
        assert da == {"query": "x"}
        assert do == "search"

    def test_level_0_passthrough(self):
        comp = PratCompressor(level=0)
        payload = {"tool": "search_memories", "args": {"query": "test"}}
        assert comp.compress(payload) == payload

    def test_stats_measures_savings(self):
        comp = PratCompressor(level=1)
        original = {"tool": "search_memories", "args": {"query": "test"}}
        compressed = comp.compress(original)
        st = comp.stats(original, compressed)
        assert "original_chars" in st
        assert "compressed_chars" in st
        assert "estimated_tokens_saved" in st

    def test_unknown_keys_passthrough(self):
        comp = PratCompressor(level=1)
        payload = {"unknown_key": "value", "another": 42}
        compressed = comp.compress(payload)
        decompressed = comp.decompress(compressed)
        assert decompressed == payload


def _get_gana_codes() -> dict[str, str]:
    from whitemagic.tools.prat_compressor import _GANA_CODES

    return _GANA_CODES


# ── Integration: compact strips consciousness metadata ──


class TestCompactStripsConsciousness:
    """Simulates what WM_MCP_COMPACT=1 does in run_mcp_lean.py."""

    _STRIP_KEYS = frozenset({
        "_resonance", "_citta_predecessor", "_sensorium",
        "_garden", "metadata", "metrics", "side_effects",
        "warnings", "_wm_route", "_wm_forged_skill",
    })

    def _compact(self, result: dict[str, Any]) -> dict[str, Any]:
        out = {k: v for k, v in result.items() if k not in self._STRIP_KEYS}
        return compact(out)

    def test_strips_resonance_metadata(self):
        result = {
            "status": "success",
            "tool": "health_report",
            "details": {"version": "24.1.0"},
            "_resonance": {"gana": "gana_root", "chain_position": 1},
            "_sensorium": {"coherence": 0.91, "stream_length": 100},
            "_citta_predecessor": {"emotional_tone": "neutral"},
            "metadata": {"token_tracking": {"input_tokens": 0}},
            "metrics": {"harmony_score": 0.74},
        }
        out = self._compact(result)
        assert "_resonance" not in out
        assert "_sensorium" not in out
        assert "_citta_predecessor" not in out
        assert "metadata" not in out
        assert "metrics" not in out
        assert out["status"] == "success"
        assert out["tool"] == "health_report"
        assert out["details"]["version"] == "24.1.0"

    def test_token_savings_significant(self):
        full = {
            "status": "success",
            "tool": "test",
            "details": {"version": "1.0"},
            "_resonance": {f"key_{i}": f"value_{i}" for i in range(20)},
            "_sensorium": {f"sensor_{i}": i for i in range(15)},
            "_citta_predecessor": {f"citta_{i}": f"val_{i}" for i in range(10)},
            "metadata": {"nested": {"deep": {"data": "x" * 500}}},
        }
        full_json = json.dumps(full)
        compacted = self._compact(full)
        compact_json = json.dumps(compacted)
        ratio = len(full_json) / len(compact_json)
        assert ratio >= 3.0, (
            f"Expected >=3x compression, got {ratio:.1f}x "
            f"({len(full_json)} -> {len(compact_json)} bytes)"
        )
