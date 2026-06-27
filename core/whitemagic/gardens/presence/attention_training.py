"""
Attention Training for Presence Garden

Provides exercises and metrics for:
- Focus duration
- Attention stability
- Distraction recovery
- Sustained concentration
"""

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class AttentionState(Enum):
    """States of attention."""
    FOCUSED = "focused"         # Single-pointed attention
    DIFFUSE = "diffuse"         # Broad, relaxed awareness
    DISTRACTED = "distracted"   # Lost in thought
    DROWSY = "drowsy"           # Dull, sleepy
    AGITATED = "agitated"       # Restless, scattered


@dataclass
class AttentionEvent:
    """A recorded attention event."""
    timestamp: datetime
    state: AttentionState
    duration_seconds: float
    trigger: str | None = None  # What caused state change
    recovery_time: float | None = None  # Time to return to focus


@dataclass
class AttentionSession:
    """A session of attention training."""
    started_at: datetime
    ended_at: datetime | None = None
    events: list[AttentionEvent] = field(default_factory=list)
    target_object: str = "breath"  # What we're focusing on

    def duration(self) -> timedelta:
        end = self.ended_at or datetime.now()
        return end - self.started_at

    def focus_percentage(self) -> float:
        """Calculate percentage of time in focused state."""
        if not self.events:
            return 0.0

        focused_time = sum(
            e.duration_seconds for e in self.events
            if e.state == AttentionState.FOCUSED
        )
        total_time = sum(e.duration_seconds for e in self.events)

        return (focused_time / total_time * 100) if total_time > 0 else 0.0

    def distraction_count(self) -> int:
        """Count number of distractions."""
        return sum(1 for e in self.events if e.state == AttentionState.DISTRACTED)

    def average_recovery_time(self) -> float:
        """Average time to recover from distraction."""
        recoveries = [e.recovery_time for e in self.events if e.recovery_time]
        return sum(recoveries) / len(recoveries) if recoveries else 0.0

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "duration_seconds": self.duration().total_seconds(),
            "focus_percentage": self.focus_percentage(),
            "distraction_count": self.distraction_count(),
            "average_recovery_time": self.average_recovery_time(),
            "target_object": self.target_object
        }


class AttentionTracker:
    """Tracks attention during a session."""

    def __init__(self, target: str = "breath"):
        self.session = AttentionSession(
            started_at=datetime.now(),
            target_object=target
        )
        self.current_state = AttentionState.FOCUSED
        self.state_started = datetime.now()
        self.last_distraction_end: datetime | None = None

    def record_state_change(self, new_state: AttentionState, trigger: str | None = None) -> None:
        """Record a change in attention state."""
        now = datetime.now()
        duration = (now - self.state_started).total_seconds()

        # Calculate recovery time if returning from distraction
        recovery_time = None
        if self.current_state == AttentionState.DISTRACTED and new_state == AttentionState.FOCUSED:
            recovery_time = duration

        event = AttentionEvent(
            timestamp=self.state_started,
            state=self.current_state,
            duration_seconds=duration,
            trigger=trigger,
            recovery_time=recovery_time
        )
        self.session.events.append(event)

        self.current_state = new_state
        self.state_started = now

    def mark_distracted(self, trigger: str = "thought") -> None:
        """Mark that attention has wandered."""
        self.record_state_change(AttentionState.DISTRACTED, trigger)

    def mark_focused(self) -> None:
        """Mark return to focused attention."""
        self.record_state_change(AttentionState.FOCUSED)

    def end_session(self) -> AttentionSession:
        """End the session and return results."""
        # Record final state
        self.record_state_change(self.current_state)
        self.session.ended_at = datetime.now()
        return self.session


@dataclass
class AttentionExercise:
    """An attention training exercise."""
    name: str
    description: str
    duration_minutes: int
    difficulty: int  # 1-5
    instructions: list[str]
    target: str = "breath"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "difficulty": self.difficulty,
            "target": self.target
        }


# Built-in exercises
EXERCISES: dict[str, AttentionExercise] = {}


def register_exercise(exercise: AttentionExercise) -> None:
    """Register an attention exercise."""
    EXERCISES[exercise.name] = exercise


def get_exercise(name: str) -> AttentionExercise | None:
    """Get an exercise by name."""
    return EXERCISES.get(name)


def list_exercises(difficulty: int | None = None) -> list[AttentionExercise]:
    """List exercises, optionally filtered by difficulty."""
    if difficulty:
        return [e for e in EXERCISES.values() if e.difficulty == difficulty]
    return list(EXERCISES.values())


# === REGISTER EXERCISES ===

register_exercise(AttentionExercise(
    name="breath_anchor",
    description="Use breath as anchor for attention",
    duration_minutes=10,
    difficulty=1,
    target="breath",
    instructions=[
        "Sit comfortably with eyes closed",
        "Focus attention on the sensation of breathing",
        "Notice the breath at the nostrils, chest, or belly",
        "When mind wanders, gently return to breath",
        "Count each distraction without judgment",
        "Aim to reduce distractions over time"
    ]
))

