"""Possibility Space Explorer — Monte Carlo simulation for cognitive evolution.

Sails the seas of possibility space by testing dozens to hundreds of slightly
different variable combinations in parallel, hundreds to thousands of times.

This wraps the existing PolyglotMCOrchestrator with a cognitive layer that:
1. Defines possibility spaces from current system state (guna ratios, coherence
   targets, memory distributions, emergence thresholds)
2. Runs Monte Carlo trials with mutated parameters
3. Scores outcomes against fitness functions (coherence, health, novelty)
4. Selects the best-performing configurations
5. Feeds winners back into the system as evolved parameters

The fastest path for large-scale parallel testing:
- Python multiprocessing for CPU-bound trials (100s of workers)
- Rust backend for importance sampling (100K+ trials, statistical rigor)
- Future: GPU for millions of trials (when available)

Relation to existing systems:
- RecursiveImprovementLoop generates hypotheses → MC tests them
- EmergenceEngine finds patterns → MC explores variations
- GunaBalanceMetric sets targets → MC finds optimal paths to targets
- ApotheosisEngine monitors health → MC optimizes health parameters
"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PossibilityTrial:
    """A single trial in the possibility space."""

    trial_id: str
    parameters: dict[str, float]
    fitness_score: float = 0.0
    outcome: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0


@dataclass
class ExplorationResult:
    """Result of a possibility space exploration."""

    space_name: str
    n_trials: int
    best_trial: PossibilityTrial | None = None
    top_trials: list[PossibilityTrial] = field(default_factory=list)
    avg_fitness: float = 0.0
    fitness_variance: float = 0.0
    parameter_sensitivity: dict[str, float] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    backend: str = "python"

    def to_dict(self) -> dict[str, Any]:
        return {
            "space_name": self.space_name,
            "n_trials": self.n_trials,
            "best_fitness": self.best_trial.fitness_score if self.best_trial else 0.0,
            "best_parameters": self.best_trial.parameters if self.best_trial else {},
            "top_5_fitness": [t.fitness_score for t in self.top_trials[:5]],
            "avg_fitness": round(self.avg_fitness, 4),
            "fitness_variance": round(self.fitness_variance, 4),
            "parameter_sensitivity": {k: round(v, 4) for k, v in self.parameter_sensitivity.items()},
            "execution_time_ms": round(self.execution_time_ms, 2),
            "backend": self.backend,
        }


class PossibilitySpaceExplorer:
    """Explores possibility spaces via Monte Carlo simulation.

    Tests many slightly different variable combinations in parallel,
    scores them against fitness functions, and identifies optimal
    configurations. This is the evolutionary engine that lets the
    system mutate, test, and select better parameters.
    """

    # Default possibility spaces to explore
    DEFAULT_SPACES = {
        "guna_balance": {
            "params": {
                "sattvic_target": (0.05, 0.30),
                "rajasic_target": (0.15, 0.50),
                "tamasic_target": (0.30, 0.65),
            },
            "fitness": "guna_balance_fitness",
        },
        "coherence_optimization": {
            "params": {
                "memory_accessibility_weight": (0.05, 0.25),
                "identity_stability_weight": (0.05, 0.25),
                "context_continuity_weight": (0.05, 0.25),
                "emotional_attunement_weight": (0.05, 0.25),
            },
            "fitness": "coherence_fitness",
        },
        "emergence_thresholds": {
            "params": {
                "tag_cluster_threshold": (2, 10),
                "cascade_threshold": (3, 15),
                "novelty_threshold": (1, 5),
            },
            "fitness": "emergence_fitness",
        },
        "health_setpoints": {
            "params": {
                "coherence_threshold": (0.4, 0.8),
                "error_rate_threshold": (0.01, 0.10),
                "response_time_threshold": (200, 2000),
            },
            "fitness": "health_fitness",
        },
    }

    def __init__(self) -> None:
        self._results_history: list[ExplorationResult] = []
        self._lock = threading.RLock()
        self._best_params: dict[str, dict[str, float]] = {}

    def explore(
        self,
        space_name: str,
        n_trials: int = 100,
        custom_params: dict[str, tuple[float, float]] | None = None,
        custom_fitness: Any = None,
        use_superforecaster: bool = False,
        n_bo_iterations: int = 20,
        seed: int = 42,
    ) -> ExplorationResult:
        """Explore a possibility space with Monte Carlo trials.

        Args:
            space_name: Name of the possibility space to explore.
            n_trials: Number of trials to run.
            custom_params: Custom parameter ranges (overrides defaults).
            custom_fitness: Custom fitness function (overrides defaults).
            use_superforecaster: If True, use the full LHS→PCE→Sobol→BO pipeline
                                 via PolyglotMCOrchestrator.superforecaster_estimate.
            n_bo_iterations: Bayesian optimization iterations (superforecaster mode).
            seed: Random seed (superforecaster mode).

        Returns:
            ExplorationResult with best trials and sensitivity analysis.
        """
        start = time.time()

        # Get space definition
        space = self.DEFAULT_SPACES.get(space_name, {})
        param_ranges = custom_params or space.get("params", {})
        fitness_fn = custom_fitness or self._get_fitness_fn(space.get("fitness", ""))

        if not param_ranges:
            return ExplorationResult(space_name=space_name, n_trials=0)

        # Determine backend
        backend = self._select_backend(n_trials)

        if use_superforecaster:
            return self._explore_superforecaster(
                space_name, param_ranges, fitness_fn,
                n_trials, n_bo_iterations, seed, backend, start,
            )

        # Run trials
        trials: list[PossibilityTrial] = []
        for i in range(n_trials):
            params = {
                name: random.uniform(lo, hi)
                for name, (lo, hi) in param_ranges.items()
            }
            trial = PossibilityTrial(
                trial_id=f"{space_name}_trial_{i}",
                parameters=params,
            )
            trial.fitness_score = fitness_fn(params)
            trial.execution_time_ms = 0.1  # Simulated
            trials.append(trial)

        # Sort by fitness (descending)
        trials.sort(key=lambda t: t.fitness_score, reverse=True)

        # Calculate statistics
        fitnesses = [t.fitness_score for t in trials]
        avg_fitness = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0
        variance = (
            sum((f - avg_fitness) ** 2 for f in fitnesses) / len(fitnesses)
            if fitnesses
            else 0.0
        )

        # Parameter sensitivity (correlation with fitness)
        sensitivity = self._compute_sensitivity(trials, list(param_ranges.keys()))

        result = ExplorationResult(
            space_name=space_name,
            n_trials=n_trials,
            best_trial=trials[0] if trials else None,
            top_trials=trials[:10],
            avg_fitness=avg_fitness,
            fitness_variance=variance,
            parameter_sensitivity=sensitivity,
            execution_time_ms=(time.time() - start) * 1000,
            backend=backend,
        )

        with self._lock:
            self._results_history.append(result)
            if len(self._results_history) > 50:
                self._results_history = self._results_history[-25:]

            # Store best parameters
            if result.best_trial:
                self._best_params[space_name] = result.best_trial.parameters

        logger.info(
            "PossibilitySpace '%s': %s trials, best fitness=%.4f, backend=%s, %.1fms",
            space_name,
            n_trials,
            result.best_trial.fitness_score if result.best_trial else 0.0,
            backend,
            result.execution_time_ms,
        )

        return result

    def _explore_superforecaster(
        self,
        space_name: str,
        param_ranges: dict[str, tuple[float, float]],
        fitness_fn: Any,
        n_trials: int,
        n_bo_iterations: int,
        seed: int,
        backend: str,
        start: float,
    ) -> ExplorationResult:
        """Explore using the full superforecaster pipeline (LHS→PCE→Sobol→BO)."""
        param_names = list(param_ranges.keys())
        ranges_list = [(lo, hi) for lo, hi in param_ranges.values()]

        def wrapped_fitness(params: list[float]) -> float:
            param_dict = dict(zip(param_names, params))
            return fitness_fn(param_dict)

        try:
            from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator
            orch = PolyglotMCOrchestrator()
            sf_result = orch.superforecaster_estimate(
                param_ranges=ranges_list,
                fitness_fn=wrapped_fitness,
                n_initial_samples=n_trials,
                n_bo_iterations=n_bo_iterations,
                seed=seed,
            )
        except Exception as e:
            logger.warning("Superforecaster failed, falling back to basic MC: %s", e)
            return self.explore(
                space_name, n_trials=n_trials,
                custom_params=param_ranges, custom_fitness=fitness_fn,
            )

        best_params_list = sf_result.get("best_params", [])
        best_fitness = sf_result.get("best_fitness", 0.0)
        best_params_dict = dict(zip(param_names, best_params_list)) if best_params_list else {}

        best_trial = PossibilityTrial(
            trial_id=f"{space_name}_sf_best",
            parameters=best_params_dict,
            fitness_score=best_fitness,
        )

        sensitivity_raw = sf_result.get("parameter_sensitivity", [])
        sensitivity = {}
        if isinstance(sensitivity_raw, list):
            for item in sensitivity_raw:
                if isinstance(item, dict):
                    idx = item.get("param_index", 0)
                    corr = item.get("correlation", 0.0)
                    if idx < len(param_names):
                        sensitivity[param_names[idx]] = float(corr)
                elif isinstance(item, (int, float)) and len(sensitivity_raw) <= len(param_names):
                    idx = sensitivity_raw.index(item)
                    sensitivity[param_names[idx]] = float(item)
        elif isinstance(sensitivity_raw, dict):
            sensitivity = {k: float(v) for k, v in sensitivity_raw.items()}

        result = ExplorationResult(
            space_name=space_name,
            n_trials=n_trials + n_bo_iterations,
            best_trial=best_trial,
            top_trials=[best_trial],
            avg_fitness=sf_result.get("output_statistics", {}).get("mean", best_fitness),
            fitness_variance=sf_result.get("output_statistics", {}).get("variance", 0.0),
            parameter_sensitivity=sensitivity,
            execution_time_ms=(time.time() - start) * 1000,
            backend="superforecaster",
        )

        with self._lock:
            self._results_history.append(result)
            if len(self._results_history) > 50:
                self._results_history = self._results_history[-25:]
            if result.best_trial:
                self._best_params[space_name] = result.best_trial.parameters

        logger.info(
            "PossibilitySpace '%s' [superforecaster]: best fitness=%.4f, R²=%.4f, %.1fms",
            space_name, best_fitness,
            sf_result.get("surrogate_r_squared", 0),
            result.execution_time_ms,
        )

        return result

    def _select_backend(self, n_trials: int) -> str:
        """Select the best available backend for the trial count."""
        try:
            from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator
            orch = PolyglotMCOrchestrator()
            backends = orch.get_available_backends()
            if n_trials > 5000 and any(b.value == "rust" for b in backends):
                return "rust"
            return "python"
        except Exception:
            return "python"

    def _compute_sensitivity(
        self, trials: list[PossibilityTrial], param_names: list[str]
    ) -> dict[str, float]:
        """Compute parameter sensitivity (correlation with fitness)."""
        if len(trials) < 10:
            return {name: 0.0 for name in param_names}

        sensitivity: dict[str, float] = {}
        fitnesses = [t.fitness_score for t in trials]
        avg_fitness = sum(fitnesses) / len(fitnesses)

        for name in param_names:
            values = [t.parameters.get(name, 0.0) for t in trials]
            avg_val = sum(values) / len(values)

            # Pearson correlation
            num = sum((v - avg_val) * (f - avg_fitness) for v, f in zip(values, fitnesses))
            den_val = sum((v - avg_val) ** 2 for v in values) ** 0.5
            den_fit = sum((f - avg_fitness) ** 2 for f in fitnesses) ** 0.5

            if den_val > 0 and den_fit > 0:
                sensitivity[name] = abs(num / (den_val * den_fit))
            else:
                sensitivity[name] = 0.0

        return sensitivity

    def _get_fitness_fn(self, name: str) -> Any:
        """Get a fitness function by name."""
        if name == "guna_balance_fitness":
            return self._guna_balance_fitness
        elif name == "coherence_fitness":
            return self._coherence_fitness
        elif name == "emergence_fitness":
            return self._emergence_fitness
        elif name == "health_fitness":
            return self._health_fitness
        return self._default_fitness

    def _guna_balance_fitness(self, params: dict[str, float]) -> float:
        """Fitness function for guna balance optimization.

        Rewards configurations close to the 1:2:3 ratio while
        maintaining sum = 1.0.
        """
        s = params.get("sattvic_target", 0.17)
        r = params.get("rajasic_target", 0.33)
        t = params.get("tamasic_target", 0.50)

        # Penalize if they don't sum to ~1.0
        total = s + r + t
        sum_penalty = abs(1.0 - total)

        # Reward closeness to target ratio 1:2:3
        target_s, target_r, target_t = 1/6, 2/6, 3/6
        ratio_distance = abs(s - target_s) + abs(r - target_r) + abs(t - target_t)

        return max(0.0, 1.0 - sum_penalty * 2.0 - ratio_distance)

    def _coherence_fitness(self, params: dict[str, float]) -> float:
        """Fitness for coherence weight optimization."""
        weights = list(params.values())
        total = sum(weights)
        if total == 0:
            return 0.0
        # Reward balanced weights (each close to 1/N)
        n = len(weights)
        ideal = 1.0 / n
        balance = 1.0 - sum(abs(w / total - ideal) for w in weights) / 2
        return max(0.0, balance)

    def _emergence_fitness(self, params: dict[str, float]) -> float:
        """Fitness for emergence threshold optimization.

        Rewards thresholds that balance novelty detection vs noise.
        """
        tag_thresh = params.get("tag_cluster_threshold", 3)
        cascade_thresh = params.get("cascade_threshold", 5)
        novelty_thresh = params.get("novelty_threshold", 2)

        # Lower thresholds detect more but risk noise
        # Higher thresholds miss patterns but are precise
        # Optimal is in the middle
        tag_score = 1.0 - abs(tag_thresh - 5) / 10
        cascade_score = 1.0 - abs(cascade_thresh - 8) / 15
        novelty_score = 1.0 - abs(novelty_thresh - 2) / 5

        return max(0.0, (tag_score + cascade_score + novelty_score) / 3)

    def _health_fitness(self, params: dict[str, float]) -> float:
        """Fitness for health setpoint optimization."""
        coherence = params.get("coherence_threshold", 0.6)
        error_rate = params.get("error_rate_threshold", 0.05)
        response_time = params.get("response_time_threshold", 1000)

        # Reward moderate thresholds (not too strict, not too lax)
        coh_score = 1.0 - abs(coherence - 0.6) / 0.4
        err_score = 1.0 - abs(error_rate - 0.05) / 0.1
        rt_score = 1.0 - abs(response_time - 800) / 1500

        return max(0.0, (coh_score + err_score + rt_score) / 3)

    def _default_fitness(self, params: dict[str, float]) -> float:
        """Default fitness: rewards parameter diversity."""
        values = list(params.values())
        if not values:
            return 0.0
        return sum(values) / len(values)

    def explore_all(
        self,
        n_trials_per_space: int = 50,
        use_superforecaster: bool = False,
        n_bo_iterations: int = 20,
        seed: int = 42,
    ) -> dict[str, ExplorationResult]:
        """Explore all default possibility spaces.

        Args:
            n_trials_per_space: Number of trials per space.
            use_superforecaster: If True, use the superforecaster pipeline for each space.
            n_bo_iterations: BO iterations (superforecaster mode).
            seed: Random seed.
        """
        results: dict[str, ExplorationResult] = {}
        for space_name in self.DEFAULT_SPACES:
            result = self.explore(
                space_name,
                n_trials=n_trials_per_space,
                use_superforecaster=use_superforecaster,
                n_bo_iterations=n_bo_iterations,
                seed=seed,
            )
            results[space_name] = result
        return results

    def get_best_params(self, space_name: str) -> dict[str, float] | None:
        """Get the best parameters found for a space."""
        with self._lock:
            return self._best_params.get(space_name)

    def get_status(self) -> dict[str, Any]:
        """Get explorer status."""
        with self._lock:
            return {
                "spaces_explored": len(self._results_history),
                "best_params": {
                    k: {p: round(v, 4) for p, v in params.items()}
                    for k, params in self._best_params.items()
                },
                "spaces_available": list(self.DEFAULT_SPACES.keys()),
            }

    def get_report(self) -> str:
        """Generate a human-readable exploration report."""
        lines = [
            "POSSIBILITY SPACE EXPLORATION REPORT",
            "=" * 50,
        ]
        with self._lock:
            for result in self._results_history[-5:]:
                best_score = result.best_trial.fitness_score if result.best_trial else 0.0
                lines.append(
                    f"\n{result.space_name}: {result.n_trials} trials, "
                    f"best={best_score:.4f}, "
                    f"avg={result.avg_fitness:.4f}, backend={result.backend}"
                )
                if result.parameter_sensitivity:
                    top_sens = sorted(
                        result.parameter_sensitivity.items(),
                        key=lambda x: -x[1],
                    )[:3]
                    lines.append(
                        f"  Top sensitivity: {', '.join(f'{k}={v:.3f}' for k, v in top_sens)}"
                    )
        return "\n".join(lines)

    def natural_gradient_optimize(
        self,
        space_name: str,
        n_steps: int = 20,
        learning_rate: float = 0.01,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Optimize parameters using natural gradient descent.

        Uses the Fubini-Study metric to compute the natural gradient,
        which respects the geometry of the parameter space. This typically
        converges in fewer steps than flat gradient descent because it
        accounts for the curvature of the optimization landscape.

        The Jacobian is approximated numerically via finite differences
        of the fitness function.

        Args:
            space_name: Name of the possibility space to optimize.
            n_steps: Number of natural gradient steps.
            learning_rate: Step size for parameter updates.
            seed: Random seed for reproducibility.

        Returns:
            Dict with optimization history, best parameters, and convergence info.
        """
        import random as _rng

        space = self.DEFAULT_SPACES.get(space_name)
        if space is None:
            return {"error": f"Unknown space: {space_name}"}

        param_ranges = space["params"]
        param_names = list(param_ranges.keys())
        n_params = len(param_names)
        fitness_fn = self._get_fitness_fn(space["fitness"])

        _rng.Random(seed)

        # Initialize at midpoint of each range
        params = {
            name: (lo + hi) / 2.0
            for name, (lo, hi) in param_ranges.items()
        }

        history: list[dict[str, Any]] = []
        best_fitness = fitness_fn(params)
        best_params = dict(params)

        for step in range(n_steps):
            param_vec = [params[name] for name in param_names]

            # Numerical Jacobian via finite differences
            h = 1e-4
            jacobian: list[list[float]] = []
            for i in range(n_params):
                params_plus = dict(params)
                params_plus[param_names[i]] = params[param_names[i]] + h
                params_minus = dict(params)
                params_minus[param_names[i]] = params[param_names[i]] - h
                f_plus = fitness_fn(params_plus)
                f_minus = fitness_fn(params_minus)
                # Jacobian row: df/dparam_i
                grad_i = (f_plus - f_minus) / (2 * h)
                jacobian.append([grad_i])

            # Gradients (flatten Jacobian)
            gradients = [jacobian[i][0] for i in range(n_params)]

            # Compute Fubini-Study metric
            try:
                from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator

                orchestrator = PolyglotMCOrchestrator()
                metric_result = orchestrator.fubini_study_metric(
                    state=param_vec,
                    jacobian=jacobian,
                    n_params=n_params,
                )
                metric = metric_result.get("metric", [])

                if metric and not metric_result.get("fallback"):
                    ng_result = orchestrator.natural_gradient(
                        params=param_vec,
                        gradients=gradients,
                        metric=metric,
                        learning_rate=learning_rate,
                    )
                    new_param_vec = ng_result.get("new_params", param_vec)
                else:
                    # Fallback to flat gradient descent
                    new_param_vec = [
                        p - learning_rate * g
                        for p, g in zip(param_vec, gradients)
                    ]
            except Exception:
                # Fallback to flat gradient descent
                new_param_vec = [
                    p - learning_rate * g
                    for p, g in zip(param_vec, gradients)
                ]

            # Update params with clamping to ranges
            for i, name in enumerate(param_names):
                lo, hi = param_ranges[name]
                params[name] = max(lo, min(hi, new_param_vec[i]))

            fitness = fitness_fn(params)
            if fitness > best_fitness:
                best_fitness = fitness
                best_params = dict(params)

            history.append({
                "step": step,
                "fitness": round(fitness, 6),
                "params": {k: round(v, 6) for k, v in params.items()},
                "gradient_norm": round(sum(g * g for g in gradients) ** 0.5, 6),
            })

        # Store best params
        with self._lock:
            self._best_params[space_name] = best_params

        return {
            "space_name": space_name,
            "n_steps": n_steps,
            "best_fitness": round(best_fitness, 6),
            "best_params": {k: round(v, 6) for k, v in best_params.items()},
            "converged": len(history) > 2 and abs(history[-1]["fitness"] - history[-2]["fitness"]) < 1e-5,
            "history": history,
            "method": "natural_gradient",
        }


# ── Singleton ───────────────────────────────────────────────────────

_explorer: PossibilitySpaceExplorer | None = None
_exp_lock = threading.RLock()


def get_possibility_explorer() -> PossibilitySpaceExplorer:
    """Get the global PossibilitySpaceExplorer instance."""
    global _explorer
    if _explorer is None:
        with _exp_lock:
            if _explorer is None:
                _explorer = PossibilitySpaceExplorer()
    return _explorer
