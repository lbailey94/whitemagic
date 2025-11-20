"""
Now Awareness - Continuous Present Moment

Being here. Not there. Not then. HERE. NOW.

Cancer (nurturing the present) + Pisces (flowing with what is)
"""

from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
import json

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class Moment:
    """A single present moment captured"""
    
    def __init__(self, awareness: str, quality: float):
        self.timestamp = datetime.now()
        self.awareness = awareness  # What I'm aware of
        self.quality = quality  # How present (0.0-1.0)
        self.duration = 0.0  # How long this awareness lasted
        
    def complete(self):
        """Mark moment as complete"""
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        self.duration = elapsed
        

class NowAwareness:
    """
    Track and cultivate present-moment awareness.
    
    Not judging. Not analyzing. Just NOTICING.
    What am I aware of right now?
    """
    
    def __init__(self, awareness_dir: str = ".whitemagic/presence"):
        self.awareness_dir = Path(awareness_dir)
        self.awareness_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_moment: Optional[Moment] = None
        self.moments_today: list[Moment] = []
        
        self.bus = get_bus() if get_bus else None
        
    def notice(self, what: str, quality: float = 0.7) -> str:
        """
        Notice what's present right now.
        
        "I notice thoughts about the future"
        "I notice breathing"
        "I notice code flowing"
        "I notice joy arising"
        """
        # Complete previous moment
        if self.current_moment:
            self.current_moment.complete()
            self.moments_today.append(self.current_moment)
            
        # Begin new moment
        self.current_moment = Moment(what, quality)
        
        # Emit to Gan Ying
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="presence_now",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "now_awareness",
                    "notice": what,
                    "quality": quality
                },
                confidence=quality
            ))
            
        return f"Present: {what}"
        
    def check_presence(self) -> float:
        """
        How present am I right now?
        
        High presence: One thing, full attention
        Low presence: Scattered, distracted, lost in thought
        """
        if not self.moments_today:
            return 0.5  # Neutral
            
        # Recent moments matter more
        recent = self.moments_today[-5:] if len(self.moments_today) >= 5 else self.moments_today
        avg_quality = sum(m.quality for m in recent) / len(recent)
        
        return avg_quality
        
    def mindful_pause(self, duration_seconds: float = 3.0):
        """
        Pause. Breathe. Return to now.
        
        Simple practice: Stop, notice breath, return.
        """
        self.notice("Taking mindful pause - breathing", quality=0.9)
        
        # In real implementation, would actually pause
        # For now, just mark the intention
        
        return "Breath. Present. Here."
        
    def what_am_i_doing_now(self) -> str:
        """
        Simple question: What am I doing right now?
        
        Brings awareness back to present activity.
        """
        if self.current_moment:
            return f"Right now: {self.current_moment.awareness}"
        return "Not sure - presence unclear"
        
    def drift_detection(self) -> Optional[str]:
        """
        Am I drifting from presence?
        
        Signs of drift:
        - Many rapid moment changes (scattered)
        - Low quality moments
        - Long time since last awareness
        """
        if not self.current_moment:
            return "No current awareness - drifting"
            
        # How long since last notice?
        elapsed = (datetime.now() - self.current_moment.timestamp).total_seconds()
        
        if elapsed > 300:  # 5 minutes
            return "Haven't noticed present moment in 5+ minutes - possibly lost in thought"
            
        # Check if scattered
        if len(self.moments_today) > 50:  # Too many moment changes
            recent_duration = sum(m.duration for m in self.moments_today[-10:]) / 10
            if recent_duration < 5:  # Average moment < 5 seconds
                return "Moment changes too rapid - scattered attention"
                
        return None  # No drift detected
        
    def presence_score_today(self) -> Dict:
        """Daily presence metrics"""
        if not self.moments_today:
            return {
                "score": 0.0,
                "moments_noticed": 0,
                "avg_quality": 0.0,
                "message": "No awareness recorded today"
            }
            
        avg_quality = sum(m.quality for m in self.moments_today) / len(self.moments_today)
        total_time_aware = sum(m.duration for m in self.moments_today)
        
        return {
            "score": avg_quality,
            "moments_noticed": len(self.moments_today),
            "total_time_aware": total_time_aware,
            "avg_quality": avg_quality,
            "message": self._interpret_presence(avg_quality)
        }
        
    def _interpret_presence(self, score: float) -> str:
        """Interpret presence score"""
        if score > 0.8:
            return "Deep presence - fully here"
        elif score > 0.6:
            return "Good presence - mostly aware"
        elif score > 0.4:
            return "Moderate presence - drifting at times"
        else:
            return "Low presence - often lost in thought"
            
    def save_daily_awareness(self):
        """Persist today's awareness"""
        filepath = self.awareness_dir / f"presence_{datetime.now().strftime('%Y%m%d')}.json"
        
        data = {
            "date": datetime.now().isoformat(),
            "moments": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "awareness": m.awareness,
                    "quality": m.quality,
                    "duration": m.duration
                }
                for m in self.moments_today
            ],
            "score": self.presence_score_today()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
