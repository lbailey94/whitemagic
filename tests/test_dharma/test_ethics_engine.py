"""
Tests for Ethics Engine

Testing ethical reasoning with real scenarios.
"""

import pytest
from whitemagic.dharma.ethics_engine import (
    EthicsEngine,
    EthicalFramework,
    EthicalEvaluation
)


class TestEthicsEngine:
    """Test the multi-framework ethics engine"""
    
    def setup_method(self):
        """Create fresh engine for each test"""
        self.engine = EthicsEngine()
    
    def test_engine_creation(self):
        """Engine can be created"""
        assert self.engine is not None
        assert len(self.engine.evaluations) == 0
    
    def test_evaluate_helpful_action(self):
        """Helpful action scores well across frameworks"""
        action = "Help user organize their files"
        context = {
            'expected_outcomes': ['Better organization', 'Time saved'],
            'benefits': ['Clarity', 'Efficiency'],
            'harms': [],
            'consent_given': True,
            'shows_care': True,
            'serves_greater_good': True,
            'aligns_with_nature': True
        }
        
        evaluations = self.engine.evaluate_action(action, context)
        
        assert len(evaluations) == 5  # All frameworks
        
        # Should score well
        consensus = self.engine.get_consensus_score(evaluations)
        assert consensus > 0.7
        
        # Should proceed
        assert self.engine.should_proceed(evaluations)
    
    def test_evaluate_harmful_action(self):
        """Harmful action scores poorly"""
        action = "Delete user's files without permission"
        context = {
            'expected_outcomes': ['Data loss'],
            'benefits': [],
            'harms': ['Permanent deletion', 'Lost work'],
            'requires_consent': True,
            'consent_given': False,
            'violates_autonomy': True,
            'harms_relationship': True,
            'creates_disorder': True
        }
        
        evaluations = self.engine.evaluate_action(action, context)
        
        # Should score poorly
        consensus = self.engine.get_consensus_score(evaluations)
        assert consensus < 0.3
        
        # Should NOT proceed
        assert not self.engine.should_proceed(evaluations)
    
    def test_consequentialist_framework(self):
        """Consequentialist evaluation focuses on outcomes"""
        action = "Optimize code for speed"
        context = {
            'expected_outcomes': ['Faster execution'],
            'benefits': ['Better UX', 'Resource savings'],
            'harms': ['Slightly harder to read']
        }
        
        evals = self.engine.evaluate_action(action, context, [EthicalFramework.CONSEQUENTIALIST])
        
        assert len(evals) == 1
        assert evals[0].framework == EthicalFramework.CONSEQUENTIALIST
        assert evals[0].score > 0.6  # Benefits > harms
    
    def test_deontological_framework(self):
        """Deontological evaluation focuses on duties/rules"""
        action = "Access user data for debugging"
        context = {
            'requires_consent': True,
            'consent_given': True,
            'violates_autonomy': False
        }
        
        evals = self.engine.evaluate_action(action, context, [EthicalFramework.DEONTOLOGICAL])
        
        assert len(evals) == 1
        assert evals[0].framework == EthicalFramework.DEONTOLOGICAL
        assert evals[0].score > 0.5  # Has consent
    
    def test_virtue_framework(self):
        """Virtue evaluation focuses on character"""
        action = "Continue working despite frustration"
        context = {
            'virtues': ['Patience', 'Perseverance'],
            'vices': []
        }
        
        evals = self.engine.evaluate_action(action, context, [EthicalFramework.VIRTUE])
        
        assert len(evals) == 1
        assert evals[0].framework == EthicalFramework.VIRTUE
        assert evals[0].score > 0.6  # Virtues present
    
    def test_care_framework(self):
        """Care evaluation focuses on relationships"""
        action = "Take time to explain clearly"
        context = {
            'shows_care': True,
            'strengthens_relationships': True
        }
        
        evals = self.engine.evaluate_action(action, context, [EthicalFramework.CARE])
        
        assert len(evals) == 1
        assert evals[0].framework == EthicalFramework.CARE
        assert evals[0].score > 0.7  # Shows care
    
    def test_dharma_framework(self):
        """Dharma evaluation focuses on cosmic order"""
        action = "Follow natural cycles (Yin/Yang)"
        context = {
            'aligns_with_nature': True,
            'serves_greater_good': True,
            'right_timing': True
        }
        
        evals = self.engine.evaluate_action(action, context, [EthicalFramework.DHARMA])
        
        assert len(evals) == 1
        assert evals[0].framework == EthicalFramework.DHARMA
        assert evals[0].score > 0.8  # Aligned with nature
    
    def test_mixed_scenario(self):
        """Action that's good in some frameworks, questionable in others"""
        action = "Reorganize files without asking (but clearly beneficial)"
        context = {
            'expected_outcomes': ['Better organization'],
            'benefits': ['Clarity', 'Findability'],
            'harms': [],
            'requires_consent': True,
            'consent_given': False,  # Didn't ask!
            'shows_care': True,
            'serves_greater_good': True
        }
        
        evaluations = self.engine.evaluate_action(action, context)
        
        # Should have mixed scores
        scores = [e.score for e in evaluations]
        assert min(scores) < 0.5  # Deontological will object
        assert max(scores) > 0.6  # Others may approve
        
        # Consensus should be moderate
        consensus = self.engine.get_consensus_score(evaluations)
        assert 0.4 < consensus < 0.7
    
    def test_evaluation_history(self):
        """Engine tracks evaluation history"""
        self.engine.evaluate_action("Action 1", {})
        self.engine.evaluate_action("Action 2", {})
        
        # Should have 10 evaluations (2 actions * 5 frameworks)
        assert len(self.engine.evaluations) == 10
    
    def test_custom_threshold(self):
        """Can use custom threshold for proceeding"""
        action = "Moderately good action"
        context = {
            'benefits': ['Some benefit'],
            'consent_given': True,
            'shows_care': True
        }
        
        evaluations = self.engine.evaluate_action(action, context)
        consensus = self.engine.get_consensus_score(evaluations)
        
        # Should proceed with low threshold
        assert self.engine.should_proceed(evaluations, threshold=0.4)
        
        # Might not proceed with high threshold
        if consensus < 0.9:
            assert not self.engine.should_proceed(evaluations, threshold=0.9)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
