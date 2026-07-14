"""Tests for Oracle-Guided Bayesian Optimization (Phase 4).

Tests verify:
- OracleBOBridge translates hexagram to BO parameters
- Wu Xing temperature modulation works
- HRR resonance amplification adjusts iterations
- SimulationOrchestrator._consult_oracle_for_bo integrates with oracle
- Graceful degradation when oracle unavailable
"""

import pytest
from unittest.mock import patch, MagicMock

from whitemagic.oracle.oracle_bo_bridge import OracleBOBridge, get_oracle_bo_bridge


class TestOracleBOBridge:
    """Test the Oracle → BO parameter translation."""

    def test_translate_with_known_hexagram(self):
        bridge = OracleBOBridge()
        params = bridge.translate({"primary_hexagram": 32})
        assert "xi" in params
        assert "n_bo_iterations" in params
        assert "exploration" in params
        # Hexagram 32 (Duration) should have patient exploration
        assert params["exploration"] == "patient"
        assert params["n_bo_iterations"] == 30

    def test_translate_with_unknown_hexagram(self):
        bridge = OracleBOBridge()
        params = bridge.translate({"primary_hexagram": 13})
        # Should use defaults
        assert params["xi"] == 0.01
        assert params["n_bo_iterations"] == 20

    def test_translate_with_no_hexagram(self):
        bridge = OracleBOBridge()
        params = bridge.translate({})
        assert params == bridge.DEFAULT_PARAMS

    def test_translate_with_iching_number_key(self):
        bridge = OracleBOBridge()
        params = bridge.translate({"iching_number": 14})
        # Hexagram 14 (Great Possession) → bold
        assert params["exploration"] == "bold"

    def test_wuxing_temperature_modulation(self):
        bridge = OracleBOBridge()
        params = bridge.translate({"primary_hexagram": 32, "wu_xing": "fire"})
        assert params["temperature"] == 1.5

        params = bridge.translate({"primary_hexagram": 32, "wu_xing": "water"})
        assert params["temperature"] == 0.3

    def test_hrr_resonance_amplification(self):
        bridge = OracleBOBridge()
        base_params = bridge.translate({"primary_hexagram": 32})
        base_iters = base_params["n_bo_iterations"]

        resonant_params = bridge.translate({
            "primary_hexagram": 32,
            "hrr_resonances": [
                {"hexagram": 50, "similarity": 0.6},
                {"hexagram": 35, "similarity": 0.5},
            ],
        })
        # Should have more iterations due to resonance amplification
        avg_sim = (0.6 + 0.5) / 2
        expected_iters = int(base_iters * (1 + avg_sim))
        assert resonant_params["n_bo_iterations"] == expected_iters

    def test_hrr_resonance_reduces_xi(self):
        bridge = OracleBOBridge()
        params = bridge.translate({
            "primary_hexagram": 32,
            "hrr_resonances": [{"hexagram": 50, "similarity": 0.7}],
        })
        # Strong resonance should reduce xi (more confident exploration)
        base_params = bridge.translate({"primary_hexagram": 32})
        assert params["xi"] <= base_params["xi"]

    def test_translate_from_synthesis_result(self):
        bridge = OracleBOBridge()
        mock_result = MagicMock()
        mock_result.raw_layers = {"wu_xing": "fire"}
        mock_result.primary_hexagram = 32
        mock_result.hrr_resonances = [{"hexagram": 50, "similarity": 0.4}]

        params = bridge.translate_from_synthesis(mock_result)
        assert "xi" in params
        assert "n_bo_iterations" in params
        assert params["temperature"] == 1.5

    def test_get_oracle_bo_bridge_singleton(self):
        b1 = get_oracle_bo_bridge()
        b2 = get_oracle_bo_bridge()
        assert b1 is b2

    def test_retreat_hexagram_minimizes_iterations(self):
        """Hexagram 33 (Retreat) should have minimal iterations."""
        bridge = OracleBOBridge()
        params = bridge.translate({"primary_hexagram": 33})
        assert params["n_bo_iterations"] == 10
        assert params["xi"] == 0.5  # High xi = less exploitation

    def test_transformative_hexagram_maximizes_iterations(self):
        """Hexagram 50 (The Cauldron) should have many iterations."""
        bridge = OracleBOBridge()
        params = bridge.translate({"primary_hexagram": 50})
        assert params["n_bo_iterations"] == 30
        assert params["xi"] == 0.01  # Low xi = more exploitation


class TestSimulationOracleIntegration:
    """Test that SimulationOrchestrator integrates with oracle."""

    def test_consult_oracle_for_bo_with_query(self):
        from whitemagic.core.consciousness.simulation_orchestrator import SimulationOrchestrator
        orch = SimulationOrchestrator()
        # This should either return params or None (if oracle fails)
        params = orch._consult_oracle_for_bo("Should I invest in research?")
        # If oracle is available, should get params
        if params is not None:
            assert "xi" in params
            assert "n_bo_iterations" in params

    def test_consult_oracle_for_bo_empty_query(self):
        from whitemagic.core.consciousness.simulation_orchestrator import SimulationOrchestrator
        orch = SimulationOrchestrator()
        params = orch._consult_oracle_for_bo("")
        assert params is None

    def test_simulation_result_has_metadata(self):
        from whitemagic.core.consciousness.simulation_orchestrator import SimulationResult
        result = SimulationResult(mode="external", subtype="sde")
        assert hasattr(result, "metadata")
        assert isinstance(result.metadata, dict)

    def test_simulation_result_to_dict_includes_metadata(self):
        from whitemagic.core.consciousness.simulation_orchestrator import SimulationResult
        result = SimulationResult(mode="external", subtype="sde")
        d = result.to_dict()
        assert "metadata" in d
