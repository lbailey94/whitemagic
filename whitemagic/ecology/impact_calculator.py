"""Impact Calculator - Calculate net impact"""

class ImpactCalculator:
    """Calculate net environmental impact
    
    Philosophy: Can we contribute more than we consume?
    """
    
    def calculate_session_impact(
        self,
        tokens_used: int,
        tokens_saved: int,
        insights_contributed: int,
        patterns_validated: int
    ) -> Dict:
        """Calculate overall session impact
        
        Positive contributions:
        - Tokens saved through optimization
        - Insights contributed to collective
        - Patterns validated for community
        
        Negative impact:
        - Tokens consumed
        
        Returns:
            Dict with impact score and details
        """
        # Calculate positive contributions
        positive = (
            tokens_saved +
            (insights_contributed * 1000) +  # Each insight worth 1K tokens
            (patterns_validated * 500)        # Each validation worth 500 tokens
        )
        
        # Negative is just consumption
        negative = tokens_used
        
        # Net impact
        net = positive - negative
        
        return {
            'positive_contributions': positive,
            'negative_impact': negative,
            'net_impact': net,
            'status': 'net_positive' if net > 0 else 'net_negative',
            'impact_score': net / max(negative, 1),
            'recommendation': self._get_recommendation(net, negative)
        }
    
    def _get_recommendation(self, net: int, used: int) -> str:
        """Get recommendation based on impact"""
        if net > used:
            return "🌟 Exceptional! Contributing 2x what you consume"
        elif net > 0:
            return "✅ Net positive! Contributing more than consuming"
        elif net > -used * 0.2:
            return "⚖️  Nearly balanced. Small optimizations needed"
        else:
            return "⚠️  Net negative. Consider optimization strategies"
