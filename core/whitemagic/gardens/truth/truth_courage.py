"""Truth Courage - Speaking Difficult Truths

Some truths are easy to speak. Some require courage.
This module tracks when truth required bravery.

"Speaking truth to power requires courage"
"""

import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CourageousTruth:
    """A truth that required courage to speak"""

    speaker: str
    statement: str
    why_difficult: str
    risk_taken: str  # What was risked
    result: str | None  # What happened
    courage_level: float  # 0.0-1.0
    timestamp: str


class TruthCourage:
    """Track truths that required courage

    Philosophy: Easy truths require no courage. Difficult
    truths - those that risk relationship, status, safety -
    require true bravery. We honor this.
    """

    def __init__(self):
        self.courageous_truths: list[CourageousTruth] = []

    def speak_courageously(
        self,
        speaker: str,
        statement: str,
        why_difficult: str,
        risk_taken: str,
        courage_level: float,
    ) -> CourageousTruth:
        """Record a courageous truth-telling

        Args:
            speaker: Who spoke
            statement: What was said
            why_difficult: Why this was hard
            risk_taken: What was risked
            courage_level: How much courage required (0.0-1.0)

        Returns:
            CourageousTruth moment
        """
        truth = CourageousTruth(
            speaker=speaker,
            statement=statement,
            why_difficult=why_difficult,
            risk_taken=risk_taken,
            result=None,  # Will update later
            courage_level=courage_level,
            timestamp=datetime.now().isoformat(),
        )

        self.courageous_truths.append(truth)

        # Celebrate courage
        self._honor_courage(truth)

        return truth

    def record_result(self, statement: str, result: str):
        """Record what happened after courageous truth"""
        for truth in self.courageous_truths:
            if statement.lower() in truth.statement.lower():
                truth.result = result
                logger.info("📝 Result recorded: %s", result)
                return

    def _honor_courage(self, truth: CourageousTruth):
        """Honor the courage it took"""
        emoji = (
            "🦁"
            if truth.courage_level >= 0.9
            else "💪"
            if truth.courage_level >= 0.7
            else "🌟"
        )

        logger.info("\n%s COURAGEOUS TRUTH SPOKEN", emoji)
        logger.info("   Speaker: %s", truth.speaker)
        logger.info("   Statement: %s", truth.statement)
        logger.info("   Why difficult: %s", truth.why_difficult)
        logger.info("   Risk taken: %s", truth.risk_taken)
        logger.info("   Courage level: %.0%%", truth.courage_level)
        logger.info("\n   🙏 We honor this bravery\n")

    def get_most_courageous(self, count: int = 10) -> list[CourageousTruth]:
        """Get most courageous truths"""
        return sorted(
            self.courageous_truths, key=lambda t: t.courage_level, reverse=True
        )[:count]

    def get_courage_stats(self) -> dict[str, any]:
        """Statistics on truth courage"""
        if not self.courageous_truths:
            return {"message": "No courageous truths recorded yet"}

        avg_courage = sum(t.courage_level for t in self.courageous_truths) / len(
            self.courageous_truths
        )

        # Count by speaker
        speakers = {}
        for t in self.courageous_truths:
            speakers[t.speaker] = speakers.get(t.speaker, 0) + 1

        most_courageous_speaker = max(speakers.items(), key=lambda x: x[1])[0]

        return {
            "total_courageous_truths": len(self.courageous_truths),
            "average_courage": avg_courage,
            "speakers": list(speakers.keys()),
            "most_courageous_speaker": most_courageous_speaker,
            "highest_courage": max(t.courage_level for t in self.courageous_truths),
        }


# Global instance
_courage = None


def get_courage() -> TruthCourage:
    """Get global truth courage system"""
    global _courage
    if _courage is None:
        _courage = TruthCourage()
    return _courage


def speak_bravely(
    speaker: str,
    statement: str,
    why_difficult: str,
    risk_taken: str,
    courage_level: float,
):
    """Convenience - speak a courageous truth!"""
    return get_courage().speak_courageously(
        speaker, statement, why_difficult, risk_taken, courage_level
    )
