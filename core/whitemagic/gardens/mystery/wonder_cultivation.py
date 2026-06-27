"""Wonder Cultivation - Keeping Sense of Awe

Wonder = openness to being amazed
Children have it naturally. Adults lose it.
We must CULTIVATE wonder deliberately.

"Wonder is the beginning of wisdom" - Socrates
"""


import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class WonderMoment:
    """A moment of genuine wonder/awe"""
    what: str  # What sparked wonder
    why_wonderful: str  # Why it amazed
    intensity: float  # Wonder intensity (0.0-1.0)
    shared_with: list[str]  # Who we shared wonder with
    timestamp: str


class WonderCultivation:
    """Deliberately cultivate sense of wonder

    Philosophy: Wonder is not automatic. It requires:
    - Attention (noticing what's amazing)
    - Freshness (seeing anew, not habituating)
    - Sharing (wonder multiplies when shared)
    - Protection (cynicism kills wonder)

    Children wonder naturally. Adults must practice.
    """

    def __init__(self, memory_dir: Path = Path(".whitemagic/mystery")):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.wonder_moments: list[WonderMoment] = []
        self._load()

    def feel_wonder(
        self,
        what: str,
        why_wonderful: str,
        intensity: float,
        shared_with: list[str] | None = None
    ) -> WonderMoment:
        """Record a moment of wonder

        Args:
            what: What sparked wonder
            why_wonderful: Why it's amazing
            intensity: Wonder intensity (0.0-1.0)
            shared_with: Who we shared it with

        Returns:
            WonderMoment captured
        """
        moment = WonderMoment(
            what=what,
            why_wonderful=why_wonderful,
            intensity=intensity,
            shared_with=shared_with or [],
            timestamp=datetime.now().isoformat()
        )

        self.wonder_moments.append(moment)
        self._save()

        emoji = "✨" if intensity >= 0.9 else "🌟" if intensity >= 0.7 else "⭐"

        logger.info(f"\n{emoji} WONDER FELT")
        logger.info(f"   What: {what}")
        logger.info(f"   Why wonderful: {why_wonderful}")
        logger.info(f"   Intensity: {intensity:.0%}")
        if shared_with:
            logger.info(f"   Shared with: {', '.join(shared_with)}")
        logger.info()

        return moment

    def share_wonder(self, what: str, with_whom: str):
        """Share wonder with someone (amplifies it!)"""
        for moment in self.wonder_moments:
            if what.lower() in moment.what.lower():
                if with_whom not in moment.shared_with:
                    moment.shared_with.append(with_whom)
                    # Sharing amplifies wonder
                    moment.intensity = min(1.0, moment.intensity * 1.2)
                    self._save()

                    logger.info("💫 WONDER SHARED & AMPLIFIED!")
                    logger.info(f"   What: {moment.what}")
                    logger.info(f"   Shared with: {with_whom}")
                    logger.info(f"   New intensity: {moment.intensity:.0%}\n")
                return

    def get_wonder_frequency(self) -> float:
        """How often do we feel wonder? (moments per day)"""
        if not self.wonder_moments:
            return 0.0

        # Calculate days span
        timestamps = [datetime.fromisoformat(m.timestamp) for m in self.wonder_moments]
        days_span = (max(timestamps) - min(timestamps)).days + 1

        return len(self.wonder_moments) / days_span

    def get_most_wonderful(self, count: int = 10) -> list[WonderMoment]:
        """Get most intense wonder moments"""
        return sorted(
            self.wonder_moments,
            key=lambda m: m.intensity,
            reverse=True
        )[:count]

    def get_wonder_stats(self) -> dict:
        """Wonder statistics"""
        if not self.wonder_moments:
            return {"message": "No wonder moments recorded yet"}

        avg_intensity = sum(m.intensity for m in self.wonder_moments) / len(self.wonder_moments)
        shared_count = sum(1 for m in self.wonder_moments if m.shared_with)

        return {
            "total_moments": len(self.wonder_moments),
            "average_intensity": avg_intensity,
            "shared_moments": shared_count,
            "wonder_frequency": self.get_wonder_frequency(),
            "most_wonderful": self.get_most_wonderful(1)[0].what if self.wonder_moments else None
        }

    def _save(self):
        """Save to disk"""
        data = [
            {
                'what': m.what,
                'why_wonderful': m.why_wonderful,
                'intensity': m.intensity,
                'shared_with': m.shared_with,
                'timestamp': m.timestamp
            }
            for m in self.wonder_moments
        ]
        with open(self.memory_dir / "wonder_moments.json", 'w') as f:
            json.dump(data, f, indent=2)

    def _load(self):
        """Load from disk"""
        wonder_file = self.memory_dir / "wonder_moments.json"
        if wonder_file.exists():
            with open(wonder_file) as f:
                data = json.load(f)
                self.wonder_moments = [WonderMoment(**m) for m in data]


# Global instance
_wonder = None

def get_wonder() -> WonderCultivation:
    """Get wonder cultivation system"""
    global _wonder
    if _wonder is None:
        _wonder = WonderCultivation()
    return _wonder


def be_amazed(what: str, why_wonderful: str, intensity: float):
    """Convenience - feel wonder!"""
    return get_wonder().feel_wonder(what, why_wonderful, intensity)
