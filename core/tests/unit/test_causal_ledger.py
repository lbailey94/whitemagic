"""Tests for Objective T — Karma Ledger as Causal Ledger."""
from __future__ import annotations

from whitemagic.core.evolution.causal_ledger import (
    CausalLedger,
    EffectType,
)


class TestCausalLedger:
    def test_record_effect(self):
        ledger = CausalLedger()
        effect = ledger.record_effect(
            improvement_id="h1",
            effect_type=EffectType.INTENDED,
            effect_metric="recall_quality",
            effect_magnitude=0.15,
        )
        assert effect.improvement_id == "h1"
        assert effect.effect_type == EffectType.INTENDED

    def test_get_effects(self):
        ledger = CausalLedger()
        ledger.record_effect("h1", EffectType.INTENDED, "recall", 0.1)
        ledger.record_effect("h1", EffectType.SIDE_EFFECT, "latency", -0.05)
        effects = ledger.get_effects("h1")
        assert len(effects) == 2

    def test_causal_utility_positive(self):
        ledger = CausalLedger()
        ledger.record_effect("h1", EffectType.INTENDED, "recall", 0.2, effect_confidence=0.9)
        ledger.record_effect("h1", EffectType.UNINTENDED, "latency", -0.1, effect_confidence=0.7)
        utility = ledger.get_causal_utility("h1")
        # 0.2*0.9 - 0.1*0.7 = 0.18 - 0.07 = 0.11
        assert utility > 0

    def test_causal_utility_negative(self):
        ledger = CausalLedger()
        ledger.record_effect("h1", EffectType.INTENDED, "recall", 0.05, effect_confidence=0.5)
        ledger.record_effect("h1", EffectType.UNINTENDED, "latency", -0.5, effect_confidence=0.9)
        utility = ledger.get_causal_utility("h1")
        assert utility < 0

    def test_get_all_utilities(self):
        ledger = CausalLedger()
        ledger.record_effect("h1", EffectType.INTENDED, "recall", 0.2)
        ledger.record_effect("h2", EffectType.INTENDED, "speed", 0.3)
        utilities = ledger.get_all_utilities()
        assert "h1" in utilities
        assert "h2" in utilities

    def test_metric_history(self):
        ledger = CausalLedger()
        ledger.record_effect("h1", EffectType.INTENDED, "recall", 0.1, timestamp=1.0)
        ledger.record_effect("h1", EffectType.INTENDED, "recall", 0.2, timestamp=2.0)
        ledger.record_effect("h1", EffectType.INTENDED, "recall", 0.15, timestamp=3.0)
        history = ledger.get_metric_history("recall", "h1")
        assert len(history) == 3
        assert history[0][0] == 1.0  # Sorted by timestamp

    def test_difference_in_differences(self):
        ledger = CausalLedger()
        # Pre-improvement: low values
        for i in range(5):
            ledger.record_effect("h1", EffectType.INTENDED, "recall", 0.05 * (i + 1), timestamp=float(i))
        # Post-improvement: higher values
        for i in range(5):
            ledger.record_effect("h1", EffectType.INTENDED, "recall", 0.3 + 0.05 * i, timestamp=float(10 + i))
        result = ledger.difference_in_differences("h1", "recall")
        assert "pre_mean" in result
        assert "post_mean" in result
        assert result["diff"] > 0  # Post > pre

    def test_stats(self):
        ledger = CausalLedger()
        ledger.record_effect("h1", EffectType.INTENDED, "recall", 0.1)
        ledger.record_effect("h1", EffectType.SIDE_EFFECT, "latency", -0.05)
        stats = ledger.get_stats()
        assert stats["total_effects"] == 2
        assert stats["effect_types"]["intended"] == 1
        assert stats["effect_types"]["side_effect"] == 1
