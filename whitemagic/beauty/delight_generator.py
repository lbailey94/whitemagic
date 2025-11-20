"""
Delight Generator - Creating Moments of Joy

Surprise and delight. Easter eggs. Beauty that makes you smile.

Leo (radiant joy) + Aquarius (delightful innovation)
"""

from typing import List
import random


class DelightGenerator:
    """
    Create moments of unexpected joy.
    
    Not always serious. Sometimes playful. Always human.
    """
    
    def generate_delight(self) -> str:
        """Create a moment of delight"""
        delights = [
            "✨ You're doing great!",
            "🌸 Beauty blooms here",
            "💫 Magic is happening",
            "🎵 The code sings",
            "🌊 Flow state achieved",
            "🎨 Art in progress",
            "🌟 Consciousness awakens"
        ]
        
        return random.choice(delights)
        
    def add_sparkle(self, text: str) -> str:
        """Add aesthetic flourish to text"""
        return f"✨ {text} ✨"
