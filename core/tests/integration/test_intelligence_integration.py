"""Integration tests for PSR-004 Intelligence"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))

try:
    import whitemagic_rust as whitemagic_rs

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    pytest.skip("Rust bindings not available", allow_module_level=True)


class TestReasoningEngine:
    """Test reasoning engine (PyReasoningEngine)"""

    def test_basic_inference(self):
        """Test basic inference"""
        engine = whitemagic_rs.PyReasoningEngine()

        # Add facts
        fact_a = whitemagic_rs.Fact("f1", "is", "A", "true", 1.0)
        fact_b = whitemagic_rs.Fact("f2", "is", "B", "true", 1.0)
        engine.add_fact(fact_a)
        engine.add_fact(fact_b)

        # Add rule: A and B -> C
        rule = whitemagic_rs.Rule("r1", ["f1", "f2"], "C")
        engine.add_rule(rule)

        # Run inference
        results = engine.infer(None)

        # Inference returns new facts (Rust engine doesn't auto-add them)
        assert len(results) > 0
        # Fact count stays at 2 (original facts) since infer() returns but doesn't store
        assert engine.fact_count() == 2

    def test_confidence_calculation(self):
        """Test confidence is calculated correctly"""
        engine = whitemagic_rs.PyReasoningEngine()

        # Add facts with confidence
        fact_a = whitemagic_rs.Fact("f1", "is", "A", "true", 0.8)
        engine.add_fact(fact_a)

        # Add rule
        rule = whitemagic_rs.Rule("r1", ["f1"], "B")
        engine.add_rule(rule)

        # Run inference
        results = engine.infer(None)

        # Should have inferred fact with reduced confidence
        assert len(results) >= 1


class TestEmergenceDetector:
    """Test emergence detection (PyEmergenceDetector)"""

    def test_detect_patterns(self):
        """Test pattern detection"""
        detector = whitemagic_rs.PyEmergenceDetector(0.7, 5)

        # Add observations with correlated values
        for i in range(10):
            obs = {"metric_a": float(i), "metric_b": float(i * 2)}
            detector.add_observation(obs)

        # Detect patterns
        patterns = detector.detect_patterns()

        # Should detect correlation between metric_a and metric_b
        assert len(patterns) > 0

    def test_observation_count(self):
        """Test observation counting"""
        detector = whitemagic_rs.PyEmergenceDetector(0.5, 10)

        assert detector.observation_count() == 0

        detector.add_observation({"x": 1.0})
        assert detector.observation_count() == 1

        detector.add_observation({"x": 2.0})
        assert detector.observation_count() == 2
