# ruff: noqa: BLE001
"""Simulation Handlers — Monte Carlo, Bayesian optimization, rare events, SDEs.

Exposes the PolyglotMCOrchestrator's Tier 2-4 methods as MCP tool handlers.
These handlers wrap the Python orchestrator (which calls Rust with fallbacks),
persist significant results to memory, and feed into the research DAG.

Yin-within-yang: introspective simulation (internal parameter optimization)
Yang-within-yin: external research simulation (modeling external systems)
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def _get_orchestrator() -> Any:
    """Lazy-load the PolyglotMCOrchestrator singleton."""
    from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator
    return PolyglotMCOrchestrator()


def _persist_simulation_memory(
    title: str,
    content: str,
    tags: list[str] | None = None,
    importance: float = 0.6,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist a simulation result as a memory in the research galaxy."""
    try:
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
        um.store(
            content=content,
            title=title,
            tags=tags or ["simulation", "monte_carlo"],
            galaxy="research",
            importance=importance,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.debug("Simulation memory persist: %s", e, exc_info=True)


def _record_dag_experiment(
    hypothesis: str,
    parameters: dict[str, Any],
    fitness_score: float,
    outcome: dict[str, Any] | None = None,
) -> Any:
    """Record a simulation result as a Research DAG experiment."""
    try:
        from whitemagic.core.evolution.research_dag import (
            get_research_dag,
            ResearchDomain,
        )
        dag = get_research_dag()
        exp = dag.submit_hypothesis(
            hypothesis=hypothesis,
            domain=ResearchDomain.COGNITIVE,
            parameters=parameters,
        )
        dag.record_trial(exp.experiment_id, parameters=parameters)
        return dag.record_result(
            exp.experiment_id,
            fitness_score=fitness_score,
            outcome=outcome,
        )
    except Exception as e:
        logger.debug("DAG experiment recording: %s", e, exc_info=True)
        return None


# ── Core MC Tool Handlers ─────────────────────────────────────────────


def handle_mc_surrogate(**kwargs: Any) -> dict[str, Any]:
    """Fit and/or evaluate a Gaussian Process surrogate model.

    Args:
        x_train: Training inputs (list of lists).
        y_train: Training outputs (list of floats).
        x_predict: Optional points to predict at. If provided, returns predictions.
        length_scale: GP kernel length scale (default 1.0).
        sigma_f: GP signal variance (default 1.0).
        sigma_n: GP noise variance (default 0.01).
    """
    try:
        orch = _get_orchestrator()
        x_train = kwargs.get("x_train", [])
        y_train = kwargs.get("y_train", [])
        length_scale = float(kwargs.get("length_scale", 1.0))
        sigma_f = float(kwargs.get("sigma_f", 1.0))
        sigma_n = float(kwargs.get("sigma_n", 0.01))

        fit_result = orch.gp_fit(
            x_train, y_train,
            length_scale=length_scale,
            sigma_f=sigma_f,
            sigma_n=sigma_n,
        )

        result: dict[str, Any] = {
            "status": "success",
            "fit": fit_result,
        }

        x_predict = kwargs.get("x_predict")
        if x_predict:
            predictions = []
            for x in x_predict:
                pred = orch.gp_predict(
                    x_train, y_train, x,
                    length_scale=length_scale,
                    sigma_f=sigma_f,
                    sigma_n=sigma_n,
                )
                predictions.append(pred)
            result["predictions"] = predictions

        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_mc_optimize(**kwargs: Any) -> dict[str, Any]:
    """Run Bayesian optimization to find optimal parameters.

    Args:
        param_ranges: List of [min, max] pairs for each parameter.
        fitness_fn: Python callable or fitness expression string.
        n_initial_samples: Initial LHS samples (default 50).
        n_iterations: BO iterations (default 20).
        n_candidates: Candidate points per iteration (default 100).
        seed: Random seed.
    """
    try:
        orch = _get_orchestrator()
        param_ranges = kwargs.get("param_ranges", [[0.0, 1.0]])
        n_initial = int(kwargs.get("n_initial_samples", 50))
        n_iterations = int(kwargs.get("n_iterations", 20))
        n_candidates = int(kwargs.get("n_candidates", 100))
        seed = int(kwargs.get("seed", 42))

        fitness_expr = kwargs.get("fitness_expr", "x[0]")

        # Generate initial samples via LHS
        lhs_samples = orch.lhs_sample(
            n=n_initial,
            param_ranges=[(r[0], r[1]) for r in param_ranges],
            seed=seed,
        )
        initial_x = [list(s) for s in lhs_samples]
        initial_y = []
        for x in initial_x:
            try:
                y = eval(fitness_expr, {"x": x, "sum": sum, "abs": abs, "max": max, "min": min})
            except Exception:
                y = x[0] if x else 0.0
            initial_y.append(float(y))

        result = orch.bayesian_optimize(
            initial_x=initial_x,
            initial_y=initial_y,
            param_ranges=[(r[0], r[1]) for r in param_ranges],
            fitness_expr=fitness_expr,
            n_iterations=n_iterations,
            n_candidates=n_candidates,
            seed=seed,
        )

        if isinstance(result, dict) and result.get("best_y", 0) > 0.5:
            _persist_simulation_memory(
                title=f"BO result: best_y={result.get('best_y', 0):.4f}",
                content=f"Bayesian optimization found optimal parameters with fitness {result.get('best_y', 0):.4f}. "
                        f"Best params: {result.get('best_x', [])}",
                tags=["bayesian_optimization", "surrogate"],
                importance=min(0.9, float(result.get("best_y", 0))),
                metadata=result,
            )

        return {"status": "success", **result} if isinstance(result, dict) else {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_mc_rare_event(**kwargs: Any) -> dict[str, Any]:
    """Estimate rare event probabilities using subset simulation or multilevel splitting.

    Args:
        method: 'subset' or 'splitting' or 'importance' (default 'subset').
        dim: Dimensionality of the problem.
        n_samples: Number of samples per level.
        threshold: Failure threshold for the limit state function.
        g_expr: Limit state function expression (e.g. 'threshold - sum_sq').
        seed: Random seed.
    """
    try:
        orch = _get_orchestrator()
        method = kwargs.get("method", "subset")
        dim = int(kwargs.get("dim", 2))
        n_samples = int(kwargs.get("n_samples", 1000))
        threshold = float(kwargs.get("threshold", 2.0))
        g_expr = kwargs.get("g_expr", "threshold - sum_sq")
        seed = int(kwargs.get("seed", 42))

        if method == "splitting":
            result = orch.multilevel_splitting(
                dim=dim, n_samples=n_samples,
                survival_fraction=float(kwargs.get("survival_fraction", 0.1)),
                threshold=threshold, g_expr=g_expr, seed=seed,
            )
        elif method == "importance":
            result = orch.importance_sampling_rare(
                dim=dim, n_samples=n_samples,
                pilot_n=int(kwargs.get("pilot_n", 200)),
                threshold=threshold, g_expr=g_expr, seed=seed,
            )
        else:
            result = orch.subset_simulation(
                dim=dim, n_samples=n_samples,
                target_pf=float(kwargs.get("target_pf", 0.001)),
                threshold=threshold, g_expr=g_expr, seed=seed,
            )

        prob = result.get("probability", 0) if isinstance(result, dict) else 0
        _persist_simulation_memory(
            title=f"Rare event P={prob:.6e} via {method}",
            content=f"Rare event probability estimation via {method}: P={prob:.6e}, "
                    f"threshold={threshold}, dim={dim}, n_samples={n_samples}",
            tags=["rare_event", method, "risk_analysis"],
            importance=0.7,
            metadata=result,
        )

        return {"status": "success", "method": method, **result} if isinstance(result, dict) else {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_mc_sde(**kwargs: Any) -> dict[str, Any]:
    """Solve stochastic differential equations via Euler-Maruyama or Milstein.

    Args:
        x0: Initial condition.
        t_end: End time.
        n_steps: Number of time steps.
        n_paths: Number of paths (for parallel simulation).
        drift_type: 'gbm' or 'ou'.
        mu: Drift parameter.
        sigma: Diffusion parameter.
        solver: 'euler' or 'milstein' (default 'euler').
        mlmc: If true, use multilevel Monte Carlo.
        n_levels: MLMC levels (if mlmc=true).
        seed: Random seed.
    """
    try:
        orch = _get_orchestrator()
        x0 = float(kwargs.get("x0", 100.0))
        t_end = float(kwargs.get("t_end", 1.0))
        n_steps = int(kwargs.get("n_steps", 100))
        drift_type = kwargs.get("drift_type", "gbm")
        mu = float(kwargs.get("mu", 0.05))
        sigma = float(kwargs.get("sigma", 0.2))
        solver = kwargs.get("solver", "euler")
        seed = int(kwargs.get("seed", 42))
        n_paths = int(kwargs.get("n_paths", 1000))
        use_mlmc = bool(kwargs.get("mlmc", False))

        if use_mlmc:
            result = orch.sde_mlmc(
                x0=x0, t_end=t_end,
                n_levels=int(kwargs.get("n_levels", 3)),
                n_paths_fine=n_paths,
                drift_type=drift_type, mu=mu, sigma=sigma,
                seed=seed,
            )
        elif n_paths > 1:
            if solver == "milstein":
                result = orch.sde_parallel_milstein(
                    x0=x0, t_end=t_end, n_steps=n_steps, n_paths=n_paths,
                    drift_type=drift_type, mu=mu, sigma=sigma, seed=seed,
                )
            else:
                result = orch.sde_parallel_euler(
                    x0=x0, t_end=t_end, n_steps=n_steps, n_paths=n_paths,
                    drift_type=drift_type, mu=mu, sigma=sigma, seed=seed,
                )
        else:
            if solver == "milstein":
                result = orch.sde_milstein(
                    x0=x0, t_end=t_end, n_steps=n_steps,
                    drift_type=drift_type, mu=mu, sigma=sigma, seed=seed,
                )
            else:
                result = orch.sde_euler(
                    x0=x0, t_end=t_end, n_steps=n_steps,
                    drift_type=drift_type, mu=mu, sigma=sigma, seed=seed,
                )

        return {"status": "success", "solver": solver, **result} if isinstance(result, dict) else {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Superforecaster Pipeline ──────────────────────────────────────────


def handle_mc_superforecaster(**kwargs: Any) -> dict[str, Any]:
    """Run the full superforecaster pipeline: LHS → PCE → Sobol → BO → rare event.

    This is the unified entry point for comprehensive possibility space exploration.
    Combines sampling, surrogate fitting, sensitivity analysis, Bayesian optimization,
    statistics, and optional rare event estimation into a single structured output.

    Args:
        param_ranges: List of [min, max] pairs for each parameter.
        fitness_fn: Python callable or fitness expression string.
        n_initial_samples: Initial LHS samples (default 100).
        n_bo_iterations: BO iterations (default 20).
        rare_event_threshold: Optional threshold for rare event estimation.
        seed: Random seed.
    """
    try:
        orch = _get_orchestrator()
        param_ranges = kwargs.get("param_ranges", [[0.0, 1.0]])
        n_initial = int(kwargs.get("n_initial_samples", 100))
        n_bo_iterations = int(kwargs.get("n_bo_iterations", 20))
        seed = int(kwargs.get("seed", 42))

        fitness_fn = kwargs.get("fitness_fn")
        if fitness_fn is None:
            expr = kwargs.get("fitness_expr", "x[0]")
            fitness_fn = lambda x: eval(expr, {"x": x, "sum": sum, "abs": abs, "max": max, "min": min})

        result = orch.superforecaster_estimate(
            param_ranges=[(r[0], r[1]) for r in param_ranges],
            fitness_fn=fitness_fn,
            n_initial_samples=n_initial,
            n_bo_iterations=n_bo_iterations,
            seed=seed,
        )

        best_fitness = result.get("best_fitness", 0)
        if best_fitness > 0.5:
            _record_dag_experiment(
                hypothesis=f"Superforecaster optimization: best_fitness={best_fitness:.4f}",
                parameters={"param_ranges": param_ranges, "n_samples": n_initial, "n_bo": n_bo_iterations},
                fitness_score=best_fitness,
                outcome=result,
            )
            _persist_simulation_memory(
                title=f"Superforecaster: fitness={best_fitness:.4f}",
                content=f"Superforecaster pipeline completed. Best fitness: {best_fitness:.4f}, "
                        f"best params: {result.get('best_params', [])}, "
                        f"surrogate R²: {result.get('surrogate_r_squared', 0):.4f}, "
                        f"sensitivity: {result.get('parameter_sensitivity', [])}",
                tags=["superforecaster", "bayesian_optimization", "sensitivity_analysis"],
                importance=min(0.95, best_fitness),
                metadata=result,
            )

        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Yin-Within-Yang: Introspective Simulation ─────────────────────────


def handle_simulation_introspect(**kwargs: Any) -> dict[str, Any]:
    """Run introspective simulation — optimize internal system parameters.

    Yin-within-yang: the reflective (yin) simulation runs within the active (yang)
    system. Uses the superforecaster pipeline to optimize consciousness parameters
    (guna balance, coherence weights, emergence thresholds, health setpoints).

    Delegates to SimulationOrchestrator.run_introspective() which handles
    persistence to memory and Research DAG recording.

    Args:
        space: Which internal space to optimize (guna_balance, coherence_optimization,
               emergence_thresholds, health_setpoints). Default: guna_balance.
        n_trials: Number of initial MC trials.
        n_bo_iterations: Bayesian optimization iterations.
        seed: Random seed.
    """
    try:
        from whitemagic.core.consciousness.simulation_orchestrator import get_simulation_orchestrator
        orch = get_simulation_orchestrator()
        space = kwargs.get("space", "guna_balance")
        n_trials = int(kwargs.get("n_trials", 100))
        n_bo_iterations = int(kwargs.get("n_bo_iterations", 20))
        seed = int(kwargs.get("seed", 42))

        result = orch.run_introspective(
            space=space,
            n_trials=n_trials,
            n_bo_iterations=n_bo_iterations,
            seed=seed,
        )

        return {
            "status": "success" if result.success else "error",
            "space": space,
            "optimal_parameters": result.best_params,
            "best_fitness": result.best_fitness,
            "statistics": result.statistics,
            "parameter_sensitivity": result.sensitivity,
            "execution_time_ms": result.execution_time_ms,
            "memory_id": result.memory_id,
            "dag_experiment_id": result.dag_experiment_id,
            "error": result.error,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Yang-Within-Yin: External Research Simulation ─────────────────────


def handle_simulation_forecast(**kwargs: Any) -> dict[str, Any]:
    """Run external research simulation — model and forecast external systems.

    Yang-within-yin: the active (yang) research runs within the reflective (yin)
    simulation framework. Uses SDE solvers and rare event estimation to model
    external systems, forecast outcomes, and assess risks.

    Delegates to SimulationOrchestrator.run_external() which handles
    persistence to memory and Research DAG recording.

    Args:
        model_type: 'sde' for stochastic differential equations, 'rare_event' for
                    rare event probability estimation, 'superforecaster' for full pipeline.
        sde config (if model_type='sde'):
            x0, t_end, n_steps, n_paths, drift_type, mu, sigma, solver, mlmc
        rare_event config (if model_type='rare_event'):
            method, dim, n_samples, threshold, g_expr
        superforecaster config (if model_type='superforecaster'):
            param_ranges, fitness_expr, n_initial_samples, n_bo_iterations
        research_query: Optional research question to frame the simulation.
        seed: Random seed.
    """
    try:
        from whitemagic.core.consciousness.simulation_orchestrator import get_simulation_orchestrator
        orch = get_simulation_orchestrator()
        model_type = kwargs.pop("model_type", "sde")
        research_query = kwargs.pop("research_query", "")

        result = orch.run_external(
            model_type=model_type,
            research_query=research_query,
            **kwargs,
        )

        return {
            "status": "success" if result.success else "error",
            "model_type": model_type,
            "research_query": research_query,
            "statistics": result.statistics,
            "best_params": result.best_params,
            "best_fitness": result.best_fitness,
            "parameter_sensitivity": result.sensitivity,
            "execution_time_ms": result.execution_time_ms,
            "memory_id": result.memory_id,
            "dag_experiment_id": result.dag_experiment_id,
            "error": result.error,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Simulation Orchestrator Status & Recursive Cycle ──────────────────


def handle_simulation_status(**kwargs: Any) -> dict[str, Any]:
    """Get SimulationOrchestrator status — simulation history and counts.

    Returns total simulations run, introspective vs external counts,
    and recent results (last 10).
    """
    try:
        from whitemagic.core.consciousness.simulation_orchestrator import get_simulation_orchestrator
        orch = get_simulation_orchestrator()
        return {"status": "success", **orch.get_status()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_simulation_recursive(**kwargs: Any) -> dict[str, Any]:
    """Run a recursive yin/yang simulation cycle.

    Alternates between introspective (yin-within-yang) and external
    (yang-within-yin) simulation, feeding results forward:

        introspective -> external -> introspective -> external -> ...

    Each cycle's results inform the next cycle's parameters.

    Args:
        n_cycles: Number of yin/yang cycles (default 3).
        introspective_space: Internal space to optimize (default guna_balance).
        external_model: External model type (default sde).
        seed: Random seed.
    """
    try:
        from whitemagic.core.consciousness.simulation_orchestrator import get_simulation_orchestrator
        orch = get_simulation_orchestrator()
        n_cycles = int(kwargs.get("n_cycles", 3))
        introspective_space = kwargs.get("introspective_space", "guna_balance")
        external_model = kwargs.get("external_model", "sde")
        seed = int(kwargs.get("seed", 42))

        results = orch.run_recursive_cycle(
            n_cycles=n_cycles,
            introspective_space=introspective_space,
            external_model=external_model,
            seed=seed,
        )

        return {
            "status": "success",
            "n_cycles": n_cycles,
            "results": [r.to_dict() for r in results],
            "summary": {
                "total_simulations": len(results),
                "introspective_count": sum(1 for r in results if r.mode == "introspective"),
                "external_count": sum(1 for r in results if r.mode == "external"),
                "avg_fitness": sum(r.best_fitness for r in results) / len(results) if results else 0.0,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
