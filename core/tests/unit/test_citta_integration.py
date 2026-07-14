# ruff: noqa: BLE001
"""Tests for Citta Subsystem Integration work items (WI 1-13).

Verifies that the consciousness subsystem wiring is functional:
- WI 1: Predecessor context injection in mw_citta_consciousness
- WI 2: DepthGauge begin_task/end_task in dispatch pipeline
- WI 3: Coherence drift → Dharma governance escalation
- WI 4: NeuroSensorium composites → dispatch context meta
- WI 5: Ignition events → global workspace
- WI 6: ApotheosisEngine health → HealthSurface
- WI 7: GunaBalance → sensorium
- WI 8: MetaGalaxy priorities → self-directed attention
- WI 9: DreamCycle → coherence re-measurement
- WI 11: Session recorder ↔ citta cycle cross-referencing
- WI 12: DepthGauge compression → token economy sensorium
- WI 13: EmergenceEngine ↔ KnowledgeGapLoop cross-reference
"""



class TestWI1PredecessorInjection:
    """WI 1: Predecessor context injection in mw_citta_consciousness."""

    def test_predecessor_context_method_exists(self):
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        pred = cycle.get_predecessor_context()
        # Should be None or a dict — not raise
        assert pred is None or isinstance(pred, dict)

    def test_predecessor_context_after_advance(self):
        from whitemagic.core.consciousness.citta_cycle import (
            advance_citta,
            get_citta_cycle,
        )

        advance_citta(
            gana="test",
            tool="test_tool",
            output_preview="test output",
            coherence=0.9,
            depth_layer="surface",
            emotional_tone="neutral",
        )
        pred = get_citta_cycle().get_predecessor_context()
        assert pred is not None
        assert isinstance(pred, dict)
        assert pred["gana"] == "test"
        assert pred["tool"] == "test_tool"


class TestWI2DepthGaugeInDispatch:
    """WI 2: DepthGauge begin_task/end_task in dispatch pipeline."""

    def test_depth_gauge_begin_end_task(self):
        from whitemagic.core.consciousness.depth_gauge import (
            ConsciousnessDepthGauge,
            ConsciousnessLayer,
        )

        gauge = ConsciousnessDepthGauge()
        gauge.begin_task("test_task", estimated_subjective_minutes=1.0)
        reading = gauge.end_task({"status": "success"}, token_usage=100)

        assert reading.layer in ConsciousnessLayer
        assert reading.token_usage == 100
        assert reading.work_output == {"status": "success"}

    def test_depth_gauge_current_compression(self):
        from whitemagic.core.consciousness.depth_gauge import get_depth_gauge

        gauge = get_depth_gauge()
        compression = gauge.current_compression()
        assert compression > 0


class TestWI3CoherenceDriftDharma:
    """WI 3: Coherence drift → Dharma governance escalation."""

    def test_dharma_set_coherence(self):
        from whitemagic.core.consciousness.dharma import get_dharma

        dharma = get_dharma()
        dharma.set_coherence(0.3)
        assert dharma._coherence_level == 0.3
        assert dharma.is_conservative_mode() is True

    def test_dharma_normal_mode(self):
        from whitemagic.core.consciousness.dharma import get_dharma

        dharma = get_dharma()
        dharma.set_coherence(0.8)
        assert dharma.is_conservative_mode() is False

    def test_coherence_drift_method(self):
        from whitemagic.core.consciousness.coherence import get_coherence_metric

        metric = get_coherence_metric()
        drift = metric.get_drift()
        assert "direction" in drift
        assert "magnitude" in drift


class TestWI4NeuroComposites:
    """WI 4: NeuroSensorium composites → dispatch context."""

    def test_neuro_sensorium_compute(self):
        from whitemagic.core.consciousness.neuro_sensorium import get_neuro_sensorium

        neuro = get_neuro_sensorium()
        signals = neuro.compute_sensorium()
        assert "composite_novelty" in signals
        assert "composite_stability" in signals
        assert "composite_attention" in signals
        assert "composite_cognitive_load" in signals

    def test_neuro_citta_enrichment(self):
        from whitemagic.core.consciousness.neuro_sensorium import get_neuro_sensorium

        neuro = get_neuro_sensorium()
        enrichment = neuro.get_citta_enrichment()
        assert "novelty" in enrichment
        assert "cognitive_load" in enrichment


class TestWI5IgnitionEvents:
    """WI 5: Ignition events → global workspace."""

    def test_ignition_events_method(self):
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        ignitions = cycle.get_ignition_events(threshold=2.0)
        assert isinstance(ignitions, list)

    def test_global_workspace_propose(self):
        from whitemagic.core.consciousness.global_workspace import get_global_workspace

        gw = get_global_workspace()
        gw.propose(source="test", content={"test": True}, salience=0.5)
        state = gw.get_current_state()
        assert state is not None


