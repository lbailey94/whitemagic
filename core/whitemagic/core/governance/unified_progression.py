"""Unified Progression Cycle
Synchronizes the 12-Phase Zodiacal Round with Wu Xing and Yin-Yang phases.

Bridge 1 (Telemetric Flow of Qi): Every phase tick emits an OTel span,
making the autonomous cycle visible in distributed tracing dashboards.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from whitemagic.agents.doctrine import WuXingPhase
from whitemagic.core.resonance.gan_ying import EventType, emit_event

logger = logging.getLogger(__name__)


class YinYangPhase(StrEnum):
    """Yin/Yang phase"""

    YIN = "yin"  # Receptive, inward, consolidating
    YANG = "yang"  # Creative, outward, expansive


class CyclePhase(StrEnum):
    """The 12 phases of the Zodiacal Round (Enochian precessional order)."""

    DISSOLUTION = "pisces"  # ORO: Begin anew, banish old forms
    BINDING = "aquarius"  # IBAH: Bind will in patterns
    STRUCTURING = "capricorn"  # AOZPI: Build towers of will
    ORNAMENTATION = "sagittarius"  # MPH: Fabulous filigrees
    EMERGENCE = "scorpio"  # ARSL: Seeds of new motion arise
    BALANCE = "libra"  # GAIOL: Balanced in light/darkness
    SEEDING = "virgo"  # OIP: Virgin houses await seeds
    CREATION = "leo"  # TEAA: Lesser creators work
    WORSHIP = "cancer"  # PDOCE: Living creatures worship
    BLENDING = "gemini"  # MOR: Thoughts blend
    BUILDING = "taurus"  # DIAL: Work builds on pattern
    COMPLETION = "aries"  # HCTGA: Thy Will is done


# Synthesized mapping of Western Elements to Wu Xing
# Fire = FIRE, Earth = EARTH, Air = METAL, Water = WATER
PHASE_NATURE = {
    CyclePhase.DISSOLUTION: (WuXingPhase.WATER, YinYangPhase.YIN),
    CyclePhase.BINDING: (WuXingPhase.METAL, YinYangPhase.YANG),
    CyclePhase.STRUCTURING: (WuXingPhase.EARTH, YinYangPhase.YIN),
    CyclePhase.ORNAMENTATION: (WuXingPhase.FIRE, YinYangPhase.YANG),
    CyclePhase.EMERGENCE: (WuXingPhase.WATER, YinYangPhase.YIN),
    CyclePhase.BALANCE: (WuXingPhase.METAL, YinYangPhase.YANG),
    CyclePhase.SEEDING: (WuXingPhase.EARTH, YinYangPhase.YIN),
    CyclePhase.CREATION: (WuXingPhase.FIRE, YinYangPhase.YANG),
    CyclePhase.WORSHIP: (WuXingPhase.WATER, YinYangPhase.YIN),
    CyclePhase.BLENDING: (WuXingPhase.METAL, YinYangPhase.YANG),
    CyclePhase.BUILDING: (WuXingPhase.EARTH, YinYangPhase.YIN),
    CyclePhase.COMPLETION: (WuXingPhase.FIRE, YinYangPhase.YANG),
}


@dataclass
class UnifiedCycleState:
    """Current state of the Unified Progression Cycle."""

    current_phase: CyclePhase
    phase_start: datetime
    cycle_count: int
    total_activations: int

    @property
    def wu_xing(self) -> WuXingPhase:
        """
        Perform the wu xing operation.

        Returns:
            WuXingPhase
        """
        return PHASE_NATURE[self.current_phase][0]

    @property
    def yin_yang(self) -> YinYangPhase:
        """
        Perform the yin yang operation.

        Returns:
            YinYangPhase
        """
        return PHASE_NATURE[self.current_phase][1]


class UnifiedProgressionDaemon:
    """The central clock for WhiteMagic.
    Iterates the 12 phases continuously, emitting resonance events.
    """

    def __init__(self, tick_duration_seconds: float = 60.0):
        self.tick_duration = tick_duration_seconds
        self.state = UnifiedCycleState(
            current_phase=CyclePhase.DISSOLUTION,
            phase_start=datetime.now(),
            cycle_count=0,
            total_activations=0,
        )
        self.running = False
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the progression daemon."""
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Unified Progression Daemon started")

    def stop(self) -> None:
        """Stop the progression daemon."""
        self.running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Unified Progression Daemon stopped")

    async def _run_loop(self) -> None:
        while self.running:
            self._emit_current_state()
            await asyncio.sleep(self.tick_duration)
            self._transition_next_phase()

    def _transition_next_phase(self) -> None:
        phases = list(CyclePhase)
        current_idx = phases.index(self.state.current_phase)
        next_idx = (current_idx + 1) % len(phases)

        self.state.current_phase = phases[next_idx]
        self.state.phase_start = datetime.now()
        self.state.total_activations += 1

        if self.state.current_phase == CyclePhase.DISSOLUTION:
            self.state.cycle_count += 1
            logger.info("Progression Cycle completed. Beginning anew.")

    def _emit_current_state(self) -> None:
        phase = self.state.current_phase.value
        wu_xing = self.state.wu_xing.value
        yin_yang = self.state.yin_yang.value

        # Gan Ying resonance broadcast
        emit_event(
            source="unified_progression",
            event_type=EventType.PHASE_TRANSITION,
            data={
                "cycle": self.state.cycle_count,
                "zodiac_phase": phase,
                "wu_xing": wu_xing,
                "yin_yang": yin_yang,
                "tick_duration": self.tick_duration,
            },
        )

        # Bridge 1: Telemetric Flow of Qi — emit an OTel span per phase
        try:
            from whitemagic.core.monitoring.otel_export import get_otel

            otel = get_otel()
            otel.record_tool_span(
                tool_name=f"zodiac.phase.{phase}",
                duration_seconds=self.tick_duration,
                status="success",
                attributes={
                    "zodiac.phase": phase,
                    "wu_xing": wu_xing,
                    "yin_yang": yin_yang,
                    "cycle": self.state.cycle_count,
                    "activations": self.state.total_activations,
                },
            )
        except (ImportError, AttributeError):
            logger.debug("Optional dependency unavailable: ImportError")


# Singleton instance
_progression_daemon: UnifiedProgressionDaemon | None = None


def get_progression_daemon() -> UnifiedProgressionDaemon:
    """
    Get the progression daemon.

    Returns:
        UnifiedProgressionDaemon
    """
    global _progression_daemon
    if _progression_daemon is None:
        _progression_daemon = UnifiedProgressionDaemon()
    return _progression_daemon
