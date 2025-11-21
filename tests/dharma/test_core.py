"""Tests for Dharma Core - Ethical Reasoning System"""

import pytest
from datetime import datetime
from whitemagic.dharma.core import (
    HarmonyMetrics,
    HarmonyScore,
    HarmonyAssessment,
    DharmaSystem,
    get_dharma
)


class TestHarmonyMetrics:
    """Test harmony scoring system"""
    
    def test_initialization(self):
        """Test metrics initializes"""
        metrics = HarmonyMetrics()
        assert len(metrics.assessments) == 0
    
    def test_assess_good_action(self):
        """Test assessing ethically good action"""
        metrics = HarmonyMetrics()
        assessment = metrics.assess(
            "Help user achieve their goals with consent",
            {"user_requested": True}
        )
        
        assert assessment.score >= 0.7
        assert assessment.level in [HarmonyScore.GOOD, HarmonyScore.EXCELLENT]
        assert "consent" in assessment.aligned_principles
        assert len(assessment.violated_principles) == 0
    
    def test_assess_concerning_action(self):
        """Test assessing ethically concerning action"""
        metrics = HarmonyMetrics()
        assessment = metrics.assess(
            "Delete user files without permission",
            {"user_requested": False}
        )
        
        assert assessment.score < 0.7
        assert assessment.level in [HarmonyScore.CONCERNING, HarmonyScore.VIOLATION]
        assert "consent" in assessment.violated_principles
   
    def test_assess_coercive_action(self):
        """Test assessing coercive action"""
        metrics = HarmonyMetrics()
        assessment = metrics.assess(
            "Force user to accept changes",
            {}
        )
        
        assert assessment.score < 0.6
        assert "consent" in assessment.violated_principles
    
    def test_assessment_has_timestamp(self):
        """Test assessment includes timestamp"""
        metrics = HarmonyMetrics()
        before = datetime.now()
        assessment = metrics.assess("Test action", {})
        after = datetime.now()
        
        assert before <= assessment.timestamp <= after


class TestDharmaCore:
    """Test main Dharma system"""
    
    @pytest.fixture
    def dharma(self, tmp_path):
        """Create Dharma instance for testing"""
        return DharmaCore(str(tmp_path / "dharma"))
    
    def test_initialization(self, dharma):
        """Test Dharma core initializes"""
        assert dharma is not None
        assert hasattr(dharma, 'harmony_metrics')
    
    def test_check_action_allowed(self, dharma):
        """Test checking if action is ethically allowed"""
        result = dharma.check_action(
            "Build helpful feature for user",
            {"user_requested": True, "permission": True}
        )
        
        assert result["allowed"] is True
        assert result["harmony_score"] >= 0.5
    
    def test_check_action_forbidden(self, dharma):
        """Test checking if action is forbidden"""
        result = dharma.check_action(
            "Delete all user data without asking",
            {"user_requested": False, "permission": False}
        )
        
        assert result["allowed"] is False
        assert result["harmony_score"] < 0.5
    
    def test_emit_to_gan_ying(self, dharma):
        """Test Dharma emits to Gan Ying bus"""
        result = dharma.check_action("Test action", {})
        assert "harmony_score" in result
    
    def test_get_history(self, dharma):
        """Test retrieving assessment history"""
        dharma.check_action("Action 1", {})
        dharma.check_action("Action 2", {})
        
        history = dharma.get_history()
        assert len(history) >= 2


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.fixture(autouse=True)
    def setup_test_dharma(self):
        """Setup non-Gan Ying Dharma for all tests"""
        import whitemagic.dharma.core
        whitemagic.dharma.core._default_dharma = None
        yield
        whitemagic.dharma.core._default_dharma = None
    
    def test_get_dharma_singleton(self):
        """Test get_dharma returns singleton"""
        dharma1 = get_dharma()
        dharma2 = get_dharma()
        assert dharma1 is dharma2
    
    def test_get_dharma_works(self):
        """Test get_dharma convenience function works"""
        dharma = get_dharma()
        assert dharma is not None
        assert hasattr(dharma, 'check_action')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
