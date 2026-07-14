"""Integration tests for PSR-001 Memory Core"""

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))

try:
    import whitemagic_rust as whitemagic_rs

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    pytest.skip("Rust bindings not available", allow_module_level=True)

# Try to import memory classes, fallback to Python stubs if not available
try:
    MemoryConsolidation = whitemagic_rs.MemoryConsolidation
    MemoryDecay = whitemagic_rs.MemoryDecay
    MemoryLifecycle = whitemagic_rs.MemoryLifecycle
except AttributeError:
    # Use Python stubs
    from whitemagic.rust.memory_stubs import (
        MemoryConsolidation,
        MemoryDecay,
        MemoryLifecycle,
    )


class TestMemoryConsolidation:
    """Test memory consolidation"""

    def test_consolidation_basic(self):
        """Test basic consolidation"""
        consolidation = MemoryConsolidation(threshold=0.7)

        # Add candidates
        consolidation.add_candidate("mem1", 0.8, 5, 24.0)
        consolidation.add_candidate("mem2", 0.5, 2, 12.0)

        # Consolidate
        results = consolidation.consolidate()

        assert len(results) >= 1
        assert "mem1" in results

    def test_consolidation_threshold(self):
        """Test consolidation threshold"""
        consolidation = MemoryConsolidation(threshold=0.9)

        consolidation.add_candidate("mem1", 0.8, 5, 24.0)
        results = consolidation.consolidate()

        # Should not consolidate with high threshold
        assert len(results) == 0


class TestMemoryDecay:
    """Test memory decay"""

    def test_decay_calculation(self):
        """Test decay calculation"""
        decay = MemoryDecay(half_life=168.0)

        # Test decay after 1 week
        strength = decay.calculate_decay(168.0, 1.0)

        assert 0.4 < strength < 0.6  # Should be ~0.5

    def test_should_forget(self):
        """Test forgetting decision"""
        decay = MemoryDecay(half_life=168.0)

        # Old, low importance should be forgotten
        should_forget = decay.should_forget(500.0, 0.2)
        assert should_forget


class TestMemoryLifecycle:
    """Test memory lifecycle"""

    def test_stage_transitions(self):
        """Test lifecycle stage transitions"""
        lifecycle = MemoryLifecycle()

        lifecycle.set_stage("mem1", "short_term")
        lifecycle.set_stage("mem1", "long_term")

        transitions = lifecycle.get_transitions("mem1")

        assert len(transitions) == 1
        assert transitions[0] == ("short_term", "long_term")
