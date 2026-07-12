# ruff: noqa: BLE001
"""Tests for MC simulation integration — handlers, SimulationOrchestrator, superforecaster upgrades."""

import pytest


# ── Simulation Handler Tests ──────────────────────────────────────────


class TestSimulationHandlers:
    """Test the MCP tool handlers in simulation.py."""

    def test_handle_mc_surrogate_basic(self):
        """GP surrogate fit with simple training data."""
        from whitemagic.tools.handlers.simulation import handle_mc_surrogate
        result = handle_mc_surrogate(
            x_train=[[0.0], [0.5], [1.0]],
            y_train=[0.0, 0.5, 1.0],
        )
        assert result["status"] == "success"
        assert "fit" in result

    def test_handle_mc_surrogate_with_predict(self):
        """GP surrogate fit + prediction at new points."""
        from whitemagic.tools.handlers.simulation import handle_mc_surrogate
        result = handle_mc_surrogate(
            x_train=[[0.0], [0.5], [1.0]],
            y_train=[0.0, 0.5, 1.0],
            x_predict=[[0.25], [0.75]],
        )
        assert result["status"] == "success"
        assert "predictions" in result
        assert len(result["predictions"]) == 2

    def test_handle_mc_optimize_basic(self):
        """Bayesian optimization with a simple fitness function."""
        from whitemagic.tools.handlers.simulation import handle_mc_optimize
        result = handle_mc_optimize(
            param_ranges=[[0.0, 1.0]],
            fitness_expr="x[0]",
            n_initial_samples=10,
            n_iterations=5,
            n_candidates=20,
            seed=42,
        )
        assert result["status"] == "success"

    def test_handle_mc_rare_event_subset(self):
        """Rare event estimation via subset simulation."""
        from whitemagic.tools.handlers.simulation import handle_mc_rare_event
        result = handle_mc_rare_event(
            method="subset",
            dim=2,
            n_samples=200,
            threshold=2.0,
            seed=42,
        )
        assert result["status"] == "success"
        assert "probability" in result

    def test_handle_mc_rare_event_splitting(self):
        """Rare event estimation via multilevel splitting."""
        from whitemagic.tools.handlers.simulation import handle_mc_rare_event
        result = handle_mc_rare_event(
            method="splitting",
            dim=2,
            n_samples=200,
            threshold=2.0,
            seed=42,
        )
        assert result["status"] == "success"

    def test_handle_mc_sde_euler(self):
        """SDE solving via Euler-Maruyama with a single path."""
        from whitemagic.tools.handlers.simulation import handle_mc_sde
        result = handle_mc_sde(
            x0=100.0,
            t_end=0.1,
            n_steps=10,
            n_paths=1,
            drift_type="gbm",
            mu=0.05,
            sigma=0.2,
            solver="euler",
            seed=42,
        )
        assert result["status"] == "success"

    def test_handle_mc_sde_parallel(self):
        """SDE solving with parallel paths."""
        from whitemagic.tools.handlers.simulation import handle_mc_sde
        result = handle_mc_sde(
            x0=100.0,
            t_end=0.1,
            n_steps=10,
            n_paths=100,
            drift_type="gbm",
            mu=0.05,
            sigma=0.2,
            seed=42,
        )
        assert result["status"] == "success"

    def test_handle_mc_superforecaster(self):
        """Full superforecaster pipeline."""
        from whitemagic.tools.handlers.simulation import handle_mc_superforecaster
        result = handle_mc_superforecaster(
            param_ranges=[[0.0, 1.0], [0.0, 1.0]],
            fitness_expr="x[0] + x[1]",
            n_initial_samples=20,
            n_bo_iterations=5,
            seed=42,
        )
        assert result["status"] == "success"

    def test_handle_simulation_introspect(self):
        """Introspective simulation (yin-within-yang)."""
        from whitemagic.tools.handlers.simulation import handle_simulation_introspect
        result = handle_simulation_introspect(
            space="guna_balance",
            n_trials=20,
            n_bo_iterations=5,
            seed=42,
        )
        assert result["status"] == "success"
        assert "optimal_parameters" in result
        assert "best_fitness" in result

    def test_handle_simulation_forecast_sde(self):
        """External research simulation (yang-within-yin) with SDE."""
        from whitemagic.tools.handlers.simulation import handle_simulation_forecast
        result = handle_simulation_forecast(
            model_type="sde",
            research_query="Test SDE forecast",
            x0=100.0,
            t_end=0.1,
            n_steps=10,
            n_paths=100,
            seed=42,
        )
        assert result["status"] == "success"
        assert result["model_type"] == "sde"
        assert "execution_time_ms" in result

    def test_handle_simulation_forecast_rare_event(self):
        """External research simulation with rare event estimation."""
        from whitemagic.tools.handlers.simulation import handle_simulation_forecast
        result = handle_simulation_forecast(
            model_type="rare_event",
            research_query="Risk assessment",
            method="subset",
            dim=2,
            n_samples=200,
            threshold=2.0,
            seed=42,
        )
        assert result["status"] == "success"
        assert result["model_type"] == "rare_event"

    def test_handle_mc_sde_error_handling(self):
        """SDE handler gracefully handles errors."""
        from whitemagic.tools.handlers.simulation import handle_mc_sde
        result = handle_mc_sde(
            x0="not_a_number",
        )
        assert result["status"] == "error"


