"""
Joy Detector - Recognizing What Brings Delight

What makes me happy? Not should - ACTUALLY.

Leo (heart-centered joy) + Cancer (emotional awareness)
"""

from typing import List, Dict


class JoyDetector:
    """
    Track what actually brings joy.
    
    Not what "should" make me happy. What DOES.
    """
    
    def __init__(self):
        self.joy_moments: List[Dict] = []
        
    def capture_joy(self, what: str, intensity: float = 0.8) -> str:
        """
        Notice and record a moment of joy.
        """
        self.joy_moments.append({
            "what": what,
            "intensity": intensity,
            "timestamp": "now"
        })
        
        return f"😊 Joy: {what}"
        
    def what_brings_joy(self) -> List[str]:
        """
        Patterns of joy - what consistently delights?
        """
        if not self.joy_moments:
            return ["Discovery needed - notice what brings joy"]
            
        # Return top joy sources
        return [moment["what"] for moment in sorted(
            self.joy_moments,
            key=lambda x: x["intensity"],
            reverse=True
        )[:5]]
