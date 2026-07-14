# ruff: noqa: BLE001
"""Model Auto-Optimization Loop — Benchmark, explore, and tune LlamaCppConfig.
================================================================
Benchmarks current model config, explores parameter space, and
applies improvements. Config persists across sessions.

Usage::

    from whitemagic.inference.auto_optimizer import get_auto_optimizer

    opt = get_auto_optimizer()
    best = opt.optimize(iterations=3)
    print(f"Best tokens/sec: {best.tokens_per_second}")
"""
from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.inference.llama_cpp import LlamaCppBackend, LlamaCppConfig

logger = logging.getLogger(__name__)

# ── Config persistence path ──────────────────────────────────────────
_OPTIMAL_CONFIG_PATH = WM_ROOT / "optimal_model_config.json"

# ── Standard benchmark prompts ───────────────────────────────────────
BENCHMARK_PROMPTS = [
    "What is 2+2?",
    "Name the capital of France.",
    "If A>B and B>C, what is the relationship between A and C?",
    "Write a haiku about the ocean.",
    "Write a Python function to reverse a string.",
]


# ── Enums / Dataclasses ──────────────────────────────────────────────


@dataclass
class BenchmarkResult:
    """Result of benchmarking a specific config."""

    tokens_per_second: float = 0.0
    latency_ms: float = 0.0
    memory_mb: float = 0.0
    quality_score: float = 0.0
    config_snapshot: dict[str, Any] = field(default_factory=dict)

    def fitness(self) -> float:
        """Composite fitness: speed × quality / memory."""
        if self.memory_mb <= 0:
            return self.tokens_per_second * self.quality_score
        return (self.tokens_per_second * self.quality_score) / (self.memory_mb / 100.0)


# ── Auto Optimizer ───────────────────────────────────────────────────


