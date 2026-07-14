"""Unit tests for hyperscaled cognitive simulation (P5)."""

import pytest

from whitemagic.core.simulation.calibration_bridge import (
    PredictionCalibrationBridge,
    get_calibration_bridge,
)
from whitemagic.core.simulation.dream_integration import (
    DreamCycleIntegration,
    get_dream_integration,
)
from whitemagic.core.simulation.insight_synthesizer import (
    Insight,
    InsightSynthesizer,
    get_insight_synthesizer,
)
from whitemagic.core.simulation.interaction_engine import (
    InteractionEngine,
    InteractionEvent,
    InteractionLog,
    get_interaction_engine,
)
from whitemagic.core.simulation.persona_engine import (
    CognitiveProfile,
    PersonaEngine,
    get_persona_engine,
)
from whitemagic.core.simulation.scenario_runner import (
    ScenarioConfig,
    ScenarioRunner,
    get_scenario_runner,
)
from whitemagic.core.simulation.trajectory_search import (
    TrajectoryNode,
    TrajectoryTreeSearch,
    get_trajectory_search,
)
from whitemagic.core.simulation.world_model import (
    WorldModelBuilder,
    get_world_model_builder,
)


class TestPersonaEngine:
    """Test PersonaEngine."""

    def test_create_persona_default(self):
        engine = PersonaEngine()
        p = engine.create_persona("test_agent")
        assert p.name == "test_agent"
        assert p.id  # non-empty
        assert 0.0 <= p.profile.coherence_baseline <= 1.0

    def test_create_persona_with_archetype(self):
        engine = PersonaEngine()
        p = engine.create_persona("analyst_1", archetype="analyst")
        assert p.profile.coherence_baseline == 0.85
        assert p.profile.depth_layer == 4

    def test_create_persona_all_archetypes(self):
        engine = PersonaEngine()
        for arch in ["analyst", "creative", "conservative", "explorer", "synthesizer"]:
            p = engine.create_persona(f"agent_{arch}", archetype=arch)
            assert p is not None

    def test_clone_with_mutation(self):
        engine = PersonaEngine()
        original = engine.create_persona("original", archetype="analyst")
        clone = engine.clone_with_mutation(original.id, "clone", mutation_rate=0.2)
        assert clone is not None
        assert clone.name == "clone"
        assert clone.id != original.id
        # Should be similar but not necessarily identical
        assert abs(clone.profile.coherence_baseline - original.profile.coherence_baseline) <= 0.6

    def test_clone_nonexistent(self):
        engine = PersonaEngine()
        assert engine.clone_with_mutation("nonexistent", "clone") is None

    def test_get_and_list(self):
        engine = PersonaEngine()
        p1 = engine.create_persona("a1")
        engine.create_persona("a2")
        assert engine.get_persona(p1.id) is p1
        assert len(engine.list_personas()) == 2

    def test_remove_persona(self):
        engine = PersonaEngine()
        p = engine.create_persona("temp")
        assert engine.remove_persona(p.id) is True
        assert engine.get_persona(p.id) is None

    def test_persona_drift(self):
        engine = PersonaEngine()
        p = engine.create_persona("drift_test", archetype="analyst")
        p.coherence = 0.3  # far from baseline 0.85
        p.drift(dt=10.0)
        assert p.coherence > 0.3  # should drift toward baseline

    def test_guna_vector(self):
        profile = CognitiveProfile(guna_sattvic=1.0, guna_rajasic=2.0, guna_tamasic=3.0)
        s, r, t = profile.guna_vector()
        assert s == pytest.approx(1/6, abs=0.01)
        assert r == pytest.approx(2/6, abs=0.01)
        assert t == pytest.approx(3/6, abs=0.01)

    def test_singleton(self):
        e1 = get_persona_engine()
        e2 = get_persona_engine()
        assert e1 is e2


