"""Unit tests for neuro-cognitive MCP handler wiring and integration.

Tests that the 6 new neuro systems are properly wired into:
- MCP dispatch table
- PRAT Gana mappings
- NLU routing patterns
- PRAT sensorium (neuro_cognitive field)
- Citta cycle (neuro_signals auto-injection)
- Sleep consolidation (replay + metaplasticity + ripple decay)
"""

import os
import tempfile

import pytest

os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_neuro_mcp_"))


class TestDispatchEntries:
    """Verify all 23 new dispatch entries exist."""

    def test_ripple_dispatch_entries(self):
        from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY

        for tool in ["ripple.tag", "ripple.tags", "ripple.decay", "ripple.stats"]:
            assert tool in DISPATCH_MEMORY, f"{tool} missing from dispatch"

    def test_replay_dispatch_entries(self):
        from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY

        for tool in ["replay.run", "replay.batch", "replay.stats"]:
            assert tool in DISPATCH_MEMORY, f"{tool} missing from dispatch"

    def test_neuro_dispatch_entries(self):
        from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY

        for tool in ["neuro.compute", "neuro.modulate", "neuro.reset", "neuro.stats"]:
            assert tool in DISPATCH_MEMORY, f"{tool} missing from dispatch"

    def test_metaplasticity_dispatch_entries(self):
        from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY

        for tool in [
            "metaplasticity.apply",
            "metaplasticity.batch",
            "metaplasticity.plasticity",
            "metaplasticity.decay",
            "metaplasticity.stats",
        ]:
            assert tool in DISPATCH_MEMORY, f"{tool} missing from dispatch"

    def test_workspace_dispatch_entries(self):
        from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY

        for tool in ["workspace.propose", "workspace.state", "workspace.history", "workspace.stats"]:
            assert tool in DISPATCH_MEMORY, f"{tool} missing from dispatch"

    def test_sensorium_dispatch_entries(self):
        from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY

        for tool in ["sensorium.state", "sensorium.citta", "sensorium.stats"]:
            assert tool in DISPATCH_MEMORY, f"{tool} missing from dispatch"


