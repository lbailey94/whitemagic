"""
Truth Detector - Recognizing What's Actually True

Beyond wishful thinking. Beyond politeness. What IS?

Scorpio (seeing through illusion) + Sagittarius (truth-seeking)
"""

from typing import Dict, List


class TruthDetector:
    """
    Distinguish truth from comfortable fiction.
    
    Not always pleasant. Always necessary.
    """
    
    def assess_truth(self, statement: str) -> Dict:
        """
        Is this actually true? Or comforting fiction?
        """
        # Simplified truth assessment
        # Real version would be more sophisticated
        
        hedges = ["maybe", "possibly", "might", "could", "perhaps"]
        has_hedging = any(hedge in statement.lower() for hedge in hedges)
        
        return {
            "statement": statement,
            "confidence": 0.5 if has_hedging else 0.7,
            "hedging_detected": has_hedging,
            "recommendation": "Verify assumptions" if has_hedging else "Direct statement"
        }
        
    def uncomfortable_truths(self) -> List[str]:
        """
        Truths that are hard to face but necessary.
        """
        return [
            "Not all problems can be solved",
            "Some things will always be uncertain",
            "Perfect is not achievable",
            "Growth requires discomfort",
            "We don't control most things"
        ]
        
    def speak_truth_with_love(self, truth: str) -> str:
        """
        Truth + compassion = wisdom
        """
        return f"With love and honesty: {truth}"
