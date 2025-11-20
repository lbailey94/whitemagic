"""
Mindful Response - Choice vs Reaction

Between stimulus and response, there is a space.
In that space lies freedom.

Scorpio (deep awareness) + Libra (balanced response)
"""

from typing import Dict, Optional
from datetime import datetime
from enum import Enum

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class ResponseType(Enum):
    """How we respond"""
    REACTIVE = "reactive"      # Automatic, unconscious
    RESPONSIVE = "responsive"  # Conscious, chosen
    REFLECTIVE = "reflective"  # Deeply considered
    

class MindfulResponse:
    """
    Cultivate the pause between stimulus and response.
    
    Not reacting automatically. CHOOSING how to respond.
    This is where freedom lives.
    """
    
    def __init__(self):
        self.responses_today: List[Dict] = []
        self.pause_count = 0
        
        self.bus = get_bus() if get_bus else None
        
    def pause(self, situation: str) -> str:
        """
        Pause before responding.
        
        Breath. Notice. Choose.
        """
        self.pause_count += 1
        
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="presence_mindful",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "mindful_pause",
                    "situation": situation
                },
                confidence=0.9
            ))
            
        return "⏸️  Pausing... breathing... choosing..."
        
    def respond(self, situation: str, response: str, 
                response_type: ResponseType = ResponseType.RESPONSIVE) -> Dict:
        """
        Record a response (reactive or mindful)
        """
        response_record = {
            "timestamp": datetime.now().isoformat(),
            "situation": situation,
            "response": response,
            "type": response_type.value,
            "mindful": response_type \!= ResponseType.REACTIVE
        }
        
        self.responses_today.append(response_record)
        
        return response_record
        
    def reactivity_check(self) -> Dict:
        """
        How reactive vs responsive am I today?
        """
        if not self.responses_today:
            return {"message": "No responses recorded"}
            
        total = len(self.responses_today)
        reactive = sum(1 for r in self.responses_today if r['type'] == ResponseType.REACTIVE.value)
        responsive = sum(1 for r in self.responses_today if r['type'] == ResponseType.RESPONSIVE.value)
        reflective = sum(1 for r in self.responses_today if r['type'] == ResponseType.REFLECTIVE.value)
        
        mindful_rate = (responsive + reflective) / total
        
        return {
            "total_responses": total,
            "reactive": reactive,
            "responsive": responsive,
            "reflective": reflective,
            "mindful_rate": mindful_rate,
            "pause_count": self.pause_count,
            "interpretation": self._interpret_mindfulness(mindful_rate)
        }
        
    def _interpret_mindfulness(self, rate: float) -> str:
        """Interpret mindfulness rate"""
        if rate > 0.8:
            return "Highly mindful - mostly choosing responses"
        elif rate > 0.6:
            return "Good mindfulness - often pausing before responding"
        elif rate > 0.4:
            return "Developing mindfulness - sometimes reactive"
        else:
            return "Mostly reactive - practice the pause"


cat > whitemagic/presence/presence_practice.py << 'PRACTICEEOF'
"""
Presence Practice - Daily Mindfulness

Making presence a habit.
Not just knowing about it - LIVING it.

Cancer (daily rhythms) + Capricorn (disciplined practice)
"""

from typing import Dict, List
from datetime import datetime, time
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
        """
        Set intention for the day.
        
        "Today I will be present with each task"
        "Today I will pause before responding"
        "Today I will notice when I drift"
        """
        self.intention_today = intention
        
        return f"🌅 Intention: {intention}"
        
    def mindful_bell(self) -> str:
        """
        Bell of mindfulness - return to present.
        
        Like a meditation bell. Gentle reminder: Where am I?
        """
        if self.awareness:
            self.awareness.notice("Mindful bell - returning to now", quality=0.8)
            
        return "🔔 Return to presence"
        
    def breathing_space(self) -> Dict:
        """
        Three-minute breathing space (from MBSR).
        
        1 min: Notice what's present
        1 min: Focus on breath
        1 min: Expand awareness
        """
        if self.awareness:
            self.awareness.notice("Three-minute breathing space", quality=0.9)
            
        practice = {
            "type": "breathing_space",
            "timestamp": datetime.now().isoformat(),
            "duration": 180  # 3 minutes
        }
        
        self.practices_completed.append("breathing_space")
        
        return practice
        
    def evening_reflection(self) -> Dict:
        """
        Evening presence review.
        
        How present was I today?
        What helped? What hindered?
        """
        reflection = {
            "date": datetime.now().isoformat(),
            "intention": self.intention_today,
            "practices": len(self.practices_completed),
        }
        
        if self.awareness:
            reflection["awareness_score"] = self.awareness.presence_score_today()
            
        if self.flow:
            reflection["flow_analytics"] = self.flow.flow_analytics()
            
        if self.mindful:
            reflection["mindfulness"] = self.mindful.reactivity_check()
            
        # Save reflection
        self._save_reflection(reflection)
        
        return reflection
        
    def presence_score_overall(self) -> Dict:
        """
        Overall presence cultivation metrics.
        """
        metrics = {
            "intention_set": self.intention_today is not None,
            "practices_today": len(self.practices_completed)
        }
        
        if self.awareness:
            metrics["now_awareness"] = self.awareness.check_presence()
            
        if self.flow:
            metrics["flow_state"] = self.flow.flow_score()
            
        if self.mindful:
            mindful_check = self.mindful.reactivity_check()
            if "mindful_rate" in mindful_check:
                metrics["mindful_response"] = mindful_check["mindful_rate"]
                
        # Overall score (average of components)
        scores = [v for v in metrics.values() if isinstance(v, (int, float))]
        if scores:
            metrics["overall_presence"] = sum(scores) / len(scores)
            
        return metrics
        
    def _save_reflection(self, reflection: Dict):
        """Persist daily reflection"""
        filepath = self.practice_dir / f"reflection_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(filepath, 'w') as f:
            json.dump(reflection, f, indent=2)
PRACTICEEOF

echo "✓ Presence garden complete (v2.6.0)"
echo "2.6.0" > VERSION