class TestPratMappings:
    """Verify all 23 new PRAT Gana mappings."""

    def test_ripple_prat_mappings(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA

        for tool in ["ripple.tag", "ripple.tags", "ripple.decay", "ripple.stats"]:
            assert tool in TOOL_TO_GANA, f"{tool} missing from PRAT mappings"
            assert TOOL_TO_GANA[tool] == "gana_abundance"

    def test_replay_prat_mappings(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA

        for tool in ["replay.run", "replay.batch", "replay.stats"]:
            assert TOOL_TO_GANA[tool] == "gana_abundance"

    def test_neuro_prat_mappings(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA

        for tool in ["neuro.compute", "neuro.modulate", "neuro.reset", "neuro.stats"]:
            assert TOOL_TO_GANA[tool] == "gana_dipper"

    def test_metaplasticity_prat_mappings(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA

        for tool in ["metaplasticity.apply", "metaplasticity.batch", "metaplasticity.plasticity",
                      "metaplasticity.decay", "metaplasticity.stats"]:
            assert TOOL_TO_GANA[tool] == "gana_extended_net"

    def test_workspace_prat_mappings(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA

        for tool in ["workspace.propose", "workspace.state", "workspace.history", "workspace.stats"]:
            assert TOOL_TO_GANA[tool] == "gana_three_stars"

    def test_sensorium_prat_mappings(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA

        for tool in ["sensorium.state", "sensorium.citta", "sensorium.stats"]:
            assert TOOL_TO_GANA[tool] == "gana_ghost"


class TestNLURouting:
    """Verify NLU routing patterns for neuro-cognitive tools."""

    @pytest.mark.parametrize(
        "phrase,expected_tool",
        [
            ("ripple tag these memories", "ripple.tag"),
            ("ripple stats", "ripple.stats"),
            ("replay memory sequence", "replay.run"),
            ("compute neuromodulator levels", "neuro.compute"),
            ("modulate memories with neuromodulators", "neuro.modulate"),
            ("metaplasticity plasticity score", "metaplasticity.plasticity"),
            ("apply metaplasticity gating", "metaplasticity.apply"),
            ("global workspace propose", "workspace.propose"),
            ("workspace state", "workspace.state"),
            ("sensorium state", "sensorium.state"),
            ("citta enrichment", "sensorium.citta"),
        ],
    )
    def test_nlu_classification(self, phrase, expected_tool):
        from whitemagic.tools.handlers.meta_tool import classify

        gana, tool, conf = classify(phrase)
        assert tool == expected_tool, f"Expected {expected_tool}, got {tool} for '{phrase}'"
        assert conf > 0.0


class TestPratSensoriumIntegration:
    """Verify neuro-cognitive signals are in the PRAT sensorium."""

    def test_sensorium_has_neuro_cognitive(self):
        from whitemagic.tools.prat_resonance import _build_sensorium

        sensorium = _build_sensorium()
        assert "neuro_cognitive" in sensorium, "neuro_cognitive missing from sensorium"
        neuro = sensorium["neuro_cognitive"]
        for key in ["novelty", "stability", "attention", "cognitive_load",
                     "emotional_attunement", "memory_accessibility", "temporal_orientation"]:
            assert key in neuro, f"{key} missing from neuro_cognitive sensorium"


class TestCittaCycleNeuroIntegration:
    """Verify citta cycle auto-injects neuro signals."""

    def test_citta_moment_has_neuro_signals(self):
        from whitemagic.core.consciousness.citta_cycle import advance_citta, get_citta_predecessor

        advance_citta(gana="gana_ghost", tool="test", coherence=0.9)
        pred = get_citta_predecessor()
        assert pred is not None
        assert "neuro_signals" in pred
        assert pred["neuro_signals"] is not None
        # Should have citta enrichment keys
        assert "emotional_attunement" in pred["neuro_signals"]
        assert "memory_accessibility" in pred["neuro_signals"]


class TestSleepConsolidationNeuroIntegration:
    """Verify sleep consolidation has replay + metaplasticity + ripple decay."""

    def test_report_has_neuro_fields(self):
        from whitemagic.core.memory.sleep_consolidation import ConsolidationReport

        report = ConsolidationReport()
        d = report.to_dict()
        assert "replayed" in d
        assert "ripples_decayed" in d
        assert "metaplasticity_updated" in d

    def test_replay_method_exists(self):
        from whitemagic.core.memory.sleep_consolidation import SleepConsolidation

        consol = SleepConsolidation()
        assert hasattr(consol, "_replay_transferred_memories")
        assert hasattr(consol, "_metaplasticity_sleep_cycle")
        assert hasattr(consol, "_decay_ripple_tags")


class TestHandlerExecution:
    """Verify handlers can be called and return success."""

    def test_neuro_compute_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_neuro_compute

        result = handle_neuro_compute(novelty=0.8, reward=0.6, stability=0.5)
        assert result["status"] == "success"
        assert "da" in result or "dopamine" in result

    def test_neuro_stats_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_neuro_stats

        result = handle_neuro_stats()
        assert result["status"] == "success"

    def test_ripple_stats_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_ripple_stats

        result = handle_ripple_stats()
        assert result["status"] == "success"

    def test_replay_stats_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_replay_stats

        result = handle_replay_stats()
        assert result["status"] == "success"

    def test_metaplasticity_stats_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_metaplasticity_stats

        result = handle_metaplasticity_stats()
        assert result["status"] == "success"

    def test_workspace_stats_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_workspace_stats

        result = handle_workspace_stats()
        assert result["status"] == "success"

    def test_sensorium_state_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_sensorium_state

        result = handle_sensorium_state()
        assert result["status"] == "success"
        assert "signals" in result

    def test_sensorium_citta_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_sensorium_citta

        result = handle_sensorium_citta()
        assert result["status"] == "success"
        assert "enrichment" in result

    def test_workspace_propose_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_workspace_propose

        result = handle_workspace_propose(source="test", content={"msg": "hello"}, salience=0.9)
        assert result["status"] == "success"

    def test_ripple_tag_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_ripple_tag

        result = handle_ripple_tag(memory_ids=["mem-1", "mem-2"], emotional_weight=0.8)
        assert result["status"] == "success"

    def test_metaplasticity_apply_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_metaplasticity_apply

        result = handle_metaplasticity_apply(memory_id="test-mem", delta=0.1)
        assert result["status"] == "success"

    def test_metaplasticity_plasticity_handler(self):
        from whitemagic.tools.handlers.neuro_cognitive import handle_metaplasticity_plasticity

        result = handle_metaplasticity_plasticity(memory_id="test-mem")
        assert result["status"] == "success"
        assert "plasticity_score" in result
