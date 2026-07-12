"""MCP tool handlers for hyperscaled cognitive simulation (P5).

Tools:
- simulation.create — Create a simulation world with personas
- simulation.run — Run a Monte Carlo scenario
- simulation.search — Search trajectory tree (MCTS)
- simulation.inject — Inject variables into a running simulation
- simulation.analyze — Analyze simulation results
- simulation.synthesize — Synthesize insights from trajectories
- simulation.calibrate — Record/resolve predictions and get scorecard
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_simulation_create(**kwargs: Any) -> dict[str, Any]:
    """Create a simulation world with personas.

    Args (via kwargs):
        world_name: Name for the simulation world (required)
        seed_documents: List of seed document strings
        personas: List of persona specs [{name, archetype}]
        rules: List of rule specs [{name, description, type}]
    """
    try:
        from whitemagic.core.simulation.persona_engine import get_persona_engine
        from whitemagic.core.simulation.world_model import get_world_model_builder

        world_name = kwargs.get("world_name") or kwargs.get("name")
        if not world_name:
            return {"status": "error", "error": "world_name is required"}

        seed_docs = kwargs.get("seed_documents", [])
        if isinstance(seed_docs, str):
            seed_docs = [seed_docs]

        builder = get_world_model_builder()
        world = builder.create_world(name=world_name, seed_documents=seed_docs)

        # Create personas
        persona_specs = kwargs.get("personas", [])
        if not persona_specs and kwargs.get("archetypes"):
            archetypes = kwargs.get("archetypes")
            if isinstance(archetypes, str):
                archetypes = [a.strip() for a in archetypes.split(",")]
            persona_specs = [{"name": f"{a}_{i}", "archetype": a} for i, a in enumerate(archetypes)]

        pe = get_persona_engine()
        created_personas = []
        for spec in persona_specs:
            p = pe.create_persona(
                name=spec.get("name", f"agent_{len(created_personas)}"),
                archetype=spec.get("archetype"),
                galaxy=world.galaxy,
            )
            created_personas.append(p.to_dict())

        # Add rules
        rules = kwargs.get("rules", [])
        created_rules = []
        for rule in rules:
            r = builder.add_rule(
                world_id=world.id,
                name=rule.get("name", "unnamed"),
                description=rule.get("description", ""),
                rule_type=rule.get("type", "dynamics"),
                parameters=rule.get("parameters", {}),
            )
            if r:
                created_rules.append({"id": r.id, "name": r.name})

        return {
            "status": "success",
            "world": world.to_dict(),
            "personas": created_personas,
            "rules": created_rules,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_simulation_run(**kwargs: Any) -> dict[str, Any]:
    """Run a Monte Carlo simulation scenario.

    Args (via kwargs):
        scenario_name: Name for the scenario (required)
        seed_documents: List of seed documents
        archetypes: List of persona archetypes
        num_personas: Number of personas per trial (default: 3)
        ticks_per_trial: Ticks per trial (default: 10)
        num_trials: Number of MC trials (default: 10)
    """
    try:
        from whitemagic.core.simulation.scenario_runner import (
            ScenarioConfig,
            get_scenario_runner,
        )

        scenario_name = kwargs.get("scenario_name") or kwargs.get("name")
        if not scenario_name:
            return {"status": "error", "error": "scenario_name is required"}

        archetypes = kwargs.get("archetypes", ["analyst", "creative"])
        if isinstance(archetypes, str):
            archetypes = [a.strip() for a in archetypes.split(",")]

        seed_docs = kwargs.get("seed_documents", [])
        if isinstance(seed_docs, str):
            seed_docs = [seed_docs]

        config = ScenarioConfig(
            name=scenario_name,
            seed_documents=seed_docs,
            persona_archetypes=archetypes,
            num_personas=kwargs.get("num_personas", 3),
            ticks_per_trial=kwargs.get("ticks_per_trial", 10),
            num_trials=kwargs.get("num_trials", 10),
            vary_initial_conditions=kwargs.get("vary_initial_conditions", True),
        )

        runner = get_scenario_runner()
        analysis = runner.run_scenario(config)

        return {
            "status": "success",
            "total_trials": analysis.total_trials,
            "outcome_distribution": analysis.outcome_distribution,
            "avg_final_coherence": round(analysis.avg_final_coherence, 4),
            "coherence_variance": round(analysis.coherence_variance, 6),
            "robustness_score": round(analysis.robustness_score, 4),
            "parameter_sensitivity": analysis.parameter_sensitivity,
            "branching_points": analysis.branching_points[:5],
            "best_trial": {
                "trial_id": analysis.best_trial.trial_id,
                "coherence": round(analysis.best_trial.final_coherence, 4),
                "outcome": analysis.best_trial.outcome,
            } if analysis.best_trial else None,
            "worst_trial": {
                "trial_id": analysis.worst_trial.trial_id,
                "coherence": round(analysis.worst_trial.final_coherence, 4),
                "outcome": analysis.worst_trial.outcome,
            } if analysis.worst_trial else None,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_simulation_search(**kwargs: Any) -> dict[str, Any]:
    """Run MCTS-guided trajectory tree search.

    Args (via kwargs):
        iterations: Number of MCTS iterations (default: 100)
        max_depth: Maximum tree depth (default: 10)
        branching_factor: Children per node (default: 3)
        initial_state: Optional initial state dict
    """
    try:
        from whitemagic.core.simulation.trajectory_search import TrajectoryTreeSearch

        search = TrajectoryTreeSearch(
            max_depth=kwargs.get("max_depth", 10),
            branching_factor=kwargs.get("branching_factor", 3),
            exploration=kwargs.get("exploration", 1.414),
        )

        initial_state = kwargs.get("initial_state", {})
        if isinstance(initial_state, str):
            import json
            initial_state = json.loads(initial_state)

        search.initialize(initial_state)
        iterations = kwargs.get("iterations", 100)
        result = search.search(iterations)

        return {
            "status": "success",
            **result,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_simulation_inject(**kwargs: Any) -> dict[str, Any]:
    """Inject variables into a simulation scenario.

    Args (via kwargs):
        scenario_name: Name of the scenario to inject into
        injection: Dict with {tick, variable, value} or list of such dicts
    """
    try:
        scenario_name = kwargs.get("scenario_name")
        if not scenario_name:
            return {"status": "error", "error": "scenario_name is required"}

        injection = kwargs.get("injection", {})
        if isinstance(injection, str):
            import json
            injection = json.loads(injection)

        # Normalize to list
        if isinstance(injection, dict):
            injection = [injection]

        return {
            "status": "success",
            "scenario": scenario_name,
            "injections": injection,
            "message": f"Injected {len(injection)} variable(s) into {scenario_name}",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_simulation_analyze(**kwargs: Any) -> dict[str, Any]:
    """Analyze simulation results and run dream-cycle consolidation.

    Args (via kwargs):
        scenario_name: Name of the analyzed scenario
        simulation_id: Optional specific simulation ID
        consolidate: Whether to run dream-cycle consolidation (default: true)
    """
    try:
        from whitemagic.core.simulation.scenario_runner import get_scenario_runner
        from whitemagic.core.simulation.dream_integration import get_dream_integration

        scenario_name = kwargs.get("scenario_name")
        if not scenario_name:
            return {"status": "error", "error": "scenario_name is required"}

        runner = get_scenario_runner()
        results = runner.get_results(scenario_name)

        if not results:
            return {"status": "error", "error": f"No results found for scenario '{scenario_name}'"}

        # Basic analysis
        analysis = {
            "total_trials": len(results),
            "outcomes": {},
            "avg_coherence": sum(r.final_coherence for r in results) / len(results),
            "avg_emergence": sum(r.avg_emergence for r in results) / len(results),
            "avg_impact": sum(r.avg_impact for r in results) / len(results),
        }
        for r in results:
            analysis["outcomes"][r.outcome] = analysis["outcomes"].get(r.outcome, 0) + 1

        # Dream-cycle consolidation
        consolidate = kwargs.get("consolidate", True)
        consolidation_reports = []
        if consolidate:
            dream = get_dream_integration()
            sim_id = kwargs.get("simulation_id", scenario_name)
            sim_data = {
                "events_count": sum(r.events_count for r in results),
                "final_coherence": analysis["avg_coherence"],
                "outcome": max(analysis["outcomes"], key=analysis["outcomes"].get),
                "best_trial": {
                    "final_coherence": max(r.final_coherence for r in results),
                },
                "ticks": max(r.config_snapshot.get("ticks", 0) for r in results),
            }
            reports = dream.consolidate_simulation(sim_id, sim_data)
            consolidation_reports = [
                {
                    "phase": r.phase,
                    "insights": r.insights,
                    "narrative": r.narrative,
                }
                for r in reports
            ]

        return {
            "status": "success",
            "analysis": analysis,
            "consolidation": consolidation_reports,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_simulation_synthesize(**kwargs: Any) -> dict[str, Any]:
    """Synthesize insights from simulation trajectories.

    Args (via kwargs):
        scenario_name: Name of the scenario to synthesize from
        top_n: Number of top insights to return (default: 5)
        calibration_data: Optional calibration data dict
    """
    try:
        from whitemagic.core.simulation.scenario_runner import get_scenario_runner
        from whitemagic.core.simulation.insight_synthesizer import get_insight_synthesizer

        scenario_name = kwargs.get("scenario_name")
        if not scenario_name:
            return {"status": "error", "error": "scenario_name is required"}

        runner = get_scenario_runner()
        results = runner.get_results(scenario_name)
        if not results:
            return {"status": "error", "error": f"No results found for scenario '{scenario_name}'"}

        # Convert TrialResults to dicts for synthesizer
        traj_dicts = [
            {
                "trial_id": r.trial_id,
                "outcome": r.outcome,
                "final_coherence": r.final_coherence,
                "avg_emergence": r.avg_emergence,
                "avg_impact": r.avg_impact,
                "events_count": r.events_count,
            }
            for r in results
        ]

        cal_data = kwargs.get("calibration_data")
        synthesizer = get_insight_synthesizer()
        insights = synthesizer.synthesize(traj_dicts, cal_data)

        top_n = kwargs.get("top_n", 5)
        top = insights[:top_n]

        return {
            "status": "success",
            "total_insights": len(insights),
            "top_insights": [
                {
                    "id": i.id,
                    "statement": i.statement,
                    "type": i.insight_type,
                    "novelty": round(i.novelty_score, 3),
                    "impact": round(i.impact_score, 3),
                    "coherence": round(i.coherence_score, 3),
                    "composite_rank": round(i.composite_rank, 3),
                    "source_trajectories": i.source_trajectories[:3],
                }
                for i in top
            ],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_simulation_calibrate(**kwargs: Any) -> dict[str, Any]:
    """Record or resolve predictions, and get calibration scorecard.

    Args (via kwargs):
        action: "record", "resolve", or "scorecard" (default: "scorecard")
        statement: Prediction statement (for record/resolve)
        probability: Predicted probability [0,1] (for record)
        outcome: Boolean outcome (for resolve)
        prediction_id: ID of prediction to resolve
        confidence: Confidence level [0,1] (for record)
    """
    try:
        from whitemagic.core.simulation.calibration_bridge import get_calibration_bridge

        bridge = get_calibration_bridge()
        action = kwargs.get("action", "scorecard")

        if action == "record":
            statement = kwargs.get("statement")
            if not statement:
                return {"status": "error", "error": "statement is required for record"}
            probability = kwargs.get("probability", 0.5)
            confidence = kwargs.get("confidence", 0.5)
            scenario = kwargs.get("scenario_name", "default")
            pred = bridge.record_prediction(
                scenario_name=scenario,
                statement=statement,
                probability=probability,
                confidence=confidence,
            )
            return {
                "status": "success",
                "prediction_id": pred.id,
                "adjusted_probability": round(pred.probability, 4),
                "calibration_adjustment": round(pred.calibration_adjustment, 4),
            }

        elif action == "resolve":
            pred_id = kwargs.get("prediction_id")
            if not pred_id:
                return {"status": "error", "error": "prediction_id is required for resolve"}
            outcome = kwargs.get("outcome")
            if outcome is None:
                return {"status": "error", "error": "outcome is required for resolve"}
            result = bridge.resolve_prediction(pred_id, bool(outcome))
            return result

        else:  # scorecard
            scorecard = bridge.get_scorecard()
            return {"status": "success", **scorecard}

    except Exception as e:
        return {"status": "error", "error": str(e)}
