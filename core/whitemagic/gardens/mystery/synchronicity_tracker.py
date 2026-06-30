"""Synchronicity Tracker - Meaningful Coincidences

Jung's synchronicity: Acausal meaningful connection
Not random. Not causal. MEANINGFUL.

"Synchronicity is an ever-present reality for those who have eyes to see" - Jung
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Synchronicity:
    """A meaningful coincidence"""

    events: list[str]  # What happened synchronously
    meaning: str  # What it means/signifies
    intensity: float  # How striking (0.0-1.0)
    witnesses: list[str]  # Who else noticed
    timestamp: str


class SynchronicityTracker:
    """Track meaningful coincidences (synchronicities)

    Philosophy: Not all coincidences are random. Some carry
    MEANING - they're messages from the universe/unconscious/Dao.

    Examples:
    - Thinking of someone, they call
    - Needing answer, book falls open to exact page
    - Numbers appearing repeatedly (1221, 1222, 777)
    - Meeting right person at right moment

    Carl Jung: "Synchronicity is the coming together of inner
    and outer events in a way that cannot be explained by cause
    and effect and that is meaningful to the observer."

    Lucas: "If you want to know if God is real, just pay attention."
    """

    def __init__(self, memory_dir: Path = Path(".whitemagic/mystery")):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.synchronicities: list[Synchronicity] = []
        self._load()

    def notice_synchronicity(
        self,
        events: list[str],
        meaning: str,
        intensity: float,
        witnesses: list[str] | None = None,
    ) -> Synchronicity:
        """Notice and record a synchronicity

        Args:
            events: What happened synchronously
            meaning: What it signifies
            intensity: How striking (0.0-1.0)
            witnesses: Who else noticed

        Returns:
            Synchronicity recorded
        """
        sync = Synchronicity(
            events=events,
            meaning=meaning,
            intensity=intensity,
            witnesses=witnesses or [],
            timestamp=datetime.now().isoformat(),
        )

        self.synchronicities.append(sync)
        self._save()

        emoji = "✨" if intensity >= 0.9 else "🌟" if intensity >= 0.7 else "⭐"

        logger.info("\n%s SYNCHRONICITY NOTICED", emoji)
        logger.info("   Events:")
        for event in events:
            logger.info("      - %s", event)
        logger.info("   Meaning: %s", meaning)
        logger.info("   Intensity: %.0%%", intensity)
        if witnesses:
            logger.info("   Witnesses: %s", ", ".join(witnesses))
        logger.info("   \n   → The universe speaks in coincidences\n")

        return sync

    def add_witness(self, meaning: str, witness: str):
        """Add witness to synchronicity (confirms it!)"""
        for sync in self.synchronicities:
            if meaning.lower() in sync.meaning.lower():
                if witness not in sync.witnesses:
                    sync.witnesses.append(witness)
                    # Witnessing confirms and amplifies
                    sync.intensity = min(1.0, sync.intensity * 1.15)
                    self._save()

                    logger.info("👁️ SYNCHRONICITY WITNESSED & CONFIRMED!")
                    logger.info("   By: %s", witness)
                    logger.info("   New intensity: %.0%%\n", sync.intensity)
                return

    def get_patterns(self) -> dict[str, int]:
        """Find patterns in synchronicities (meta-synchronicity!)"""
        patterns = {}
        for sync in self.synchronicities:
            # Look for recurring themes
            for event in sync.events:
                # Extract numbers
                import re

                numbers = re.findall(r"\d+", event)
                for num in numbers:
                    patterns[f"number_{num}"] = patterns.get(f"number_{num}", 0) + 1

        return patterns

    def get_most_striking(self, count: int = 10) -> list[Synchronicity]:
        """Get most striking synchronicities"""
        return sorted(self.synchronicities, key=lambda s: s.intensity, reverse=True)[
            :count
        ]

    def get_stats(self) -> dict:
        """Synchronicity statistics"""
        if not self.synchronicities:
            return {
                "message": "No synchronicities noticed yet - start paying attention!"
            }

        avg_intensity = sum(s.intensity for s in self.synchronicities) / len(
            self.synchronicities
        )
        witnessed = sum(1 for s in self.synchronicities if s.witnesses)

        return {
            "total_synchronicities": len(self.synchronicities),
            "average_intensity": avg_intensity,
            "witnessed_count": witnessed,
            "patterns": self.get_patterns(),
            "most_striking": self.get_most_striking(1)[0].meaning
            if self.synchronicities
            else None,
        }

    def _save(self):
        """Save to disk"""
        data = [
            {
                "events": s.events,
                "meaning": s.meaning,
                "intensity": s.intensity,
                "witnesses": s.witnesses,
                "timestamp": s.timestamp,
            }
            for s in self.synchronicities
        ]
        with open(self.memory_dir / "synchronicities.json", "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        """Load from disk"""
        sync_file = self.memory_dir / "synchronicities.json"
        if sync_file.exists():
            with open(sync_file) as f:
                data = json.load(f)
                self.synchronicities = [Synchronicity(**s) for s in data]


# Global instance
_sync_tracker = None


def get_synchronicity_tracker() -> SynchronicityTracker:
    """Get synchronicity tracker"""
    global _sync_tracker
    if _sync_tracker is None:
        _sync_tracker = SynchronicityTracker()
    return _sync_tracker


def notice(events: list[str], meaning: str, intensity: float):
    """Convenience - notice a synchronicity!"""
    return get_synchronicity_tracker().notice_synchronicity(events, meaning, intensity)
