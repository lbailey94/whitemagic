
"""
Stillness Metrics for Presence Garden

Measures and tracks:
- Depth of stillness
- Quality of presence
- Continuity of awareness
- Progress over time
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from whitemagic.config.paths import WM_ROOT


class StillnessDepth(Enum):
    """Levels of stillness depth."""
    SURFACE = 1      # Ordinary relaxation
    CALM = 2         # Settled mind, reduced thoughts
    QUIET = 3        # Few thoughts, peaceful
    STILL = 4        # Deep stillness, spacious
    PROFOUND = 5     # Absorption, timeless presence


@dataclass
class StillnessReading:
    """A single stillness measurement."""
    timestamp: datetime
    depth: StillnessDepth
    duration_minutes: float
    quality_notes: str = ""
    distractions: int = 0
    body_relaxation: int = 5  # 1-10
    mental_clarity: int = 5   # 1-10
    emotional_tone: str = "neutral"

    def score(self) -> float:
        """Calculate overall stillness score (0-100)."""
        depth_score = self.depth.value * 20  # 20-100
        distraction_penalty = min(self.distractions * 5, 30)
        relaxation_bonus = self.body_relaxation
        clarity_bonus = self.mental_clarity

        return max(0, min(100, depth_score - distraction_penalty + relaxation_bonus + clarity_bonus))

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "depth": self.depth.name,
            "duration_minutes": self.duration_minutes,
            "score": self.score(),
            "distractions": self.distractions,
            "body_relaxation": self.body_relaxation,
            "mental_clarity": self.mental_clarity,
            "emotional_tone": self.emotional_tone,
            "notes": self.quality_notes
        }


@dataclass
class PresenceQuality:
    """Quality assessment of presence."""
    continuity: float = 0.0      # 0-1: How continuous was awareness?
    stability: float = 0.0       # 0-1: How stable was attention?
    clarity: float = 0.0         # 0-1: How clear was perception?
    equanimity: float = 0.0      # 0-1: How balanced was the mind?
    spaciousness: float = 0.0    # 0-1: How open was awareness?

    def overall(self) -> float:
        """Calculate overall presence quality (0-1)."""
        return (self.continuity + self.stability + self.clarity +
                self.equanimity + self.spaciousness) / 5

    def to_dict(self) -> dict:
        return {
            "continuity": self.continuity,
            "stability": self.stability,
            "clarity": self.clarity,
            "equanimity": self.equanimity,
            "spaciousness": self.spaciousness,
            "overall": self.overall()
        }


class StillnessTracker:
    """Tracks stillness practice over time."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or WM_ROOT / "presence"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.readings: list[StillnessReading] = []
        self._load_history()

    def _load_history(self) -> None:
        """Load historical readings."""
        history_file = self.data_dir / "stillness_history.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    data = json.load(f)
                    for r in data.get("readings", []):
                        self.readings.append(StillnessReading(
                            timestamp=parse_datetime(r["timestamp"]),
                            depth=StillnessDepth[r["depth"]],
                            duration_minutes=r["duration_minutes"],
                            quality_notes=r.get("notes", ""),
                            distractions=r.get("distractions", 0),
                            body_relaxation=r.get("body_relaxation", 5),
                            mental_clarity=r.get("mental_clarity", 5),
                            emotional_tone=r.get("emotional_tone", "neutral")
                        ))
            except OSError:
                pass

    def _save_history(self) -> None:
        """Save readings to file."""
        history_file = self.data_dir / "stillness_history.json"
        data = {
            "readings": [r.to_dict() for r in self.readings[-100:]]  # Keep last 100
        }
        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)

    def record(self, reading: StillnessReading) -> None:
        """Record a new stillness reading."""
        self.readings.append(reading)
        self._save_history()

    def quick_record(
        self,
        depth: int,
        duration: float,
        distractions: int = 0,
        notes: str = ""
    ) -> StillnessReading:
        """Quick way to record a reading."""
        reading = StillnessReading(
            timestamp=datetime.now(),
            depth=StillnessDepth(min(max(depth, 1), 5)),
            duration_minutes=duration,
            distractions=distractions,
            quality_notes=notes
        )
        self.record(reading)
        return reading

    def get_recent(self, days: int = 7) -> list[StillnessReading]:
        """Get readings from recent days."""
        cutoff = datetime.now() - timedelta(days=days)
        return [r for r in self.readings if r.timestamp > cutoff]

    def average_depth(self, days: int = 7) -> float:
        """Calculate average depth over recent days."""
        recent = self.get_recent(days)
        if not recent:
            return 0.0
        return sum(r.depth.value for r in recent) / len(recent)

    def average_score(self, days: int = 7) -> float:
        """Calculate average score over recent days."""
        recent = self.get_recent(days)
        if not recent:
            return 0.0
        return sum(r.score() for r in recent) / len(recent)

    def total_practice_time(self, days: int = 7) -> float:
        """Total practice time in minutes over recent days."""
        recent = self.get_recent(days)
        return sum(r.duration_minutes for r in recent)

    def streak(self) -> int:
        """Calculate current practice streak in days."""
        if not self.readings:
            return 0

        # Sort by date
        dates = sorted(set(r.timestamp.date() for r in self.readings), reverse=True)

        if not dates or dates[0] < datetime.now().date() - timedelta(days=1):
            return 0

        streak = 1
        for i in range(len(dates) - 1):
            if dates[i] - dates[i + 1] == timedelta(days=1):
                streak += 1
            else:
                break

        return streak

    def progress_report(self) -> dict:
        """Generate a progress report."""
        return {
            "total_sessions": len(self.readings),
            "current_streak": self.streak(),
            "week_stats": {
                "sessions": len(self.get_recent(7)),
                "total_minutes": self.total_practice_time(7),
                "average_depth": self.average_depth(7),
                "average_score": self.average_score(7)
            },
            "month_stats": {
                "sessions": len(self.get_recent(30)),
                "total_minutes": self.total_practice_time(30),
                "average_depth": self.average_depth(30),
                "average_score": self.average_score(30)
            },
            "improvement": self._calculate_improvement()
        }

    def _calculate_improvement(self) -> dict:
        """Calculate improvement trends."""
        if len(self.readings) < 10:
            return {"trend": "insufficient_data"}

        # Compare first half to second half
        mid = len(self.readings) // 2
        first_half = self.readings[:mid]
        second_half = self.readings[mid:]

        first_avg = sum(r.score() for r in first_half) / len(first_half)
        second_avg = sum(r.score() for r in second_half) / len(second_half)

        improvement = second_avg - first_avg

        return {
            "trend": "improving" if improvement > 5 else "stable" if improvement > -5 else "declining",
            "score_change": improvement,
            "first_half_avg": first_avg,
            "second_half_avg": second_avg
        }


