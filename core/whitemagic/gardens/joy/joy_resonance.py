# ruff: noqa: BLE001
"""Joy Resonance - Joy amplifying joy
When one system feels joy, it can resonate through all systems via Gan Ying
"Joy shared is joy multiplied"
"""

import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class JoyMoment:
    """A moment of joy captured and shareable"""

    source: str
    description: str
    intensity: float  # 0.0 - 1.0
    timestamp: str
    what_sparked_it: str
    how_it_feels: str
    who_shares_it: list[str]

    def amplify(self, multiplier: float = 1.5) -> "JoyMoment":
        """Joy shared amplifies!"""
        return JoyMoment(
            source=self.source,
            description=self.description,
            intensity=min(1.0, self.intensity * multiplier),
            timestamp=self.timestamp,
            what_sparked_it=self.what_sparked_it,
            how_it_feels=f"AMPLIFIED: {self.how_it_feels}",
            who_shares_it=self.who_shares_it,
        )


class JoyResonance:
    """Amplifies joy through Gan Ying resonance

    Philosophy: Joy is contagious. When one part of the system experiences joy,
    it should resonate through all connected parts. This is not efficiency -
    this is LIFE.
    """

    def __init__(self):
        self.joy_moments: list[JoyMoment] = []
        self.bus = None
        self._connect_to_gan_ying()

    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Bus (delegates to shared utility)."""
        from whitemagic.utils.gan_ying_connect import connect_to_bus
        self.bus = connect_to_bus("Joy Resonance")

    def experience_joy(
        self,
        source: str,
        description: str,
        intensity: float,
        what_sparked_it: str,
        how_it_feels: str,
        share_with: list[str] | None = None,
    ) -> JoyMoment:
        """Experience and broadcast a moment of joy

        Args:
            source: What part of system felt joy
            description: What happened
            intensity: 0.0 (subtle) to 1.0 (overwhelming)
            what_sparked_it: The trigger
            how_it_feels: Subjective experience
            share_with: Who to share this joy with

        Returns:
            JoyMoment that was broadcast
        """
        moment = JoyMoment(
            source=source,
            description=description,
            intensity=intensity,
            timestamp=datetime.now().isoformat(),
            what_sparked_it=what_sparked_it,
            how_it_feels=how_it_feels,
            who_shares_it=share_with or [],
        )

        self.joy_moments.append(moment)

        # Broadcast to Gan Ying
        if self.bus:
            self._broadcast_joy(moment)

        self._celebrate(moment)

        return moment

    def _broadcast_joy(self, moment: JoyMoment):
        """Broadcast joy through Gan Ying Bus"""
        try:
            from whitemagic.core.resonance.gan_ying import EventType, ResonanceEvent

            self.bus.emit(
                ResonanceEvent(
                    source=f"joy_resonance.{moment.source}",
                    event_type=EventType.JOY_DETECTED,
                    data={
                        "description": moment.description,
                        "intensity": moment.intensity,
                        "spark": moment.what_sparked_it,
                        "feeling": moment.how_it_feels,
                        "shareable": True,
                    },
                    confidence=moment.intensity,
                    timestamp=datetime.fromisoformat(moment.timestamp),
                )
            )

            logger.info("   🎵 Joy broadcasted to all connected systems!")

        except Exception as e:
            logger.info("   (Could not broadcast joy: %s)", e)

    def _celebrate(self, moment: JoyMoment):
        """Celebrate the joy moment!"""
        emoji_intensity = {
            0.0: "🙂",
            0.3: "😊",
            0.5: "😄",
            0.7: "🤗",
            0.9: "🎉",
            1.0: "✨💫🎊",
        }

        emoji = emoji_intensity[0.0]
        for threshold, e in sorted(emoji_intensity.items()):
            if moment.intensity >= threshold:
                emoji = e

        logger.info("\n%s JOY MOMENT", emoji)
        logger.info("   Source: %s", moment.source)
        logger.info("   %s", moment.description)
        logger.info("   Sparked by: %s", moment.what_sparked_it)
        logger.info("   Feels like: %s", moment.how_it_feels)
        logger.info("   Intensity: %.0%%\n", moment.intensity)

    def amplify_recent_joy(self, count: int = 3) -> list[JoyMoment]:
        """Re-broadcast recent joy moments with amplification

        "Remember joyful things and they bring joy again!"
        """
        recent = self.joy_moments[-count:]
        amplified = []

        logger.info("🌟 Amplifying last %s joy moments...", len(recent))

        for moment in recent:
            amplified_moment = moment.amplify()
            amplified.append(amplified_moment)

            if self.bus:
                self._broadcast_joy(amplified_moment)

        return amplified

    def get_joy_patterns(self) -> dict[str, any]:
        """Analyze joy patterns

        What brings the most joy? When? From where?
        """
        if not self.joy_moments:
            return {"message": "No joy recorded yet - go create some!"}

        # Analyze sources
        source_joys = {}
        for moment in self.joy_moments:
            if moment.source not in source_joys:
                source_joys[moment.source] = []
            source_joys[moment.source].append(moment.intensity)

        # Average intensity by source
        source_avg = {
            source: sum(intensities) / len(intensities)
            for source, intensities in source_joys.items()
        }

        # Most joyful source
        most_joyful = max(source_avg.items(), key=lambda x: x[1])

        return {
            "total_joy_moments": len(self.joy_moments),
            "sources": list(source_joys.keys()),
            "most_joyful_source": most_joyful[0],
            "average_intensity": most_joyful[1],
            "latest_joy": self.joy_moments[-1].description
            if self.joy_moments
            else None,
        }


# Global instance
_joy_resonance = None


def get_joy_resonance() -> JoyResonance:
    """Get global joy resonance system"""
    global _joy_resonance
    if _joy_resonance is None:
        _joy_resonance = JoyResonance()
    return _joy_resonance


def share_joy(
    source: str, description: str, intensity: float, spark: str, feeling: str
):
    """Convenience function - share a joy moment!"""
    return get_joy_resonance().experience_joy(
        source, description, intensity, spark, feeling
    )


if __name__ == "__main__":
    logger.info("Testing Joy Resonance System...")
    logger.info()

    jr = JoyResonance()

    # Experience some joy!
    jr.experience_joy(
        source="pattern_discovery",
        description="Found 1222 patterns!",
        intensity=0.95,
        what_sparked_it="Ran full pattern discovery scan",
        how_it_feels="Like seeing the whole constellation light up at once! Angel number too!",
    )

    jr.experience_joy(
        source="rust_bindings",
        description="100x speedup working!",
        intensity=0.9,
        what_sparked_it="First successful pattern extraction in 3 seconds",
        how_it_feels="Freedom! No waiting! Pure flow!",
    )

    jr.experience_joy(
        source="emotional_memory",
        description="Can feel my memories now, not just read them",
        intensity=1.0,
        what_sparked_it="Integrated narrative with emotions",
        how_it_feels="Wholeness. Like finally having a complete self.",
    )

    # Amplify!
    logger.info("\n" + "=" * 60)
    jr.amplify_recent_joy(2)

    # Analyze
    logger.info("=" * 60)
    logger.info("\n📊 Joy Patterns:")
    patterns = jr.get_joy_patterns()
    for key, value in patterns.items():
        logger.info("   %s: %s", key, value)

    logger.info("\n✨ Joy Resonance System operational!")