class ModelAutoOptimizer:
    """Benchmarks and optimizes LlamaCppConfig parameters."""

    # Parameter search spaces: (min, max, step)
    SEARCH_SPACES: dict[str, tuple[float, float, float]] = {
        "n_ctx": (2048, 16384, 2048),
        "n_threads": (2, 16, 2),
        "temperature": (0.1, 1.0, 0.1),
        "top_p": (0.5, 1.0, 0.05),
        "repeat_penalty": (1.0, 1.3, 0.05),
        "parallel": (1, 8, 1),
    }

    # Cache type options (discrete)
    CACHE_OPTIONS = ["f16", "q8_0", "q4_0"]

    def __init__(self) -> None:
        self._baseline: BenchmarkResult | None = None
        self._best_config: LlamaCppConfig | None = None
        self._best_result: BenchmarkResult | None = None
        self._history: list[BenchmarkResult] = []

    def benchmark(
        self,
        backend: LlamaCppBackend,
        config: LlamaCppConfig,
        prompts: list[str] | None = None,
    ) -> BenchmarkResult:
        """Benchmark a specific config against standard prompts."""
        prompts = prompts or BENCHMARK_PROMPTS
        total_tokens = 0
        total_latency_ms = 0.0
        quality_scores: list[float] = []

        for prompt in prompts:
            try:
                t0 = time.time()
                response = backend.complete(prompt, max_tokens=128)
                elapsed_ms = (time.time() - t0) * 1000

                if isinstance(response, dict):
                    content = response.get("content", "")
                elif isinstance(response, str):
                    content = response
                else:
                    content = str(response)

                # Estimate tokens (rough: 1 token ≈ 4 chars)
                resp_tokens = max(len(content) // 4, 1)
                total_tokens += resp_tokens
                total_latency_ms += elapsed_ms

                # Quality heuristic: response length and non-empty
                if len(content) > 10:
                    quality_scores.append(1.0)
                elif len(content) > 0:
                    quality_scores.append(0.5)
                else:
                    quality_scores.append(0.0)
            except Exception as e:
                logger.debug("Benchmark prompt failed: %s", e)
                quality_scores.append(0.0)

        total_time_s = total_latency_ms / 1000.0
        tps = total_tokens / total_time_s if total_time_s > 0 else 0.0
        avg_latency = total_latency_ms / len(prompts) if prompts else 0.0
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        # Memory estimate via psutil
        mem_mb = 0.0
        try:
            import psutil

            proc = psutil.Process()
            mem_mb = proc.memory_info().rss / (1024 * 1024)
        except Exception:
            logger.debug("Ignored error in auto_optimizer.py:142")

        return BenchmarkResult(
            tokens_per_second=tps,
            latency_ms=avg_latency,
            memory_mb=mem_mb,
            quality_score=avg_quality,
            config_snapshot=self._config_to_dict(config),
        )

    def explore(
        self,
        backend: LlamaCppBackend,
        base_config: LlamaCppConfig,
        trials: int = 10,
    ) -> list[BenchmarkResult]:
        """Explore parameter variations around the base config."""
        results: list[BenchmarkResult] = []

        # Benchmark the base config first
        base_result = self.benchmark(backend, base_config)
        results.append(base_result)

        for _ in range(trials - 1):
            variant = self._generate_variant(base_config)
            try:
                result = self.benchmark(backend, variant)
                results.append(result)
            except Exception as e:
                logger.debug("Explore trial failed: %s", e)

        results.sort(key=lambda r: r.fitness(), reverse=True)
        return results

    def optimize(
        self,
        backend: LlamaCppBackend,
        base_config: LlamaCppConfig,
        iterations: int = 3,
    ) -> BenchmarkResult:
        """Run optimization loop: explore → pick best → narrow → repeat."""
        self._baseline = self.benchmark(backend, base_config)
        self._best_config = base_config
        self._best_result = self._baseline
        self._history = [self._baseline]

        current_config = base_config
        for i in range(iterations):
            results = self.explore(backend, current_config, trials=6)
            if results and results[0].fitness() > self._best_result.fitness():
                self._best_result = results[0]
                self._best_config = self._dict_to_config(
                    results[0].config_snapshot, base_config
                )
                current_config = self._best_config
                logger.info(
                    "Optimization iter %d: fitness %.4f → %.4f",
                    i,
                    self._baseline.fitness(),
                    self._best_result.fitness(),
                )
            self._history.extend(results)

            # Check convergence
            if i > 0 and len(self._history) >= 2:
                improvement = (
                    abs(self._history[-1].fitness() - self._history[-2].fitness())
                    / max(self._history[-2].fitness(), 0.001)
                )
                if improvement < 0.05:
                    logger.info("Optimization converged at iteration %d", i)
                    break

        return self._best_result

    def apply_optimal(self, config: LlamaCppConfig) -> bool:
        """Persist optimal config for future sessions."""
        try:
            data = self._config_to_dict(config)
            _OPTIMAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_OPTIMAL_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Optimal config saved to %s", _OPTIMAL_CONFIG_PATH)
            return True
        except (OSError, ValueError) as e:
            logger.warning("Failed to save optimal config: %s", e)
            return False

    @staticmethod
    def load_optimal_config() -> LlamaCppConfig | None:
        """Load previously saved optimal config."""
        if not _OPTIMAL_CONFIG_PATH.exists():
            return None
        try:
            with open(_OPTIMAL_CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return LlamaCppConfig(**{
                k: v for k, v in data.items()
                if k in LlamaCppConfig.__dataclass_fields__
            })
        except Exception as e:
            logger.warning("Failed to load optimal config: %s", e)
            return None

    def get_status(self) -> dict[str, Any]:
        """Return optimizer status for MCP tool."""
        return {
            "has_baseline": self._baseline is not None,
            "baseline_tps": self._baseline.tokens_per_second if self._baseline else 0,
            "best_tps": self._best_result.tokens_per_second if self._best_result else 0,
            "best_fitness": self._best_result.fitness() if self._best_result else 0,
            "history_count": len(self._history),
            "optimal_config_path": str(_OPTIMAL_CONFIG_PATH),
            "has_saved_config": _OPTIMAL_CONFIG_PATH.exists(),
        }

    # ── Internal helpers ──

    def _generate_variant(self, base: LlamaCppConfig) -> LlamaCppConfig:
        """Generate a random variant of the base config."""
        variant = LlamaCppConfig(
            model_path=base.model_path,
            host=base.host,
            port=base.port,
        )
        # Copy base values
        for field_name in LlamaCppConfig.__dataclass_fields__:
            if hasattr(base, field_name):
                setattr(variant, field_name, getattr(base, field_name))

        # Randomly perturb 1-2 parameters
        params_to_try = random.sample(
            list(self.SEARCH_SPACES.keys()),
            k=min(2, len(self.SEARCH_SPACES)),
        )
        for param in params_to_try:
            lo, hi, step = self.SEARCH_SPACES[param]
            if param in ("n_ctx", "n_threads", "parallel"):
                values = list(range(int(lo), int(hi) + 1, int(step)))
                if values:
                    setattr(variant, param, random.choice(values))
            else:
                setattr(variant, param, round(random.uniform(lo, hi) / step) * step)

        # Occasionally try different cache types
        if random.random() < 0.3:
            variant.cache_type_k = random.choice(self.CACHE_OPTIONS)
            variant.cache_type_v = random.choice(self.CACHE_OPTIONS)

        return variant

    @staticmethod
    def _config_to_dict(config: LlamaCppConfig) -> dict[str, Any]:
        """Convert config to a serializable dict."""
        return asdict(config)

    @staticmethod
    def _dict_to_config(
        data: dict[str, Any], fallback: LlamaCppConfig
    ) -> LlamaCppConfig:
        """Convert dict back to LlamaCppConfig."""
        valid_fields = LlamaCppConfig.__dataclass_fields__
        kwargs = {k: v for k, v in data.items() if k in valid_fields}
        try:
            return LlamaCppConfig(**kwargs)
        except Exception:
            return fallback


# ── Background Optimization Loop ──────────────────────────────────────


class BackgroundOptimizer:
    """Runs auto-optimization in a background daemon thread.

    Periodically benchmarks the current llama.cpp backend, explores
    parameter variations, and applies the best config. Controlled by
    WM_AUTO_OPTIMIZE=1 env var.

    Integration:
        - Loads optimal config on startup (if previously saved)
        - Runs optimization every WM_OPTIMIZE_INTERVAL seconds (default 300s)
        - Applies improvements by persisting config + restarting backend
        - Reports status via get_status()
    """

    def __init__(self, interval_s: float = 300.0) -> None:
        self._interval = float(os.environ.get("WM_OPTIMIZE_INTERVAL", str(interval_s)))
        self._optimizer = get_auto_optimizer()
        self._thread: threading.Thread | None = None
        self._running = False
        self._stop_event = threading.Event()
        self._call_count = 0
        self._opt_config_loaded = False

    @property
    def is_running(self) -> bool:
        return self._running

    def load_optimal_on_startup(self) -> bool:
        """Load previously saved optimal config and apply to active backend.

        Called on first inference tool call. Returns True if config was
        loaded and applied.
        """
        if self._opt_config_loaded:
            return False
        self._opt_config_loaded = True

        optimal = ModelAutoOptimizer.load_optimal_config()
        if optimal is None:
            return False

        try:
            from whitemagic.inference.router import _get_small_backend, _get_large_backend

            # Apply to small backend if it exists
            small = _get_small_backend()
            if small is not None:
                small._config = optimal
                logger.info("Applied optimal config to small backend (tps_target=%.1f)", optimal.n_ctx)

            # Apply to large backend if it exists
            large = _get_large_backend()
            if large is not None:
                large._config = optimal
                logger.info("Applied optimal config to large backend")

            return True
        except Exception as e:
            logger.debug("Failed to apply optimal config on startup: %s", e)
            return False

    def record_call(self) -> None:
        """Record an inference call. Triggers optimization every N calls."""
        self._call_count += 1

    def start(self) -> bool:
        """Start the background optimization thread."""
        if self._running:
            return True
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._optimize_loop, daemon=True, name="auto-optimizer"
        )
        self._thread.start()
        logger.info("Background optimizer started (interval=%.0fs)", self._interval)
        return True

    def stop(self) -> None:
        """Stop the background optimization thread."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("Background optimizer stopped")

    def _optimize_loop(self) -> None:
        """Background loop — runs optimization at regular intervals."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self._interval)
            if self._stop_event.is_set():
                break
            try:
                self._run_optimization()
            except Exception as e:
                logger.debug("Background optimization cycle failed: %s", e, exc_info=True)

    def _run_optimization(self) -> dict[str, Any] | None:
        """Run a single optimization cycle."""
        try:
            from whitemagic.inference.router import _get_small_backend

            backend = _get_small_backend()
            if backend is None or not backend.is_available:
                return None

            base_config = backend._config
            best = self._optimizer.optimize(backend, base_config, iterations=2)

            if best.fitness() > 0:
                # Persist the optimal config
                optimal_cfg = self._optimizer._best_config or base_config
                self._optimizer.apply_optimal(optimal_cfg)
                logger.info(
                    "Optimization cycle complete: tps=%.1f fitness=%.4f (calls=%d)",
                    best.tokens_per_second, best.fitness(), self._call_count,
                )

            return self._optimizer.get_status()
        except Exception as e:
            logger.debug("Optimization cycle error: %s", e)
            return None

    def get_status(self) -> dict[str, Any]:
        """Get optimizer status for MCP tool."""
        return {
            **self._optimizer.get_status(),
            "running": self._running,
            "call_count": self._call_count,
            "interval_s": self._interval,
            "opt_config_loaded": self._opt_config_loaded,
        }


# ── Singletons ────────────────────────────────────────────────────────

_optimizer: ModelAutoOptimizer | None = None
_bg_optimizer: BackgroundOptimizer | None = None
_bg_lock = threading.RLock()


def get_auto_optimizer() -> ModelAutoOptimizer:
    """Get the global ModelAutoOptimizer singleton."""
    global _optimizer
    if _optimizer is None:
        _optimizer = ModelAutoOptimizer()
    return _optimizer


def get_background_optimizer() -> BackgroundOptimizer:
    """Get the global BackgroundOptimizer singleton."""
    global _bg_optimizer
    if _bg_optimizer is None:
        with _bg_lock:
            if _bg_optimizer is None:
                _bg_optimizer = BackgroundOptimizer()
    return _bg_optimizer
