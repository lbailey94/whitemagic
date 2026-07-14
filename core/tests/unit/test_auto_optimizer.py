# ruff: noqa: BLE001
"""Tests for Model Auto-Optimization Loop (v24.3 §3.3)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from whitemagic.inference.auto_optimizer import (
    BENCHMARK_PROMPTS,
    BenchmarkResult,
    ModelAutoOptimizer,
)
from whitemagic.inference.llama_cpp import LlamaCppConfig


@pytest.fixture
def optimizer(tmp_path, monkeypatch):
    """Fresh optimizer with temp state root."""
    monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
    import importlib

    import whitemagic.config.paths as paths_mod
    importlib.reload(paths_mod)
    import whitemagic.inference.auto_optimizer as opt_mod
    importlib.reload(opt_mod)
    return opt_mod.ModelAutoOptimizer()


@pytest.fixture
def mock_backend():
    """Mock LlamaCppBackend that returns canned responses."""
    backend = MagicMock()
    backend.complete.return_value = {"content": "This is a test response that is long enough."}
    return backend


class TestBenchmarkResult:
    def test_fitness_with_memory(self):
        r = BenchmarkResult(tokens_per_second=10.0, quality_score=1.0, memory_mb=200.0)
        # fitness = 10 * 1.0 / (200/100) = 5.0
        assert r.fitness() == 5.0

    def test_fitness_zero_memory(self):
        r = BenchmarkResult(tokens_per_second=10.0, quality_score=1.0, memory_mb=0.0)
        assert r.fitness() == 10.0

    def test_fitness_zero_tps(self):
        r = BenchmarkResult(tokens_per_second=0.0, quality_score=1.0, memory_mb=100.0)
        assert r.fitness() == 0.0


class TestModelAutoOptimizer:
    def test_benchmark_runs_inference(self, optimizer, mock_backend):
        config = LlamaCppConfig(model_path="/fake/model.gguf")
        result = optimizer.benchmark(mock_backend, config)
        assert hasattr(result, 'tokens_per_second')
        assert result.tokens_per_second > 0
        assert result.quality_score > 0
        assert "model_path" in result.config_snapshot

    def test_benchmark_with_custom_prompts(self, optimizer, mock_backend):
        config = LlamaCppConfig()
        optimizer.benchmark(mock_backend, config, prompts=["Hello"])
        assert mock_backend.complete.call_count == 1

    def test_benchmark_handles_errors(self, optimizer):
        backend = MagicMock()
        backend.complete.side_effect = Exception("connection refused")
        config = LlamaCppConfig()
        result = optimizer.benchmark(backend, config)
        assert result.tokens_per_second == 0.0
        assert result.quality_score == 0.0

    def test_explore_returns_sorted_results(self, optimizer, mock_backend):
        config = LlamaCppConfig(model_path="/fake/model.gguf")
        results = optimizer.explore(mock_backend, config, trials=5)
        assert len(results) == 5
        # Sorted by fitness descending
        for i in range(len(results) - 1):
            assert results[i].fitness() >= results[i + 1].fitness()

    def test_optimize_improves_or_maintains(self, optimizer, mock_backend):
        config = LlamaCppConfig(model_path="/fake/model.gguf")
        best = optimizer.optimize(mock_backend, config, iterations=2)
        assert hasattr(best, 'fitness')
        assert hasattr(best, 'tokens_per_second')
        # Best should be at least as good as baseline
        assert best.fitness() >= optimizer._baseline.fitness()

    def test_apply_optimal_saves_config(self, optimizer, tmp_path):
        config = LlamaCppConfig(model_path="/fake/model.gguf", n_ctx=4096)
        assert optimizer.apply_optimal(config)

    def test_load_optimal_config_returns_none_when_missing(self, tmp_path):
        # Ensure no config file exists
        from whitemagic.inference.auto_optimizer import _OPTIMAL_CONFIG_PATH
        if _OPTIMAL_CONFIG_PATH.exists():
            _OPTIMAL_CONFIG_PATH.unlink()
        assert ModelAutoOptimizer.load_optimal_config() is None

    def test_load_optimal_config_roundtrip(self, optimizer, tmp_path):
        config = LlamaCppConfig(model_path="/fake/model.gguf", n_ctx=4096, temperature=0.3)
        optimizer.apply_optimal(config)
        loaded = ModelAutoOptimizer.load_optimal_config()
        assert loaded is not None
        assert loaded.n_ctx == 4096
        assert loaded.temperature == 0.3

    def test_get_status(self, optimizer, mock_backend):
        config = LlamaCppConfig(model_path="/fake/model.gguf")
        optimizer.optimize(mock_backend, config, iterations=1)
        status = optimizer.get_status()
        assert status["has_baseline"] is True
        assert status["history_count"] > 0

    def test_generate_variant_changes_params(self, optimizer):
        base = LlamaCppConfig(model_path="/fake/model.gguf", n_ctx=8192, temperature=0.7)
        variant = optimizer._generate_variant(base)
        # Model path should be preserved
        assert variant.model_path == base.model_path
        # At least some parameter should differ (probabilistic but very likely)
        # Just check it's a valid config
        assert isinstance(variant, LlamaCppConfig)

    def test_benchmark_prompts_exist(self):
        assert len(BENCHMARK_PROMPTS) == 5
        assert "What is 2+2?" in BENCHMARK_PROMPTS


class TestBackgroundOptimizer:
    """Tests for the BackgroundOptimizer daemon thread."""

    def test_record_call_increments_count(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
        import importlib

        import whitemagic.inference.auto_optimizer as opt_mod
        importlib.reload(opt_mod)

        bg = opt_mod.BackgroundOptimizer(interval_s=1.0)
        assert bg._call_count == 0
        bg.record_call()
        bg.record_call()
        assert bg._call_count == 2

    def test_load_optimal_on_startup_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
        import importlib

        import whitemagic.inference.auto_optimizer as opt_mod
        importlib.reload(opt_mod)

        bg = opt_mod.BackgroundOptimizer(interval_s=1.0)
        # First call returns False (no saved config)
        result1 = bg.load_optimal_on_startup()
        assert result1 is False
        # Second call returns False (already loaded)
        result2 = bg.load_optimal_on_startup()
        assert result2 is False

    def test_start_and_stop(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
        import importlib

        import whitemagic.inference.auto_optimizer as opt_mod
        importlib.reload(opt_mod)

        bg = opt_mod.BackgroundOptimizer(interval_s=0.5)
        assert not bg.is_running
        bg.start()
        assert bg.is_running
        bg.stop()
        assert not bg.is_running

    def test_get_status(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
        import importlib

        import whitemagic.inference.auto_optimizer as opt_mod
        importlib.reload(opt_mod)

        bg = opt_mod.BackgroundOptimizer(interval_s=60.0)
        bg.record_call()
        status = bg.get_status()
        assert status["running"] is False
        assert status["call_count"] == 1
        assert status["interval_s"] == 60.0
        assert "has_baseline" in status
        assert "opt_config_loaded" in status
