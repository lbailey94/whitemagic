# ruff: noqa: D101, D102
"""Tests for SimulationOrchestrator MCP tool wiring.

Verifies that:
- simulation.introspect delegates to SimulationOrchestrator.run_introspective()
- simulation.forecast delegates to SimulationOrchestrator.run_external()
- simulation.status delegates to SimulationOrchestrator.get_status()
- simulation.recursive delegates to SimulationOrchestrator.run_recursive_cycle()
- All 4 tools are registered in dispatch table, registry, PRAT mappings, NLU patterns
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_orchestrator():
    """Reset SimulationOrchestrator singleton between tests."""
    from whitemagic.core.consciousness.simulation_orchestrator import (
        SimulationOrchestrator,
    )
    SimulationOrchestrator._instance = None
    yield
    SimulationOrchestrator._instance = None


def _make_sim_result(mode="introspective", subtype="guna_balance", success=True):
    """Create a mock SimulationResult."""
    from whitemagic.core.consciousness.simulation_orchestrator import SimulationResult
    return SimulationResult(
        mode=mode,
        subtype=subtype,
        success=success,
        best_fitness=0.85,
        best_params={"sattvic_target": 0.17},
        statistics={"avg_fitness": 0.7, "n_trials": 100},
        sensitivity={"sattvic_target": 0.42},
        execution_time_ms=123.4,
        memory_id="mem-123",
        dag_experiment_id="dag-456",
    )


# ---------------------------------------------------------------------------
# Handler Delegation Tests
# ---------------------------------------------------------------------------


class TestSimulationIntrospectDelegation:
    def test_delegates_to_orchestrator(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_introspect
        result = _make_sim_result()
        with patch(
            "whitemagic.core.consciousness.simulation_orchestrator.get_simulation_orchestrator"
        ) as mock_get:
            orch = MagicMock()
            orch.run_introspective.return_value = result
            mock_get.return_value = orch

            out = handle_simulation_introspect(space="guna_balance", n_trials=50, seed=7)

            assert out["status"] == "success"
            assert out["space"] == "guna_balance"
            assert out["best_fitness"] == 0.85
            assert out["optimal_parameters"] == {"sattvic_target": 0.17}
            assert out["memory_id"] == "mem-123"
            assert out["dag_experiment_id"] == "dag-456"
            orch.run_introspective.assert_called_once_with(
                space="guna_balance", n_trials=50, n_bo_iterations=20, seed=7,
            )

    def test_returns_error_on_failure(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_introspect
        with patch(
            "whitemagic.core.consciousness.simulation_orchestrator.get_simulation_orchestrator"
        ) as mock_get:
            mock_get.side_effect = RuntimeError("boom")
            out = handle_simulation_introspect()
            assert out["status"] == "error"
            assert "boom" in out["error"]


class TestSimulationForecastDelegation:
    def test_delegates_to_orchestrator(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_forecast
        result = _make_sim_result(mode="external", subtype="sde")
        with patch(
            "whitemagic.core.consciousness.simulation_orchestrator.get_simulation_orchestrator"
        ) as mock_get:
            orch = MagicMock()
            orch.run_external.return_value = result
            mock_get.return_value = orch

            out = handle_simulation_forecast(
                model_type="sde", research_query="test query", seed=99,
            )

            assert out["status"] == "success"
            assert out["model_type"] == "sde"
            assert out["research_query"] == "test query"
            assert out["best_fitness"] == 0.85
            assert out["memory_id"] == "mem-123"
            orch.run_external.assert_called_once()

    def test_returns_error_on_failure(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_forecast
        with patch(
            "whitemagic.core.consciousness.simulation_orchestrator.get_simulation_orchestrator"
        ) as mock_get:
            mock_get.side_effect = RuntimeError("crash")
            out = handle_simulation_forecast()
            assert out["status"] == "error"


class TestSimulationStatusHandler:
    def test_returns_status(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_status
        with patch(
            "whitemagic.core.consciousness.simulation_orchestrator.get_simulation_orchestrator"
        ) as mock_get:
            orch = MagicMock()
            orch.get_status.return_value = {
                "total_simulations": 5,
                "introspective_count": 3,
                "external_count": 2,
                "recent_results": [],
            }
            mock_get.return_value = orch

            out = handle_simulation_status()
            assert out["status"] == "success"
            assert out["total_simulations"] == 5
            assert out["introspective_count"] == 3


class TestSimulationRecursiveHandler:
    def test_delegates_to_orchestrator(self):
        from whitemagic.tools.handlers.simulation import handle_simulation_recursive
        r1 = _make_sim_result(mode="introspective", subtype="guna_balance")
        r2 = _make_sim_result(mode="external", subtype="sde", success=True)
        with patch(
            "whitemagic.core.consciousness.simulation_orchestrator.get_simulation_orchestrator"
        ) as mock_get:
            orch = MagicMock()
            orch.run_recursive_cycle.return_value = [r1, r2]
            mock_get.return_value = orch

            out = handle_simulation_recursive(n_cycles=1, seed=10)

            assert out["status"] == "success"
            assert out["n_cycles"] == 1
            assert len(out["results"]) == 2
            assert out["summary"]["total_simulations"] == 2
            assert out["summary"]["introspective_count"] == 1
            assert out["summary"]["external_count"] == 1
            orch.run_recursive_cycle.assert_called_once_with(
                n_cycles=1, introspective_space="guna_balance",
                external_model="sde", seed=10,
            )


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------


class TestSimulationToolRegistration:
    def test_dispatch_table_has_all_four(self):
        from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY
        assert "simulation.introspect" in DISPATCH_MEMORY
        assert "simulation.forecast" in DISPATCH_MEMORY
        assert "simulation.status" in DISPATCH_MEMORY
        assert "simulation.recursive" in DISPATCH_MEMORY

    def test_registry_has_all_four(self):
        from whitemagic.tools.registry import get_all_tools
        names = {t.name for t in get_all_tools()}
        assert "simulation.introspect" in names
        assert "simulation.forecast" in names
        assert "simulation.status" in names
        assert "simulation.recursive" in names

    def test_prat_mappings_exist(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        assert TOOL_TO_GANA.get("simulation.introspect") == "gana_ghost"
        assert TOOL_TO_GANA.get("simulation.forecast") == "gana_chariot"
        assert TOOL_TO_GANA.get("simulation.status") == "gana_ghost"
        assert TOOL_TO_GANA.get("simulation.recursive") == "gana_ghost"

    def test_nlu_patterns_exist(self):
        from whitemagic.tools.handlers.meta_tool import _ROUTING_PATTERNS
        tool_names = {entry[2] for entry in _ROUTING_PATTERNS}
        assert "simulation.introspect" in tool_names
        assert "simulation.forecast" in tool_names
        assert "simulation.status" in tool_names
        assert "simulation.recursive" in tool_names