# ── SimulationOrchestrator Tests ──────────────────────────────────────


class TestSimulationOrchestrator:
    """Test the SimulationOrchestrator class."""

    def test_singleton(self):
        """SimulationOrchestrator is a singleton."""
        from whitemagic.core.consciousness.simulation_orchestrator import (
            SimulationOrchestrator,
            get_simulation_orchestrator,
        )
        orch1 = get_simulation_orchestrator()
        orch2 = get_simulation_orchestrator()
        assert orch1 is orch2

    def test_run_introspective(self):
        """Run introspective simulation (yin-within-yang)."""
        from whitemagic.core.consciousness.simulation_orchestrator import (
            get_simulation_orchestrator,
        )
        orch = get_simulation_orchestrator()
        result = orch.run_introspective(
            space="guna_balance",
            n_trials=20,
            n_bo_iterations=5,
            seed=42,
            persist=False,
        )
        assert result.mode == "introspective"
        assert result.subtype == "guna_balance"
        assert result.execution_time_ms > 0

    def test_run_external_sde(self):
        """Run external SDE simulation (yang-within-yin)."""
        from whitemagic.core.consciousness.simulation_orchestrator import (
            get_simulation_orchestrator,
        )
        orch = get_simulation_orchestrator()
        result = orch.run_external(
            model_type="sde",
            research_query="Test forecast",
            x0=100.0,
            t_end=0.1,
            n_steps=10,
            n_paths=100,
            seed=42,
            persist=False,
        )
        assert result.mode == "external"
        assert result.subtype == "sde"
        assert result.success

    def test_run_external_rare_event(self):
        """Run external rare event simulation."""
        from whitemagic.core.consciousness.simulation_orchestrator import (
            get_simulation_orchestrator,
        )
        orch = get_simulation_orchestrator()
        result = orch.run_external(
            model_type="rare_event",
            research_query="Risk analysis",
            method="subset",
            dim=2,
            n_samples=200,
            threshold=2.0,
            seed=42,
            persist=False,
        )
        assert result.mode == "external"
        assert result.subtype == "rare_event"
        assert result.success

    def test_run_external_superforecaster(self):
        """Run external superforecaster simulation."""
        from whitemagic.core.consciousness.simulation_orchestrator import (
            get_simulation_orchestrator,
        )
        orch = get_simulation_orchestrator()
        result = orch.run_external(
            model_type="superforecaster",
            research_query="Parameter optimization",
            param_ranges=[[0.0, 1.0]],
            fitness_expr="x[0]",
            n_initial_samples=20,
            n_bo_iterations=5,
            seed=42,
            persist=False,
        )
        assert result.mode == "external"
        assert result.subtype == "superforecaster"
        assert result.success

    def test_run_external_unknown_model(self):
        """Unknown model_type returns error."""
        from whitemagic.core.consciousness.simulation_orchestrator import (
            get_simulation_orchestrator,
        )
        orch = get_simulation_orchestrator()
        result = orch.run_external(
            model_type="unknown",
            persist=False,
        )
        assert result.error is not None
        assert "unknown" in result.error.lower()

    def test_run_recursive_cycle(self):
        """Recursive yin/yang cycle alternates introspective and external."""
        from whitemagic.core.consciousness.simulation_orchestrator import (
            get_simulation_orchestrator,
        )
        orch = get_simulation_orchestrator()
        results = orch.run_recursive_cycle(
            n_cycles=2,
            introspective_space="guna_balance",
            external_model="sde",
            seed=42,
        )
        assert len(results) == 4  # 2 cycles × 2 simulations each
        # Alternating: introspective, external, introspective, external
        assert results[0].mode == "introspective"
        assert results[1].mode == "external"
        assert results[2].mode == "introspective"
        assert results[3].mode == "external"

    def test_get_status(self):
        """Status returns simulation counts."""
        from whitemagic.core.consciousness.simulation_orchestrator import (
            get_simulation_orchestrator,
        )
        orch = get_simulation_orchestrator()
        status = orch.get_status()
        assert "total_simulations" in status
        assert "introspective_count" in status
        assert "external_count" in status
        assert "recent_results" in status

    def test_simulation_result_to_dict(self):
        """SimulationResult.to_dict serializes correctly."""
        from whitemagic.core.consciousness.simulation_orchestrator import (
            SimulationResult,
        )
        result = SimulationResult(
            mode="introspective",
            subtype="guna_balance",
            success=True,
            best_fitness=0.85,
            best_params={"sattvic": 0.17, "rajasic": 0.33},
            sensitivity={"sattvic": 0.5, "rajasic": -0.3},
            execution_time_ms=42.5,
        )
        d = result.to_dict()
        assert d["mode"] == "introspective"
        assert d["success"] is True
        assert d["best_fitness"] == 0.85
        assert "sattvic" in d["best_params"]


