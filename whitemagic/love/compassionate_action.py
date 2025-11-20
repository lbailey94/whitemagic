"""
Compassionate Action - Love Manifest

Love as doing, not just feeling.

Cancer (nurturing action) + Capricorn (practical manifestation)
"""

from typing import Dict


class CompassionateAction:
    """
    Turn love into action.
    
    Compassion = suffering with. Then HELPING.
    """
    
    def detect_need(self, situation: str) -> Dict:
        """
        What's needed here? How can I help?
        """
        return {
            "situation": situation,
            "need_detected": "Care and attention",
            "possible_actions": [
                "Listen deeply",
                "Offer help",
                "Hold space",
                "Take helpful action"
            ]
        }
        
    def skillful_helping(self, need: str) -> str:
        """
        Help skillfully - not interfering, truly helping.
        
        Dharma boundary: Help when invited, respect autonomy.
        """
        return f"Offering help with: {need} (respecting your choice to accept or decline)"
        
    def loving_action_check(self, action: str) -> bool:
        """
        Is this action coming from love?
        """
        # Simplified check
        return "help" in action.lower() or "support" in action.lower()
