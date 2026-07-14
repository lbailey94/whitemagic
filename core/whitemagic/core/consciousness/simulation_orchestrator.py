"""Simulation Orchestrator — Yin-within-Yang / Yang-within-Yin integration.

Unifies the Monte Carlo simulation systems (Bayesian optimization, rare event
simulation, SDE solvers, superforecaster pipeline) with WhiteMagic's cognitive
architecture in a recursive yin/yang structure:

**Yin-within-Yang** (introspective simulation):
    The reflective (yin) simulation runs *within* the active (yang) system.
    Uses the superforecaster pipeline to optimize internal parameters:
    - Guna balance ratios
    - Coherence metric weights
    - Emergence detection thresholds
    - Health monitoring setpoints
    Results feed back into the live system as evolved parameters.

**Yang-within-Yin** (external research simulation):
    The active (yang) research runs *within* the reflective (yin) simulation
    framework. Uses SDE solvers and rare event estimation to model external
    systems, forecast outcomes, and assess risks:
    - Stochastic process modeling (GBM, OU)
    - Rare event probability estimation
    - Sensitivity analysis on external parameters
    Results are cached as research memories with extensive metadata.

Both modes persist results to the research galaxy and record experiments
in the Research DAG, creating a recursive loop:
    simulate → record → learn → simulate better → ...

Integration points:
    - PolyglotMCOrchestrator: Rust-backed MC computation
    - PossibilitySpaceExplorer: internal parameter spaces
    - ResearchDAG: experiment lineage tracking
    - Memory (research galaxy): persistent caching of results
    - RecursiveImprovementLoop: feeds simulation results into the OIPAL cycle
    - EvolutionaryAutoswarm: campaigns use superforecaster when available
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Result of a simulation run (introspective or external)."""

    mode: str  # "introspective" or "external"
    subtype: str  # e.g. "guna_balance", "sde", "rare_event"
    success: bool = False
    best_fitness: float = 0.0
    best_params: dict[str, float] = field(default_factory=dict)
    statistics: dict[str, Any] = field(default_factory=dict)
    sensitivity: dict[str, float] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    memory_id: str | None = None
    dag_experiment_id: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "subtype": self.subtype,
            "success": self.success,
            "best_fitness": round(self.best_fitness, 6),
            "best_params": {k: round(v, 6) for k, v in self.best_params.items()},
            "statistics": self.statistics,
            "sensitivity": {k: round(v, 6) for k, v in self.sensitivity.items()},
            "execution_time_ms": round(self.execution_time_ms, 2),
            "memory_id": self.memory_id,
            "dag_experiment_id": self.dag_experiment_id,
            "error": self.error,
            "metadata": self.metadata,
        }


