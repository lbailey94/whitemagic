"""Tests for Objective I — Resonance-Driven Transfer Learning."""

from __future__ import annotations

from whitemagic.core.evolution.resonance_transfer import (
    ResonanceSignature,
    ResonanceTransferEngine,
)


class TestResonance:
    def test_self_resonance(self):
        engine = ResonanceTransferEngine()
        sig = ResonanceSignature(subsystem_id="s1", error_pattern=[1, 2, 3, 2, 1])
        engine.register_signature(sig)
        assert engine.compute_resonance("s1", "s1") == 1.0

    def test_identical_patterns_high_resonance(self):
        engine = ResonanceTransferEngine(resonance_threshold=0.3)
        pattern = [1, 2, 3, 2, 1, 0, 1, 2]
        engine.register_signature(
            ResonanceSignature(
                subsystem_id="s1", error_pattern=pattern, activity_rhythm=pattern
            )
        )
        engine.register_signature(
            ResonanceSignature(
                subsystem_id="s2", error_pattern=pattern, activity_rhythm=pattern
            )
        )
        score = engine.compute_resonance("s1", "s2")
        assert score > 0.5

    def test_different_patterns_low_resonance(self):
        engine = ResonanceTransferEngine(resonance_threshold=0.0)
        engine.register_signature(
            ResonanceSignature(subsystem_id="s1", error_pattern=[1, 1, 1, 1, 1])
        )
        engine.register_signature(
            ResonanceSignature(subsystem_id="s2", error_pattern=[5, 0, 5, 0, 5])
        )
        score = engine.compute_resonance("s1", "s2")
        assert score < 0.8  # Not perfectly correlated

    def test_nonexistent_subsystem(self):
        engine = ResonanceTransferEngine()
        assert engine.compute_resonance("s1", "s2") == 0.0


class TestTransfer:
    def test_find_resonant(self):
        engine = ResonanceTransferEngine(resonance_threshold=0.3)
        pattern = [1, 2, 3, 2, 1, 0, 1, 2]
        engine.register_signature(
            ResonanceSignature(
                subsystem_id="s1", error_pattern=pattern, activity_rhythm=pattern
            )
        )
        engine.register_signature(
            ResonanceSignature(
                subsystem_id="s2", error_pattern=pattern, activity_rhythm=pattern
            )
        )
        resonant = engine.find_resonant_subsystems("s1")
        assert len(resonant) >= 1
        assert resonant[0][0] == "s2"

    def test_propose_transfer(self):
        engine = ResonanceTransferEngine(resonance_threshold=0.3)
        pattern = [1, 2, 3, 2, 1, 0, 1, 2]
        engine.register_signature(
            ResonanceSignature(
                subsystem_id="s1", error_pattern=pattern, activity_rhythm=pattern
            )
        )
        engine.register_signature(
            ResonanceSignature(
                subsystem_id="s2", error_pattern=pattern, activity_rhythm=pattern
            )
        )
        proposals = engine.propose_transfer(
            "s1", "improvement_1", source_confidence=0.9
        )
        assert len(proposals) >= 1
        assert proposals[0].source_id == "s1"
        assert proposals[0].target_id == "s2"
        assert proposals[0].transferred_prior > 0

    def test_no_transfer_for_low_resonance(self):
        engine = ResonanceTransferEngine(resonance_threshold=0.9)
        engine.register_signature(
            ResonanceSignature(subsystem_id="s1", error_pattern=[1, 1, 1])
        )
        engine.register_signature(
            ResonanceSignature(subsystem_id="s2", error_pattern=[5, 0, 5])
        )
        proposals = engine.propose_transfer("s1", "improvement_1")
        assert len(proposals) == 0

    def test_get_transfers(self):
        engine = ResonanceTransferEngine(resonance_threshold=0.3)
        pattern = [1, 2, 3, 2, 1, 0, 1, 2]
        engine.register_signature(
            ResonanceSignature(
                subsystem_id="s1", error_pattern=pattern, activity_rhythm=pattern
            )
        )
        engine.register_signature(
            ResonanceSignature(
                subsystem_id="s2", error_pattern=pattern, activity_rhythm=pattern
            )
        )
        engine.propose_transfer("s1", "improvement_1")
        transfers = engine.get_transfers()
        assert len(transfers) >= 1

    def test_stats(self):
        engine = ResonanceTransferEngine()
        engine.register_signature(ResonanceSignature(subsystem_id="s1"))
        stats = engine.get_stats()
        assert stats["total_subsystems"] == 1
        assert stats["total_transfers"] == 0