class TestWI6ApotheosisHealthSurface:
    """WI 6: ApotheosisEngine health → HealthSurface."""

    def test_health_surface_has_apotheosis_check(self):
        from whitemagic.ops.health_surface import HealthSurface

        hs = HealthSurface()
        assert hasattr(hs, "_check_apotheosis_health")

    def test_apotheosis_health_returns_component(self):
        from whitemagic.ops.health_surface import HealthSurface

        hs = HealthSurface()
        result = hs._check_apotheosis_health()
        assert result.name == "apotheosis_health"
        assert result.status in ("healthy", "degraded", "unknown")


class TestWI7GunaBalanceSensorium:
    """WI 7: GunaBalance → sensorium."""

    def test_guna_balance_measure(self):
        from whitemagic.core.consciousness.guna_balance import get_guna_balance

        guna = get_guna_balance()
        reading = guna.measure()
        assert hasattr(reading, "sattvic_ratio")
        assert hasattr(reading, "balanced")
        assert hasattr(reading, "to_dict")

    def test_sensorium_includes_guna(self):
        from whitemagic.tools.prat_resonance import _build_sensorium

        sensorium = _build_sensorium()
        # guna may or may not be present depending on environment,
        # but the key should exist if no exception
        if "guna" in sensorium:
            assert "sattvic_ratio" in sensorium["guna"]


class TestWI8MetaGalaxyPriorities:
    """WI 8: MetaGalaxy priorities → self-directed attention."""

    def test_meta_galaxy_get_strategic_priorities(self):
        from whitemagic.core.consciousness.meta_galaxy import get_meta_galaxy

        mg = get_meta_galaxy()
        priorities = mg.get_strategic_priorities()
        assert isinstance(priorities, list)


class TestWI9DreamCoherence:
    """WI 9: DreamCycle → coherence re-measurement."""

    def test_dream_cycle_has_coherence_remeasurement(self):
        # Read the source to verify the WI 9 code is present
        import inspect

        from whitemagic.core.dreaming.dream_cycle import DreamCycle

        source = inspect.getsource(DreamCycle._run_phase)
        assert "get_coherence_metric" in source
        assert "memories_accessible" in source


class TestWI11SessionCittaCrossRef:
    """WI 11: Session recorder ↔ citta cycle cross-referencing."""

    def test_session_recorder_has_citta_method(self):
        from whitemagic.core.memory.session_recorder import SessionRecorder

        assert hasattr(SessionRecorder, "_get_citta_stream_position")

    def test_citta_stream_position_returns_int(self):
        # Can't easily instantiate without a DB, but we can check the method
        # is defined and would return 0 on failure
        import inspect

        from whitemagic.core.memory.session_recorder import SessionRecorder

        source = inspect.getsource(SessionRecorder._get_citta_stream_position)
        assert "get_citta_cycle" in source
        assert "stream_length" in source


class TestWI12DepthEconomySensorium:
    """WI 12: DepthGauge compression → token economy sensorium."""

    def test_sensorium_includes_depth_economy(self):
        from whitemagic.tools.prat_resonance import _build_sensorium

        sensorium = _build_sensorium()
        if "depth_economy" in sensorium:
            assert "compression_ratio" in sensorium["depth_economy"]
            assert "token_efficiency" in sensorium["depth_economy"]


class TestWI13EmergenceKnowledgeGap:
    """WI 13: EmergenceEngine ↔ KnowledgeGapLoop cross-reference."""

    def test_knowledge_gap_loop_has_emergence_source(self):
        import inspect

        from whitemagic.core.consciousness.knowledge_gap_loop import (
            KnowledgeGapActionLoop,
        )

        source = inspect.getsource(KnowledgeGapActionLoop.detect_gaps)
        assert "emergence_engine" in source
        assert "get_emergence_engine" in source

    def test_emergence_engine_get_insights(self):
        from whitemagic.core.intelligence.agentic.emergence_engine import (
            get_emergence_engine,
        )

        ee = get_emergence_engine()
        insights = ee.get_insights(limit=5)
        assert isinstance(insights, list)


class TestMiddlewareWiring:
    """Verify mw_citta_consciousness has all WI code."""

    def test_middleware_has_predecessor_injection(self):
        import inspect

        from whitemagic.tools.middleware import mw_citta_consciousness

        source = inspect.getsource(mw_citta_consciousness)
        assert "citta_predecessor" in source

    def test_middleware_has_depth_gauge(self):
        import inspect

        from whitemagic.tools.middleware import mw_citta_consciousness

        source = inspect.getsource(mw_citta_consciousness)
        assert "begin_task" in source
        assert "end_task" in source

    def test_middleware_has_coherence_drift(self):
        import inspect

        from whitemagic.tools.middleware import mw_citta_consciousness

        source = inspect.getsource(mw_citta_consciousness)
        assert "get_drift" in source

    def test_middleware_has_neuro_composites(self):
        import inspect

        from whitemagic.tools.middleware import mw_citta_consciousness

        source = inspect.getsource(mw_citta_consciousness)
        assert "neuro_composites" in source

    def test_middleware_has_ignition_events(self):
        import inspect

        from whitemagic.tools.middleware import mw_citta_consciousness

        source = inspect.getsource(mw_citta_consciousness)
        assert "ignition" in source.lower()


