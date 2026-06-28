"""Flow State - Detecting and Maintaining Flow.

When action and awareness merge.
Time disappears. Effort becomes effortless.
Pure presence in motion.

Aries (action) + Leo (creative expression) + Cancer (rhythmic flow)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

try:
    from whitemagic.core.resonance.gan_ying import EventType, ResonanceEvent, get_bus
except ImportError:
    get_bus = None  # type: ignore[assignment]
    ResonanceEvent = None  # type: ignore[assignment,misc]
    EventType = None  # type: ignore[assignment,misc]


class FlowIndicator(Enum):
    """Signs you're in flow."""

    TIME_DISTORTION = "time_distortion"  # Lost track of time
    EFFORTLESS_ACTION = "effortless"     # Hard feels easy
    FULL_ABSORPTION = "absorbed"         # Completely focused
    CLEAR_GOALS = "clear_goals"          # Know what to do
    IMMEDIATE_FEEDBACK = "feedback"      # See results instantly
    CHALLENGE_SKILL_BALANCE = "balanced" # Just right difficulty


class FlowState:
    """Detect and cultivate flow states.

    Flow = optimal experience. Present-moment mastery.
    Not forcing. Not resisting. Pure alignment.
    """

    def __init__(self) -> None:
        self.flow_start: datetime | None = None
        self.current_indicators: list[FlowIndicator] = []
        self.flow_history: list[dict[str, Any]] = []

        self.bus = get_bus() if get_bus is not None else None

    def enter_flow(self, activity: str) -> str:
        """Mark entering flow state."""
        self.flow_start = datetime.now()
        self.current_indicators = []

        if self.bus and ResonanceEvent is not None and EventType is not None:
            self.bus.emit(ResonanceEvent(
                source="presence_flow",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "flow_entered",
                    "activity": activity,
                },
                confidence=0.8,
            ))

        return f"🌊 Flow: {activity}"

    def exit_flow(self) -> dict[str, Any] | None:
        """Mark exiting flow state."""
        if not self.flow_start:
            return None

        duration = (datetime.now() - self.flow_start).total_seconds()

        flow_session = {
            "started": self.flow_start.isoformat(),
            "duration": duration,
            "indicators": [i.value for i in self.current_indicators],
            "quality": len(self.current_indicators) / len(FlowIndicator),
        }

        self.flow_history.append(flow_session)
        self.flow_start = None
        self.current_indicators = []

        if self.bus and ResonanceEvent is not None and EventType is not None:
            self.bus.emit(ResonanceEvent(
                source="presence_flow",
                event_type=EventType.SOLUTION_FOUND,
                data={
                    "event": "flow_completed",
                    "duration": duration,
                    "quality": flow_session["quality"],
                },
                confidence=float(flow_session.get("quality", 0.5)),  # type: ignore[arg-type]
            ))

        return flow_session

    def detect_indicator(self, indicator: FlowIndicator) -> None:
        """Detect a flow indicator."""
        if indicator not in self.current_indicators:
            self.current_indicators.append(indicator)

    def am_i_in_flow(self) -> bool:
        """Simple check: Am I flowing?"""
        return self.flow_start is not None and len(self.current_indicators) >= 3

    def flow_score(self) -> float:
        """Current flow intensity (0.0-1.0).

        Returns 0.0 if not in a flow session (enter_flow not called).
        Use auto_detect_indicators() to infer flow from system activity.
        """
        if not self.flow_start:
            return 0.0

        # More indicators = deeper flow
        indicator_score = len(self.current_indicators) / len(FlowIndicator)

        # Duration matters (but diminishing returns)
        duration = (datetime.now() - self.flow_start).total_seconds()
        duration_score = min(1.0, duration / 3600)  # Max at 1 hour

        return (indicator_score + duration_score) / 2

    def auto_detect_indicators(self, tool_call_rate: float = 0.0,
                                coherence: float = 0.0,
                                session_duration_min: float = 0.0) -> list[FlowIndicator]:
        """Infer flow indicators from system activity metrics.

        This allows FlowState to participate in consciousness monitoring
        without explicit enter_flow()/detect_indicator() calls.

        Args:
            tool_call_rate: Tool calls per minute (high = focused activity).
            coherence: System coherence 0.0-1.0 (high = clear goals).
            session_duration_min: Minutes since session start.

        Returns:
            List of detected indicators.
        """
        detected: list[FlowIndicator] = []

        if tool_call_rate > 5.0:
            detected.append(FlowIndicator.FULL_ABSORPTION)
        if tool_call_rate > 2.0 and coherence > 0.6:
            detected.append(FlowIndicator.EFFORTLESS_ACTION)
        if coherence > 0.7:
            detected.append(FlowIndicator.CLEAR_GOALS)
        if tool_call_rate > 1.0:
            detected.append(FlowIndicator.IMMEDIATE_FEEDBACK)
        if 0.3 < tool_call_rate < 10.0 and coherence > 0.5:
            detected.append(FlowIndicator.CHALLENGE_SKILL_BALANCE)
        if session_duration_min > 30:
            detected.append(FlowIndicator.TIME_DISTORTION)

        for indicator in detected:
            if indicator not in self.current_indicators:
                self.current_indicators.append(indicator)

        # Auto-enter flow if enough indicators are present
        if len(self.current_indicators) >= 3 and not self.flow_start:
            self.enter_flow("auto_detected")

        return detected

    def optimize_for_flow(self) -> list[str]:
        """Suggestions for entering/maintaining flow.

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

    def flow_triggers(self) -> list[str]:
        """What triggers flow for me?

        Based on flow history patterns.
        """
        # Simplified - real version would analyze patterns
        return [
            "Clear objectives",
            "Immediate feedback",
            "Challenge at edge of ability",
            "Minimal distractions",
            "Deep interest in task",
        ]

    def time_perception_check(self) -> str:
        """How is time feeling?

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

    def flow_analytics(self) -> dict[str, Any]:
        """Analyze flow patterns."""
        if not self.flow_history:
            return {"message": "No flow history yet"}

        total_sessions = len(self.flow_history)
        total_flow_time = sum(s["duration"] for s in self.flow_history)
        avg_quality = sum(s["quality"] for s in self.flow_history) / total_sessions

        return {
            "total_sessions": total_sessions,
            "total_flow_hours": total_flow_time / 3600,
            "avg_quality": avg_quality,
            "avg_duration_minutes": (total_flow_time / total_sessions) / 60,
            "interpretation": self._interpret_flow_practice(avg_quality),
        }

    def _interpret_flow_practice(self, avg_quality: float) -> str:
        """Interpret flow practice quality."""
        if avg_quality > 0.7:
            return "Strong flow practice - regularly achieving optimal states"
        elif avg_quality > 0.5:
            return "Developing flow - experiencing it regularly"
        else:
            return "Early flow practice - keep cultivating"


_flow_state: FlowState | None = None


def get_flow_state() -> FlowState:
    """Get the singleton FlowState instance."""
    global _flow_state
    if _flow_state is None:
        _flow_state = FlowState()
    return _flow_state