register_exercise(AttentionExercise(
    name="candle_gaze",
    description="Trataka - steady gaze meditation",
    duration_minutes=5,
    difficulty=2,
    target="candle",
    instructions=[
        "Place a candle at eye level, arm's length away",
        "Gaze steadily at the flame without blinking",
        "When eyes water, close them and visualize the flame",
        "Open eyes and repeat",
        "Builds concentration and visual focus"
    ]
))

register_exercise(AttentionExercise(
    name="sound_focus",
    description="Focus on a single sound",
    duration_minutes=10,
    difficulty=2,
    target="sound",
    instructions=[
        "Choose a continuous sound (fan, traffic, nature)",
        "Focus attention entirely on that sound",
        "Notice its qualities: pitch, rhythm, texture",
        "When mind wanders, return to the sound",
        "Practice hearing without labeling"
    ]
))

register_exercise(AttentionExercise(
    name="body_point",
    description="Focus on a single point in the body",
    duration_minutes=10,
    difficulty=2,
    target="body_point",
    instructions=[
        "Choose a point: tip of nose, center of chest, or third eye",
        "Rest attention there without forcing",
        "Notice any sensations that arise",
        "When attention drifts, gently return",
        "Allow the point to become vivid and clear"
    ]
))

register_exercise(AttentionExercise(
    name="counting_meditation",
    description="Count breaths to train sustained attention",
    duration_minutes=15,
    difficulty=3,
    target="counting",
    instructions=[
        "Count each exhale from 1 to 10",
        "If you lose count, start over at 1",
        "If you go past 10, start over at 1",
        "The goal is sustained, accurate counting",
        "Track how many times you complete 1-10"
    ]
))

register_exercise(AttentionExercise(
    name="noting_practice",
    description="Note distractions to build metacognition",
    duration_minutes=15,
    difficulty=3,
    target="breath",
    instructions=[
        "Focus on breath as primary object",
        "When distracted, silently note the type: 'thinking', 'planning', 'remembering'",
        "Return to breath after noting",
        "This builds awareness of attention patterns",
        "Track which types of distraction are most common"
    ]
))

register_exercise(AttentionExercise(
    name="expanding_attention",
    description="Expand and contract attention field",
    duration_minutes=10,
    difficulty=4,
    target="field",
    instructions=[
        "Start with narrow focus on breath",
        "Gradually expand to include body sensations",
        "Expand further to include sounds",
        "Expand to include the whole room",
        "Contract back to breath",
        "Practice smooth expansion and contraction"
    ]
))

register_exercise(AttentionExercise(
    name="dual_attention",
    description="Hold two objects in attention simultaneously",
    duration_minutes=10,
    difficulty=5,
    target="dual",
    instructions=[
        "Focus on breath AND a body sensation simultaneously",
        "Don't alternate - hold both at once",
        "This is challenging and builds attention capacity",
        "Start with brief periods and extend",
        "Notice when attention collapses to one object"
    ]
))


class AttentionMetrics:
    """Calculates attention metrics across sessions."""

    def __init__(self):
        self.sessions: list[AttentionSession] = []

    def add_session(self, session: AttentionSession) -> None:
        """Add a completed session."""
        self.sessions.append(session)

    def average_focus(self) -> float:
        """Average focus percentage across sessions."""
        if not self.sessions:
            return 0.0
        return sum(s.focus_percentage() for s in self.sessions) / len(self.sessions)

    def total_practice_time(self) -> timedelta:
        """Total time spent practicing."""
        return sum((s.duration() for s in self.sessions), timedelta())

    def improvement_trend(self) -> float:
        """Calculate improvement trend (positive = improving)."""
        if len(self.sessions) < 2:
            return 0.0

        # Compare first half to second half
        mid = len(self.sessions) // 2
        first_half = sum(s.focus_percentage() for s in self.sessions[:mid]) / mid
        second_half = sum(s.focus_percentage() for s in self.sessions[mid:]) / (len(self.sessions) - mid)

        return second_half - first_half

    def to_dict(self) -> dict:
        return {
            "total_sessions": len(self.sessions),
            "total_practice_minutes": self.total_practice_time().total_seconds() / 60,
            "average_focus_percentage": self.average_focus(),
            "improvement_trend": self.improvement_trend()
        }


def generate_training_plan(
    current_level: int = 1,
    sessions_per_week: int = 5,
    weeks: int = 4
) -> list[dict]:
    """Generate a progressive attention training plan."""
    plan = []

    exercises_by_difficulty = {
        1: [e for e in EXERCISES.values() if e.difficulty == 1],
        2: [e for e in EXERCISES.values() if e.difficulty == 2],
        3: [e for e in EXERCISES.values() if e.difficulty == 3],
        4: [e for e in EXERCISES.values() if e.difficulty == 4],
        5: [e for e in EXERCISES.values() if e.difficulty == 5],
    }

    for week in range(1, weeks + 1):
        week_plan = {
            "week": week,
            "sessions": []
        }

        # Gradually increase difficulty
        target_difficulty = min(current_level + (week - 1) // 2, 5)
        available = []
        for d in range(1, target_difficulty + 1):
            available.extend(exercises_by_difficulty.get(d, []))

        for session in range(sessions_per_week):
            if available:
                exercise = random.choice(available)
                week_plan["sessions"].append({
                    "day": session + 1,
                    "exercise": exercise.name,
                    "duration": exercise.duration_minutes
                })

        plan.append(week_plan)

    return plan