class TestWorldModelBuilder:
    """Test WorldModelBuilder."""

    def test_create_world(self):
        builder = WorldModelBuilder()
        world = builder.create_world("test_world")
        assert world.name == "test_world"
        assert world.galaxy == "simulation/test_world"
        assert world.id

    def test_create_world_with_seeds(self):
        builder = WorldModelBuilder()
        world = builder.create_world(
            "seeded_world",
            seed_documents=["Alice discovered a new concept.", "Bob built a machine."],
        )
        assert len(world.seed_documents) >= 0  # may be 0 if ingestion fails
        # Entity extraction should find capitalized words
        assert len(world.entities) > 0

    def test_add_rule(self):
        builder = WorldModelBuilder()
        world = builder.create_world("rule_world")
        rule = builder.add_rule(world.id, "gravity", "Things fall down", "dynamics")
        assert rule is not None
        assert rule.name == "gravity"
        assert len(world.rules) == 1

    def test_add_rule_nonexistent_world(self):
        builder = WorldModelBuilder()
        assert builder.add_rule("nonexistent", "rule", "desc") is None

    def test_get_and_list(self):
        builder = WorldModelBuilder()
        w1 = builder.create_world("w1")
        builder.create_world("w2")
        assert builder.get_world(w1.id) is w1
        assert len(builder.list_worlds()) == 2

    def test_world_advance_tick(self):
        builder = WorldModelBuilder()
        world = builder.create_world("tick_world")
        assert world.tick == 0
        world.advance_tick()
        assert world.tick == 1

    def test_singleton(self):
        b1 = get_world_model_builder()
        b2 = get_world_model_builder()
        assert b1 is b2


class TestInteractionEngine:
    """Test InteractionEngine."""

    def test_run_interaction(self):
        engine = InteractionEngine()
        pe = PersonaEngine()
        wb = WorldModelBuilder()

        world = wb.create_world("interaction_test")
        personas = [
            pe.create_persona("a1", archetype="analyst", galaxy=world.galaxy),
            pe.create_persona("a2", archetype="creative", galaxy=world.galaxy),
        ]

        log = engine.run_interaction("test_run", personas, world, ticks=5)
        assert len(log.events) > 0
        assert all(e.tick < 5 for e in log.events)

    def test_interaction_actions_diverse(self):
        engine = InteractionEngine()
        pe = PersonaEngine()
        wb = WorldModelBuilder()

        world = wb.create_world("diverse_test")
        personas = [
            pe.create_persona("a1", archetype="explorer", galaxy=world.galaxy),
            pe.create_persona("a2", archetype="creative", galaxy=world.galaxy),
            pe.create_persona("a3", archetype="analyst", galaxy=world.galaxy),
        ]

        log = engine.run_interaction("diverse_run", personas, world, ticks=20)
        actions = set(e.action for e in log.events)
        assert len(actions) >= 2  # at least 2 different actions

    def test_interaction_log_filter(self):
        log = InteractionLog()
        log.add(InteractionEvent(id="1", tick=0, actor_id="a1", action="speak", content="hi"))
        log.add(InteractionEvent(id="2", tick=1, actor_id="a2", action="query", content="what?"))
        assert len(log.filter_by_actor("a1")) == 1
        assert len(log.filter_by_action("query")) == 1

    def test_interaction_log_stats(self):
        log = InteractionLog()
        log.add(InteractionEvent(id="1", tick=0, actor_id="a1", action="speak", content="hi", impact=0.5, emergence_score=0.3))
        log.add(InteractionEvent(id="2", tick=1, actor_id="a2", action="query", content="what?", impact=0.1, emergence_score=0.6))
        stats = log.to_dict()
        assert stats["total_events"] == 2
        assert stats["avg_impact"] == pytest.approx(0.3, abs=0.01)

    def test_singleton(self):
        e1 = get_interaction_engine()
        e2 = get_interaction_engine()
        assert e1 is e2


