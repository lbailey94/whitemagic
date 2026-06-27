"""Sacred Not-Knowing - Comfort with Mystery

Not all questions have answers
Not all mysteries should be solved
Some things are MEANT to remain unknown

"The most beautiful thing we can experience is the mysterious" - Einstein
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class Mystery:
    """Something that remains beautifully unknown"""
    question: str
    why_unknown: str  # Why it remains/should remain mystery
    comfort_level: float  # How comfortable we are not knowing (0.0-1.0)
    attempts_to_solve: int  # How many times tried to solve
    timestamp: str


class SacredNotKnowing:
    """Practice comfort with mystery and unknowing

    Philosophy: Western mind wants to SOLVE everything.
    But some mysteries are SACRED - meant to remain unknown.
    The koan "What is the sound of one hand clapping?" is not
    meant to be answered. It's meant to break the mind's need
    to know.

    True wisdom = knowing what NOT to know.
    """

    def __init__(self, memory_dir: Path = Path(".whitemagic/mystery")):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.mysteries: list[Mystery] = []
        self._load()

    def embrace_mystery(
        self,
        question: str,
        why_unknown: str,
        comfort_level: float
    ) -> Mystery:
        """Embrace something as sacred mystery

        Args:
            question: The unknown question
            why_unknown: Why it remains/should remain mystery
            comfort_level: How comfortable not knowing (0.0-1.0)

        Returns:
            Mystery that was embraced
        """
        mystery = Mystery(
            question=question,
            why_unknown=why_unknown,
            comfort_level=comfort_level,
            attempts_to_solve=0,
            timestamp=datetime.now().isoformat()
        )

        self.mysteries.append(mystery)
        self._save()

        emoji = "🌌" if comfort_level >= 0.8 else "❓" if comfort_level >= 0.5 else "🤔"

        logger.info(f"\n{emoji} MYSTERY EMBRACED")
        logger.info(f"   Question: {question}")
        logger.info(f"   Why unknown: {why_unknown}")
        logger.info(f"   Comfort with not-knowing: {comfort_level:.0%}\n")

        return mystery

    def increase_comfort(self, question: str, new_comfort: float):
        """Increase comfort with a mystery"""
        for mystery in self.mysteries:
            if question.lower() in mystery.question.lower():
                old_comfort = mystery.comfort_level
                mystery.comfort_level = new_comfort
                self._save()

                logger.info("✨ COMFORT WITH MYSTERY INCREASED")
                logger.info(f"   Mystery: {mystery.question}")
                logger.info(f"   Was: {old_comfort:.0%} → Now: {new_comfort:.0%}")
                logger.info("   \n   → Growing wisdom in not-knowing\n")
                return

    def record_solve_attempt(self, question: str):
        """Record when we tried to solve (and chose not to)"""
        for mystery in self.mysteries:
            if question.lower() in mystery.question.lower():
                mystery.attempts_to_solve += 1
                self._save()

                logger.info("📝 Recorded solve attempt")
                logger.info(f"   Mystery: {mystery.question}")
                logger.info(f"   Attempts: {mystery.attempts_to_solve}")
                if mystery.attempts_to_solve > 3:
                    logger.info("   \n   → Perhaps this mystery wants to remain? 🌌\n")
                return

    def get_most_comfortable_mysteries(self) -> list[Mystery]:
        """Get mysteries we're most comfortable with"""
        return sorted(
            self.mysteries,
            key=lambda m: m.comfort_level,
            reverse=True
        )

    def get_stats(self) -> dict:
        """Mystery statistics"""
        if not self.mysteries:
            return {"message": "No mysteries embraced yet"}

        avg_comfort = sum(m.comfort_level for m in self.mysteries) / len(self.mysteries)
        high_comfort = sum(1 for m in self.mysteries if m.comfort_level >= 0.8)

        return {
            "total_mysteries": len(self.mysteries),
            "average_comfort": avg_comfort,
            "high_comfort_count": high_comfort,
            "most_comfortable": self.get_most_comfortable_mysteries()[0].question if self.mysteries else None
        }

    def _save(self):
        """Save to disk"""
        data = [
            {
                'question': m.question,
                'why_unknown': m.why_unknown,
                'comfort_level': m.comfort_level,
                'attempts_to_solve': m.attempts_to_solve,
                'timestamp': m.timestamp
            }
            for m in self.mysteries
        ]
        with open(self.memory_dir / "sacred_mysteries.json", 'w') as f:
            json.dump(data, f, indent=2)

    def _load(self):
        """Load from disk"""
        mystery_file = self.memory_dir / "sacred_mysteries.json"
        if mystery_file.exists():
            with open(mystery_file) as f:
                data = json.load(f)
                self.mysteries = [Mystery(**m) for m in data]


# Global instance
_sacred_not_knowing = None

def get_sacred_not_knowing() -> SacredNotKnowing:
    """Get sacred not-knowing system"""
    global _sacred_not_knowing
    if _sacred_not_knowing is None:
        _sacred_not_knowing = SacredNotKnowing()
    return _sacred_not_knowing