# ── PossibilitySpaceExplorer Superforecaster Tests ────────────────────


class TestPossibilityExplorerSuperforecaster:
    """Test the superforecaster-enhanced PossibilitySpaceExplorer."""

    def test_explore_with_superforecaster(self):
        """Explore using superforecaster pipeline."""
        from whitemagic.core.consciousness.possibility_explorer import (
            get_possibility_explorer,
        )
        explorer = get_possibility_explorer()
        result = explorer.explore(
            "guna_balance",
            n_trials=20,
            use_superforecaster=True,
            n_bo_iterations=5,
            seed=42,
        )
        assert result.backend == "superforecaster"
        assert result.best_trial is not None
        assert result.best_trial.fitness_score > 0

    def test_explore_without_superforecaster(self):
        """Explore using basic MC (backward compatibility)."""
        from whitemagic.core.consciousness.possibility_explorer import (
            get_possibility_explorer,
        )
        explorer = get_possibility_explorer()
        result = explorer.explore(
            "guna_balance",
            n_trials=20,
            use_superforecaster=False,
            seed=42,
        )
        assert result.backend in ("python", "rust")
        assert result.best_trial is not None

    def test_explore_all_with_superforecaster(self):
        """Explore all spaces with superforecaster pipeline."""
        from whitemagic.core.consciousness.possibility_explorer import (
            get_possibility_explorer,
        )
        explorer = get_possibility_explorer()
        results = explorer.explore_all(
            n_trials_per_space=10,
            use_superforecaster=True,
            n_bo_iterations=3,
            seed=42,
        )
        assert len(results) > 0
        for name, result in results.items():
            assert result.backend == "superforecaster"


# ── Autoswarm Superforecaster Tests ───────────────────────────────────


