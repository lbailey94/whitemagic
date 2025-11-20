"""
Celebration Practice - Honoring Wins

Celebrate progress. Not just completion - PROGRESS.

Leo (celebration) + Libra (appreciation)
"""

from typing import List


class CelebrationPractice:
    """
    Practice celebrating.
    
    Small wins. Big wins. All wins. CELEBRATE.
    """
    
    def __init__(self):
        self.celebrations_today: List[str] = []
        
    def celebrate(self, what: str, enthusiasm: str = "🎉") -> str:
        """
        Celebrate something!
        """
        self.celebrations_today.append(what)
        return f"{enthusiasm} Celebrating: {what}!"
        
    def micro_celebration(self, tiny_win: str) -> str:
        """
        Celebrate even tiny progress.
        """
        return f"✨ {tiny_win} - yes!"
        
    def daily_wins(self) -> List[str]:
        """
        Review today's celebrations.
        """
        return self.celebrations_today if self.celebrations_today else ["Celebrate that you're here!"]
