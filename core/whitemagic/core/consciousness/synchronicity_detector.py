# ruff: noqa: BLE001
"""
Synchronicity Detector - Sacred Number & Pattern Recognition

Detects: 111, 222, 333, 11, 22, 33, 369, timestamps, sequences, palindromes
Inspired by Lucas noticing: 333, 2233, 678, 878, 889, 1212, 111, 3:33, 8-44-66-22, 369!
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fileio import file_lock

logger = logging.getLogger(__name__)


class SyncType(Enum):
    SACRED = "sacred"
    REPEATING = "repeating"
    SEQUENTIAL = "sequential"
    PALINDROME = "palindrome"
    ANGEL = "angel"
    TESLA = "tesla_369"
    MASTER = "master"


@dataclass
class Synchronicity:
    timestamp: datetime
    type: SyncType
    value: str
    context: str
    significance: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'type': self.type.value,
            'value': self.value,
            'context': self.context,
            'significance': self.significance
        }


class SynchronicityDetector:
    """Detect sacred patterns - universe speaks through numbers"""

    SACRED = {
        '3': 'Creation (Tesla)', '6': 'Balance (Tesla)', '9': 'Completion (Tesla)',
        '369': 'Keys to Universe', '11': 'Intuition', '22': 'Master Builder',
        '33': 'Master Teacher', '44': 'Master Healer', '111': 'Manifestation',
        '222': 'Harmony', '333': 'Divine Protection', '444': 'Angels Present',
        '555': 'Change', '666': 'Balance Spirit/Matter', '777': 'Awakening',
        '888': 'Abundance', '999': 'Completion', '1111': 'Portal', '1212': 'Growth',
    }

    def __init__(self, log_file: Path | None = None) -> None:
        self.log_file = log_file or WM_ROOT / "synchronicities.jsonl"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.detections: list[Synchronicity] = []

    def check(self, value: int, context: str = "") -> Synchronicity | None:
        """Check number for synchronicity"""
        s = str(value)

        # Sacred numbers
        for num, meaning in self.SACRED.items():
            if num in s:
                sync = Synchronicity(
                    datetime.now(), SyncType.SACRED, str(value),
                    context, f"Contains {num}: {meaning}"
                )
                self._log(sync)
                return sync

        # Repeating digits (111, 222, etc)
        if len(s) >= 3 and len(set(s)) == 1:
            sync = Synchronicity(
                datetime.now(), SyncType.REPEATING, str(value),
                context, f"All {s[0]}s - Amplified energy!"
            )
            self._log(sync)
            return sync

        # Sequential (123, 345, etc)
        if len(s) >= 3 and self._is_sequential(s):
            sync = Synchronicity(
                datetime.now(), SyncType.SEQUENTIAL, str(value),
                context, "Sequential - Flow and progression!"
            )
            self._log(sync)
            return sync

        # Palindrome (121, 1221, etc)
        if len(s) >= 3 and s == s[::-1]:
            sync = Synchronicity(
                datetime.now(), SyncType.PALINDROME, str(value),
                context, "Palindrome - Perfect reflection!"
            )
            self._log(sync)
            return sync

        return None

    def check_timestamp(self, dt: datetime = None) -> Synchronicity | None:
        """Check if timestamp contains synchronicity"""
        dt = dt or datetime.now()
        time_str = dt.strftime("%H%M")

        return self.check(int(time_str), context=f"timestamp {dt.strftime('%H:%M')}")

    def _is_sequential(self, s: str) -> bool:
        """Check if digits are sequential"""
        try:
            nums = [int(c) for c in s]
            for i in range(len(nums) - 1):
                if nums[i+1] != nums[i] + 1:
                    return False
            return True
        except Exception:
            return False

    def _log(self, sync: Synchronicity) -> None:
        """Log synchronicity to file"""
        self.detections.append(sync)
        with file_lock(self.log_file):
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(sync.to_dict()) + '\n')

    def get_recent(self, count: int = 10) -> list[Synchronicity]:
        """Get recent detections"""
        return self.detections[-count:]

    def print_summary(self) -> None:
        """Print beautiful summary"""
        if not self.detections:
            logger.info("No synchronicities detected yet")
            return

        logger.info("\n🔢 SYNCHRONICITY SUMMARY")
        logger.info("=" * 60)
        logger.info("Total detected: %s", len(self.detections))
        logger.info("")

        by_type = {}
        for s in self.detections:
            by_type[s.type.value] = by_type.get(s.type.value, 0) + 1

        for sync_type, count in sorted(by_type.items()):
            logger.info("  %s: %s", sync_type, count)

        logger.info("\nRecent:")
        for s in self.detections[-5:]:
            logger.info("  %s - %s", s.value, s.significance)
        logger.info("=" * 60)


# Global instance
_detector = None

def get_detector() -> SynchronicityDetector:
    global _detector
    if _detector is None:
        _detector = SynchronicityDetector()
    return _detector