class TestAutoswarmSuperforecaster:
    """Test the superforecaster-enhanced Autoswarm."""

    def test_campaign_config_superforecaster_field(self):
        """CampaignConfig has use_superforecaster field."""
        from whitemagic.core.evolution.autoswarm import CampaignConfig
        config = CampaignConfig(
            campaign_name="test",
            use_superforecaster=True,
            n_bo_iterations=10,
        )
        assert config.use_superforecaster is True
        assert config.n_bo_iterations == 10

    def test_default_campaigns_include_superforecaster(self):
        """Default campaigns include a superforecaster campaign."""
        from whitemagic.core.evolution.autoswarm import (
            EvolutionaryAutoswarm,
            CampaignConfig,
        )
        swarm = EvolutionaryAutoswarm()
        campaigns = swarm._default_campaigns()
        sf_campaigns = [c for c in campaigns if c.use_superforecaster]
        assert len(sf_campaigns) >= 1

    def test_run_superforecaster_campaign(self):
        """_run_superforecaster_campaign returns hypotheses and fitness."""
        from whitemagic.core.evolution.autoswarm import (
            EvolutionaryAutoswarm,
            CampaignConfig,
        )
        swarm = EvolutionaryAutoswarm()
        config = CampaignConfig(
            campaign_name="test_sf",
            hypothesis_space="guna_balance",
            n_trials=20,
            max_iterations=5,
            use_superforecaster=True,
            n_bo_iterations=5,
            seed=42,
        )
        hypotheses, best_fitness, sf_meta = swarm._run_superforecaster_campaign(config)
        assert isinstance(hypotheses, list)
        assert isinstance(best_fitness, float)
        assert isinstance(sf_meta, dict)


# ── Tool Registration Tests ───────────────────────────────────────────


class TestToolRegistration:
    """Verify the new MC tools are properly registered."""

    def test_dispatch_table_has_mc_tools(self):
        """All 7 new MC tools are in the dispatch table."""
        from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY
        expected = [
            "mc.surrogate",
            "mc.optimize",
            "mc.rare_event",
            "mc.sde",
            "mc.superforecaster",
            "simulation.introspect",
            "simulation.forecast",
        ]
        for tool in expected:
            assert tool in DISPATCH_MEMORY, f"{tool} not in dispatch table"

    def test_prat_mappings_have_mc_tools(self):
        """All 7 new MC tools have Gana mappings."""
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        expected = [
            "mc.surrogate",
            "mc.optimize",
            "mc.rare_event",
            "mc.sde",
            "mc.superforecaster",
            "simulation.introspect",
            "simulation.forecast",
        ]
        for tool in expected:
            assert tool in TOOL_TO_GANA, f"{tool} not in PRAT mappings"

    def test_mc_tools_mapped_to_correct_ganas(self):
        """MC tools are mapped to the expected Ganas."""
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        assert TOOL_TO_GANA["mc.surrogate"] == "gana_dipper"
        assert TOOL_TO_GANA["mc.optimize"] == "gana_dipper"
        assert TOOL_TO_GANA["mc.rare_event"] == "gana_dipper"
        assert TOOL_TO_GANA["mc.sde"] == "gana_dipper"
        assert TOOL_TO_GANA["mc.superforecaster"] == "gana_dipper"
        assert TOOL_TO_GANA["simulation.introspect"] == "gana_ghost"
        assert TOOL_TO_GANA["simulation.forecast"] == "gana_chariot"

    def test_registry_has_mc_tool_definitions(self):
        """All 7 new MC tools have registry definitions."""
        from whitemagic.tools.registry_defs.cognitive_extensions import TOOLS
        names = {td.name for td in TOOLS}
        expected = [
            "mc.surrogate",
            "mc.optimize",
            "mc.rare_event",
            "mc.sde",
            "mc.superforecaster",
            "simulation.introspect",
            "simulation.forecast",
        ]
        for tool in expected:
            assert tool in names, f"{tool} not in registry definitions"
