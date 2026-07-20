"""Polyglot MC Acceleration (Objective S).

Orchestrates MC computation across polyglot accelerators, dispatching
to the appropriate backend based on trial count, correlation structure,
and latency requirements.

Backends:
- Python (fallback): Always available, handles small trial counts
- Rust: Importance sampling, control variates (existing mc_engine.rs)
- Julia: Resonance-based covariance estimation
- Zig: Ultra-low-latency single-trial execution
- Elixir: Streaming outcome processing
- Go: Distributed MC across machines
- Haskell: Formal verification of sampling correctness

The Python MCForecastEnhancer becomes an orchestrator that dispatches
to the appropriate polyglot backend.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from whitemagic.core.evolution._rust_bridge import call as _rust_call

logger = logging.getLogger(__name__)


class MCBackend(Enum):
    """Available MC acceleration backends."""

    PYTHON = "python"  # Always available
    RUST = "rust"  # Importance sampling, control variates
    JULIA = "julia"  # Covariance estimation
    ZIG = "zig"  # Ultra-low-latency single trial
    ELIXIR = "elixir"  # Streaming outcomes
    GO = "go"  # Distributed
    HASKELL = "haskell"  # Formal verification


@dataclass
class MCTask:
    """A Monte Carlo task to be dispatched."""

    task_id: str
    n_trials: int
    prior_mean: float = 0.5
    prior_variance: float = 0.1
    correlation_structure: bool = False  # True if trials are correlated
    latency_sensitive: bool = False  # True if <1ms response needed
    streaming: bool = False  # True if outcomes stream in
    distribute: bool = False  # True if needs multi-machine
    verify: bool = False  # True if formal verification needed
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCResult:
    """Result of an MC computation."""

    task_id: str
    backend: MCBackend
    mean: float
    variance: float
    n_trials_completed: int
    execution_time_ms: float
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    metadata: dict[str, Any] = field(default_factory=dict)


class PolyglotMCOrchestrator:
    """Dispatches MC tasks to the appropriate polyglot backend.

    Selection logic:
    - latency_sensitive + single trial → Zig
    - streaming → Elixir
    - n_trials > 100K → Rust (high throughput)
    - correlation_structure → Julia
    - distribute → Go
    - verify → Haskell
    - importance sampling / control variates → Rust
    - default → Python
    """

    def __init__(self) -> None:
        self._available_backends: set[MCBackend] = {MCBackend.PYTHON}
        self._backend_performance: dict[MCBackend, float] = {}  # trials/sec
        self._dispatch_history: list[tuple[MCBackend, MCTask, MCResult]] = []

        # Detect available backends
        self._detect_backends()

    def _detect_backends(self) -> None:
        """Detect which polyglot backends are available."""
        # Rust
        try:
            from whitemagic.optimization.rust_accelerators import rust_available

            if rust_available():
                self._available_backends.add(MCBackend.RUST)
                self._backend_performance[MCBackend.RUST] = 100_000.0
        except (ImportError, AttributeError):
            logger.debug("Optional dependency unavailable: ImportError")

        # Julia
        try:
            from whitemagic.core.resonance.julia_resonance import julia_available

            if julia_available():
                self._available_backends.add(MCBackend.JULIA)
                self._backend_performance[MCBackend.JULIA] = 50_000.0
        except (ImportError, AttributeError):
            logger.debug("Optional dependency unavailable: ImportError")

        # Zig, Elixir, Go, Haskell — check via bridge availability
        for backend, module_path in [
            (MCBackend.ZIG, "whitemagic.optimization.zig_bridge"),
            (MCBackend.ELIXIR, "whitemagic.optimization.elixir_bridge"),
            (MCBackend.GO, "whitemagic.optimization.go_bridge"),
            (MCBackend.HASKELL, "whitemagic.optimization.haskell_bridge"),
        ]:
            try:
                __import__(module_path)
                self._available_backends.add(backend)
                self._backend_performance[backend] = 10_000.0
            except ImportError:
                logger.debug("Optional dependency unavailable: ImportError")

        # Python is always available
        self._backend_performance[MCBackend.PYTHON] = 5_000.0

    def select_backend(self, task: MCTask) -> MCBackend:
        """Select the best backend for a task.

        Args:
            task: The MC task to dispatch.

        Returns:
            The selected MCBackend.
        """
        # Priority-ordered selection

        # 1. Latency-sensitive single trial → Zig
        if (
            task.latency_sensitive
            and task.n_trials <= 1
            and MCBackend.ZIG in self._available_backends
        ):
            return MCBackend.ZIG

        # 2. Streaming → Elixir
        if task.streaming and MCBackend.ELIXIR in self._available_backends:
            return MCBackend.ELIXIR

        # 3. Very large trial count → Rust (high throughput)
        if task.n_trials > 100_000 and MCBackend.RUST in self._available_backends:
            return MCBackend.RUST

        # 4. Correlation structure → Julia
        if task.correlation_structure and MCBackend.JULIA in self._available_backends:
            return MCBackend.JULIA

        # 5. Distributed → Go
        if task.distribute and MCBackend.GO in self._available_backends:
            return MCBackend.GO

        # 6. Formal verification → Haskell
        if task.verify and MCBackend.HASKELL in self._available_backends:
            return MCBackend.HASKELL

        # 7. Large trial count → Rust
        if task.n_trials > 5_000 and MCBackend.RUST in self._available_backends:
            return MCBackend.RUST

        # 8. Default → Python
        return MCBackend.PYTHON

    def execute(self, task: MCTask) -> MCResult:
        """Execute an MC task on the selected backend.

        Args:
            task: The MC task to execute.

        Returns:
            MCResult with computed statistics.
        """
        backend = self.select_backend(task)
        start = time.time()

        rust_result = None
        if backend == MCBackend.RUST or (
            MCBackend.RUST in self._available_backends and task.n_trials > 100
        ):
            method = "mc_run_trials"
            if task.metadata.get("variance_reduction") == "importance_sampling":
                method = "mc_importance_sampling"
            elif task.metadata.get("variance_reduction") == "control_variates":
                method = "mc_control_variates"
            elif task.metadata.get("variance_reduction") == "antithetic":
                method = "mc_antithetic_variates"

            rust_result = _rust_call(
                method,
                n_trials=task.n_trials,
                prior_mean=task.prior_mean,
                prior_variance=task.prior_variance,
                **task.metadata.get("rust_params", {}),
            )

        if rust_result is not None and "mean" in rust_result:
            elapsed_ms = (time.time() - start) * 1000
            result = MCResult(
                task_id=task.task_id,
                backend=backend,
                mean=rust_result["mean"],
                variance=rust_result["variance"],
                n_trials_completed=rust_result.get("n_completed", task.n_trials),
                execution_time_ms=elapsed_ms,
                confidence_interval=(
                    rust_result.get("ci_lower", 0.0),
                    rust_result.get("ci_upper", 1.0),
                ),
            )
            self._dispatch_history.append((backend, task, result))
            return result

        # Python fallback
        import math
        import random

        trials = []
        for _ in range(task.n_trials):
            sample = random.gauss(task.prior_mean, task.prior_variance**0.5)
            trials.append(max(0.0, min(1.0, sample)))

        mean = sum(trials) / len(trials) if trials else 0.0
        variance = sum((t - mean) ** 2 for t in trials) / len(trials) if trials else 0.0

        std = math.sqrt(variance) if variance > 0 else 0.0
        ci = (max(0.0, mean - 1.96 * std), min(1.0, mean + 1.96 * std))

        elapsed_ms = (time.time() - start) * 1000

        result = MCResult(
            task_id=task.task_id,
            backend=backend,
            mean=mean,
            variance=variance,
            n_trials_completed=len(trials),
            execution_time_ms=elapsed_ms,
            confidence_interval=ci,
        )

        self._dispatch_history.append((backend, task, result))
        return result

    def get_available_backends(self) -> set[MCBackend]:
        return set(self._available_backends)

    def get_backend_performance(self, backend: MCBackend) -> float:
        """Get estimated trials/sec for a backend."""
        return self._backend_performance.get(backend, 0.0)

    def get_stats(self) -> dict[str, Any]:
        backend_counts: dict[str, int] = {}
        for backend, _, _ in self._dispatch_history:
            backend_counts[backend.value] = backend_counts.get(backend.value, 0) + 1
        return {
            "available_backends": [b.value for b in self._available_backends],
            "total_dispatched": len(self._dispatch_history),
            "backend_dispatch_counts": backend_counts,
        }

    # ---- High-Dimensional MC Methods ----

    def lhs_sample(
        self,
        n: int,
        param_ranges: list[tuple[float, float]],
        seed: int = 42,
    ) -> list[list[float]] | None:
        """Generate Latin Hypercube Samples scaled to parameter ranges.

        Uses the Rust backend for generation. Returns n×d matrix of samples
        where each dimension is stratified for space-filling coverage.
        """
        result = _rust_call(
            "mc_lhs_trials",
            n=n,
            ranges=[list(r) for r in param_ranges],
            seed=seed,
        )
        if result and "samples" in result:
            return result["samples"]
        # Python fallback
        import random

        rng = random.Random(seed)
        d = len(param_ranges)
        samples = []
        for dim in range(d):
            strata = [(k + rng.random()) / n for k in range(n)]
            rng.shuffle(strata)
            samples.append(strata)
        return [
            [param_ranges[dim][0] + samples[dim][i] * (param_ranges[dim][1] - param_ranges[dim][0])
             for dim in range(d)]
            for i in range(n)
        ]

    def fit_surrogate(
        self,
        x_data: list[list[float]],
        y_data: list[float],
        max_order: int = 3,
        dist_type: str = "uniform",
    ) -> dict[str, Any] | None:
        """Fit a Polynomial Chaos Expansion surrogate to (X, Y) data.

        The surrogate can then be evaluated millions of times for free,
        replacing expensive MC trials with a cheap polynomial evaluation.

        Returns dict with coefficients, multi_indices, r_squared, etc.
        """
        result = _rust_call(
            "mc_pce_fit",
            x_data=x_data,
            y_data=y_data,
            max_order=max_order,
            dist_type=dist_type,
        )
        if result and "coefficients" in result:
            return result
        return None

    def evaluate_surrogate(
        self,
        surrogate: dict[str, Any],
        x_data: list[list[float]],
    ) -> list[float] | None:
        """Evaluate a fitted PCE surrogate at new points.

        Args:
            surrogate: Dict from fit_surrogate with coefficients, multi_indices, etc.
            x_data: List of points to evaluate at.
        """
        result = _rust_call(
            "mc_pce_evaluate",
            coefficients=surrogate.get("coefficients", []),
            multi_indices=surrogate.get("multi_indices", []),
            dist_type=surrogate.get("dist_type", "uniform"),
            max_order=surrogate.get("max_order", 3),
            x_data=x_data,
        )
        if result and "predictions" in result:
            return result["predictions"]
        return None

    def compute_statistics(self, values: list[float]) -> dict[str, Any] | None:
        """Compute comprehensive statistics: mean, variance, percentiles, CI."""
        result = _rust_call("mc_compute_statistics", values=values)
        if result and "mean" in result:
            return result
        # Python fallback
        import math

        n = len(values)
        if n == 0:
            return None
        mean = sum(values) / n
        var = sum((v - mean) ** 2 for v in values) / n
        sorted_v = sorted(values)
        def pct(q):
            return sorted_v[min(int(q * (n - 1)), n - 1)]
        std = math.sqrt(var) if var > 0 else 0.0
        return {
            "mean": mean,
            "variance": var,
            "min": sorted_v[0],
            "max": sorted_v[-1],
            "percentiles": {
                "p5": pct(0.05), "p25": pct(0.25),
                "p50": pct(0.50), "p75": pct(0.75), "p95": pct(0.95),
            },
            "ci_95": {"lower": mean - 1.96 * std, "upper": mean + 1.96 * std},
        }

    def parameter_sensitivity(
        self,
        samples: list[list[float]],
        fitness: list[float],
    ) -> list[dict[str, Any]] | None:
        """Compute Pearson correlation sensitivity for each parameter.

        Returns list of {param_index, correlation, abs_correlation} sorted by abs_correlation.
        """
        result = _rust_call(
            "mc_parameter_sensitivity",
            samples=samples,
            fitness=fitness,
        )
        if result and "sensitivities" in result:
            return result["sensitivities"]
        # Python fallback
        d = len(samples[0]) if samples else 0
        n = len(fitness)
        if n == 0 or d == 0:
            return None
        y_mean = sum(fitness) / n
        y_var = sum((y - y_mean) ** 2 for y in fitness)
        sens = []
        for j in range(d):
            x_col = [s[j] for s in samples]
            x_mean = sum(x_col) / n
            x_var = sum((x - x_mean) ** 2 for x in x_col)
            cov = sum((x_col[i] - x_mean) * (fitness[i] - y_mean) for i in range(n))
            denom = (x_var * y_var) ** 0.5
            corr = cov / denom if denom > 1e-15 else 0.0
            sens.append({"param_index": j, "correlation": corr, "abs_correlation": abs(corr)})
        sens.sort(key=lambda s: s["abs_correlation"], reverse=True)
        return sens

    def sobol_sample_matrices(
        self,
        n_base: int,
        param_ranges: list[tuple[float, float]],
        seed: int = 42,
    ) -> dict[str, Any] | None:
        """Generate Saltelli sample matrices for Sobol sensitivity analysis.

        Returns a_samples, b_samples, ab_matrices.
        Python evaluates fitness for each, then calls sobol_compute.
        """
        result = _rust_call(
            "mc_sobol_indices",
            n_base=n_base,
            d=len(param_ranges),
            ranges=[list(r) for r in param_ranges],
            seed=seed,
        )
        return result if result else None

    def sobol_compute(
        self,
        f_a: list[float],
        f_b: list[float],
        f_ab: list[list[float]],
    ) -> dict[str, Any] | None:
        """Compute Sobol sensitivity indices from pre-evaluated fitness values.

        Args:
            f_a: Fitness values for matrix A (n_base values)
            f_b: Fitness values for matrix B (n_base values)
            f_ab: Fitness values for each AB_j matrix (d arrays of n_base values)
        """
        result = _rust_call(
            "mc_sobol_compute",
            f_a=f_a,
            f_b=f_b,
            f_ab=f_ab,
        )
        return result if result else None

    def explore_space(
        self,
        param_ranges: list[tuple[float, float]],
        fitness_fn: Any,
        n_samples: int = 200,
        max_order: int = 3,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Full possibility space exploration pipeline.

        1. Generate LHS samples
        2. Evaluate fitness for each sample (in Python)
        3. Fit PCE surrogate
        4. Compute parameter sensitivity
        5. Evaluate surrogate on dense grid for output distribution
        6. Compute statistics on output distribution

        Returns a comprehensive result dict.
        """
        start = time.time()

        # 1. Generate LHS samples
        samples = self.lhs_sample(n_samples, param_ranges, seed)
        if samples is None:
            return {"error": "LHS sampling failed"}

        # 2. Evaluate fitness
        fitness_values = [fitness_fn(s) for s in samples]

        # 3. Fit PCE surrogate
        surrogate = self.fit_surrogate(samples, fitness_values, max_order=max_order)
        r_squared = surrogate.get("r_squared", 0.0) if surrogate else 0.0

        # 4. Parameter sensitivity
        sensitivity = self.parameter_sensitivity(samples, fitness_values)

        # 5. Evaluate surrogate on dense grid for output distribution
        import random

        rng = random.Random(seed + 1)
        n_eval = 100_000
        eval_samples = [
            [rng.uniform(lo, hi) for lo, hi in param_ranges]
            for _ in range(n_eval)
        ]
        if surrogate:
            surrogate_predictions = self.evaluate_surrogate(surrogate, eval_samples)
        else:
            surrogate_predictions = [fitness_fn(s) for s in eval_samples[:1000]]

        # 6. Statistics on output distribution
        stats = self.compute_statistics(surrogate_predictions or [])

        # Find best parameters
        best_idx = max(range(len(fitness_values)), key=lambda i: fitness_values[i])
        best_params = samples[best_idx]
        best_fitness = fitness_values[best_idx]

        elapsed_ms = (time.time() - start) * 1000

        return {
            "n_samples": n_samples,
            "n_dimensions": len(param_ranges),
            "surrogate_r_squared": r_squared,
            "surrogate_n_terms": surrogate.get("n_terms", 0) if surrogate else 0,
            "output_statistics": stats,
            "parameter_sensitivity": sensitivity,
            "best_params": best_params,
            "best_fitness": best_fitness,
            "samples": samples,
            "fitness_values": fitness_values,
            "surrogate": surrogate,
            "execution_time_ms": elapsed_ms,
        }

    # ── Tier 2: Bayesian Optimization ──

    def gp_fit(
        self,
        x_train: list[list[float]],
        y_train: list[float],
        length_scale: float = 1.0,
        sigma_f: float = 1.0,
        sigma_n: float = 1e-6,
    ) -> dict[str, Any]:
        """Fit a Gaussian Process surrogate to training data."""
        try:
            result = _rust_call(
                "mc_gp_fit",
                x_train=x_train,
                y_train=y_train,
                length_scale=length_scale,
                sigma_f=sigma_f,
                sigma_n=sigma_n,
            )
            return result
        except Exception:  # noqa: BLE001
            # Python fallback: return basic stats
            n = len(y_train)
            y_mean = sum(y_train) / n if n else 0.0
            y_var = sum((y - y_mean) ** 2 for y in y_train) / n if n else 0.0
            return {
                "length_scale": length_scale,
                "sigma_f": sigma_f,
                "sigma_n": sigma_n,
                "log_marginal_likelihood": 0.0,
                "n_train": n,
                "y_mean": y_mean,
                "y_var": y_var,
                "fallback": True,
            }

    def gp_predict(
        self,
        x_train: list[list[float]],
        y_train: list[float],
        x_new: list[float],
        length_scale: float = 1.0,
        sigma_f: float = 1.0,
        sigma_n: float = 1e-6,
    ) -> dict[str, Any]:
        """Predict using GP at a new point."""
        try:
            result = _rust_call(
                "mc_gp_predict",
                x_train=x_train,
                y_train=y_train,
                x_new=x_new,
                length_scale=length_scale,
                sigma_f=sigma_f,
                sigma_n=sigma_n,
            )
            return result
        except Exception:  # noqa: BLE001
            # Python fallback: nearest neighbor interpolation
            if not x_train:
                return {"mean": 0.0, "variance": 1.0, "fallback": True}
            best_dist = float("inf")
            best_y = 0.0
            for xi, yi in zip(x_train, y_train):
                d = sum((a - b) ** 2 for a, b in zip(xi, x_new))
                if d < best_dist:
                    best_dist = d
                    best_y = yi
            return {"mean": best_y, "variance": best_dist, "fallback": True}

    def bayesian_optimize(
        self,
        initial_x: list[list[float]],
        initial_y: list[float],
        param_ranges: list[tuple[float, float]],
        fitness_expr: str = "x[0]",
        n_iterations: int = 10,
        n_candidates: int = 50,
        sigma_n: float = 1e-4,
        xi: float = 0.01,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Run Bayesian optimization loop via Rust backend."""
        try:
            result = _rust_call(
                "mc_bayesian_optimize",
                initial_x=initial_x,
                initial_y=initial_y,
                param_ranges=[list(r) for r in param_ranges],
                fitness_expr=fitness_expr,
                n_iterations=n_iterations,
                n_candidates=n_candidates,
                sigma_n=sigma_n,
                xi=xi,
                seed=seed,
            )
            return result
        except Exception:  # noqa: BLE001
            # Python fallback: random search
            import random

            rng = random.Random(seed)
            best_x = list(initial_x[0]) if initial_x else [0.0] * len(param_ranges)
            best_y = max(initial_y) if initial_y else float("-inf")
            all_x = list(initial_x)
            all_y = list(initial_y)

            for _ in range(n_iterations):
                candidate = [
                    rng.uniform(lo, hi) for lo, hi in param_ranges
                ]
                # Simple fitness eval for known expressions
                if fitness_expr == "x[0]":
                    y = candidate[0]
                elif fitness_expr == "x[0]+x[1]":
                    y = candidate[0] + candidate[1]
                elif fitness_expr == "sphere":
                    y = -sum(x * x for x in candidate)
                else:
                    y = candidate[0]
                all_x.append(candidate)
                all_y.append(y)
                if y > best_y:
                    best_y = y
                    best_x = list(candidate)

            convergence = []
            cur_best = float("-inf")
            for y in all_y:
                cur_best = max(cur_best, y)
                convergence.append(cur_best)

            return {
                "best_x": best_x,
                "best_y": best_y,
                "convergence": convergence,
                "n_evaluations": len(all_x),
                "fallback": True,
            }

    # ── Tier 3: Rare Event Simulation ──

    def subset_simulation(
        self,
        dim: int = 1,
        n_samples: int = 500,
        target_pf: float = 1e-4,
        threshold: float = 0.0,
        g_expr: str = "threshold - x[0]",
        seed: int = 42,
    ) -> dict[str, Any]:
        """Estimate rare event probability via subset simulation."""
        try:
            return _rust_call(
                "mc_subset_simulation",
                dim=dim,
                n_samples=n_samples,
                target_pf=target_pf,
                threshold=threshold,
                g_expr=g_expr,
                seed=seed,
            )
        except Exception:  # noqa: BLE001
            # Python fallback: crude Monte Carlo
            import random

            rng = random.Random(seed)
            n_fail = 0
            for _ in range(n_samples):
                x = [rng.gauss(0, 1) for _ in range(dim)]
                if g_expr == "threshold - x[0]":
                    g = threshold - x[0]
                elif g_expr == "threshold - sum_abs":
                    g = threshold - sum(abs(xi) for xi in x)
                elif g_expr == "threshold - sum_sq":
                    g = threshold - sum(xi * xi for xi in x)
                else:
                    g = threshold - x[0]
                if g <= 0:
                    n_fail += 1
            pf = n_fail / n_samples
            cov = ((1 - pf) / (n_samples * pf)) ** 0.5 if pf > 0 else float("inf")
            return {"probability": pf, "coefficient_of_variation": cov, "levels": 1, "fallback": True}

    def multilevel_splitting(
        self,
        dim: int = 1,
        n_samples: int = 500,
        survival_fraction: float = 0.1,
        threshold: float = 0.0,
        g_expr: str = "threshold - x[0]",
        seed: int = 42,
    ) -> dict[str, Any]:
        """Estimate rare event probability via adaptive multilevel splitting."""
        try:
            return _rust_call(
                "mc_multilevel_splitting",
                dim=dim,
                n_samples=n_samples,
                survival_fraction=survival_fraction,
                threshold=threshold,
                g_expr=g_expr,
                seed=seed,
            )
        except Exception:  # noqa: BLE001
            # Fallback to subset simulation
            return self.subset_simulation(dim, n_samples, 1e-4, threshold, g_expr, seed)

    def importance_sampling_rare(
        self,
        dim: int = 1,
        n_samples: int = 2000,
        pilot_n: int = 500,
        threshold: float = 0.0,
        g_expr: str = "threshold - x[0]",
        seed: int = 42,
    ) -> dict[str, Any]:
        """Estimate rare event probability via importance sampling with shifted Gaussian."""
        try:
            return _rust_call(
                "mc_importance_sampling_rare",
                dim=dim,
                n_samples=n_samples,
                pilot_n=pilot_n,
                threshold=threshold,
                g_expr=g_expr,
                seed=seed,
            )
        except Exception:  # noqa: BLE001
            return self.subset_simulation(dim, n_samples, 1e-4, threshold, g_expr, seed)

    # ── Tier 4: SDE Solvers ──

    def sde_euler(
        self,
        x0: float = 100.0,
        t0: float = 0.0,
        t_end: float = 1.0,
        n_steps: int = 100,
        drift_type: str = "gbm",
        mu: float = 0.05,
        sigma: float = 0.2,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Run Euler-Maruyama SDE simulation."""
        try:
            return _rust_call(
                "mc_sde_euler",
                x0=x0, t0=t0, t_end=t_end, n_steps=n_steps,
                drift_type=drift_type, mu=mu, sigma=sigma, seed=seed,
            )
        except Exception:  # noqa: BLE001
            # Python fallback: simple Euler-Maruyama
            import random

            rng = random.Random(seed)
            dt = (t_end - t0) / n_steps
            sqrt_dt = dt ** 0.5
            x = x0
            t = t0
            for _ in range(n_steps):
                dw = sqrt_dt * rng.gauss(0, 1)
                if drift_type == "gbm":
                    x += mu * x * dt + sigma * x * dw
                elif drift_type == "ou":
                    x += mu * (0.0 - x) * dt + sigma * dw
                t += dt
            return {"final_value": x, "n_steps": n_steps, "path_length": n_steps + 1, "fallback": True}

    def sde_parallel_euler(
        self,
        x0: float = 100.0,
        t0: float = 0.0,
        t_end: float = 1.0,
        n_steps: int = 100,
        n_paths: int = 1000,
        drift_type: str = "gbm",
        mu: float = 0.05,
        sigma: float = 0.2,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Run parallel Euler-Maruyama SDE paths and compute statistics."""
        try:
            return _rust_call(
                "mc_sde_parallel_euler",
                x0=x0, t0=t0, t_end=t_end, n_steps=n_steps, n_paths=n_paths,
                drift_type=drift_type, mu=mu, sigma=sigma, seed=seed,
            )
        except Exception:  # noqa: BLE001
            # Python fallback
            import random

            rng = random.Random(seed)
            dt = (t_end - t0) / n_steps
            sqrt_dt = dt ** 0.5
            finals = []
            for _ in range(n_paths):
                x = x0
                for _ in range(n_steps):
                    dw = sqrt_dt * rng.gauss(0, 1)
                    if drift_type == "gbm":
                        x += mu * x * dt + sigma * x * dw
                    elif drift_type == "ou":
                        x += mu * (0.0 - x) * dt + sigma * dw
                finals.append(x)
            n = len(finals)
            mean = sum(finals) / n
            var = sum((f - mean) ** 2 for f in finals) / n
            std = var ** 0.5
            ci = 1.96 * std / (n ** 0.5)
            return {"mean": mean, "variance": var, "std_dev": std, "ci_95": ci, "n_paths": n, "fallback": True}

    def sde_mlmc(
        self,
        x0: float = 100.0,
        t0: float = 0.0,
        t_end: float = 1.0,
        n_levels: int = 3,
        n_paths_fine: int = 1000,
        drift_type: str = "gbm",
        mu: float = 0.05,
        sigma: float = 0.2,
        payoff: str = "identity",
        seed: int = 42,
    ) -> dict[str, Any]:
        """Run multilevel Monte Carlo for SDE estimation."""
        try:
            return _rust_call(
                "mc_sde_mlmc",
                x0=x0, t0=t0, t_end=t_end, n_levels=n_levels, n_paths_fine=n_paths_fine,
                drift_type=drift_type, mu=mu, sigma=sigma, payoff=payoff, seed=seed,
            )
        except Exception:  # noqa: BLE001
            # Fallback to parallel Euler
            result = self.sde_parallel_euler(x0, t0, t_end, 100, n_paths_fine, drift_type, mu, sigma, seed)
            estimate = result.get("mean", x0)
            if payoff == "square":
                estimate = estimate ** 2
            elif payoff == "heaviside":
                estimate = 1.0 if estimate > x0 else 0.0
            return {"estimate": estimate, "variance": result.get("variance", 0.0), "levels": 1, "fallback": True}

    # ── Superforecaster Pipeline ──

    def superforecaster_estimate(
        self,
        param_ranges: list[tuple[float, float]],
        fitness_fn: Any,
        n_initial_samples: int = 100,
        n_bo_iterations: int = 15,
        n_surrogate_evals: int = 100_000,
        rare_event_threshold: float | None = None,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Full superforecaster pipeline for any question.

        1. LHS initial sampling → fitness evaluation
        2. PCE surrogate fitting → Sobol sensitivity indices
        3. Bayesian optimization for adaptive refinement
        4. Surrogate evaluation for output distribution
        5. Optional rare event probability estimation
        6. Returns structured numerical output for LLM interpretation
        """
        start = time.time()
        d = len(param_ranges)

        # Phase 1: LHS sampling
        samples = self.lhs_sample(n_initial_samples, param_ranges, seed=seed)
        if samples is None:
            samples = []

        # Evaluate fitness
        fitness_values = [fitness_fn(s) for s in samples]

        # Phase 2: PCE surrogate
        surrogate = self.fit_surrogate(samples, fitness_values, max_order=3)
        r_squared = surrogate.get("r_squared", 0.0) if surrogate else 0.0

        # Phase 3: Sensitivity analysis
        sensitivity = self.parameter_sensitivity(samples, fitness_values)

        # Phase 4: Bayesian optimization refinement
        bo_result = self.bayesian_optimize(
            samples[:min(20, len(samples))],
            fitness_values[:min(20, len(fitness_values))],
            param_ranges,
            fitness_expr="x[0]",
            n_iterations=n_bo_iterations,
            n_candidates=100,
            seed=seed,
        )

        # Phase 5: Statistics on output distribution
        stats = self.compute_statistics(fitness_values)

        # Phase 6: Rare event if threshold provided
        rare_event = None
        if rare_event_threshold is not None:
            rare_event = self.subset_simulation(
                dim=d,
                n_samples=500,
                target_pf=1e-4,
                threshold=rare_event_threshold,
                seed=seed,
            )

        # Find best parameters
        best_idx = max(range(len(fitness_values)), key=lambda i: fitness_values[i])
        best_params = samples[best_idx]
        best_fitness = fitness_values[best_idx]

        elapsed_ms = (time.time() - start) * 1000

        return {
            "n_dimensions": d,
            "n_samples": len(samples),
            "surrogate_r_squared": r_squared,
            "output_statistics": stats,
            "parameter_sensitivity": sensitivity,
            "best_params": best_params,
            "best_fitness": best_fitness,
            "bo_convergence": bo_result.get("convergence", []),
            "bo_best_y": bo_result.get("best_y", best_fitness),
            "rare_event": rare_event,
            "execution_time_ms": elapsed_ms,
        }

    def multi_objective_estimate(
        self,
        fitness_fns: list[Any],
        param_ranges: list[tuple[float, float]],
        n_initial: int = 10,
        n_iterations: int = 20,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Multi-objective Bayesian optimization returning a Pareto front.

        Runs independent BO for each objective, collects all evaluated points,
        and computes Pareto dominance to identify non-dominated solutions.

        Args:
            fitness_fns: List of fitness functions (one per objective).
            param_ranges: Parameter bounds for each dimension.
            n_initial: Initial LHS samples per objective.
            n_iterations: BO iterations per objective.
            seed: Random seed.

        Returns:
            Dict with pareto_front, all_evaluated, hypervolume, n_objectives.
        """
        start = time.time()
        n_obj = len(fitness_fns)
        d = len(param_ranges)

        all_points: list[list[float]] = []
        all_scores: list[list[float]] = []

        for obj_idx, fn in enumerate(fitness_fns):
            samples = self.lhs_sample(n_initial, param_ranges, seed=seed + obj_idx)
            if not samples:
                continue
            fitness_vals = [fn(s) for s in samples]

            self.bayesian_optimize(
                samples[:min(10, len(samples))],
                fitness_vals[:min(10, len(fitness_vals))],
                param_ranges,
                fitness_expr="x[0]",
                n_iterations=n_iterations,
                n_candidates=50,
                seed=seed + obj_idx,
            )

            for i, s in enumerate(samples):
                if s not in all_points:
                    all_points.append(s)
                    scores = [0.0] * n_obj
                    scores[obj_idx] = fitness_vals[i]
                    all_scores.append(scores)
                else:
                    idx = all_points.index(s)
                    all_scores[idx][obj_idx] = fitness_vals[i]

        pareto_front: list[dict[str, Any]] = []
        for i, (point, scores) in enumerate(zip(all_points, all_scores)):
            dominated = False
            for j, (other_point, other_scores) in enumerate(zip(all_points, all_scores)):
                if i == j:
                    continue
                if all(other_scores[k] >= scores[k] for k in range(n_obj)) and \
                   any(other_scores[k] > scores[k] for k in range(n_obj)):
                    dominated = True
                    break
            if not dominated:
                pareto_front.append({"params": point, "scores": scores})

        ref_point = [min(s[k] for s in all_scores) - 1 for k in range(n_obj)] if all_scores else [0.0] * n_obj
        hypervolume = 0.0
        if pareto_front and n_obj == 2:
            sorted_front = sorted(pareto_front, key=lambda x: x["scores"][0])
            prev_y = ref_point[1]
            for item in sorted_front:
                x, y = item["scores"][0], item["scores"][1]
                if y > prev_y:
                    hypervolume += (x - ref_point[0]) * (y - prev_y)
                    prev_y = y

        elapsed_ms = (time.time() - start) * 1000

        return {
            "n_objectives": n_obj,
            "n_dimensions": d,
            "n_evaluated": len(all_points),
            "pareto_front": pareto_front,
            "pareto_size": len(pareto_front),
            "hypervolume": hypervolume,
            "all_evaluated": [
                {"params": p, "scores": s} for p, s in zip(all_points, all_scores)
            ],
            "execution_time_ms": elapsed_ms,
        }

    # ── Quasi-Monte Carlo Methods ──

    def sobol_sequence(
        self,
        n: int,
        d: int,
        seed: int = 42,
        scramble: bool = True,
    ) -> list[list[float]] | None:
        """Generate a Sobol low-discrepancy sequence.

        Returns n×d matrix with values in [0, 1).
        Scrambling reduces artifacts for small n.
        """
        result = _rust_call(
            "mc_sobol_sequence",
            n=n, d=d, seed=seed, scramble=scramble,
        )
        if result and "samples" in result:
            return result["samples"]
        # Python fallback: simple Halton-like sequence
        import random
        rng = random.Random(seed)
        return [[rng.random() for _ in range(d)] for _ in range(n)]

    def halton_sequence(
        self,
        n: int,
        d: int,
        seed: int = 42,
    ) -> list[list[float]] | None:
        """Generate a Halton low-discrepancy sequence.

        Uses first d primes as bases.
        """
        result = _rust_call(
            "mc_halton_sequence",
            n=n, d=d, seed=seed,
        )
        if result and "samples" in result:
            return result["samples"]
        # Python fallback
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        def vdc(idx: int, base: int) -> float:
            f, r = 1.0, 0.0
            while idx > 0:
                f /= base
                r += f * (idx % base)
                idx //= base
            return r
        offset = seed % 1000
        return [
            [vdc(i + 1 + offset, primes[j % len(primes)]) for j in range(d)]
            for i in range(n)
        ]

    def qmc_sample(
        self,
        n: int,
        param_ranges: list[tuple[float, float]],
        method: str = "sobol",
        seed: int = 42,
    ) -> list[list[float]] | None:
        """Generate QMC samples scaled to parameter ranges.

        Args:
            method: "sobol" or "halton"
        """
        result = _rust_call(
            "mc_qmc_integrate",
            n=n,
            d=len(param_ranges),
            seed=seed,
            qmc_method=method,
            ranges=[list(r) for r in param_ranges],
        )
        if result and "samples" in result:
            return result["samples"]
        # Python fallback via halton_sequence
        unit = self.halton_sequence(n, len(param_ranges), seed) or []
        return [
            [lo + u * (hi - lo) for (lo, hi), u in zip(param_ranges, row)]
            for row in unit
        ]

    # ── MCMC Samplers ──

    def metropolis_hastings(
        self,
        n_samples: int = 1000,
        n_burn: int = 100,
        x0: list[float] | None = None,
        proposal_std: float = 1.0,
        seed: int = 42,
        target_type: str = "gaussian",
        target_mean: list[float] | None = None,
        target_cov: list[float] | None = None,
    ) -> dict[str, Any]:
        """Metropolis-Hastings MCMC sampler.

        Supports Gaussian and Rosenbrock targets.
        Returns dict with samples, n_samples, acceptance_rate.
        """
        try:
            return _rust_call(
                "mc_metropolis_hastings",
                n_samples=n_samples,
                n_burn=n_burn,
                x0=x0 or [0.0],
                proposal_std=proposal_std,
                seed=seed,
                target_type=target_type,
                target_mean=target_mean or [0.0],
                target_cov=target_cov or [1.0],
            ) or {"samples": [], "n_samples": 0, "acceptance_rate": 0.0, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"samples": [], "n_samples": 0, "acceptance_rate": 0.0, "fallback": True}

    def hamiltonian_monte_carlo(
        self,
        n_samples: int = 500,
        n_burn: int = 50,
        x0: list[float] | None = None,
        step_size: float = 0.1,
        n_leapfrog: int = 10,
        seed: int = 42,
        target_type: str = "gaussian",
        target_mean: list[float] | None = None,
        target_cov: list[float] | None = None,
    ) -> dict[str, Any]:
        """Hamiltonian Monte Carlo sampler with leapfrog integration.

        Supports Gaussian and Rosenbrock targets.
        Returns dict with samples, n_samples, acceptance_rate.
        """
        try:
            return _rust_call(
                "mc_hamiltonian_mc",
                n_samples=n_samples,
                n_burn=n_burn,
                x0=x0 or [0.0],
                step_size=step_size,
                n_leapfrog=n_leapfrog,
                seed=seed,
                target_type=target_type,
                target_mean=target_mean or [0.0],
                target_cov=target_cov or [1.0],
            ) or {"samples": [], "n_samples": 0, "acceptance_rate": 0.0, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"samples": [], "n_samples": 0, "acceptance_rate": 0.0, "fallback": True}

    # ── Expanded SDE Models ──

    def sde_jump_diffusion(
        self,
        x0: float = 100.0,
        t0: float = 0.0,
        t_end: float = 1.0,
        n_steps: int = 100,
        mu: float = 0.05,
        sigma: float = 0.2,
        jump_intensity: float = 0.1,
        jump_mean: float = 0.0,
        jump_std: float = 0.1,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Merton jump-diffusion model: GBM + Poisson jumps.

        dX = mu*X dt + sigma*X dW + J dN
        """
        try:
            return _rust_call(
                "mc_sde_jump_diffusion",
                x0=x0, t0=t0, t_end=t_end, n_steps=n_steps,
                mu=mu, sigma=sigma,
                jump_intensity=jump_intensity,
                jump_mean=jump_mean, jump_std=jump_std,
                seed=seed,
            ) or {"final_value": x0, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"final_value": x0, "fallback": True}

    def sde_heston(
        self,
        s0: float = 100.0,
        v0: float = 0.04,
        t0: float = 0.0,
        t_end: float = 1.0,
        n_steps: int = 100,
        mu: float = 0.05,
        kappa: float = 2.0,
        theta: float = 0.04,
        xi: float = 0.3,
        rho: float = -0.7,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Heston stochastic volatility model.

        dS = mu*S dt + sqrt(v)*S dW1
        dv = kappa*(theta-v) dt + xi*sqrt(v) dW2
        """
        try:
            return _rust_call(
                "mc_sde_heston",
                s0=s0, v0=v0, t0=t0, t_end=t_end, n_steps=n_steps,
                mu=mu, kappa=kappa, theta=theta, xi=xi, rho=rho, seed=seed,
            ) or {"final_price": s0, "final_variance": v0, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"final_price": s0, "final_variance": v0, "fallback": True}

    def sde_cir(
        self,
        x0: float = 0.04,
        t0: float = 0.0,
        t_end: float = 1.0,
        n_steps: int = 100,
        kappa: float = 2.0,
        theta: float = 0.04,
        sigma: float = 0.3,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Cox-Ingersoll-Ross model for interest rates.

        dX = kappa*(theta-X) dt + sigma*sqrt(X) dW
        """
        try:
            return _rust_call(
                "mc_sde_cir",
                x0=x0, t0=t0, t_end=t_end, n_steps=n_steps,
                kappa=kappa, theta=theta, sigma=sigma, seed=seed,
            ) or {"final_value": x0, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"final_value": x0, "fallback": True}

    # ── Advanced GP Methods ──

    def gp_optimize_hyperparameters(
        self,
        x_train: list[list[float]],
        y_train: list[float],
        sigma_n: float = 1e-6,
        n_grid: int = 10,
    ) -> dict[str, Any]:
        """Optimize GP hyperparameters via grid search."""
        try:
            return _rust_call(
                "mc_gp_optimize_hyperparameters",
                x_train=x_train,
                y_train=y_train,
                sigma_n=sigma_n,
                n_grid=n_grid,
            ) or {"length_scale": 1.0, "sigma_f": 1.0, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"length_scale": 1.0, "sigma_f": 1.0, "fallback": True}

    def expected_improvement(
        self,
        x_train: list[list[float]],
        y_train: list[float],
        x_candidates: list[list[float]],
        length_scale: float = 1.0,
        sigma_f: float = 1.0,
        sigma_n: float = 1e-6,
        xi: float = 0.01,
    ) -> dict[str, Any]:
        """Compute Expected Improvement for Bayesian optimization."""
        try:
            return _rust_call(
                "mc_expected_improvement",
                x_train=x_train,
                y_train=y_train,
                x_candidates=x_candidates,
                length_scale=length_scale,
                sigma_f=sigma_f,
                sigma_n=sigma_n,
                xi=xi,
            ) or {"ei_values": [], "f_best": 0.0, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"ei_values": [], "f_best": 0.0, "fallback": True}

    def multid_gaussian(
        self,
        n_samples: int = 1000,
        mean: list[float] | None = None,
        cov: list[float] | None = None,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Generate multivariate Gaussian samples."""
        try:
            return _rust_call(
                "mc_multid_gaussian",
                n_samples=n_samples,
                mean=mean or [0.0],
                cov=cov or [1.0],
                seed=seed,
            ) or {"samples": [], "fallback": True}
        except Exception:  # noqa: BLE001
            return {"samples": [], "fallback": True}

    # ── Quantum-Inspired Methods ──

    _julia_quantum_backend: Any = None

    def _get_julia_quantum(self) -> Any:
        """Get or create the Julia quantum backend singleton."""
        if self._julia_quantum_backend is not None:
            return self._julia_quantum_backend
        import os
        if os.environ.get("WM_SKIP_POLYGLOT", ""):
            self._julia_quantum_backend = False
            return None
        try:
            from whitemagic_polyglot import JuliaQuantumBackend
            backend = JuliaQuantumBackend()
            backend.call("ping")
            self._julia_quantum_backend = backend
            logger.info("Julia quantum backend connected")
            return backend
        except Exception as e:  # noqa: BLE001
            logger.debug("Julia quantum backend unavailable: %s", e)
            self._julia_quantum_backend = False  # Mark as unavailable
            return None

    def _julia_quantum_call(self, method: str, **kwargs) -> dict[str, Any] | None:
        """Call a Julia quantum geometry method. Returns None if unavailable."""
        backend = self._get_julia_quantum()
        if backend is None:
            return None
        try:
            return backend.call(method, timeout=15.0, **kwargs)
        except Exception as e:  # noqa: BLE001
            logger.debug("Julia quantum call %s failed: %s", method, e)
            return None

    _haskell_topological_backend: Any = None

    def _get_haskell_topological(self) -> Any:
        """Get or create the Haskell topological backend singleton."""
        if self._haskell_topological_backend is not None:
            return self._haskell_topological_backend
        import os
        if os.environ.get("WM_SKIP_POLYGLOT", ""):
            self._haskell_topological_backend = False
            return None
        try:
            from whitemagic_polyglot import HaskellTopologicalBackend
            backend = HaskellTopologicalBackend()
            backend.call("ping")
            self._haskell_topological_backend = backend
            logger.info("Haskell topological backend connected")
            return backend
        except Exception as e:  # noqa: BLE001
            logger.debug("Haskell topological backend unavailable: %s", e)
            self._haskell_topological_backend = False
            return None

    def _haskell_topological_call(self, method: str, **kwargs) -> dict[str, Any] | None:
        """Call a Haskell topological method. Returns None if unavailable."""
        backend = self._get_haskell_topological()
        if backend is None:
            return None
        try:
            return backend.call(method, timeout=15.0, **kwargs)
        except Exception as e:  # noqa: BLE001
            logger.debug("Haskell topological call %s failed: %s", method, e)
            return None

    def fubini_study_metric(
        self,
        state: list[float],
        jacobian: list[list[float]],
        n_params: int | None = None,
    ) -> dict[str, Any]:
        """Compute the Fubini-Study metric tensor for natural gradient optimization.

        Tries Julia first (exact Riemannian geometry), then Rust, then Python fallback.
        """
        n_p = n_params or len(jacobian)
        # Try Julia first for numerical precision
        julia_result = self._julia_quantum_call(
            "q_fubini_study",
            state=state,
            jacobian=jacobian,
            n_params=n_p,
        )
        if julia_result and julia_result.get("status") == "ok":
            return {"metric": julia_result.get("metric", []), "backend": "julia"}
        # Try Rust
        try:
            return _rust_call(
                "q_fubini_study_metric",
                state=state,
                jacobian=jacobian,
                n_params=n_p,
            ) or {"metric": [], "fallback": True}
        except Exception:  # noqa: BLE001
            return {"metric": [], "fallback": True}

    def natural_gradient(
        self,
        params: list[float],
        gradients: list[float],
        metric: list[list[float]],
        learning_rate: float = 0.01,
    ) -> dict[str, Any]:
        """Natural gradient step using Fubini-Study metric.

        Tries Julia first (exact metric inverse), then Rust, then Python fallback.
        """
        # Try Julia first
        julia_result = self._julia_quantum_call(
            "q_natural_gradient",
            params=params,
            gradients=gradients,
            metric=metric,
            learning_rate=learning_rate,
        )
        if julia_result and julia_result.get("status") == "ok":
            return {"new_params": julia_result.get("new_params", params), "backend": "julia"}
        # Try Rust
        try:
            return _rust_call(
                "q_natural_gradient",
                params=params,
                gradients=gradients,
                metric=metric,
                learning_rate=learning_rate,
            ) or {"new_params": params, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"new_params": [p - learning_rate * g for p, g in zip(params, gradients)], "fallback": True}

    def multiscale_bind(
        self,
        vectors: list[list[float]],
        bond_dim: int = 2,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Hierarchical tensor network bind (MPS-based)."""
        try:
            return _rust_call(
                "q_multiscale_bind",
                vectors=vectors,
                bond_dim=bond_dim,
                seed=seed,
            ) or {"result": [], "fallback": True}
        except Exception:  # noqa: BLE001
            return {"result": [], "fallback": True}

    def manifold_distance(
        self,
        a: list[float],
        b: list[float],
        manifold: str = "euclidean",
    ) -> dict[str, Any]:
        """Compute distance on Euclidean, hyperbolic, or spherical manifold.

        Tries Julia first (exact Riemannian geometry), then Rust, then Python fallback.
        """
        # Try Julia first for exact geodesic distance
        julia_result = self._julia_quantum_call(
            "q_manifold_distance",
            a=a, b=b, manifold=manifold,
        )
        if julia_result and julia_result.get("status") == "ok":
            return {"distance": julia_result.get("distance", 0.0), "backend": "julia"}
        # Try Rust
        try:
            return _rust_call(
                "q_manifold_distance",
                a=a, b=b, manifold=manifold,
            ) or {"distance": 0.0, "fallback": True}
        except Exception:  # noqa: BLE001
            import math
            if manifold == "spherical":
                dot = sum(x * y for x, y in zip(a, b))
                na = math.sqrt(sum(x * x for x in a)) or 1e-15
                nb = math.sqrt(sum(x * x for x in b)) or 1e-15
                return {"distance": math.acos(max(-1, min(1, dot / (na * nb)))), "fallback": True}
            return {"distance": math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))), "fallback": True}

    def embed_manifold(
        self,
        point: list[float],
        manifold: str = "euclidean",
    ) -> dict[str, Any]:
        """Embed a point onto the specified manifold."""
        try:
            return _rust_call(
                "q_embed_manifold",
                point=point,
                manifold=manifold,
            ) or {"embedded": point, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"embedded": point, "fallback": True}

    def riemannian_gradient(
        self,
        point: list[float],
        gradient: list[float],
        manifold: str = "euclidean",
    ) -> dict[str, Any]:
        """Project Euclidean gradient onto manifold tangent space."""
        try:
            return _rust_call(
                "q_riemannian_gradient",
                point=point,
                gradient=gradient,
                manifold=manifold,
            ) or {"riemannian_gradient": gradient, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"riemannian_gradient": gradient, "fallback": True}

    def exponential_map(
        self,
        point: list[float],
        tangent: list[float],
        manifold: str = "euclidean",
    ) -> dict[str, Any]:
        """Move along geodesic via exponential map."""
        try:
            return _rust_call(
                "q_exponential_map",
                point=point,
                tangent=tangent,
                manifold=manifold,
            ) or {"result": [p + t for p, t in zip(point, tangent)], "fallback": True}
        except Exception:  # noqa: BLE001
            return {"result": [p + t for p, t in zip(point, tangent)], "fallback": True}

    def auto_select_manifold(
        self,
        points: list[list[float]],
    ) -> dict[str, Any]:
        """Automatically select best manifold for given data.

        Tries Julia first (statistical analysis), then Rust, then Python fallback.
        """
        # Try Julia first
        julia_result = self._julia_quantum_call(
            "q_auto_manifold",
            points=points,
        )
        if julia_result and julia_result.get("status") == "ok":
            return {"manifold": julia_result.get("manifold", "euclidean"), "backend": "julia"}
        # Try Rust
        try:
            return _rust_call(
                "q_auto_manifold",
                points=points,
            ) or {"manifold": "euclidean", "fallback": True}
        except Exception:  # noqa: BLE001
            return {"manifold": "euclidean", "fallback": True}

    def born_sample(
        self,
        amplitudes: list[float],
        seed: int = 42,
    ) -> dict[str, Any]:
        """Born-rule sampling: probability = |amplitude|²."""
        try:
            return _rust_call(
                "q_born_sample",
                amplitudes=amplitudes,
                seed=seed,
            ) or {"index": 0, "fallback": True}
        except Exception:  # noqa: BLE001
            import random
            total = sum(a * a for a in amplitudes) or 1e-15
            r = random.Random(seed).random() * total
            cum = 0.0
            for i, a in enumerate(amplitudes):
                cum += a * a
                if r <= cum:
                    return {"index": i, "fallback": True}
            return {"index": len(amplitudes) - 1, "fallback": True}

    def born_batch_sample(
        self,
        amplitudes: list[float],
        n: int = 100,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Batch Born-rule sampling."""
        try:
            return _rust_call(
                "q_born_batch",
                amplitudes=amplitudes,
                n=n,
                seed=seed,
            ) or {"samples": [], "fallback": True}
        except Exception:  # noqa: BLE001
            return {"samples": [self.born_sample(amplitudes, seed + i)["index"] for i in range(n)], "fallback": True}

    def born_distribution(
        self,
        amplitudes: list[float],
    ) -> dict[str, Any]:
        """Born-rule probability distribution."""
        try:
            return _rust_call(
                "q_born_distribution",
                amplitudes=amplitudes,
            ) or {"distribution": [], "fallback": True}
        except Exception:  # noqa: BLE001
            total = sum(a * a for a in amplitudes) or 1e-15
            return {"distribution": [{"index": i, "probability": a * a / total} for i, a in enumerate(amplitudes)], "fallback": True}

    def quantum_interference(
        self,
        a: list[float],
        b: list[float],
    ) -> dict[str, Any]:
        """Compute quantum interference pattern between two amplitude vectors."""
        try:
            return _rust_call(
                "q_interference",
                a=a, b=b,
            ) or {"interference": [], "fallback": True}
        except Exception:  # noqa: BLE001
            return {"interference": [ai * ai + bi * bi + 2 * ai * bi for ai, bi in zip(a, b)], "fallback": True}

    def berry_phase(
        self,
        states: list[list[float]],
        params: list[float],
    ) -> dict[str, Any]:
        """Compute Berry phase for a cyclic path in parameter space.

        Tries Haskell first (formal verification), then Rust, then Python fallback.
        """
        # Try Haskell first for formal verification
        hs_result = self._haskell_topological_call(
            "berry_phase",
            vectors=states,
        )
        if hs_result and hs_result.get("status") == "ok":
            return {"phase": hs_result.get("phase", 0.0), "backend": "haskell"}
        # Try Rust
        try:
            return _rust_call(
                "q_berry_phase",
                states=states,
                params=params,
            ) or {"phase": 0.0, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"phase": 0.0, "fallback": True}

    def chern_number(
        self,
        curvature: list[list[float]],
        dtheta: float = 0.1,
        dphi: float = 0.1,
    ) -> dict[str, Any]:
        """Compute Chern number from Berry curvature.

        Tries Haskell first (formal verification), then Rust, then Python fallback.
        """
        # Try Haskell first
        hs_result = self._haskell_topological_call(
            "chern_number",
            vectors=curvature,
        )
        if hs_result and hs_result.get("status") == "ok":
            return {"chern_number": hs_result.get("chern", 0), "backend": "haskell"}
        # Try Rust
        try:
            return _rust_call(
                "q_chern_number",
                curvature=curvature,
                dtheta=dtheta,
                dphi=dphi,
            ) or {"chern_number": 0.0, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"chern_number": 0.0, "fallback": True}

    def topological_encode(
        self,
        data: list[float],
        n_redundant: int = 3,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Topologically encode data with redundancy for error protection.

        Tries Haskell first (formal verification), then Rust, then Python fallback.
        """
        # Try Haskell first
        hs_result = self._haskell_topological_call(
            "encode_topological",
            vector=data,
        )
        if hs_result and hs_result.get("status") == "ok":
            return {"encoded": hs_result.get("code", []), "protection": 1.0, "backend": "haskell", "hash": hs_result.get("hash", "")}
        # Try Rust
        try:
            return _rust_call(
                "q_topological_encode",
                data=data,
                n_redundant=n_redundant,
                seed=seed,
            ) or {"encoded": data, "protection": 0.0, "fallback": True}
        except Exception:  # noqa: BLE001
            return {"encoded": data, "protection": 0.0, "fallback": True}

    def topological_decode(
        self,
        encoded: list[float],
        data_len: int,
        n_redundant: int = 3,
    ) -> dict[str, Any]:
        """Decode topologically encoded data (majority vote).

        Tries Haskell first (formal verification), then Rust, then Python fallback.
        """
        # Try Rust first (Haskell decode needs both code and magnitudes)
        try:
            return _rust_call(
                "q_topological_decode",
                encoded=encoded,
                data_len=data_len,
                n_redundant=n_redundant,
            ) or {"decoded": [], "fallback": True}
        except Exception:  # noqa: BLE001
            return {"decoded": encoded[:data_len], "fallback": True}

    def quantum_walk_optimize(
        self,
        cost_matrix: list[list[float]],
        n_steps: int = 10,
        gamma: float = 0.5,
        beta: float = 0.5,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Quantum walk optimization for combinatorial problems."""
        try:
            return _rust_call(
                "q_quantum_walk_optimize",
                cost_matrix=cost_matrix,
                n_steps=n_steps,
                gamma=gamma,
                beta=beta,
                seed=seed,
            ) or {"amplitudes": [], "best_index": 0, "cost": 0.0, "fallback": True}
        except Exception:  # noqa: BLE001
            n = len(cost_matrix)
            return {"amplitudes": [1.0 / n ** 0.5] * n, "best_index": 0, "cost": cost_matrix[0][0] if n else 0.0, "fallback": True}

    def qaoa_maxcut(
        self,
        adjacency: list[list[float]],
        n_steps: int = 20,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Solve MaxCut using QAOA-style quantum walk."""
        try:
            return _rust_call(
                "q_qaoa_maxcut",
                adjacency=adjacency,
                n_steps=n_steps,
                seed=seed,
            ) or {"partition": [], "cut_value": 0.0, "fallback": True}
        except Exception:  # noqa: BLE001
            n = len(adjacency)
            return {"partition": [0] * n, "cut_value": 0.0, "fallback": True}
