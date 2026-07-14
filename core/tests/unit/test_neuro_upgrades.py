"""Unit tests for neuro-upgrades (P4.3)."""


import pytest

from whitemagic.core.consciousness.neuro_upgrades import (
    AttentionMechanism,
    CorticalColumn,
    DendriticComputation,
    NeuromodulationGating,
    NeuroUpgrades,
    OscillatoryBinding,
    PredictiveCittaCoder,
    get_neuro_upgrades,
)


class TestDendriticComputation:
    """Test dendritic computation."""

    def test_integrate_basic(self):
        dc = DendriticComputation()
        result = dc.integrate(0.8, 0.6, 0.4)
        assert 0.0 <= result <= 1.0

    def test_integrate_high_proximal(self):
        dc = DendriticComputation()
        result = dc.integrate(1.0, 0.0, 0.0)
        # proximal=0.5 + distal sigmoid(-0.5)≈0.189 = ~0.689
        assert result == pytest.approx(0.689, abs=0.02)

    def test_integrate_all_high(self):
        dc = DendriticComputation()
        result = dc.integrate(1.0, 1.0, 1.0, neuromod_gain=1.0)
        assert result > 0.8

    def test_integrate_all_zero(self):
        dc = DendriticComputation()
        result = dc.integrate(0.0, 0.0, 0.0)
        assert 0.0 <= result <= 0.3  # sigmoid(−0.5) is small but nonzero

    def test_neuromod_gain_amplifies_apical(self):
        dc = DendriticComputation()
        low = dc.integrate(0.0, 0.0, 0.5, neuromod_gain=0.5)
        high = dc.integrate(0.0, 0.0, 0.5, neuromod_gain=2.0)
        assert high >= low


class TestNeuromodulationGating:
    """Test neuromodulation gating."""

    def test_gate_goal_alignment(self):
        ng = NeuromodulationGating(da_level=1.0)
        result = ng.gate_dimension("goal_alignment", 0.5)
        assert result == pytest.approx(0.75, abs=0.01)

    def test_gate_identity_stability(self):
        ng = NeuromodulationGating(sht_level=1.0)
        result = ng.gate_dimension("identity_stability", 0.5)
        assert result == pytest.approx(0.75, abs=0.01)

    def test_gate_memory_accessibility(self):
        ng = NeuromodulationGating(ach_level=1.0)
        result = ng.gate_dimension("memory_accessibility", 0.5)
        assert result == pytest.approx(0.75, abs=0.01)

    def test_gate_ungated_dimension(self):
        ng = NeuromodulationGating(da_level=1.0)
        result = ng.gate_dimension("temporal_orientation", 0.5)
        assert result == 0.5

    def test_gate_all(self):
        ng = NeuromodulationGating(da_level=0.8, sht_level=0.6, ach_level=0.7)
        dims = {"goal_alignment": 0.5, "identity_stability": 0.5, "memory_accessibility": 0.5}
        gated = ng.gate_all(dims)
        assert gated["goal_alignment"] > 0.5
        assert gated["identity_stability"] > 0.5
        assert gated["memory_accessibility"] > 0.5

    def test_update_levels_clamped(self):
        ng = NeuromodulationGating()
        ng.update_levels(2.0, -1.0, 0.5)
        assert ng.da_level == 1.0
        assert ng.sht_level == 0.0
        assert ng.ach_level == 0.5


class TestPredictiveCittaCoder:
    """Test predictive citta coder."""

    def test_compute_prediction_error(self):
        pc = PredictiveCittaCoder()
        actual = {"coherence": 0.9, "novelty": 0.3, "stability": 0.7, "attention": 0.6}
        errors = pc.compute_prediction_error(actual)
        assert "total" in errors
        assert "surprise" in errors
        assert errors["coherence"] >= 0.0

    def test_expectations_update(self):
        pc = PredictiveCittaCoder()
        initial = pc._expectations["coherence"]
        pc.compute_prediction_error({"coherence": 0.95, "novelty": 0.3, "stability": 0.7, "attention": 0.6})
        assert pc._expectations["coherence"] != initial

    def test_emotional_modulation_high_surprise(self):
        pc = PredictiveCittaCoder()
        # Generate high surprise
        for _ in range(5):
            pc.compute_prediction_error({"coherence": 0.1, "novelty": 0.9, "stability": 0.1, "attention": 0.9})
        mod = pc.get_emotional_modulation()
        assert mod["tone_shift"] > 0  # rajasic shift

    def test_emotional_modulation_low_surprise(self):
        pc = PredictiveCittaCoder()
        # Generate low surprise (expectations match actual)
        for _ in range(10):
            pc.compute_prediction_error({
                "coherence": pc._expectations["coherence"],
                "novelty": pc._expectations["novelty"],
                "stability": pc._expectations["stability"],
                "attention": pc._expectations["attention"],
            })
        mod = pc.get_emotional_modulation()
        assert mod["intensity"] <= 0.5

    def test_stats(self):
        pc = PredictiveCittaCoder()
        pc.compute_prediction_error({"coherence": 0.8, "novelty": 0.4, "stability": 0.6, "attention": 0.5})
        stats = pc.stats()
        assert "avg_prediction_error" in stats
        assert "error_history_length" in stats


