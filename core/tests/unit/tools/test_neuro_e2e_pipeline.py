"""End-to-end pipeline tests for neuro-cognitive MCP tools.

Tests the full round-trip: NLU classify → dispatch lookup → handler execution → result validation.
This verifies that the wiring is correct from the agent's perspective — an agent saying
"compute neuromodulator levels" should get a successful result with modulator data.
"""

import os
import tempfile

import pytest

os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_e2e_"))


def _full_pipeline(phrase: str) -> tuple[str, str | None, float, dict]:
    """Run the full classify → dispatch → handler pipeline and return (gana, tool, conf, result)."""
    from whitemagic.tools.handlers.meta_tool import classify
    from whitemagic.tools.dispatch_table import DISPATCH_TABLE

    gana, tool, conf = classify(phrase)
    assert tool is not None, f"NLU classify returned no tool for '{phrase}'"
    assert tool in DISPATCH_TABLE, f"Tool '{tool}' not in dispatch table"

    handler = DISPATCH_TABLE[tool]
    result = handler()
    return gana, tool, conf, result


class TestStatsPipeline:
    """Test stats endpoints through direct dispatch (programmatic, not NLU)."""

    @pytest.mark.parametrize(
        "tool_name",
        [
            "ripple.stats",
            "replay.stats",
            "neuro.stats",
            "metaplasticity.stats",
            "workspace.stats",
            "sensorium.stats",
        ],
    )
    def test_stats_direct_dispatch(self, tool_name):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        assert tool_name in DISPATCH_TABLE, f"{tool_name} not in dispatch table"
        handler = DISPATCH_TABLE[tool_name]
        result = handler()
        assert result["status"] == "success"


class TestSensoriumPipeline:
    """Test sensorium endpoints through the full pipeline."""

    def test_sensorium_state_full_pipeline(self):
        gana, tool, conf, result = _full_pipeline("sensorium state")
        assert tool == "sensorium.state"
        assert gana == "gana_ghost"
        assert result["status"] == "success"
        assert "signals" in result

    def test_sensorium_citta_full_pipeline(self):
        gana, tool, conf, result = _full_pipeline("citta enrichment")
        assert tool == "sensorium.citta"
        assert gana == "gana_ghost"
        assert result["status"] == "success"
        assert "enrichment" in result


class TestNeuroComputePipeline:
    """Test neuromodulation compute through the full pipeline."""

    def test_neuro_compute_with_args(self):
        from whitemagic.tools.handlers.meta_tool import classify
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        gana, tool, conf = classify("compute neuromodulator levels")
        assert tool == "neuro.compute"
        assert gana == "gana_dipper"
        assert conf == 1.0

        handler = DISPATCH_TABLE[tool]
        result = handler(novelty=0.9, reward=0.7, stability=0.4, coherence=0.6, focus=0.8, activity_level=0.5)
        assert result["status"] == "success"
        # Should have modulator values
        assert any(k in result for k in ("da", "dopamine", "sht", "serotonin", "ach", "acetylcholine"))


class TestWorkspacePipeline:
    """Test global workspace through the full pipeline."""

    def test_workspace_propose_full_pipeline(self):
        from whitemagic.tools.handlers.meta_tool import classify
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        gana, tool, conf = classify("global workspace propose")
        assert tool == "workspace.propose"
        assert gana == "gana_three_stars"

        handler = DISPATCH_TABLE[tool]
        result = handler(source="test_module", content={"msg": "hello world"}, salience=0.95)
        assert result["status"] == "success"
        assert "broadcast" in result

    def test_workspace_state_full_pipeline(self):
        gana, tool, conf, result = _full_pipeline("workspace state")
        assert tool == "workspace.state"
        assert gana == "gana_three_stars"
        assert result["status"] == "success"


class TestMetaplasticityPipeline:
    """Test metaplasticity through the full pipeline."""

    def test_metaplasticity_apply_full_pipeline(self):
        from whitemagic.tools.handlers.meta_tool import classify
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        gana, tool, conf = classify("apply metaplasticity gating")
        assert tool == "metaplasticity.apply"
        assert gana == "gana_extended_net"

        handler = DISPATCH_TABLE[tool]
        result = handler(memory_id="test-e2e-mem", delta=0.15)
        assert result["status"] == "success"

    def test_metaplasticity_plasticity_full_pipeline(self):
        from whitemagic.tools.handlers.meta_tool import classify
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        gana, tool, conf = classify("metaplasticity plasticity score")
        assert tool == "metaplasticity.plasticity"
        assert gana == "gana_extended_net"

        handler = DISPATCH_TABLE[tool]
        result = handler(memory_id="test-e2e-mem")
        assert result["status"] == "success"
        assert "plasticity_score" in result
        assert "threshold" in result


