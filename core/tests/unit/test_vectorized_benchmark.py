"""Benchmark: VectorizedDispatcher compression on realistic tool call patterns."""
import pytest
from whitemagic.tools.vectorized import VectorizedDispatcher, decode_call, encode_call

BENCHMARK_CASES = [
    ("search_memories", {"query": "consciousness", "limit": 10, "sort_by": "importance", "order": "desc"}),
    ("search_memories", {"query": "karma ledger", "limit": 5, "tags": ["ethics", "governance"], "threshold": 0.7}),
    ("read_memory", {"id": "abc123", "compact": True}),
    ("create_memory", {"content": "Dream cycle insight", "title": "REM", "memory_type": "SHORT_TERM", "auto_embed": True}),
    ("update_memory", {"id": "mem_456", "content": "Updated", "tags": ["dream", "pattern"]}),
    ("batch_read_memories", {"ids": ["a", "b", "c"], "include_metadata": True}),
    ("hybrid_recall", {"query": "agentic governance", "limit": 20, "ground_in_memory": True}),
    ("list_memories", {"limit": 50, "memory_type": "LONG_TERM", "sort_by": "accessed", "order": "desc"}),
    ("gnosis", {"query": "What is the current system state?"}),
    ("capabilities", {"compact": True}),
    ("get_telemetry_summary", {}),
    ("selfmodel.forecast", {"horizon_days": 7}),
    ("graph_topology", {"depth": 2}),
    ("scratchpad", {"operation": "create", "content": "Session notes"}),
    ("context.pack", {}),
    ("working_memory.attend", {"topic": "PRAT compression"}),
    ("governor_validate", {"goal": "ship v22.3.0"}),
    ("prat_invoke", {"tool": "gnosis", "args": {"compact": True}}),
    ("dharma.reload", {}),
    ("health_report", {"include_diagnostics": True}),
    ("state.summary", {}),
    ("ship.check", {}),
    ("kg.query", {"query": "SELECT * WHERE { ?s ?p ?o }", "limit": 10}),
    ("kg2.extract", {"source": "memory", "min_confidence": 0.8}),
    ("archaeology", {"target": "docs", "depth": 3}),
    ("pattern_search", {"query": "tool-call-anomaly", "threshold": 0.5}),
    ("learning.patterns", {"domain": "memory"}),
    ("dream", {"phase": "REM", "duration_min": 15}),
    ("memory.lifecycle", {"action": "sweep", "dry_run": True}),
    ("serendipity_surface", {"min_novelty": 0.8}),
    ("view_hologram", {"garden": "winnowing_basket"}),
    ("track_metric", {"name": "tool_calls_per_hour", "value": 120.5}),
    ("evaluate_ethics", {"scenario": "MCP tool delegation to untrusted agent"}),
    ("harmony_vector", {}),
    ("simd.cosine", {"a": [0.1, 0.2, 0.3], "b": [0.3, 0.2, 0.1]}),
    ("simd.batch", {"vectors": [[1, 2], [3, 4]], "query": [1, 1]}),
    ("watcher_add", {"name": "memory_growth", "condition": "count > 10000"}),
    ("watcher_status", {}),
    ("galaxy_status", {}),
    ("export_memories", {"format": "json", "include_embeddings": False}),
    ("mesh.status", {}),
    ("grimoire_suggest", {"intent": "compress", "domain": "tool_dsl"}),
    ("cast_oracle", {"question": "Should we ship this week?"}),
    ("forge.status", {}),
    ("prompt.list", {"tag": "system"}),
]


class TestCompressionBenchmark:
    @pytest.mark.parametrize("tool_name,args", BENCHMARK_CASES)
    def test_roundtrip(self, tool_name, args):
        vd = VectorizedDispatcher()
        encoded = vd.encode(tool_name, args)
        decoded_tool, decoded_args = vd.decode(encoded)
        assert decoded_tool == tool_name
        assert decoded_args == args

    def test_summary_stats(self):
        vd = VectorizedDispatcher()
        ratios = []
        unmapped = []
        for tool_name, args in BENCHMARK_CASES:
            m = vd.measure(tool_name, args)
            ratios.append(m["ratio"])
            if m["encoded_bytes"] >= m["raw_bytes"]:
                unmapped.append((tool_name, m["encoded"], m["raw_bytes"], m["encoded_bytes"]))
        avg = sum(ratios) / len(ratios)
        print(f"\n{'='*60}")
        print(f"Benchmark ({len(BENCHMARK_CASES)} cases) | avg={avg:.1%} min={min(ratios):.1%} max={max(ratios):.1%}")
        print(f"  Expanded: {len(unmapped)}")
        for t, enc, raw_b, enc_b in unmapped:
            print(f"    {t:35s} raw={raw_b:3d}b enc={enc_b:3d}b -> {enc}")
        assert avg > 0.15
        assert len(unmapped) <= 10


class TestEdgeCases:
    def test_empty_args(self):
        assert encode_call("gnosis") == "Gg"
        assert decode_call("Gg") == ("gnosis", {})

    def test_unicode_in_args(self):
        vd = VectorizedDispatcher()
        enc = vd.encode("create_memory", {"content": "日本語", "title": "🌙"})
        _, dargs = vd.decode(enc)
        assert dargs["content"] == "日本語"
        assert dargs["title"] == "🌙"

    def test_unmapped_tool_falls_through(self):
        vd = VectorizedDispatcher()
        enc = vd.encode("totally_unknown_tool_xyz", {"foo": "bar"})
        tool, args = vd.decode(enc)
        assert tool == "totally_unknown_tool_xyz"
        assert args == {"foo": "bar"}

    def test_float_precision(self):
        vd = VectorizedDispatcher()
        enc = vd.encode("track_metric", {"value": 3.14159})
        _, args = vd.decode(enc)
        assert args["value"] == 3.14159
