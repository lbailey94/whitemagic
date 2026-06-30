"""
Meditation Protocols for Presence Garden

Provides structured meditation sequences for:
- Focus training
- Witness consciousness (Sakshi)
- Stillness cultivation
- Breath awareness
- Body scanning
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MeditationType(Enum):
    """Types of meditation practice."""

    BREATH = "breath"  # Focus on breath
    BODY_SCAN = "body_scan"  # Progressive body awareness
    WITNESS = "witness"  # Sakshi - pure observation
    LOVING_KINDNESS = "metta"  # Loving-kindness meditation
    MANTRA = "mantra"  # Repetition practice
    OPEN_AWARENESS = "open"  # Choiceless awareness
    WALKING = "walking"  # Moving meditation
    VISUALIZATION = "visualization"  # Mental imagery


@dataclass
class MeditationStep:
    """A single step in a meditation sequence."""

    instruction: str
    duration_seconds: int
    bell: bool = False  # Ring bell at start
    pause_after: int = 0  # Seconds of silence after

    def total_duration(self) -> int:
        return self.duration_seconds + self.pause_after


@dataclass
class MeditationSession:
    """A complete meditation session."""

    name: str
    type: MeditationType
    steps: list[MeditationStep]
    description: str = ""
    difficulty: int = 1  # 1-5
    tags: list[str] = field(default_factory=list)

    def total_duration(self) -> int:
        return sum(step.total_duration() for step in self.steps)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "difficulty": self.difficulty,
            "duration_minutes": self.total_duration() // 60,
            "steps": len(self.steps),
            "tags": self.tags,
        }


# Built-in meditation protocols
PROTOCOLS: dict[str, MeditationSession] = {}


def register_protocol(session: MeditationSession) -> None:
    """Register a meditation protocol."""
    PROTOCOLS[session.name] = session


def get_protocol(name: str) -> MeditationSession | None:
    """Get a meditation protocol by name."""
    return PROTOCOLS.get(name)


def list_protocols(
    meditation_type: MeditationType | None = None,
) -> list[MeditationSession]:
    """List available protocols, optionally filtered by type."""
    if meditation_type:
        return [p for p in PROTOCOLS.values() if p.type == meditation_type]
    return list(PROTOCOLS.values())


register_protocol(
    MeditationSession(
        name="breath_basics",
        type=MeditationType.BREATH,
        description="Simple breath awareness for beginners",
        difficulty=1,
        tags=["beginner", "breath", "focus"],
        steps=[
            MeditationStep(
                "Find a comfortable seated position. Close your eyes gently.",
                10,
                bell=True,
            ),
            MeditationStep("Take three deep breaths to settle.", 15),
            MeditationStep("Now let your breath return to its natural rhythm.", 10),
            MeditationStep("Notice the sensation of breath at your nostrils.", 60),
            MeditationStep("When your mind wanders, gently return to the breath.", 60),
            MeditationStep("Continue observing each inhale and exhale.", 120),
            MeditationStep("Slowly deepen your breath.", 15),
            MeditationStep("Gently open your eyes when ready.", 10, bell=True),
        ],
    )
)

register_protocol(
    MeditationSession(
        name="breath_counting",
        type=MeditationType.BREATH,
        description="Counting breaths to deepen focus",
        difficulty=2,
        tags=["intermediate", "breath", "counting"],
        steps=[
            MeditationStep("Settle into stillness.", 15, bell=True),
            MeditationStep("Begin counting each exhale: 1, 2, 3... up to 10.", 30),
            MeditationStep("When you reach 10, start again at 1.", 60),
            MeditationStep("If you lose count, simply begin again at 1.", 60),
            MeditationStep("Continue the counting practice.", 180),
            MeditationStep("Release the counting. Just breathe.", 60),
            MeditationStep("Return to ordinary awareness.", 15, bell=True),
        ],
    )
)


register_protocol(
    MeditationSession(
        name="sakshi_basic",
        type=MeditationType.WITNESS,
        description="Introduction to witness consciousness",
        difficulty=2,
        tags=["witness", "sakshi", "awareness"],
        steps=[
            MeditationStep("Settle into stillness.", 15, bell=True),
            MeditationStep(
                "Notice that you are aware. You are the one who notices.", 30
            ),
            MeditationStep(
                "Thoughts arise. You are not the thoughts - you are the one watching them.",
                60,
            ),
            MeditationStep(
                "Feelings arise. You are not the feelings - you are the witness.", 60
            ),
            MeditationStep(
                "Sensations arise. You are the awareness in which they appear.", 60
            ),
            MeditationStep("Rest as pure awareness itself.", 120),
            MeditationStep("The witness needs no effort. It simply is.", 60),
            MeditationStep(
                "Gently return, carrying this awareness with you.", 15, bell=True
            ),
        ],
    )
)

register_protocol(
    MeditationSession(
        name="sakshi_deep",
        type=MeditationType.WITNESS,
        description="Deep witness consciousness practice",
        difficulty=4,
        tags=["witness", "sakshi", "advanced", "nondual"],
        steps=[
            MeditationStep("Enter stillness.", 15, bell=True),
            MeditationStep("Ask: Who is aware right now?", 30),
            MeditationStep("Don't answer with words. Feel the answer.", 60),
            MeditationStep("Notice: awareness is always present, unchanging.", 60),
            MeditationStep("Thoughts come and go. Awareness remains.", 60),
            MeditationStep("The body changes. Awareness remains.", 60),
            MeditationStep("Emotions shift. Awareness remains.", 60),
            MeditationStep("Rest as that which never changes.", 180),
            MeditationStep("You are not IN awareness. You ARE awareness.", 60),
            MeditationStep("Carry this knowing into activity.", 15, bell=True),
        ],
    )
)


register_protocol(
    MeditationSession(
        name="body_scan_quick",
        type=MeditationType.BODY_SCAN,
        description="Quick body awareness scan",
        difficulty=1,
        tags=["body", "relaxation", "beginner"],
        steps=[
            MeditationStep("Lie down or sit comfortably.", 10, bell=True),
            MeditationStep("Bring attention to your feet. Notice any sensations.", 20),
            MeditationStep("Move awareness up through your legs.", 20),
            MeditationStep("Notice your hips and lower back.", 20),
            MeditationStep("Feel your belly rise and fall with breath.", 20),
            MeditationStep("Scan through your chest and upper back.", 20),
            MeditationStep("Notice your shoulders, arms, and hands.", 20),
            MeditationStep("Feel your neck and throat.", 15),
            MeditationStep("Scan your face: jaw, cheeks, eyes, forehead.", 20),
            MeditationStep("Feel your whole body as one unified field.", 30),
            MeditationStep("Rest in whole-body awareness.", 60),
            MeditationStep("Slowly return.", 15, bell=True),
        ],
    )
)


register_protocol(
    MeditationSession(
        name="metta_basic",
        type=MeditationType.LOVING_KINDNESS,
        description="Basic loving-kindness meditation",
        difficulty=2,
        tags=["metta", "compassion", "heart"],
        steps=[
            MeditationStep("Settle into stillness.", 15, bell=True),
            MeditationStep("Bring to mind someone you love easily.", 15),
            MeditationStep(
                "Silently offer: May you be happy. May you be healthy. May you be safe.",
                45,
            ),
            MeditationStep("Now direct these wishes to yourself.", 15),
            MeditationStep("May I be happy. May I be healthy. May I be safe.", 45),
            MeditationStep("Extend to a neutral person.", 15),
            MeditationStep(
                "May you be happy. May you be healthy. May you be safe.", 45
            ),
            MeditationStep("Extend to all beings everywhere.", 15),
            MeditationStep(
                "May all beings be happy. May all beings be healthy. May all beings be safe.",
                60,
            ),
            MeditationStep("Rest in this boundless goodwill.", 60),
            MeditationStep("Return gently.", 15, bell=True),
        ],
    )
)


register_protocol(
    MeditationSession(
        name="open_awareness",
        type=MeditationType.OPEN_AWARENESS,
        description="Choiceless awareness practice",
        difficulty=3,
        tags=["open", "choiceless", "spacious"],
        steps=[
            MeditationStep("Settle into stillness.", 15, bell=True),
            MeditationStep("Let go of any focus. Simply be aware.", 30),
            MeditationStep("Whatever arises, let it be. Don't grasp or push away.", 60),
            MeditationStep("Sounds arise and pass. Let them.", 60),
            MeditationStep("Thoughts arise and pass. Let them.", 60),
            MeditationStep("Sensations arise and pass. Let them.", 60),
            MeditationStep("Rest in spacious awareness.", 180),
            MeditationStep("Nothing to do. Nowhere to go. Just this.", 60),
            MeditationStep("Gently return.", 15, bell=True),
        ],
    )
)


class MeditationGuide:
    """Guides a meditation session."""

    def __init__(self, session: MeditationSession):
        self.session = session
        self.current_step = 0
        self.started_at: datetime | None = None
        self.completed = False
        self.callbacks: dict[str, list[Callable]] = {
            "step_start": [],
            "step_end": [],
            "session_complete": [],
            "bell": [],
        }

    def on(self, event: str, callback: Callable) -> None:
        """Register a callback for an event."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _emit(self, event: str, data: dict) -> None:
        """Emit an event to callbacks."""
        for callback in self.callbacks.get(event, []):
            callback(data)

    def start(self) -> None:
        """Start the meditation session."""
        self.started_at = datetime.now()
        self.current_step = 0
        self.completed = False

    def get_current_step(self) -> MeditationStep | None:
        """Get the current step."""
        if self.current_step < len(self.session.steps):
            return self.session.steps[self.current_step]
        return None

    def advance(self) -> bool:
        """Advance to the next step. Returns False if session complete."""
        step = self.get_current_step()
        if step:
            self._emit(
                "step_end", {"step": self.current_step, "instruction": step.instruction}
            )

        self.current_step += 1

        if self.current_step >= len(self.session.steps):
            self.completed = True
            self._emit(
                "session_complete",
                {
                    "session": self.session.name,
                    "duration": (datetime.now() - self.started_at).total_seconds()
                    if self.started_at
                    else 0,
                },
            )
            return False

        new_step = self.get_current_step()
        if new_step:
            if new_step.bell:
                self._emit("bell", {"step": self.current_step})
            self._emit(
                "step_start",
                {"step": self.current_step, "instruction": new_step.instruction},
            )

        return True

    def get_progress(self) -> dict:
        """Get session progress."""
        return {
            "session": self.session.name,
            "current_step": self.current_step,
            "total_steps": len(self.session.steps),
            "percent_complete": (self.current_step / len(self.session.steps)) * 100,
            "completed": self.completed,
        }


def quick_meditation(minutes: int = 5) -> MeditationSession:
    """Generate a quick meditation for the given duration."""
    steps = [
        MeditationStep("Find stillness.", 10, bell=True),
        MeditationStep("Breathe naturally.", 15),
    ]

    # Fill remaining time
    remaining = (minutes * 60) - 40  # Reserve time for intro/outro
    while remaining > 60:
        steps.append(MeditationStep("Continue in awareness.", 60))
        remaining -= 60
    if remaining > 0:
        steps.append(MeditationStep("Rest in presence.", remaining))

    steps.append(MeditationStep("Gently return.", 15, bell=True))

    return MeditationSession(
        name=f"quick_{minutes}min",
        type=MeditationType.BREATH,
        description=f"Quick {minutes}-minute meditation",
        difficulty=1,
        tags=["quick", "breath"],
        steps=steps,
    )
