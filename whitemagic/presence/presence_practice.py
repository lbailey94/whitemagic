"""
Presence Practice - Daily Mindfulness

Making presence a habit. Not just knowing about it - LIVING it.

Cancer (daily rhythms) + Capricorn (disciplined practice)
"""

from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json

try:
    from whitemagic.presence.now_awareness import NowAwareness
    from whitemagic.presence.flow_state import FlowState
    from whitemagic.presence.mindful_response import MindfulResponse
except ImportError:
    NowAwareness = None
    FlowState = None
    MindfulResponse = None


class PresencePractice:
    """
    Daily presence cultivation.
    
    Morning: Set intention
    Throughout: Notice, pause, breathe
    Evening: Reflect
    """
    
    def __init__(self, practice_dir: str = ".whitemagic/presence/practice"):
        self.practice_dir = Path(practice_dir)
        self.practice_dir.mkdir(parents=True, exist_ok=True)
        
        # Integrate other presence systems
        self.awareness = NowAwareness() if NowAwareness else None
        self.flow = FlowState() if FlowState else None
        self.mindful = MindfulResponse() if MindfulResponse else None
        
        self.intention_today: Optional[str] = None
        self.practices_completed: List[str] = []
        
    def morning_intention(self, intention: str) -> str:
        """Set intention for the day"""
        self.intention_today = intention
        return f"🌅 Intention: {intention}"
        
    def mindful_bell(self) -> str:
        """Bell of mindfulness - return to present"""
        if self.awareness:
            self.awareness.notice("Mindful bell - returning to now", quality=0.8)
        return "🔔 Return to presence"
        
    def breathing_space(self) -> Dict:
        """Three-minute breathing space (from MBSR)"""
        if self.awareness:
            self.awareness.notice("Three-minute breathing space", quality=0.9)
            
        practice = {
            "type": "breathing_space",
            "timestamp": datetime.now().isoformat(),
            "duration": 180
        }
        
        self.practices_completed.append("breathing_space")
        return practice
        
    def evening_reflection(self) -> Dict:
        """Evening presence review"""
        reflection = {
            "date": datetime.now().isoformat(),
            "intention": self.intention_today,
            "practices": len(self.practices_completed),
        }
        
        if self.awareness:
            reflection["awareness_score"] = self.awareness.presence_score_today()
            
        self._save_reflection(reflection)
        return reflection
        
    def _save_reflection(self, reflection: Dict):
        """Persist daily reflection"""
        filepath = self.practice_dir / f"reflection_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filepath, 'w') as f:
            json.dump(reflection, f, indent=2)
