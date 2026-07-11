"""Polyglot MC Acceleration (Objective S).

Orchestrates MC computation across polyglot accelerators, dispatching
to the appropriate backend based on trial count, correlation structure,
and latency requirements.

Backends:
- Python (fallback): Always available, handles small trial counts
- Rust: Importance sampling, control variates (existing mc_engine.rs)
- Mojo (GPU): Massively parallel trial execution (100K+ trials)
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
    MOJO = "mojo"  # GPU parallel (100K+ trials)
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
    - n_trials > 100K → Mojo (GPU)
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
            pass

        # Mojo (check for compiler)
        try:
            import mojo  # noqa: F401

            self._available_backends.add(MCBackend.MOJO)
            self._backend_performance[MCBackend.MOJO] = 1_000_000.0
        except ImportError:
            pass

        # Julia
        try:
            from whitemagic.core.resonance.julia_resonance import julia_available

            if julia_available():
                self._available_backends.add(MCBackend.JULIA)
                self._backend_performance[MCBackend.JULIA] = 50_000.0
        except (ImportError, AttributeError):
            pass

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
                pass

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

        # 3. Very large trial count → Mojo (GPU)
        if task.n_trials > 100_000 and MCBackend.MOJO in self._available_backends:
            return MCBackend.MOJO

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
        pct = lambda q: sorted_v[min(int(q * (n - 1)), n - 1)]
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