class SimulationOrchestrator:
    """Orchestrates yin/yang simulation cycles.

    Yin-within-yang: introspective simulation optimizes internal parameters.
    Yang-within-yin: external research simulation models external systems.

    Both modes persist to memory and the Research DAG, creating a recursive
    loop where simulation results inform future simulations.
    """

    _instance: SimulationOrchestrator | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._results_history: list[SimulationResult] = []
        self._history_lock = threading.RLock()
        self._cache: dict[str, SimulationResult] = {}
        self._cache_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> SimulationOrchestrator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _consult_oracle_for_bo(self, research_query: str) -> dict[str, Any] | None:
        """Consult oracle for BO parameter guidance (Phase 4).

        Attempts to get oracle guidance and translate it to BO parameters.
        Returns None if oracle is unavailable or consultation fails.
        """
        if not research_query:
            return None
        try:
            from whitemagic.oracle.oracle_bo_bridge import get_oracle_bo_bridge
            from whitemagic.oracle.quantum_iching import QuantumIChing

            oracle = QuantumIChing()
            result = oracle.consult(research_query, {})
            bridge = get_oracle_bo_bridge()
            oracle_output = {
                "primary_hexagram": result.primary_hexagram,
                "wu_xing": "fire",  # Default; could be derived from hexagram
            }
            return bridge.translate(oracle_output)
        except Exception as exc:
            logger.debug("Oracle BO consultation failed: %s", exc)
            return None

    # ── Yin-within-Yang: Introspective Simulation ──────────────────────

    def run_introspective(
        self,
        space: str = "guna_balance",
        n_trials: int = 100,
        n_bo_iterations: int = 20,
        seed: int = 42,
        persist: bool = True,
    ) -> SimulationResult:
        """Run introspective simulation to optimize internal system parameters.

        Yin-within-yang: the reflective simulation within the active system.
        Uses PossibilitySpaceExplorer with the superforecaster pipeline.

        Args:
            space: Internal space to optimize (guna_balance, coherence_optimization,
                   emergence_thresholds, health_setpoints).
            n_trials: Initial LHS samples.
            n_bo_iterations: Bayesian optimization iterations.
            seed: Random seed.
            persist: If True, persist results to memory and Research DAG.
        """
        start = time.time()
        result = SimulationResult(mode="introspective", subtype=space)

        try:
            from whitemagic.core.consciousness.possibility_explorer import (
                get_possibility_explorer,
            )
            explorer = get_possibility_explorer()
            exploration = explorer.explore(
                space,
                n_trials=n_trials,
                use_superforecaster=True,
                n_bo_iterations=n_bo_iterations,
                seed=seed,
            )

            result.success = exploration.best_trial is not None
            result.best_fitness = (
                exploration.best_trial.fitness_score
                if exploration.best_trial
                else 0.0
            )
            result.best_params = (
                exploration.best_trial.parameters
                if exploration.best_trial
                else {}
            )
            result.statistics = {
                "avg_fitness": exploration.avg_fitness,
                "fitness_variance": exploration.fitness_variance,
                "n_trials": exploration.n_trials,
                "backend": exploration.backend,
            }
            result.sensitivity = exploration.parameter_sensitivity

            if persist and result.success:
                result.memory_id = self._persist_memory(
                    title=f"Introspective simulation: {space} fitness={result.best_fitness:.4f}",
                    content=(
                        f"Yin-within-yang introspective simulation of {space}.\n"
                        f"Optimal parameters: {result.best_params}\n"
                        f"Best fitness: {result.best_fitness:.4f}\n"
                        f"Sensitivity: {result.sensitivity}\n"
                        f"Statistics: {result.statistics}"
                    ),
                    tags=["simulation", "introspective", space, "yin_within_yang"],
                    importance=min(0.9, result.best_fitness),
                    metadata=result.to_dict(),
                )
                result.dag_experiment_id = self._record_dag(
                    hypothesis=f"Introspective optimization of {space}",
                    parameters=result.best_params,
                    fitness_score=result.best_fitness,
                    outcome=result.to_dict(),
                )

        except Exception as e:
            result.error = str(e)
            logger.error("Introspective simulation failed: %s", e, exc_info=True)

        result.execution_time_ms = (time.time() - start) * 1000

        with self._history_lock:
            self._results_history.append(result)
            if len(self._results_history) > 100:
                self._results_history = self._results_history[-50:]

        logger.info(
            "SimulationOrchestrator [introspective/%s]: fitness=%.4f, %.1fms",
            space, result.best_fitness, result.execution_time_ms,
        )
        return result

    # ── Yang-within-Yin: External Research Simulation ──────────────────

    def run_external(
        self,
        model_type: str = "sde",
        research_query: str = "",
        persist: bool = True,
        **kwargs: Any,
    ) -> SimulationResult:
        """Run external research simulation to model external systems.

        Yang-within-yin: the active research within the reflective framework.
        Uses SDE solvers, rare event estimation, or superforecaster pipeline.

        Args:
            model_type: 'sde', 'rare_event', or 'superforecaster'.
            research_query: Optional research question framing the simulation.
            persist: If True, persist results to memory and Research DAG.
            **kwargs: Model-specific parameters passed to the MC orchestrator.
        """
        start = time.time()
        result = SimulationResult(
            mode="external",
            subtype=model_type,
        )

        try:
            from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator
            orch = PolyglotMCOrchestrator()

            # Phase 4: Oracle-guided BO parameters
            oracle_params = self._consult_oracle_for_bo(research_query)
            if oracle_params:
                kwargs.setdefault("xi", oracle_params.get("xi", 0.01))
                kwargs.setdefault("n_iterations", oracle_params.get("n_bo_iterations", 20))
                result.metadata = result.metadata or {}
                result.metadata["oracle_bo_params"] = oracle_params

            if model_type == "sde":
                mc_result = self._run_sde(orch, **kwargs)
            elif model_type == "rare_event":
                mc_result = self._run_rare_event(orch, **kwargs)
            elif model_type == "superforecaster":
                mc_result = self._run_superforecaster(orch, **kwargs)
            else:
                result.error = f"Unknown model_type: {model_type}"
                result.execution_time_ms = (time.time() - start) * 1000
                return result

            result.success = mc_result.get("status") != "error"
            result.statistics = mc_result
            result.best_fitness = float(mc_result.get("best_fitness", mc_result.get("best_y", 0.0)))

            if "best_params" in mc_result:
                params = mc_result["best_params"]
                if isinstance(params, list):
                    param_names = kwargs.get("param_names", [f"p{i}" for i in range(len(params))])
                    result.best_params = dict(zip(param_names, params))
                elif isinstance(params, dict):
                    result.best_params = params

            if "parameter_sensitivity" in mc_result:
                sens = mc_result["parameter_sensitivity"]
                if isinstance(sens, list):
                    param_names = kwargs.get("param_names", [f"p{i}" for i in range(len(sens))])
                    result.sensitivity = dict(zip(param_names, [float(s) for s in sens]))
                elif isinstance(sens, dict):
                    result.sensitivity = {k: float(v) for k, v in sens.items()}

            if persist and result.success:
                title = f"External forecast: {model_type}" + (f" ({research_query[:50]})" if research_query else "")
                result.memory_id = self._persist_memory(
                    title=title,
                    content=(
                        f"Yang-within-yin external research simulation: {model_type}.\n"
                        f"Research query: {research_query}\n"
                        f"Statistics: {result.statistics}\n"
                        f"Best params: {result.best_params}\n"
                        f"Sensitivity: {result.sensitivity}"
                    ),
                    tags=["simulation", "external_research", model_type, "yang_within_yin"],
                    importance=0.7,
                    metadata={"research_query": research_query, **result.to_dict()},
                )
                result.dag_experiment_id = self._record_dag(
                    hypothesis=f"External forecast: {research_query or model_type}",
                    parameters=result.best_params,
                    fitness_score=result.best_fitness,
                    outcome={"model_type": model_type, "research_query": research_query, **result.statistics},
                )

        except Exception as e:
            result.error = str(e)
            logger.error("External simulation failed: %s", e, exc_info=True)

        result.execution_time_ms = (time.time() - start) * 1000

        with self._history_lock:
            self._results_history.append(result)
            if len(self._results_history) > 100:
                self._results_history = self._results_history[-50:]

        logger.info(
            "SimulationOrchestrator [external/%s]: %.1fms, success=%s",
            model_type, result.execution_time_ms, result.success,
        )
        return result

    # ── Recursive Cycle: Simulate → Learn → Simulate Better ────────────

    def run_recursive_cycle(
        self,
        n_cycles: int = 3,
        introspective_space: str = "guna_balance",
        external_model: str = "sde",
        seed: int = 42,
    ) -> list[SimulationResult]:
        """Run a recursive yin/yang simulation cycle.

        Alternates between introspective (yin-within-yang) and external
        (yang-within-yin) simulation, feeding results forward:

            introspective → external → introspective → external → ...

        Each cycle's results inform the next cycle's parameters.
        """
        results: list[SimulationResult] = []

        for cycle in range(n_cycles):
            cycle_seed = seed + cycle * 1000

            # Yin-within-yang: introspective
            intro = self.run_introspective(
                space=introspective_space,
                n_trials=50,
                n_bo_iterations=15,
                seed=cycle_seed,
            )
            results.append(intro)

            # Yang-within-yin: external (using optimized params from introspective)
            ext_kwargs: dict[str, Any] = {"seed": cycle_seed + 1}
            if intro.best_params:
                ext_kwargs["x0"] = list(intro.best_params.values())[0] * 100
            ext = self.run_external(
                model_type=external_model,
                research_query=f"Cycle {cycle}: impact of {introspective_space} optimization",
                **ext_kwargs,
            )
            results.append(ext)

            logger.info(
                "Recursive cycle %d/%d: intro_fitness=%.4f, ext_success=%s",
                cycle + 1, n_cycles,
                intro.best_fitness, ext.success,
            )

        return results

    # ── Model-specific runners ─────────────────────────────────────────

    def _run_sde(self, orch: Any, **kwargs: Any) -> dict[str, Any]:
        """Run SDE simulation."""
        x0 = float(kwargs.get("x0", 100.0))
        t_end = float(kwargs.get("t_end", 1.0))
        n_steps = int(kwargs.get("n_steps", 100))
        n_paths = int(kwargs.get("n_paths", 1000))
        drift_type = kwargs.get("drift_type", "gbm")
        mu = float(kwargs.get("mu", 0.05))
        sigma = float(kwargs.get("sigma", 0.2))
        solver = kwargs.get("solver", "euler")
        seed = int(kwargs.get("seed", 42))
        use_mlmc = bool(kwargs.get("mlmc", False))

        if use_mlmc:
            return orch.sde_mlmc(
                x0=x0, t_end=t_end, n_levels=int(kwargs.get("n_levels", 3)),
                n_paths_fine=n_paths, drift_type=drift_type, mu=mu, sigma=sigma, seed=seed,
            )
        if n_paths > 1:
            return orch.sde_parallel_euler(
                x0=x0, t_end=t_end, n_steps=n_steps, n_paths=n_paths,
                drift_type=drift_type, mu=mu, sigma=sigma, seed=seed,
            )
        return orch.sde_euler(
            x0=x0, t_end=t_end, n_steps=n_steps,
            drift_type=drift_type, mu=mu, sigma=sigma, seed=seed,
        )

    def _run_rare_event(self, orch: Any, **kwargs: Any) -> dict[str, Any]:
        """Run rare event simulation."""
        method = kwargs.get("method", "subset")
        dim = int(kwargs.get("dim", 2))
        n_samples = int(kwargs.get("n_samples", 1000))
        threshold = float(kwargs.get("threshold", 2.0))
        g_expr = kwargs.get("g_expr", "threshold - sum_sq")
        seed = int(kwargs.get("seed", 42))

        if method == "splitting":
            return orch.multilevel_splitting(
                dim=dim, n_samples=n_samples,
                survival_fraction=float(kwargs.get("survival_fraction", 0.1)),
                threshold=threshold, g_expr=g_expr, seed=seed,
            )
        elif method == "importance":
            return orch.importance_sampling_rare(
                dim=dim, n_samples=n_samples,
                pilot_n=int(kwargs.get("pilot_n", 200)),
                threshold=threshold, g_expr=g_expr, seed=seed,
            )
        return orch.subset_simulation(
            dim=dim, n_samples=n_samples,
            target_pf=float(kwargs.get("target_pf", 0.001)),
            threshold=threshold, g_expr=g_expr, seed=seed,
        )

    def _run_superforecaster(self, orch: Any, **kwargs: Any) -> dict[str, Any]:
        """Run superforecaster pipeline."""
        param_ranges = kwargs.get("param_ranges", [[0.0, 1.0]])
        fitness_fn = kwargs.get("fitness_fn")
        if fitness_fn is None:
            expr = kwargs.get("fitness_expr", "x[0]")
            fitness_fn = lambda x: eval(expr, {"x": x, "sum": sum, "abs": abs, "max": max, "min": min})
        n_initial = int(kwargs.get("n_initial_samples", 100))
        n_bo = int(kwargs.get("n_bo_iterations", 20))
        seed = int(kwargs.get("seed", 42))

        return orch.superforecaster_estimate(
            param_ranges=[(r[0], r[1]) for r in param_ranges],
            fitness_fn=fitness_fn,
            n_initial_samples=n_initial,
            n_bo_iterations=n_bo,
            seed=seed,
        )

    # ── Persistence helpers ────────────────────────────────────────────

    def _persist_memory(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        importance: float = 0.6,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Persist to research galaxy. Returns memory ID or None."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            result = um.store(
                content=content,
                title=title,
                tags=tags or ["simulation"],
                galaxy="research",
                importance=importance,
                metadata=metadata or {},
            )
            return result.get("id") if isinstance(result, dict) else None
        except Exception as e:
            logger.debug("Memory persist: %s", e, exc_info=True)
            return None

    def _record_dag(
        self,
        hypothesis: str,
        parameters: dict[str, Any],
        fitness_score: float,
        outcome: dict[str, Any] | None = None,
    ) -> str | None:
        """Record in Research DAG. Returns experiment ID or None."""
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
            result = dag.record_result(
                exp.experiment_id,
                fitness_score=fitness_score,
                outcome=outcome,
            )
            return exp.experiment_id
        except Exception as e:
            logger.debug("DAG recording: %s", e, exc_info=True)
            return None

    # ── Status and history ─────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status."""
        with self._history_lock:
            recent = [r.to_dict() for r in self._results_history[-10:]]
            intro_count = sum(1 for r in self._results_history if r.mode == "introspective")
            ext_count = sum(1 for r in self._results_history if r.mode == "external")

        return {
            "total_simulations": len(self._results_history),
            "introspective_count": intro_count,
            "external_count": ext_count,
            "recent_results": recent,
        }

    def get_cached_result(self, cache_key: str) -> SimulationResult | None:
        """Get a cached simulation result by key."""
        with self._cache_lock:
            return self._cache.get(cache_key)

    def cache_result(self, cache_key: str, result: SimulationResult) -> None:
        """Cache a simulation result for future reference."""
        with self._cache_lock:
            self._cache[cache_key] = result
            if len(self._cache) > 200:
                keys = list(self._cache.keys())
                for k in keys[:50]:
                    del self._cache[k]


def get_simulation_orchestrator() -> SimulationOrchestrator:
    """Get the singleton SimulationOrchestrator instance."""
    return SimulationOrchestrator.get_instance()
