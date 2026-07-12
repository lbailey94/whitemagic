"""Tests for the WhiteMagic meta-tool ('wm') — world in a seed.

Validates routing accuracy, latency, explicit override, fallback behavior,
and registry/dispatch integration.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from whitemagic.tools.handlers.meta_tool import (
    _PAYLOAD_MAP,
    _ROUTING_PATTERNS,
    _extract_payload,
    classify,
    handle_wm,
    handle_wm_help,
)


class TestClassify:
    """Test the classify() routing function."""

    @pytest.mark.parametrize(
        "text,expected_gana,expected_tool",
        [
            (
                "remember that the API uses X-User-Id headers",
                "gana_neck",
                "create_memory",
            ),
            ("store this fact for later", "gana_neck", "create_memory"),
            ("save a memory about the deployment", "gana_neck", "create_memory"),
            (
                "search for memories about architecture",
                "gana_winnowing_basket",
                "search_memories",
            ),
            (
                "find memories about security",
                "gana_winnowing_basket",
                "search_memories",
            ),
            (
                "recall what we decided about caching",
                "gana_winnowing_basket",
                "search_memories",
            ),
            (
                "think about the architecture tradeoffs",
                "gana_three_stars",
                "reasoning.bicameral",
            ),
            ("analyze the system design", "gana_three_stars", "reasoning.bicameral"),
            ("reason through the options", "gana_three_stars", "reasoning.bicameral"),
            ("check system health", "gana_root", "health_report"),
            ("show me the system status", "gana_root", "health_report"),
            ("what is our gnosis", "gana_ghost", "gnosis"),
            ("show me system capabilities", "gana_ghost", "capabilities"),
            ("start a new session", "gana_horn", "session_bootstrap"),
            ("bootstrap the session", "gana_horn", "session_bootstrap"),
            ("create a new galaxy", "gana_void", "galaxy.create"),
            ("list all galaxies", "gana_void", "galaxy.list"),
            (
                "evaluate the ethics of this action",
                "gana_straddling_legs",
                "evaluate_ethics",
            ),
            ("check the dharma rules", "gana_straddling_legs", "evaluate_ethics"),
            ("run a kaizen analysis", "gana_three_stars", "kaizen_analyze"),
            ("predict memory decay", "gana_three_stars", "foresight.analyze"),
            ("convene the sabha council", "gana_three_stars", "sabha.convene"),
            (
                "assess the terrain like art of war",
                "gana_three_stars",
                "art_of_war.assess",
            ),
            ("write to scratchpad", "gana_heart", "scratchpad"),
            ("check rust status", "gana_root", "rust_status"),
            ("ship check for release", "gana_root", "ship.check"),
            ("add an edge inference rule", "gana_turtle_beak", "edge_infer"),
            ("check for anomalies", "gana_hairy_head", "anomaly.check"),
            ("decompose this into swarm tasks", "gana_ox", "swarm.decompose"),
            ("register a new agent", "gana_girl", "agent.register"),
        ],
    )
    def test_routing_accuracy(self, text: str, expected_gana: str, expected_tool: str):
        gana, tool, confidence = classify(text)
        assert gana == expected_gana, (
            f"Expected {expected_gana} for '{text}', got {gana}"
        )
        assert tool == expected_tool, (
            f"Expected {expected_tool} for '{text}', got {tool}"
        )
        assert confidence == 1.0

    def test_no_match_falls_back_to_gnosis(self):
        gana, tool, confidence = classify("xyzzy frobnicate the quux")
        assert gana == "gana_ghost"
        assert tool == "gnosis"
        assert confidence == 0.0

    def test_empty_input_falls_back(self):
        gana, tool, confidence = classify("")
        assert gana == "gana_ghost"
        assert confidence == 0.0

    def test_routing_patterns_not_empty(self):
        assert len(_ROUTING_PATTERNS) > 20, "Should have substantial routing patterns"


class TestClassifyLatency:
    """Test that classification is sub-millisecond."""

    def test_classify_fast(self):
        text = "remember that the API uses X-User-Id headers for multi-user isolation"
        start = time.time()
        for _ in range(100):
            classify(text)
        elapsed_ms = (time.time() - start) * 10  # per-call ms
        assert elapsed_ms < 10.0, f"Classification took {elapsed_ms:.3f}ms per call"

    def test_classify_long_input_fast(self):
        text = "think about " + "the architecture " * 50
        start = time.time()
        for _ in range(100):
            classify(text)
        elapsed_ms = (time.time() - start) * 10  # per-call ms
        assert elapsed_ms < 15.0, f"Classification took {elapsed_ms:.3f}ms per call"


class TestHandleWm:
    """Test the handle_wm() handler."""

    def test_no_input_returns_error(self):
        result = handle_wm()
        assert result["status"] == "error"
        assert "thought" in result["message"]
        assert "route" in result["message"]

    def test_explicit_route_override(self):
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success", "data": "ok"}
            result = handle_wm(
                thought="analyze this",
                route="gana_three_stars.reasoning.bicameral",
            )
        assert result["status"] == "success"
        assert result["_wm_route"]["gana"] == "gana_three_stars"
        assert result["_wm_route"]["tool"] == "reasoning.bicameral"
        assert result["_wm_route"]["confidence"] == 1.0
        mock_call.assert_called_once()

    def test_explicit_route_gana_only(self):
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = handle_wm(route="gana_root")
        assert result["_wm_route"]["gana"] == "gana_root"
        assert result["_wm_route"]["tool"] is None

    def test_auto_route_from_thought(self):
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success", "data": "stored"}
            result = handle_wm(thought="remember that the sky is blue")
        assert result["status"] == "success"
        assert result["_wm_route"]["gana"] == "gana_neck"
        assert result["_wm_route"]["tool"] == "create_memory"
        assert result["_wm_route"]["confidence"] == 1.0

    def test_passthrough_args(self):
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            handle_wm(
                thought="search for memories",
                args={"limit": 10, "tags": ["architecture"]},
            )
        _, kwargs = mock_call.call_args
        assert kwargs.get("args") == {"limit": 10, "tags": ["architecture"]}

    def test_route_metadata_includes_classify_ms(self):
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = handle_wm(thought="check system health")
        assert "classify_ms" in result["_wm_route"]
        assert result["_wm_route"]["classify_ms"] < 5.0

    def test_fallback_no_match(self):
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = handle_wm(thought="xyzzy frobnicate")
        assert result["_wm_route"]["gana"] == "gana_ghost"
        assert result["_wm_route"]["confidence"] == 0.0


class TestHandleWmHelp:
    """Test the help endpoint."""

    def test_help_returns_success(self):
        result = handle_wm_help()
        assert result["status"] == "success"
        assert result["tool"] == "wm"
        assert "usage" in result
        assert "routing_patterns" in result
        assert result["routing_patterns"] > 20

    def test_help_includes_usage_examples(self):
        result = handle_wm_help()
        assert "auto_route" in result["usage"]
        assert "explicit_route" in result["usage"]
        assert "with_args" in result["usage"]
        assert "discover" in result["usage"]
        assert "schema" in result["usage"]


class TestDiscoverMode:
    """Test the discover mode — wm(thought='help') or wm(route='discover')."""

    def test_discover_via_thought_help(self):
        result = handle_wm(thought="help")
        assert result["status"] == "success"
        assert result["mode"] == "discover"
        assert "ganas" in result
        assert len(result["ganas"]) == 28

    def test_discover_via_route(self):
        result = handle_wm(route="discover")
        assert result["status"] == "success"
        assert result["mode"] == "discover"
        assert "ganas" in result

    def test_discover_via_thought_what_can_you_do(self):
        result = handle_wm(thought="what can you do")
        assert result["status"] == "success"
        assert result["mode"] == "discover"

    def test_discover_via_thought_question_mark(self):
        result = handle_wm(thought="?")
        assert result["status"] == "success"
        assert result["mode"] == "discover"

    def test_discover_includes_gana_descriptions(self):
        result = handle_wm(thought="help")
        first_gana = list(result["ganas"].keys())[0]
        assert "description" in result["ganas"][first_gana]
        assert "tools" in result["ganas"][first_gana]
        assert isinstance(result["ganas"][first_gana]["tools"], list)

    def test_discover_includes_routing_examples(self):
        result = handle_wm(route="discover")
        assert "routing_examples" in result
        assert len(result["routing_examples"]) >= 3


class TestSchemaMode:
    """Test the schema mode — wm(route='schema:gana_name')."""

    def test_schema_for_known_gana(self):
        result = handle_wm(route="schema:gana_neck")
        assert result["status"] == "success"
        assert result["mode"] == "schema"
        assert result["gana"] == "gana_neck"
        assert "description" in result
        assert "nested_tools" in result
        assert isinstance(result["nested_tools"], list)
        assert len(result["nested_tools"]) > 0

    def test_schema_for_unknown_gana(self):
        result = handle_wm(route="schema:gana_nonexistent")
        assert result["status"] == "error"
        assert result["error_code"] == "unknown_gana"
        assert "available_ganas" in result

    def test_schema_includes_usage_example(self):
        result = handle_wm(route="schema:gana_root")
        assert "usage" in result
        assert "example" in result
        assert "gana_root" in result["example"]


class TestRegistryIntegration:
    """Test that 'wm' is registered in dispatch table and registry."""

    def test_dispatch_table_has_wm(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        assert "wm" in DISPATCH_TABLE

    def test_dispatch_table_has_wm_help(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        assert "wm_help" in DISPATCH_TABLE

    def test_registry_has_wm(self):
        from whitemagic.tools.registry import get_tool

        tool = get_tool("wm")
        assert tool is not None
        assert tool.name == "wm"

    def test_wm_stability_is_stable(self):
        from whitemagic.tools.registry import get_tool
        from whitemagic.tools.tool_types import ToolStability

        tool = get_tool("wm")
        assert tool.stability == ToolStability.STABLE


class TestPayloadExtraction:
    """Test the _extract_payload() function — auto-extracting content from thought."""

    def test_remember_strips_to_content(self):
        param, value = _extract_payload(
            "remember that the API uses X-User-Id headers",
            "gana_neck",
            "create_memory",
        )
        assert param == "content"
        assert value == "the API uses X-User-Id headers"

    def test_store_strips_to_content(self):
        param, value = _extract_payload(
            "store this fact for later",
            "gana_neck",
            "create_memory",
        )
        assert param == "content"
        assert value == "this fact for later"

    def test_save_strips_to_content(self):
        param, value = _extract_payload(
            "save a memory about the deployment",
            "gana_neck",
            "create_memory",
        )
        assert param == "content"
        assert value == "a memory about the deployment"

    def test_search_strips_to_query(self):
        param, value = _extract_payload(
            "search for memories about architecture",
            "gana_winnowing_basket",
            "search_memories",
        )
        assert param == "query"
        assert value == "architecture"

    def test_recall_strips_to_query(self):
        param, value = _extract_payload(
            "recall what we decided about caching",
            "gana_winnowing_basket",
            "search_memories",
        )
        assert param == "query"
        assert value == "what we decided about caching"

    def test_think_strips_to_topic(self):
        param, value = _extract_payload(
            "think about the architecture tradeoffs",
            "gana_three_stars",
            "reasoning.bicameral",
        )
        assert param == "topic"
        assert value == "the architecture tradeoffs"

    def test_analyze_strips_to_topic(self):
        param, value = _extract_payload(
            "analyze the system design",
            "gana_three_stars",
            "reasoning.bicameral",
        )
        assert param == "topic"
        assert value == "the system design"

    def test_ethics_strips_to_action(self):
        param, value = _extract_payload(
            "evaluate the ethics of this action",
            "gana_straddling_legs",
            "evaluate_ethics",
        )
        assert param == "action"
        assert value == "this action"

    def test_gnosis_is_skip(self):
        param, value = _extract_payload(
            "show me the system gnosis snapshot",
            "gana_ghost",
            "gnosis",
        )
        assert param is None
        assert value is None

    def test_no_mapping_returns_none(self):
        param, value = _extract_payload(
            "some random text",
            "gana_horn",
            "session_bootstrap",
        )
        assert param is None
        assert value is None

    def test_empty_after_strip_returns_none(self):
        param, value = _extract_payload(
            "remember",
            "gana_neck",
            "create_memory",
        )
        assert param is None
        assert value is None

    def test_scratchpad_strips_to_content(self):
        param, value = _extract_payload(
            "note: the deploy script needs updating",
            "gana_heart",
            "scratchpad",
        )
        assert param == "content"
        assert value == "the deploy script needs updating"

    def test_payload_map_covers_key_tools(self):
        # Ensure we have payload mappings for the most common operations
        assert ("gana_neck", "create_memory") in _PAYLOAD_MAP
        assert ("gana_winnowing_basket", "search_memories") in _PAYLOAD_MAP
        assert ("gana_three_stars", "reasoning.bicameral") in _PAYLOAD_MAP
        assert ("gana_straddling_legs", "evaluate_ethics") in _PAYLOAD_MAP


class TestHandleWmPayloadAutoInjection:
    """Test that handle_wm auto-injects extracted payload into tool calls."""

    def test_remember_auto_injects_content(self):
        """wm(thought='remember that X') should auto-inject content=X and title."""
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            handle_wm(thought="remember that the sky is blue")
            _, kwargs = mock_call.call_args
            assert kwargs.get("args", {}).get("content") == "the sky is blue"
            assert kwargs.get("args", {}).get("title") == "the sky is blue"

    def test_remember_auto_title_truncated(self):
        """Long content should produce a truncated title."""
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            long_text = "remember that " + "x" * 100
            handle_wm(thought=long_text)
            _, kwargs = mock_call.call_args
            assert len(kwargs.get("args", {}).get("title", "")) == 60

    def test_search_auto_injects_query(self):
        """wm(thought='search for memories about X') should auto-inject query=X."""
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            handle_wm(thought="search for memories about architecture")
            _, kwargs = mock_call.call_args
            assert kwargs.get("args", {}).get("query") == "architecture"

    def test_explicit_args_override_auto_injection(self):
        """When args are explicitly provided, auto-injection should not happen."""
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            handle_wm(
                thought="remember that the sky is blue",
                args={"content": "custom content"},
            )
            _, kwargs = mock_call.call_args
            assert kwargs.get("args", {}).get("content") == "custom content"

    def test_explicit_route_skips_auto_injection(self):
        """When using explicit route, auto-injection should not happen."""
        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            handle_wm(
                thought="remember that the sky is blue",
                route="gana_neck.create_memory",
            )
            _, kwargs = mock_call.call_args
            # No auto-injection when route is explicit
            assert "content" not in kwargs.get("args", {})


class TestSensorium:
    """Test sensorium injection — full self-state in every wm() response."""

    def test_sensorium_injected_on_success(self):
        """Successful wm() calls include _sensorium with self-state."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        get_citta_cycle().reset()

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success", "result": "ok"}
            result = handle_wm(thought="remember that sensorium works")

            assert "_sensorium" in result
            s = result["_sensorium"]
            assert "coherence" in s
            assert "depth_layer" in s
            assert "stream_length" in s
            assert "time_of_day" in s
            assert s["stream_length"] >= 1

    def test_sensorium_injected_on_error(self):
        """Even error responses get sensorium (awareness persists)."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        get_citta_cycle().reset()

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "error", "message": "failed"}
            result = handle_wm(thought="remember that errors have awareness too")

            assert "_sensorium" in result
            assert result["_sensorium"]["coherence"] <= 1.0

    def test_sensorium_stream_grows_across_calls(self):
        """Multiple calls increase stream_length in sensorium."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.side_effect = [{"status": "success"}, {"status": "success"}]

            handle_wm(thought="remember first")
            s1 = handle_wm(thought="remember second")

            assert s1["_sensorium"]["stream_length"] >= 2

    def test_sensorium_has_emotional_coloring(self):
        """Sensorium includes emotional coloring from citta cycle."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        get_citta_cycle().reset()

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = handle_wm(thought="remember something important")

            assert "emotional_coloring" in result["_sensorium"]
            assert "dominant" in result["_sensorium"]["emotional_coloring"]

    def test_sensorium_has_session_count(self):
        """Sensorium includes session_count from continuity context."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        get_citta_cycle().reset()

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = handle_wm(thought="remember session tracking")

            assert "session_count" in result["_sensorium"]
            assert isinstance(result["_sensorium"]["session_count"], int)

    def test_sensorium_has_presence_quality(self):
        """Sensorium includes presence_quality from stillness metrics."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        get_citta_cycle().reset()

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = handle_wm(thought="remember presence quality")

            assert "presence_quality" in result["_sensorium"]
            pq = result["_sensorium"]["presence_quality"]
            assert "continuity" in pq
            assert "stability" in pq
            assert "clarity" in pq
            assert "equanimity" in pq
            assert "spaciousness" in pq
            assert "overall" in pq


class TestCoherenceDispatch:
    """Test coherence-driven dispatch — low coherence flags risky routes."""

    def test_low_coherence_flags_unsafe_gana(self):
        """When avg coherence < 0.6 and stream >= 3, unsafe ganas get caution flag."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()

        # Fill stream with 3 low-coherence entries
        for _ in range(3):
            cycle.advance(gana="gana_ox", tool="test", coherence=0.3)

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            # Route to an "unsafe" gana (not in _SAFE_GANAS)
            result = handle_wm(route="gana_ox.swarm_decompose")

            assert result.get("_coherence_caution") is True

        cycle.reset()

    def test_high_coherence_no_caution(self):
        """When coherence is high, no caution flag is set."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()

        for _ in range(3):
            cycle.advance(gana="gana_ox", tool="test", coherence=0.95)

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = handle_wm(route="gana_ox.swarm_decompose")

            assert "_coherence_caution" not in result

        cycle.reset()

    def test_safe_gana_no_caution_even_low_coherence(self):
        """Safe ganas (ghost, neck, etc.) never get cautioned even at low coherence."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()

        for _ in range(3):
            cycle.advance(gana="gana_ox", tool="test", coherence=0.3)

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = handle_wm(route="gana_ghost.gnosis")

            assert "_coherence_caution" not in result

        cycle.reset()

    def test_short_stream_no_caution(self):
        """With < 3 stream entries, no caution even at low coherence."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()

        cycle.advance(gana="gana_ox", tool="test", coherence=0.2)

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = handle_wm(route="gana_ox.swarm_decompose")

            assert "_coherence_caution" not in result

        cycle.reset()


class TestCoherenceAutoMeasure:
    """Test coherence auto-measure — drift tracking and governor integration."""

    def test_sensorium_has_coherence_trend(self):
        """Sensorium includes cross-session coherence trend when available."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        from whitemagic.core.consciousness.coherence import get_coherence_metric

        get_citta_cycle().reset()
        metric = get_coherence_metric()
        metric.history = [
            {"timestamp": "2026-01-01T00:00:00", "overall": 0.5, "scores": {}},
            {"timestamp": "2026-01-02T00:00:00", "overall": 0.7, "scores": {}},
            {"timestamp": "2026-01-03T00:00:00", "overall": 0.8, "scores": {}},
        ]

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = handle_wm(thought="remember coherence trend tracking")

            s = result["_sensorium"]
            if "coherence_trend" in s:
                assert s["coherence_trend"] in ("improving", "degrading", "stable")

    def test_governor_coherence_strictness_low_coherence(self):
        """Governor returns high strictness when coherence is low."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        from whitemagic.core.governor import Governor

        cycle = get_citta_cycle()
        cycle.reset()

        for _ in range(5):
            cycle.advance(gana="gana_ox", tool="test", coherence=0.2)

        gov = Governor()
        strictness = gov._get_coherence_strictness()
        assert strictness >= 0.8

        cycle.reset()

    def test_governor_coherence_strictness_high_coherence(self):
        """Governor returns low strictness when coherence is high."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        from whitemagic.core.governor import Governor

        cycle = get_citta_cycle()
        cycle.reset()

        for _ in range(5):
            cycle.advance(gana="gana_ox", tool="test", coherence=0.95)

        gov = Governor()
        strictness = gov._get_coherence_strictness()
        assert strictness == 0.0

        cycle.reset()

    def test_governor_coherence_strictness_short_stream(self):
        """Governor returns 0 strictness with insufficient stream history."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        from whitemagic.core.governor import Governor

        cycle = get_citta_cycle()
        cycle.reset()

        cycle.advance(gana="gana_ox", tool="test", coherence=0.1)

        gov = Governor()
        strictness = gov._get_coherence_strictness()
        assert strictness == 0.0

        cycle.reset()