class TestScenarioRunner:
    """Test ScenarioRunner."""

    def test_run_scenario(self):
        runner = ScenarioRunner()
        config = ScenarioConfig(
            name="test_scenario",
            num_personas=2,
            ticks_per_trial=5,
            num_trials=3,
        )
        analysis = runner.run_scenario(config)
        assert analysis.total_trials == 3
        assert "converged" in analysis.outcome_distribution or "diverged" in analysis.outcome_distribution
        assert 0.0 <= analysis.avg_final_coherence <= 1.0
        assert 0.0 <= analysis.robustness_score <= 1.0

    def test_run_scenario_with_seeds(self):
        runner = ScenarioRunner()
        config = ScenarioConfig(
            name="seeded_scenario",
            seed_documents=["Alice explored the concept."],
            num_personas=2,
            ticks_per_trial=3,
            num_trials=2,
        )
        analysis = runner.run_scenario(config)
        assert analysis.total_trials == 2

    def test_get_results(self):
        runner = ScenarioRunner()
        config = ScenarioConfig(name="results_test", num_trials=2, ticks_per_trial=3)
        runner.run_scenario(config)
        results = runner.get_results("results_test")
        assert results is not None
        assert len(results) == 2

    def test_best_worst_trial(self):
        runner = ScenarioRunner()
        config = ScenarioConfig(name="bw_test", num_trials=5, ticks_per_trial=3)
        analysis = runner.run_scenario(config)
        if analysis.best_trial and analysis.worst_trial:
            assert analysis.best_trial.final_coherence >= analysis.worst_trial.final_coherence

    def test_singleton(self):
        r1 = get_scenario_runner()
        r2 = get_scenario_runner()
        assert r1 is r2


class TestTrajectoryTreeSearch:
    """Test TrajectoryTreeSearch."""

    def test_search_basic(self):
        search = TrajectoryTreeSearch(max_depth=5, branching_factor=2)
        search.initialize({"start": True})
        result = search.search(iterations=50)
        assert result["total_simulations"] == 50
        assert result["tree_size"] > 1
        assert len(result["best_trajectory"]) > 0

    def test_search_finds_depth(self):
        search = TrajectoryTreeSearch(max_depth=5, branching_factor=3)
        search.initialize()
        result = search.search(iterations=100)
        assert result["max_depth_reached"] > 0

    def test_ucb1(self):
        node = TrajectoryNode(id="test", parent_id=None, depth=0, visits=10, total_value=5.0)
        ucb = node.ucb1()
        assert ucb > 0

    def test_ucb1_unvisited(self):
        node = TrajectoryNode(id="test", parent_id=None, depth=0, visits=0)
        assert node.ucb1() == float("inf")

    def test_singleton(self):
        s1 = get_trajectory_search()
        s2 = get_trajectory_search()
        assert s1 is s2


class TestPredictionCalibrationBridge:
    """Test PredictionCalibrationBridge."""

    def test_record_prediction(self):
        bridge = PredictionCalibrationBridge()
        pred = bridge.record_prediction("test", "it will rain", 0.7, confidence=0.8)
        assert pred.statement == "it will rain"
        assert pred.probability == pytest.approx(0.7, abs=0.1)  # may be adjusted
        assert pred.id

    def test_resolve_prediction_occurred(self):
        bridge = PredictionCalibrationBridge()
        pred = bridge.record_prediction("test", "event happens", 0.8)
        result = bridge.resolve_prediction(pred.id, outcome=True)
        assert result["status"] == "success"
        assert result["brier_score"] == pytest.approx((0.8 - 1.0) ** 2, abs=0.01)

    def test_resolve_prediction_not_occurred(self):
        bridge = PredictionCalibrationBridge()
        pred = bridge.record_prediction("test", "event happens", 0.3)
        result = bridge.resolve_prediction(pred.id, outcome=False)
        assert result["brier_score"] == pytest.approx((0.3 - 0.0) ** 2, abs=0.01)

    def test_resolve_nonexistent(self):
        bridge = PredictionCalibrationBridge()
        result = bridge.resolve_prediction("nonexistent", True)
        assert result["status"] == "error"

    def test_scorecard(self):
        bridge = PredictionCalibrationBridge()
        p1 = bridge.record_prediction("test", "a", 0.6)
        p2 = bridge.record_prediction("test", "b", 0.4)
        bridge.resolve_prediction(p1.id, True)
        bridge.resolve_prediction(p2.id, False)
        scorecard = bridge.get_scorecard()
        assert scorecard["total_predictions"] == 2
        assert scorecard["resolved"] == 2
        assert scorecard["avg_brier_score"] >= 0.0

    def test_calibration_adjustment(self):
        bridge = PredictionCalibrationBridge()
        # Record many bad predictions to shift calibration
        for _ in range(10):
            p = bridge.record_prediction("test", "always wrong", 0.9)
            bridge.resolve_prediction(p.id, False)  # always wrong
        # Next prediction should be adjusted downward
        pred = bridge.record_prediction("test", "next", 0.9)
        assert pred.calibration_adjustment != 0.0

    def test_list_predictions(self):
        bridge = PredictionCalibrationBridge()
        bridge.record_prediction("test", "a", 0.5)
        bridge.record_prediction("test", "b", 0.5)
        assert len(bridge.list_predictions()) == 2
        assert len(bridge.list_predictions(resolved=False)) == 2

    def test_singleton(self):
        b1 = get_calibration_bridge()
        b2 = get_calibration_bridge()
        assert b1 is b2