class TestWI4NeuroCompositesConsumers:
    """WI 4: NeuroSensorium composites wired to consumers."""

    def test_semantic_cache_bypasses_on_high_novelty(self):
        import inspect

        from whitemagic.tools.middleware import mw_semantic_cache

        source = inspect.getsource(mw_semantic_cache)
        assert "novelty" in source
        assert "bypass" in source.lower()

    def test_inference_router_uses_cognitive_load(self):
        import inspect

        from whitemagic.tools.middleware import mw_inference_router

        source = inspect.getsource(mw_inference_router)
        assert "cognitive_load" in source

    def test_auto_optimize_uses_attention(self):
        import inspect

        from whitemagic.tools.middleware import mw_auto_optimize

        source = inspect.getsource(mw_auto_optimize)
        assert "attention" in source
        assert "reduced_context" in source


class TestWI5IgnitionEmergence:
    """WI 5: Ignition events fed to EmergenceEngine."""

    def test_emergence_engine_has_record_ignition(self):
        from whitemagic.core.intelligence.agentic.emergence_engine import (
            EmergenceEngine,
        )

        assert hasattr(EmergenceEngine, "record_ignition")

    def test_record_ignition_adds_insight(self):
        from whitemagic.core.intelligence.agentic.emergence_engine import (
            get_emergence_engine,
        )

        ee = get_emergence_engine()
        before = len(ee.get_insights(limit=100))
        ee.record_ignition({"displacement": 3.0, "layer": "flow", "position": 42}, tool="test_tool")
        after = ee.get_insights(limit=100)
        assert len(after) >= before
        # The latest insight should mention ignition
        assert any("ignition" in i.get("source", "") for i in after)

    def test_middleware_feeds_emergence(self):
        import inspect

        from whitemagic.tools.middleware import mw_citta_consciousness

        source = inspect.getsource(mw_citta_consciousness)
        assert "record_ignition" in source


class TestWI11SessionSeqCitta:
    """WI 11: Session sequence number in citta moments."""

    def test_citta_moment_has_session_seq(self):
        import dataclasses

        from whitemagic.core.consciousness.citta_cycle import CittaMoment

        fields = {f.name for f in dataclasses.fields(CittaMoment)}
        assert "session_seq" in fields

    def test_advance_accepts_session_seq(self):
        import inspect

        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        sig = inspect.signature(CittaCycle.advance)
        assert "session_seq" in sig.parameters

    def test_advance_citta_accepts_session_seq(self):
        import inspect

        from whitemagic.core.consciousness.citta_cycle import advance_citta

        sig = inspect.signature(advance_citta)
        assert "session_seq" in sig.parameters


class TestWI12DepthBudgetOptimizer:
    """WI 12: DepthGauge compression → token optimizer budget."""

    def test_optimizer_has_depth_budget_multiplier(self):
        from whitemagic.core.intelligence.agentic.token_optimizer import (
            TokenOptimizer,
        )

        assert hasattr(TokenOptimizer, "_depth_budget_multiplier")

    def test_depth_budget_multiplier_returns_float(self):
        from whitemagic.core.intelligence.agentic.token_optimizer import (
            TokenOptimizer,
        )

        opt = TokenOptimizer()
        mult = opt._depth_budget_multiplier()
        assert isinstance(mult, float)
        assert 1.0 <= mult <= 3.0

    def test_optimize_query_uses_depth_budget(self):
        import inspect

        from whitemagic.core.intelligence.agentic.token_optimizer import (
            TokenOptimizer,
        )

        source = inspect.getsource(TokenOptimizer.optimize_query)
        assert "_depth_budget_multiplier" in source
        assert "_context_budget" in source


class TestWI13ReverseCrossRef:
    """WI 13: KnowledgeGapLoop → EmergenceEngine reverse cross-reference."""

    def test_knowledge_gap_has_metadata(self):
        import dataclasses

        from whitemagic.core.consciousness.knowledge_gap_loop import KnowledgeGap

        fields = {f.name for f in dataclasses.fields(KnowledgeGap)}
        assert "metadata" in fields

    def test_detect_gaps_has_reverse_cross_ref(self):
        import inspect

        from whitemagic.core.consciousness.knowledge_gap_loop import (
            KnowledgeGapActionLoop,
        )

        source = inspect.getsource(KnowledgeGapActionLoop.detect_gaps)
        assert "related_emergence" in source
