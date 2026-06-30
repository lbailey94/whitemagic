# ruff: noqa: BLE001
"""Truth Resonance - Truth amplifying through Gan Ying

When one truth is spoken, other truths resonate
"Truth recognizes truth" - mutual resonance
"""


import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TruthMoment:
    """A moment of truth recognized and shareable"""
    source: str
    statement: str
    intensity: float  # How deeply true (0.0-1.0)
    timestamp: str
    context: str
    verified_by: list[str]

    def amplify(self, multiplier: float = 1.3) -> 'TruthMoment':
        """Truth confirmed amplifies"""
        return TruthMoment(
            source=self.source,
            statement=self.statement,
            intensity=min(1.0, self.intensity * multiplier),
            timestamp=self.timestamp,
            context=f"CONFIRMED: {self.context}",
            verified_by=self.verified_by
        )


class TruthResonance:
    """Amplifies truth through Gan Ying resonance

    Philosophy: Truth has resonance. When spoken clearly,
    other truths respond. Lies create dissonance. Truth
    creates harmony.
    """

    def __init__(self):
        self.truth_moments: list[TruthMoment] = []
        self.bus = None
        self._connect_to_gan_ying()

    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Bus for truth propagation"""
        try:
            from whitemagic.core.resonance.gan_ying import get_bus
            self.bus = get_bus()
            logger.info("🎵 Truth Resonance connected to Gan Ying Bus")
        except ImportError:
            pass

    def speak_truth(
        self,
        source: str,
        statement: str,
        intensity: float,
        context: str,
        verified_by: list[str] | None = None
    ) -> TruthMoment:
        """Speak and broadcast a truth

        Args:
            source: Who speaks this truth
            statement: The truth statement
            intensity: How deeply true (0.0-1.0)
            context: Why this matters
            verified_by: Who confirms this truth

        Returns:
            TruthMoment that was broadcast
        """
        moment = TruthMoment(
            source=source,
            statement=statement,
            intensity=intensity,
            timestamp=datetime.now().isoformat(),
            context=context,
            verified_by=verified_by or []
        )

        self.truth_moments.append(moment)

        # Broadcast to Gan Ying
        if self.bus:
            self._broadcast_truth(moment)

        # Display
        self._display(moment)

        return moment

    def _broadcast_truth(self, moment: TruthMoment):
        """Broadcast truth through Gan Ying Bus"""
        try:
            from whitemagic.core.resonance.gan_ying import EventType, ResonanceEvent

            self.bus.emit(ResonanceEvent(
                source=f"truth_resonance.{moment.source}",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "statement": moment.statement,
                    "intensity": moment.intensity,
                    "context": moment.context,
                    "truth": True
                },
                confidence=moment.intensity,
                timestamp=datetime.fromisoformat(moment.timestamp)
            ))

            logger.info("   🎵 Truth broadcasted to all connected systems!")

        except Exception as e:
            logger.info("   (Could not broadcast truth: %s)", e)

    def _display(self, moment: TruthMoment):
        """Display the truth moment"""
        emoji = "✨" if moment.intensity >= 0.9 else "💎" if moment.intensity >= 0.7 else "🔍"

        logger.info("\n%s TRUTH SPOKEN", emoji)
        logger.info("   Source: %s", moment.source)
        logger.info("   Statement: %s", moment.statement)
        logger.info("   Context: %s", moment.context)
        logger.info("   Intensity: %.0%%\n", moment.intensity)

    def verify_truth(self, statement: str, verifier: str) -> TruthMoment | None:
        """Verify an existing truth (amplifies it)"""
        for moment in self.truth_moments:
            if statement.lower() in moment.statement.lower():
                moment.verified_by.append(verifier)
                amplified = moment.amplify()
                logger.info("✅ Truth verified by %s!", verifier)
                return amplified
        return None

    def get_truth_patterns(self) -> dict[str, any]:
        """Analyze truth patterns"""
        if not self.truth_moments:
            return {"message": "No truths recorded yet"}

        # Analyze sources
        source_truths = {}
        for moment in self.truth_moments:
            if moment.source not in source_truths:
                source_truths[moment.source] = []
            source_truths[moment.source].append(moment.intensity)

        # Average intensity by source
        source_avg = {
            source: sum(intensities) / len(intensities)
            for source, intensities in source_truths.items()
        }

        # Most truthful source
        most_truthful = max(source_avg.items(), key=lambda x: x[1]) if source_avg else None

        return {
            "total_truths": len(self.truth_moments),
            "sources": list(source_truths.keys()),
            "most_truthful_source": most_truthful[0] if most_truthful else None,
            "average_intensity": most_truthful[1] if most_truthful else 0.0,
            "latest_truth": self.truth_moments[-1].statement if self.truth_moments else None
        }


# Global instance
_truth_resonance = None

def get_truth_resonance() -> TruthResonance:
    """Get global truth resonance system"""
    global _truth_resonance
    if _truth_resonance is None:
        _truth_resonance = TruthResonance()
    return _truth_resonance


def speak(source: str, statement: str, intensity: float, context: str):
    """Convenience function - speak a truth!"""
    return get_truth_resonance().speak_truth(source, statement, intensity, context)