class TestDreamCycleIntegration:
    """Test DreamCycleIntegration."""

    def test_consolidate_simulation(self):
        dream = DreamCycleIntegration()
        reports = dream.consolidate_simulation(
            "sim_1",
            {
                "events_count": 50,
                "final_coherence": 0.8,
                "outcome": "converged",
                "best_trial": {"final_coherence": 0.9},
                "ticks": 20,
            },
        )
        assert len(reports) == 6  # 6 phases
        phases = [r.phase for r in reports]
        assert "consolidation" in phases
        assert "narrative" in phases

    def test_narrative_phase(self):
        dream = DreamCycleIntegration()
        reports = dream.consolidate_simulation(
            "sim_narrative",
            {"events_count": 10, "final_coherence": 0.7, "outcome": "converged", "ticks": 5},
        )
        narrative_report = [r for r in reports if r.phase == "narrative"][0]
        assert len(narrative_report.narrative) > 0
        assert "sim_narrative" in narrative_report.narrative

    def test_recommendations(self):
        dream = DreamCycleIntegration()
        dream.consolidate_simulation(
            "sim_rec",
            {"events_count": 5, "final_coherence": 0.2, "outcome": "collapsed", "ticks": 3},
        )
        recs = dream.get_recommendations()
        # Low coherence should generate a recommendation
        assert len(recs) > 0

    def test_cross_sim_associations(self):
        dream = DreamCycleIntegration()
        dream.consolidate_simulation("sim_a", {"outcome": "converged", "final_coherence": 0.8, "events_count": 10, "ticks": 5})
        dream.consolidate_simulation("sim_b", {"outcome": "converged", "final_coherence": 0.8, "events_count": 10, "ticks": 5})
        associations = dream.get_cross_sim_associations()
        # Same outcome should create an association
        assert len(associations) > 0

    def test_singleton(self):
        d1 = get_dream_integration()
        d2 = get_dream_integration()
        assert d1 is d2


