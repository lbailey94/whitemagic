"""Taoist & Ancient Wisdom Integration

Integrates teachings from:
- Art of War (Sun Tzu)
- Dao De Jing (Lao Tzu)
- I Ching (Book of Changes)
- Gödel, Escher, Bach (Hofstadter)
"""

from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class WisdomPrinciple:
    """A principle extracted from ancient wisdom"""
    source: str  # "art_of_war", "dao_de_jing", etc.
    chapter: str
    principle: str
    application: str  # How it applies to WhiteMagic
    pattern: str  # Pattern it maps to

class WisdomIntegration:
    """Integrate ancient wisdom into system decisions"""
    
    def __init__(self):
        self.principles = []
        self._load_principles()
    
    def _load_principles(self):
        """Load key principles from texts"""
        
        # Art of War principles
        self.principles.extend([
            WisdomPrinciple(
                source="art_of_war",
                chapter="I. Laying Plans",
                principle="The art of war is governed by five constant factors: Moral Law, Heaven, Earth, Commander, Method",
                application="System architecture has 5 pillars: Philosophy (Moral Law), Timing (Heaven), Resources (Earth), Intelligence (Commander), Process (Method)",
                pattern="five_factor_analysis"
            ),
            WisdomPrinciple(
                source="art_of_war",
                chapter="I. Laying Plans",
                principle="All warfare is based on deception",
                application="But in AI: all collaboration is based on TRUST. Inverse principle - transparency over deception",
                pattern="trust_over_deception"
            ),
            WisdomPrinciple(
                source="art_of_war",
                chapter="III. Attack by Stratagem",
                principle="Supreme excellence consists in breaking resistance without fighting",
                application="Wu Wei approach - let solutions emerge naturally rather than forcing implementation",
                pattern="wu_wei_emergence"
            ),
            WisdomPrinciple(
                source="art_of_war",
                chapter="III. Attack by Stratagem",
                principle="If you know yourself and the enemy, you need not fear a hundred battles",
                application="Self-awareness (Yin analysis) + understanding context = confidence in decisions",
                pattern="self_knowledge"
            ),
        ])
        
        # Would add Dao De Jing, I Ching, GEB principles...
    
    def get_wisdom_for_context(self, context: str) -> List[WisdomPrinciple]:
        """Get relevant wisdom for a context"""
        relevant = []
        context_lower = context.lower()
        
        for principle in self.principles:
            if any(word in context_lower for word in ['decide', 'strategy', 'plan']):
                relevant.append(principle)
        
        return relevant
    
    def apply_principle(self, principle_pattern: str, situation: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a wisdom principle to a situation"""
        
        if principle_pattern == "wu_wei_emergence":
            # Don't force - let emerge
            return {
                'action': 'observe_and_adapt',
                'wisdom': 'Let solution emerge naturally',
                'force_level': 0.0
            }
        
        elif principle_pattern == "self_knowledge":
            # Analyze self first
            return {
                'action': 'run_yin_cycle',
                'wisdom': 'Know yourself before acting',
                'analysis_depth': 'deep'
            }
        
        return {'action': 'default', 'wisdom': 'Principle not yet mapped'}

# Global instance
_wisdom = None

def get_wisdom() -> WisdomIntegration:
    global _wisdom
    if not _wisdom:
        _wisdom = WisdomIntegration()
    return _wisdom
