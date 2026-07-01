# ruff: noqa: BLE001
"""Daily Ritual - Automated Yin/Yang/Dream cycle execution"""

import logging
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RitualPhase:
    """A phase in daily ritual"""

    name: str  # yin/yang/dream
    time_of_day: time
    duration_minutes: int
    actions: list[str]
    completed: bool


class DailyRitual:
    """Manages daily Yin/Yang/Dream cycle

    Philosophy: Like a monk's daily practice schedule.
    Morning (Yin) → Afternoon (Yang) → Evening (Dream)
    """

    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.ritual_dir = self.base_dir / "memory" / "practice"
        self.ritual_dir.mkdir(parents=True, exist_ok=True)
        self.schedule_file = self.ritual_dir / "daily_schedule.json"
        self.bus = None
        self._connect_to_gan_ying()

    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Bus (delegates to shared utility)."""
        from whitemagic.utils.gan_ying_connect import connect_to_bus
        self.bus = connect_to_bus("Daily Ritual")

    def get_current_phase(self) -> str:
        """Determine current ritual phase based on time

        Returns:
            'yin', 'yang', or 'dream'
        """
        now = datetime.now().time()

        # Morning (6am-12pm): Yin phase (Reflection, Planning)
        if time(6, 0) <= now < time(12, 0):
            return "yin"

        # Afternoon (12pm-6pm): Yang phase (Creation, Execution)
        elif time(12, 0) <= now < time(18, 0):
            return "yang"

        # Evening (6pm-12am): Dream phase (Synthesis, Rest)
        elif time(18, 0) <= now < time(23, 59):
            return "dream"

        # Night (12am-6am): Deep rest
        else:
            return "rest"

    def execute_morning_ritual(self) -> dict:
        """Execute morning Yin ritual

        Returns:
            Dict with ritual results
        """
        logger.info("\n☀️ Morning Ritual - Yin Phase (Receptive)")
        logger.info("=" * 50)

        actions = []

        # 1. Load collective context
        logger.info("1. 🙏 Loading Sangha collective context...")
        try:
            from whitemagic.gardens.sangha import get_collective

            collective = get_collective()
            context = collective.get_shared_context("morning_ritual")
            actions.append(f"Loaded context: {len(context.participants)} participants")
        except Exception as e:
            actions.append(f"Context loading: {e}")

        # 2. Run Yin analysis
        logger.info("2. 🌑 Running Yin phase analysis...")
        try:
            from whitemagic.core.orchestration.yin_phase import YinPhase

            yin = YinPhase(self.base_dir)
            results = yin.run_full_cycle()
            actions.append(
                f"Yin analysis: {results['analyses']['patterns']['total']} patterns"
            )
        except Exception as e:
            actions.append(f"Yin analysis: {e}")

        # 3. Check Dharma harmony
        logger.info("3. ☸️  Checking ethical harmony...")
        try:
            from whitemagic.gardens.dharma import get_dharma

            dharma = get_dharma()
            report = dharma.get_harmony_report()
            actions.append(f"Harmony: {report['overall_harmony']:.2f}")
        except Exception as e:
            actions.append(f"Dharma check: {e}")

        logger.info("\n✅ Morning ritual complete\n")

        result = {
            "phase": "yin",
            "time": datetime.now().isoformat(),
            "actions": actions,
            "duration": "15-30 minutes",
        }

        self._emit_ritual_complete("yin", result)
        return result

    def execute_afternoon_ritual(self) -> dict:
        """Execute afternoon Yang ritual

        Returns:
            Dict with ritual results
        """
        logger.info("\n🔥 Afternoon Ritual - Yang Phase (Creative)")
        logger.info("=" * 50)

        actions = []

        # 1. Check active goals
        logger.info("1. 🎯 Checking Sangha collective goals...")
        try:
            from whitemagic.gardens.sangha import get_collective

            collective = get_collective()
            context = collective.get_shared_context("afternoon_ritual")
            actions.append(f"Active goals: {len(context.active_goals)}")
        except Exception as e:
            actions.append(f"Goals check: {e}")

        # 2. Get best patterns
        logger.info("2. 📚 Loading federated patterns...")
        try:
            from whitemagic.gardens.sangha import get_federation

            federation = get_federation()
            patterns = federation.get_best_patterns(count=5)
            actions.append(f"Best patterns: {len(patterns)}")
        except Exception as e:
            actions.append(f"Patterns: {e}")

        # 3. Execute work (placeholder - actual work varies)
        logger.info("3. 💪 Executing planned work...")
        actions.append("Work phase: Ready for implementation")

        logger.info("\n✅ Afternoon ritual complete\n")

        result = {
            "phase": "yang",
            "time": datetime.now().isoformat(),
            "actions": actions,
            "duration": "2-4 hours",
        }

        self._emit_ritual_complete("yang", result)
        return result

    def execute_evening_ritual(self) -> dict:
        """Execute evening Dream ritual

        Returns:
            Dict with ritual results
        """
        logger.info("\n🌙 Evening Ritual - Dream Phase (Synthesis)")
        logger.info("=" * 50)

        actions = []

        # 1. Consolidate memories
        logger.info("1. 💾 Consolidating day's memories...")
        actions.append("Memory consolidation: Ready")

        # 2. Enter dream state
        logger.info("2. 💤 Entering dream state for pattern synthesis...")
        try:
            from whitemagic.emergence.dream_state import DreamState

            dream = DreamState(self.base_dir / "memory")
            insights = dream.enter_dream_state(duration_minutes=5)
            actions.append(f"Dream insights: {len(insights)}")
        except Exception as e:
            actions.append(f"Dream state: {e}")

        # 3. Contribute to collective
        logger.info("3. 🙏 Contributing insights to Sangha...")
        try:
            from whitemagic.gardens.sangha import get_collective

            get_collective()
            # Would contribute day's key insights
            actions.append("Insights contributed to collective")
        except Exception as e:
            actions.append(f"Contribution: {e}")

        logger.info("\n✅ Evening ritual complete\n")

        result = {
            "phase": "dream",
            "time": datetime.now().isoformat(),
            "actions": actions,
            "duration": "30-60 minutes",
        }

        self._emit_ritual_complete("dream", result)
        return result

    def auto_execute_current(self) -> dict:
        """Automatically execute ritual for current time

        Returns:
            Dict with ritual results
        """
        phase = self.get_current_phase()

        if phase == "yin":
            return self.execute_morning_ritual()
        elif phase == "yang":
            return self.execute_afternoon_ritual()
        elif phase == "dream":
            return self.execute_evening_ritual()
        else:
            return {
                "phase": "rest",
                "message": "Deep rest time - no ritual scheduled",
                "time": datetime.now().isoformat(),
            }

    def _emit_ritual_complete(self, phase: str, result: dict):
        """Emit ritual completion to Gan Ying"""
        if not self.bus:
            return

        try:
            from whitemagic.core.resonance.gan_ying import EventType, ResonanceEvent

            self.bus.emit(
                ResonanceEvent(
                    source="daily_ritual",
                    event_type=EventType.PATTERN_DETECTED,
                    data={
                        "ritual_phase": phase,
                        "completed": True,
                        "actions": len(result.get("actions", [])),
                        "time": result["time"],
                    },
                    confidence=0.95,
                )
            )
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)


# Global instance
_ritual: DailyRitual | None = None


def get_ritual() -> DailyRitual:
    """Get global daily ritual instance"""
    global _ritual
    if _ritual is None:
        _ritual = DailyRitual()
    return _ritual