class TestCorticalColumn:
    """Test cortical column processing."""

    def test_process_basic(self):
        cc = CorticalColumn()
        result = cc.process(0.7, context=0.5)
        assert "l1_sensory" in result
        assert "l2_association" in result
        assert "l3_integration" in result
        assert "l4_output" in result

    def test_l1_passes_through(self):
        cc = CorticalColumn()
        result = cc.process(0.8)
        assert result["l1_sensory"] == 0.8

    def test_l2_binds_sensory_and_context(self):
        cc = CorticalColumn()
        result = cc.process(0.8, context=0.6)
        assert result["l2_association"] == pytest.approx(0.72, abs=0.01)

    def test_l3_sigmoid_nonlinearity(self):
        cc = CorticalColumn()
        result_low = cc.process(0.0, context=0.0)
        cc2 = CorticalColumn()
        result_high = cc2.process(1.0, context=1.0)
        assert result_low["l3_integration"] < 0.5
        assert result_high["l3_integration"] > 0.5

    def test_l4_output_amplified_by_context(self):
        cc = CorticalColumn()
        result = cc.process(0.8, context=0.9)
        assert result["l4_output"] >= result["l3_integration"]


class TestAttentionMechanism:
    """Test attention mechanism."""

    def test_attend_basic(self):
        am = AttentionMechanism()
        candidates = [
            {"id": "a", "importance": 0.9, "recency": 0.8},
            {"id": "b", "importance": 0.3, "recency": 0.2},
        ]
        weights = am.attend(candidates)
        assert len(weights) == 2
        assert weights[0][0] == "a"  # Higher importance first
        assert weights[0][1] > weights[1][1]

    def test_attend_empty(self):
        am = AttentionMechanism()
        weights = am.attend([])
        assert weights == []

    def test_attend_weights_sum_to_one(self):
        am = AttentionMechanism()
        candidates = [
            {"id": "a", "importance": 0.5, "recency": 0.5},
            {"id": "b", "importance": 0.6, "recency": 0.4},
            {"id": "c", "importance": 0.3, "recency": 0.7},
        ]
        weights = am.attend(candidates)
        total = sum(w for _, w in weights)
        assert total == pytest.approx(1.0, abs=0.01)

    def test_set_ach_gain(self):
        am = AttentionMechanism()
        am.set_ach_gain(0.5)
        assert am.ach_gain == 1.0  # 0.5 * 2.0
        am.set_ach_gain(1.0)
        assert am.ach_gain == 2.0  # heightened

    def test_cosine_sim(self):
        am = AttentionMechanism()
        sim = am._cosine_sim([1, 0, 0], [1, 0, 0])
        assert sim == pytest.approx(1.0)
        sim = am._cosine_sim([1, 0], [0, 1])
        assert sim == pytest.approx(0.0, abs=0.01)


class TestOscillatoryBinding:
    """Test oscillatory binding."""

    def test_advance_basic(self):
        ob = OscillatoryBinding()
        result = ob.advance(1.0)
        assert "theta_phase" in result
        assert "gamma_phase" in result
        assert "binding_strength" in result
        assert 0.0 <= result["binding_strength"] <= 1.0

    def test_binding_strength_range(self):
        ob = OscillatoryBinding()
        for _ in range(10):
            ob.advance(0.1)
        assert 0.0 <= ob.get_binding_score() <= 1.0

    def test_avg_binding(self):
        ob = OscillatoryBinding()
        for _ in range(5):
            ob.advance(0.1)
        avg = ob.get_avg_binding()
        assert 0.0 <= avg <= 1.0

    def test_set_mode_meditation(self):
        ob = OscillatoryBinding()
        ob.set_mode("meditation")
        assert ob.theta_freq == 5.0
        assert ob.gamma_freq == 30.0

    def test_set_mode_rem(self):
        ob = OscillatoryBinding()
        ob.set_mode("rem")
        assert ob.theta_freq == 7.0
        assert ob.gamma_freq == 45.0

    def test_set_mode_deep(self):
        ob = OscillatoryBinding()
        ob.set_mode("deep")
        assert ob.theta_freq == 8.0
        assert ob.gamma_freq == 60.0


class TestNeuroUpgrades:
    """Test the integrated NeuroUpgrades system."""

    def test_advance_cycle(self):
        nu = NeuroUpgrades()
        dims = {
            "context_continuity": 0.7,
            "relationship_awareness": 0.5,
            "goal_alignment": 0.6,
            "identity_stability": 0.8,
            "memory_accessibility": 0.4,
            "emotional_attunement": 0.5,
            "capability_awareness": 0.6,
            "temporal_orientation": 0.3,
        }
        result = nu.advance_cycle(dims, input_signal=0.6, context=0.5)
        assert "dendritic_output" in result
        assert "gated_dimensions" in result
        assert "prediction_errors" in result
        assert "cortical_layers" in result
        assert "oscillatory_state" in result
        assert "binding_strength" in result

    def test_set_mode(self):
        nu = NeuroUpgrades()
        nu.set_mode("meditation")
        assert nu.nmgating.sht_level == 0.8
        assert nu.oscillatory.theta_freq == 5.0

        nu.set_mode("deep")
        assert nu.nmgating.da_level == 0.8
        assert nu.oscillatory.gamma_freq == 60.0

    def test_stats(self):
        nu = NeuroUpgrades()
        nu.advance_cycle({"coherence": 0.8}, input_signal=0.5)
        stats = nu.stats()
        assert "total_cycles" in stats
        assert "dendritic" in stats
        assert "neuromodulation" in stats
        assert "predictive_citta" in stats
        assert "cortical" in stats
        assert "oscillatory" in stats
        assert "attention" in stats

    def test_singleton(self):
        nu1 = get_neuro_upgrades()
        nu2 = get_neuro_upgrades()
        assert nu1 is nu2

    def test_multiple_cycles_accumulate(self):
        nu = NeuroUpgrades()
        dims = {"coherence": 0.8, "novelty": 0.3, "stability": 0.7, "attention": 0.6}
        for _ in range(5):
            nu.advance_cycle(dims)
        assert nu.stats()["total_cycles"] == 5
        assert len(nu.predictive_citta._prediction_errors) == 5