class TestRipplePipeline:
    """Test ripple tagging through the full pipeline."""

    def test_ripple_tag_full_pipeline(self):
        from whitemagic.tools.handlers.meta_tool import classify
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        gana, tool, conf = classify("ripple tag these memories")
        assert tool == "ripple.tag"
        assert gana == "gana_abundance"

        handler = DISPATCH_TABLE[tool]
        result = handler(memory_ids=["e2e-mem-1", "e2e-mem-2"], emotional_weight=0.8)
        assert result["status"] == "success"


class TestReplayPipeline:
    """Test replay simulation through the full pipeline."""

    def test_replay_run_full_pipeline(self):
        from whitemagic.tools.handlers.meta_tool import classify
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        gana, tool, conf = classify("replay memory sequence")
        assert tool == "replay.run"
        assert gana == "gana_abundance"

        handler = DISPATCH_TABLE[tool]
        result = handler(sequence=[
            {"memory_id": "r-1", "timestamp": 0.0, "importance": 0.8},
            {"memory_id": "r-2", "timestamp": 1.0, "importance": 0.6},
            {"memory_id": "r-3", "timestamp": 2.0, "importance": 0.9},
        ])
        assert result["status"] == "success"


class TestRegistryDiscovery:
    """Verify neuro tools appear in the tool catalog with proper descriptions."""

    def test_neuro_tools_in_catalog(self):
        from whitemagic.tools.registry_defs import collect
        from whitemagic.tools.tool_catalog import synthesize_callable_tool_definitions

        authored = collect()
        defs = synthesize_callable_tool_definitions(authored)
        neuro_names = {d.name for d in defs if any(k in d.name for k in ['ripple.', 'replay.', 'neuro.', 'metaplasticity.', 'workspace.', 'sensorium.'])}
        assert len(neuro_names) == 23

        # None should be stubs
        stubs = [d for d in defs if d.name in neuro_names and d.description.startswith("Dispatch-routable")]
        assert len(stubs) == 0, f"Stub definitions found: {[s.name for s in stubs]}"

    def test_neuro_tools_have_input_schemas(self):
        from whitemagic.tools.registry_defs import collect

        authored = collect()
        neuro_tools = [t for t in authored if any(k in t.name for k in ['ripple.', 'replay.', 'neuro.', 'metaplasticity.', 'workspace.', 'sensorium.'])]
        assert len(neuro_tools) == 23
        for tool in neuro_tools:
            assert tool.input_schema is not None
            assert "properties" in tool.input_schema
            assert tool.description and len(tool.description) > 20


class TestCittaPersistenceWithNeuro:
    """Verify citta stream persistence works with neuro_signals field."""

    def test_persist_and_load_with_neuro_signals(self, tmp_path):
        import json
        from whitemagic.core.consciousness.citta_cycle import CittaMoment

        moment = CittaMoment(
            gana="gana_ghost",
            tool="sensorium.state",
            operation="read",
            output_preview="test",
            timestamp=12345.0,
            coherence=0.85,
            depth_layer="flow",
            emotional_tone="curious",
            chain_position=42,
            duration_ms=15.3,
            neuro_signals={"novelty": 0.7, "emotional_attunement": 0.6},
        )
        data = moment.to_dict()
        assert "neuro_signals" in data
        assert data["neuro_signals"]["novelty"] == 0.7

        # Round-trip through JSON
        line = json.dumps(data)
        loaded = json.loads(line)
        restored = CittaMoment(**loaded)
        assert restored.neuro_signals is not None
        assert restored.neuro_signals["novelty"] == 0.7

    def test_load_old_stream_without_neuro_signals(self):
        """Old persisted moments without neuro_signals should load fine (defaults to None)."""
        import json
        from whitemagic.core.consciousness.citta_cycle import CittaMoment

        old_data = {
            "gana": "gana_ghost",
            "tool": "gnosis",
            "operation": None,
            "output_preview": "old moment",
            "timestamp": 10000.0,
            "coherence": 0.5,
            "depth_layer": "surface",
            "emotional_tone": "neutral",
            "chain_position": 1,
            "duration_ms": 5.0,
        }
        moment = CittaMoment(**old_data)
        assert moment.neuro_signals is None  # Default value
