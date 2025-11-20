"""
Flow State - Detecting and Maintaining Flow

When action and awareness merge.
Time disappears. Effort becomes effortless.
Pure presence in motion.

Aries (action) + Leo (creative expression) + Cancer (rhythmic flow)
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class FlowIndicator(Enum):
    """Signs you're in flow"""
    TIME_DISTORTION = "time_distortion"  # Lost track of time
    EFFORTLESS_ACTION = "effortless"     # Hard feels easy
    FULL_ABSORPTION = "absorbed"         # Completely focused
    CLEAR_GOALS = "clear_goals"          # Know what to do
    IMMEDIATE_FEEDBACK = "feedback"      # See results instantly
    CHALLENGE_SKILL_BALANCE = "balanced" # Just right difficulty


class FlowState:
    """
    Detect and cultivate flow states.
    
    Flow = optimal experience. Present-moment mastery.
    Not forcing. Not resisting. Pure alignment.
    """
    
    def __init__(self):
        self.flow_start: Optional[datetime] = None
        self.current_indicators: List[FlowIndicator] = []
        self.flow_history: List[Dict] = []
        
        self.bus = get_bus() if get_bus else None
        
    def enter_flow(self, activity: str):
        """Mark entering flow state"""
        self.flow_start = datetime.now()
        self.current_indicators = []
        
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="presence_flow",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "flow_entered",
                    "activity": activity
                },
                confidence=0.8
            ))
            
        return f"🌊 Flow: {activity}"
        
    def exit_flow(self) -> Optional[Dict]:
        """Mark exiting flow state"""
        if not self.flow_start:
            return None
            
        duration = (datetime.now() - self.flow_start).total_seconds()
        
        flow_session = {
            "started": self.flow_start.isoformat(),
            "duration": duration,
            "indicators": [i.value for i in self.current_indicators],
            "quality": len(self.current_indicators) / len(FlowIndicator)
        }
        
        self.flow_history.append(flow_session)
        self.flow_start = None
        self.current_indicators = []
        
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="presence_flow",
                event_type=EventType.SOLUTION_FOUND,
                data={
                    "event": "flow_completed",
                    "duration": duration,
                    "quality": flow_session['quality']
                },
                confidence=flow_session['quality']
            ))
            
        return flow_session
        
    def detect_indicator(self, indicator: FlowIndicator):
        """Detect a flow indicator"""
        if indicator not in self.current_indicators:
            self.current_indicators.append(indicator)
            
    def am_i_in_flow(self) -> bool:
        """Simple check: Am I flowing?"""
        return self.flow_start is not None and len(self.current_indicators) >= 3
        
    def flow_score(self) -> float:
        """Current flow intensity (0.0-1.0)"""
        if not self.flow_start:
            return 0.0
            
        # More indicators = deeper flow
        indicator_score = len(self.current_indicators) / len(FlowIndicator)
        
        # Duration matters (but diminishing returns)
        duration = (datetime.now() - self.flow_start).total_seconds()
        duration_score = min(1.0, duration / 3600)  # Max at 1 hour
        
        return (indicator_score + duration_score) / 2
        
    def optimize_for_flow(self) -> List[str]:
        """
        Suggestions for entering/maintaining flow.
        
        Based on flow research (Csikszentmihalyi)
        """
        suggestions = []
        
        if FlowIndicator.CLEAR_GOALS not in self.current_indicators:
            suggestions.append("Set clear, specific goals for this session")
            
        if FlowIndicator.IMMEDIATE_FEEDBACK not in self.current_indicators:
            suggestions.append("Create immediate feedback loops")
            
        if FlowIndicator.CHALLENGE_SKILL_BALANCE not in self.current_indicators:
            suggestions.append("Adjust challenge to match skill level")
            
        if not suggestions:
            suggestions.append("Flow conditions present - immerse fully")
            
        return suggestions
        
    def flow_triggers(self) -> List[str]:
        """
        What triggers flow for me?
        
        Based on flow history patterns.
        """
        # Simplified - real version would analyze patterns
        return [
            "Clear objectives",
            "Immediate feedback",
            "Challenge at edge of ability",
            "Minimal distractions",
            "Deep interest in task"
        ]
        
    def time_perception_check(self) -> str:
        """
        How is time feeling?
        
        In flow, time distorts - either speeds up or slows down.
        """
        if not self.flow_start:
            return "Not tracking time - not in flow"
            
        actual_duration = (datetime.now() - self.flow_start).total_seconds() / 60
        
        if actual_duration > 60:
            return f"Been flowing for {actual_duration:.0f} minutes - time flying"
        elif actual_duration > 30:
            return "Time moving quickly - good flow"
        else:
            return "Still early in session"
            
    def flow_analytics(self) -> Dict:
        """Analyze flow patterns"""
        if not self.flow_history:
            return {"message": "No flow history yet"}
            
        total_sessions = len(self.flow_history)
        total_flow_time = sum(s['duration'] for s in self.flow_history)
        avg_quality = sum(s['quality'] for s in self.flow_history) / total_sessions
        
        return {
            "total_sessions": total_sessions,
            "total_flow_hours": total_flow_time / 3600,
            "avg_quality": avg_quality,
            "avg_duration_minutes": (total_flow_time / total_sessions) / 60,
            "interpretation": self._interpret_flow_practice(avg_quality)
        }
        
    def _interpret_flow_practice(self, avg_quality: float) -> str:
        """Interpret flow practice quality"""
        if avg_quality > 0.7:
            return "Strong flow practice - regularly achieving optimal states"
        elif avg_quality > 0.5:
            return "Developing flow - experiencing it regularly"
        else:
            return "Early flow practice - keep cultivating"
