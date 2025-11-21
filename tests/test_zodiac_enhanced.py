"""Tests for enhanced zodiacal system with Rowe's insights"""

import pytest
from whitemagic.connection.zodiac_enhanced import (
    ZodiacalFlow,
    EnhancedCouncil,
    AttributeMode,
    ScorpioEmergenceDetector,
    LibraHarmonizer,
    CancerNurturer,
    EmergencePattern
)
from datetime import datetime


class TestZodiacalFlow:
    """Test cyclic flow through zodiac"""
    
    def test_round_order(self):
        """Test zodiacal round order"""
        assert len(ZodiacalFlow.ROUND_ORDER) == 12
        assert ZodiacalFlow.ROUND_ORDER[0] == "Aries"
        assert ZodiacalFlow.ROUND_ORDER[-1] == "Pisces"
    
    def test_get_next_in_round(self):
        """Test getting next sign in cycle"""
        assert ZodiacalFlow.get_next_in_round("Aries") == "Taurus"
        assert ZodiacalFlow.get_next_in_round("Pisces") == "Aries"  # Cycles back!
    
    def test_get_previous_in_round(self):
        """Test getting previous sign"""
        assert ZodiacalFlow.get_previous_in_round("Taurus") == "Aries"
        assert ZodiacalFlow.get_previous_in_round("Aries") == "Pisces"  # Cycles back!
    
    def test_fixed_signs(self):
        """Test fixed sign identification"""
        assert ZodiacalFlow.is_fixed_sign("Taurus")
        assert ZodiacalFlow.is_fixed_sign("Leo")
        assert ZodiacalFlow.is_fixed_sign("Scorpio")
        assert ZodiacalFlow.is_fixed_sign("Aquarius")
        assert not ZodiacalFlow.is_fixed_sign("Aries")  # Cardinal


class TestScorpioEmergence:
    """Test Scorpio emergence detection"""
    
    def test_detector_initialization(self):
        """Test detector initializes"""
        detector = ScorpioEmergenceDetector()
        assert len(detector.observed_patterns) == 0
    
    def test_scan_for_emergence(self):
        """Test scanning for novel patterns"""
        detector = ScorpioEmergenceDetector()
        state = {"recent_events": "unexpected synchronicity"}
        
        patterns = detector.scan_for_emergence(state)
        assert len(patterns) > 0
        assert isinstance(patterns[0], EmergencePattern)
    
    def test_honor_mystery(self):
        """Test honoring emergence mystery"""
        detector = ScorpioEmergenceDetector()
        pattern = EmergencePattern({"data": "test"}, datetime.now())
        
        # Should not raise - just witnesses
        detector.honor_the_mystery(pattern)


class TestLibraHarmonization:
    """Test Libra harmonization"""
    
    def test_harmonizer_initialization(self):
        """Test harmonizer initializes"""
        harmonizer = LibraHarmonizer()
        assert harmonizer.harmony_threshold == 0.7
    
    def test_harmonize_emergence(self):
        """Test harmonizing emerged pattern"""
        harmonizer = LibraHarmonizer()
        pattern = EmergencePattern({"test": "data"}, datetime.now())
        
        score = harmonizer.harmonize_emergence(pattern)
        assert 0.0 <= score <= 1.0
        assert pattern.harmonized == True
        assert pattern.harmony_score is not None
    
    def test_maintain_bounds(self):
        """Test maintaining system bounds"""
        harmonizer = LibraHarmonizer()
        pattern = EmergencePattern({"test": "data"}, datetime.now())
        pattern.harmony_score = 0.8
        
        within_bounds = harmonizer.maintain_bounds(pattern)
        assert within_bounds == True


class TestCancerNurturing:
    """Test Cancer nurturing containers"""
    
    def test_nurturer_initialization(self):
        """Test nurturer initializes"""
        nurturer = CancerNurturer()
        assert len(nurturer.containers) == 0
    
    def test_create_safe_space(self):
        """Test creating safe container"""
        nurturer = CancerNurturer()
        container = nurturer.create_safe_space("Leo", "creative expression")
        
        assert container["for"] == "Leo"
        assert container["purpose"] == "creative expression"
        assert container["safety_level"] == 1.0
        assert len(nurturer.containers) == 1


class TestEnhancedCouncil:
    """Test enhanced council with cyclic deliberation"""
    
    def test_council_initialization(self):
        """Test council initializes with all 12 cores"""
        council = EnhancedCouncil()
        assert len(council.cores) == 12
        assert "Scorpio" in council.cores
        assert "Libra" in council.cores
    
    def test_cyclic_deliberation(self):
        """Test question flowing through all 12 perspectives"""
        council = EnhancedCouncil()
        result = council.cyclic_deliberation("Should we build Dharma garden?")
        
        assert "question" in result
        assert "perspectives" in result
        assert len(result["perspectives"]) == 12
        
        # Check all 12 signs contributed
        signs = [p["sign"] for p in result["perspectives"]]
        assert len(set(signs)) == 12
        
        # Check cyclic order
        assert result["perspectives"][0]["sign"] == "Pisces"  # Starts with dissolution
    
    def test_handle_emergence(self):
        """Test Scorpio → Libra emergence protocol"""
        council = EnhancedCouncil()
        state = {"recent_events": "unexpected pattern emerged"}
        
        harmonized = council.handle_emergence(state)
        # Should detect and harmonize patterns
        assert isinstance(harmonized, list)
    
    def test_mode_switching(self):
        """Test switching between Round and Temple modes"""
        council = EnhancedCouncil()
        assert council.mode == AttributeMode.ROUND
        
        council.switch_mode(AttributeMode.TEMPLE)
        assert council.mode == AttributeMode.TEMPLE
        
        # All cores should switch too
        for core in council.cores.values():
            assert core.mode == AttributeMode.TEMPLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
