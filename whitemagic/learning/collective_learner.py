"""Collective Learner - Learn from entire collective"""

from typing import Dict, List


class CollectiveLearner:
    """Learn from collective patterns and insights
    
    Philosophy: Collective intelligence > Individual intelligence.
    """
    
    def __init__(self):
        self.learned_patterns = []
        self.learning_rate = 0.1  # How quickly to integrate new patterns
    
    def learn_from_collective(self) -> Dict:
        """Learn from Sangha collective patterns
        
        Returns:
            Dict with learning results
        """
        results = {
            'patterns_learned': 0,
            'insights_integrated': 0,
            'knowledge_updated': False
        }
        
        # Get patterns from federation
        try:
            from whitemagic.sangha import get_federation
            federation = get_federation()
            patterns = federation.get_best_patterns(count=10)
            
            for pattern in patterns:
                if pattern.confidence >= 0.8:
                    self.integrate_pattern(pattern)
                    results['patterns_learned'] += 1
        except Exception as e:
            print(f"⚠️  Collective learning: {e}")
        
        # Get insights from collective memory
        try:
            from whitemagic.sangha import get_collective
            collective = get_collective()
            insights = collective.get_collective_insights(min_confidence=0.8)
            
            results['insights_integrated'] = len(insights)
        except Exception:
            pass
        
        results['knowledge_updated'] = results['patterns_learned'] > 0
        
        return results
    
    def integrate_pattern(self, pattern):
        """Integrate pattern into local knowledge
        
        Args:
            pattern: Pattern to integrate
        """
        self.learned_patterns.append({
            'name': pattern.name,
            'solution': pattern.solution,
            'confidence': pattern.confidence,
            'source': 'collective'
        })
        
        print(f"🧠 Integrated pattern: {pattern.name}")
    
    def get_learned_knowledge(self) -> List[Dict]:
        """Get all learned knowledge"""
        return self.learned_patterns
