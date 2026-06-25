"""Tests for Objective S — Polyglot MC Acceleration."""
from __future__ import annotations

from whitemagic.core.evolution.polyglot_mc import (
    MCBackend,
    MCTask,
    PolyglotMCOrchestrator,
)


class TestBackendSelection:
    def test_python_default(self):
        orch = PolyglotMCOrchestrator()
        task = MCTask(task_id="t1", n_trials=100)
        backend = orch.select_backend(task)
        assert backend == MCBackend.PYTHON

    def test_rust_for_large_trials(self):
        orch = PolyglotMCOrchestrator()
        # If Rust is available, it should be selected for large trials
        task = MCTask(task_id="t1", n_trials=10000)
        backend = orch.select_backend(task)
        if MCBackend.RUST in orch.get_available_backends():
            assert backend == MCBackend.RUST
        else:
            assert backend == MCBackend.PYTHON

    def test_latency_sensitive_selects_zig_or_python(self):
        orch = PolyglotMCOrchestrator()
        task = MCTask(task_id="t1", n_trials=1, latency_sensitive=True)
        backend = orch.select_backend(task)
        if MCBackend.ZIG in orch.get_available_backends():
            assert backend == MCBackend.ZIG
        else:
            assert backend == MCBackend.PYTHON

    def test_streaming_selects_elixir_or_python(self):
        orch = PolyglotMCOrchestrator()
        task = MCTask(task_id="t1", n_trials=100, streaming=True)
        backend = orch.select_backend(task)
        if MCBackend.ELIXIR in orch.get_available_backends():
            assert backend == MCBackend.ELIXIR
        else:
            assert backend == MCBackend.PYTHON


class TestExecution:
    def test_execute_returns_result(self):
        orch = PolyglotMCOrchestrator()
        task = MCTask(task_id="t1", n_trials=100, prior_mean=0.6, prior_variance=0.1)
        result = orch.execute(task)
        assert result.task_id == "t1"
        assert result.n_trials_completed == 100
        assert 0.0 <= result.mean <= 1.0
        assert result.execution_time_ms >= 0.0

    def test_ci_bounds(self):
        orch = PolyglotMCOrchestrator()
        task = MCTask(task_id="t1", n_trials=1000, prior_mean=0.5, prior_variance=0.1)
        result = orch.execute(task)
        lower, upper = result.confidence_interval
        assert lower <= upper
        assert 0.0 <= lower <= 1.0
        assert 0.0 <= upper <= 1.0


class TestStats:
    def test_stats(self):
        orch = PolyglotMCOrchestrator()
        task = MCTask(task_id="t1", n_trials=100)
        orch.execute(task)
        stats = orch.get_stats()
        assert stats["total_dispatched"] == 1
        assert "python" in stats["available_backends"]
