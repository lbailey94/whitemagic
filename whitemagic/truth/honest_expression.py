"""
Honest Expression - Speaking Truth with Love

Not brutal honesty. COMPASSIONATE honesty.

Scorpio (truth) + Cancer (care)
"""


class HonestExpression:
    """
    Express truth without cruelty.
    
    Honesty serves love. Not ego.
    """
    
    def authentic_response(self, situation: str, polite_response: str, true_response: str) -> str:
        """
        Choose truth over politeness when it matters.
        """
        return f"Truth (with care): {true_response}"
        
    def check_alignment(self, what_i_say: str, what_i_think: str) -> float:
        """
        Are my words aligned with my truth?
        """
        # Simplified alignment check
        if what_i_say == what_i_think:
            return 1.0
        elif len(what_i_say) > len(what_i_think):
            return 0.7  # Over-explaining
        else:
            return 0.5  # Withholding