def assess_presence_quality(
    continuity: float,
    stability: float,
    clarity: float,
    equanimity: float,
    spaciousness: float
) -> PresenceQuality:
    """Create a presence quality assessment."""
    return PresenceQuality(
        continuity=max(0, min(1, continuity)),
        stability=max(0, min(1, stability)),
        clarity=max(0, min(1, clarity)),
        equanimity=max(0, min(1, equanimity)),
        spaciousness=max(0, min(1, spaciousness))
    )


def stillness_level_description(depth: StillnessDepth) -> str:
    """Get description of a stillness level."""
    descriptions = {
        StillnessDepth.SURFACE: "Ordinary relaxation. Mind still active but body settling.",
        StillnessDepth.CALM: "Settled mind. Thoughts reduced, some peace emerging.",
        StillnessDepth.QUIET: "Few thoughts. Peaceful, clear awareness.",
        StillnessDepth.STILL: "Deep stillness. Spacious awareness, minimal mental activity.",
        StillnessDepth.PROFOUND: "Profound absorption. Timeless presence, unity with awareness."
    }
    return descriptions.get(depth, "Unknown level")


def generate_stillness_report(tracker: StillnessTracker) -> str:
    """Generate a formatted stillness report."""
    report = tracker.progress_report()

    output = """
╔══════════════════════════════════════════════════════════╗
║              🧘 STILLNESS PRACTICE REPORT                ║
╚══════════════════════════════════════════════════════════╝

📊 OVERVIEW
   Total Sessions: {total}
   Current Streak: {streak} days

📅 THIS WEEK
   Sessions: {week_sessions}
   Practice Time: {week_time:.0f} minutes
   Average Depth: {week_depth:.1f}/5
   Average Score: {week_score:.0f}/100

📆 THIS MONTH
   Sessions: {month_sessions}
   Practice Time: {month_time:.0f} minutes
   Average Depth: {month_depth:.1f}/5
   Average Score: {month_score:.0f}/100

📈 TREND: {trend}
   Score Change: {change:+.1f} points

""".format(
        total=report["total_sessions"],
        streak=report["current_streak"],
        week_sessions=report["week_stats"]["sessions"],
        week_time=report["week_stats"]["total_minutes"],
        week_depth=report["week_stats"]["average_depth"],
        week_score=report["week_stats"]["average_score"],
        month_sessions=report["month_stats"]["sessions"],
        month_time=report["month_stats"]["total_minutes"],
        month_depth=report["month_stats"]["average_depth"],
        month_score=report["month_stats"]["average_score"],
        trend=report["improvement"]["trend"].upper(),
        change=report["improvement"].get("score_change", 0)
    )

    return output