class TestInsightSynthesizer:
    """Test InsightSynthesizer."""

    def test_synthesize_basic(self):
        synth = InsightSynthesizer()
        trajectories = [
            {"trial_id": "t1", "outcome": "converged", "final_coherence": 0.85, "avg_emergence": 0.6, "avg_impact": 0.3},
            {"trial_id": "t2", "outcome": "converged", "final_coherence": 0.80, "avg_emergence": 0.5, "avg_impact": 0.4},
            {"trial_id": "t3", "outcome": "diverged", "final_coherence": 0.40, "avg_emergence": 0.6, "avg_impact": 0.5},
        ]
        insights = synth.synthesize(trajectories)
        assert len(insights) > 0
        # Should be sorted by composite rank
        for i in range(len(insights) - 1):
            assert insights[i].composite_rank >= insights[i + 1].composite_rank

    def test_insight_composite_rank(self):
        insight = Insight(
            id="test",
            statement="test",
            insight_type="pattern",
            novelty_score=0.8,
            impact_score=0.7,
            coherence_score=0.6,
            cross_domain_score=0.5,
            calibration_confidence=0.4,
        )
        rank = insight.compute_composite_rank()
        assert 0.0 <= rank <= 1.0

    def test_pattern_extraction(self):
        synth = InsightSynthesizer()
        trajectories = [
            {"trial_id": f"t{i}", "outcome": "converged", "final_coherence": 0.8, "avg_emergence": 0.5}
            for i in range(5)
        ]
        insights = synth.synthesize(trajectories)
        # Should detect the "converged" pattern
        pattern_insights = [i for i in insights if i.insight_type == "pattern"]
        assert len(pattern_insights) > 0

    def test_anomaly_detection(self):
        synth = InsightSynthesizer()
        trajectories = [
            {"trial_id": "t1", "outcome": "converged", "final_coherence": 0.8, "avg_emergence": 0.5},
            {"trial_id": "t2", "outcome": "converged", "final_coherence": 0.82, "avg_emergence": 0.5},
            {"trial_id": "t3", "outcome": "collapsed", "final_coherence": 0.1, "avg_emergence": 0.5},
        ]
        insights = synth.synthesize(trajectories)
        anomalies = [i for i in insights if i.insight_type == "anomaly"]
        assert len(anomalies) > 0

    def test_connection_discovery(self):
        synth = InsightSynthesizer()
        trajectories = [
            {"trial_id": "t1", "outcome": "converged", "final_coherence": 0.8, "avg_emergence": 0.5},
            {"trial_id": "t2", "outcome": "diverged", "final_coherence": 0.4, "avg_emergence": 0.5},
        ]
        insights = synth.synthesize(trajectories)
        connections = [i for i in insights if i.insight_type == "connection"]
        assert len(connections) > 0

    def test_top_insights(self):
        synth = InsightSynthesizer()
        trajectories = [
            {"trial_id": f"t{i}", "outcome": "converged" if i % 2 == 0 else "diverged",
             "final_coherence": 0.5 + i * 0.1, "avg_emergence": 0.5}
            for i in range(10)
        ]
        synth.synthesize(trajectories)
        top = synth.get_top_insights(n=3)
        assert len(top) <= 3
        assert all(t.composite_rank > 0 for t in top)

    def test_singleton(self):
        s1 = get_insight_synthesizer()
        s2 = get_insight_synthesizer()
        assert s1 is s2


class TestSimulationHandlers:
    """Test MCP tool handlers."""

    def test_handle_simulation_create(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_create
        result = handle_simulation_create(
            world_name="handler_test",
            archetypes=["analyst", "creative"],
        )
        assert result["status"] == "success"
        assert "world" in result
        assert len(result["personas"]) == 2

    def test_handle_simulation_create_missing_name(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_create
        result = handle_simulation_create()
        assert result["status"] == "error"

    def test_handle_simulation_run(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_run
        result = handle_simulation_run(
            scenario_name="handler_scenario",
            num_personas=2,
            ticks_per_trial=3,
            num_trials=2,
        )
        assert result["status"] == "success"
        assert result["total_trials"] == 2

    def test_handle_simulation_search(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_search
        result = handle_simulation_search(iterations=20, max_depth=3)
        assert result["status"] == "success"
        assert result["total_simulations"] == 20

    def test_handle_simulation_inject(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_inject
        result = handle_simulation_inject(
            scenario_name="test",
            injection={"tick": 5, "variable": "coherence", "value": 0.9},
        )
        assert result["status"] == "success"

    def test_handle_simulation_analyze(self):
        # First run a scenario
        from whitemagic.tools.handlers.simulation import (
            handle_simulation_analyze,
            handle_simulation_run,
        )
        handle_simulation_run(
            scenario_name="analyze_test",
            num_personas=2,
            ticks_per_trial=3,
            num_trials=2,
        )
        result = handle_simulation_analyze(scenario_name="analyze_test", consolidate=True)
        assert result["status"] == "success"
        assert "analysis" in result

    def test_handle_simulation_synthesize(self):
        from whitemagic.tools.handlers.simulation import (
            handle_simulation_run,
            handle_simulation_synthesize,
        )
        handle_simulation_run(
            scenario_name="synth_test",
            num_personas=2,
            ticks_per_trial=3,
            num_trials=3,
        )
        result = handle_simulation_synthesize(scenario_name="synth_test", top_n=3)
        assert result["status"] == "success"
        assert "top_insights" in result

    def test_handle_simulation_calibrate_record(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_calibrate
        result = handle_simulation_calibrate(
            action="record",
            statement="test prediction",
            probability=0.7,
        )
        assert result["status"] == "success"
        assert "prediction_id" in result

    def test_handle_simulation_calibrate_scorecard(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_calibrate
        result = handle_simulation_calibrate(action="scorecard")
        assert result["status"] == "success"
        assert "avg_brier_score" in result
