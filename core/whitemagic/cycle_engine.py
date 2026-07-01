# ruff: noqa: BLE001
"""Unified Cycle Engine — Orchestrates Yin-Yang, Wu Xing, and Zodiacal Round.

Fuses the 10 scattered wisdom systems into a single coordinated loop:
  - YinYangBalanceTracker: activity categorization, burnout prevention
  - ZodiacalRound: 12-phase consciousness cycle
  - WuXingSystem: five-element task-type mapping
  - ContextSynthesizer: unified state gathering
  - CascadeExecutor: yin-yang paced batch execution
  - Gan Ying event bus: cross-system resonance

The CycleEngine maps Wu Xing elements to campaign phases:
  Wood  → Recon (growth, discovery)
  Fire  → Action (execution, transformation)
  Earth → Integration (consolidation, grounding)
  Metal → Verify (precision, refinement)
  Water → Rest (reflection, planning)

Zodiacal phases trigger campaign actions:
  Aries/Scorpio → Emergence, bold action
  Libra → Balance, verify equilibrium
  Capricorn → Structure, consolidation
  Pisces → Dissolution, cleanup
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

# Lazy imports to avoid circular dependencies
_yy_tracker = None
_zodiacal = None
_wu_xing = None
_context_synth = None
_gan_ying_bus = None


def _get_gan_ying():
    global _gan_ying_bus
    if _gan_ying_bus is None:
        try:
            from whitemagic.core.resonance.gan_ying_enhanced import get_bus

            _gan_ying_bus = get_bus()
        except ImportError:
            _gan_ying_bus = False
    return _gan_ying_bus if _gan_ying_bus is not False else None


def _get_yy_tracker():
    global _yy_tracker
    if _yy_tracker is None:
        try:
            from whitemagic.harmony.yin_yang_tracker import YinYangBalanceTracker

            _yy_tracker = YinYangBalanceTracker()
        except ImportError:
            _yy_tracker = False
    return _yy_tracker if _yy_tracker is not False else None


def _get_zodiacal():
    global _zodiacal
    if _zodiacal is None:
        try:
            from whitemagic.zodiac.zodiac_round_cycle import ZodiacalRound

            _zodiacal = ZodiacalRound()
        except ImportError:
            _zodiacal = False
    return _zodiacal if _zodiacal is not False else None


def _get_wu_xing():
    global _wu_xing
    if _wu_xing is None:
        try:
            from whitemagic.wu_xing import WuXingEngine

            _wu_xing = WuXingEngine()
        except ImportError:
            _wu_xing = False
    return _wu_xing if _wu_xing is not False else None


def _get_context_synth():
    global _context_synth
    if _context_synth is None:
        try:
            from whitemagic.cascade.context_synthesizer import ContextSynthesizer

            _context_synth = ContextSynthesizer()
        except ImportError:
            _context_synth = False
    return _context_synth if _context_synth is not False else None


# Wu Xing → Campaign Phase mapping
ELEMENT_TO_PHASE = {
    "wood": "recon",
    "fire": "action",
    "earth": "integration",
    "metal": "verify",
    "water": "rest",
}

# Zodiacal Phase → Campaign Action mapping
ZODIAC_TO_ACTION = {
    "ARIES": "bold_action",
    "TAURUS": "consolidate",
    "GEMINI": "communicate",
    "CANCER": "nurture",
    "LEO": "lead",
    "VIRGO": "analyze",
    "LIBRA": "balance",
    "SCORPIO": "emergence",
    "SAGITTARIUS": "explore",
    "CAPRICORN": "structure",
    "AQUARIUS": "innovate",
    "PISCES": "dissolution",
}


@dataclass
class CycleState:
    """Snapshot of the unified cycle state."""

    cycle_number: int = 0
    zodiacal_phase: str = "UNKNOWN"
    wu_xing_element: str = "unknown"
    yin_yang_balance: float = 0.5
    burnout_risk: float = 0.0
    campaign_phase: str = "recon"
    suggested_action: str = "observe"
    timestamp: str = ""
    events_emitted: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class CycleMetrics:
    """Accumulated metrics across cycle rounds."""

    total_cycles: int = 0
    total_rounds: int = 0
    yin_phases: int = 0
    yang_phases: int = 0
    phase_durations: dict[str, float] = field(default_factory=dict)
    element_counts: dict[str, int] = field(default_factory=dict)
    emergent_events: list[dict] = field(default_factory=list)
    start_time: float = 0.0
    elapsed_s: float = 0.0


class CycleEngine:
    """Unified orchestrator for Yin-Yang, Wu Xing, and Zodiacal Round systems.

    Drives campaign execution through wisdom-informed phase transitions:
    1. Gather unified context (ContextSynthesizer)
    2. Determine current wu_xing element → campaign phase
    3. Check yin-yang balance → pace execution
    4. Advance zodiacal phase → trigger appropriate action
    5. Emit Gan Ying events for cross-system resonance
    """

    def __init__(self):
        self.yy = _get_yy_tracker()
        self.zodiac = _get_zodiacal()
        self.wu_xing = _get_wu_xing()
        self.synth = _get_context_synth()
        self.gan_ying = _get_gan_ying()
        self.metrics = CycleMetrics()
        self.state = CycleState()
        self._cycle_count = 0

    @property
    def systems_available(self) -> dict[str, bool]:
        """Report which subsystems are available."""
        return {
            "yin_yang": self.yy is not None,
            "zodiacal_round": self.zodiac is not None,
            "wu_xing": self.wu_xing is not None,
            "context_synthesizer": self.synth is not None,
            "gan_ying_bus": self.gan_ying is not None,
        }

    def gather_state(self) -> CycleState:
        """Gather unified state from all available subsystems."""
        state = CycleState(
            cycle_number=self._cycle_count,
            timestamp=datetime.now().isoformat(),
        )

        # Yin-Yang balance
        if self.yy:
            try:
                summary = self.yy.get_summary()
                state.yin_yang_balance = summary.get("balance", 0.5)
                state.burnout_risk = summary.get("burnout_risk", 0.0)
            except Exception as e:
                import logging

                logging.getLogger(__name__).debug("Exception silenced: %s", e)

        # Zodiacal phase — ZodiacalRound stores phase in state.current_phase enum
        if self.zodiac:
            try:
                zstate = self.zodiac.state
                phase = zstate.current_phase
                if hasattr(phase, "name"):
                    state.zodiacal_phase = phase.name
                elif hasattr(phase, "value"):
                    state.zodiacal_phase = phase.value.upper()
                else:
                    state.zodiacal_phase = str(phase).upper()
                state.suggested_action = ZODIAC_TO_ACTION.get(
                    state.zodiacal_phase.upper(), "observe"
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).debug("Exception silenced: %s", e)

        # Wu Xing element — WuXingEngine uses get_current_cycle()
        if self.wu_xing:
            try:
                cycle = self.wu_xing.get_current_cycle()
                if cycle and isinstance(cycle, dict):
                    elem = cycle.get("element", "unknown")
                    state.wu_xing_element = str(elem).lower()
                elif hasattr(self.wu_xing, "elements"):
                    # Fallback: derive from cycle history
                    hist = self.wu_xing.cycle_history
                    if hist:
                        state.wu_xing_element = str(
                            hist[-1].get("element", "wood")
                        ).lower()
                    else:
                        state.wu_xing_element = "wood"  # default starting element
                state.campaign_phase = ELEMENT_TO_PHASE.get(
                    state.wu_xing_element, "recon"
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).debug("Exception silenced: %s", e)

        # Context synthesis
        if self.synth:
            try:
                ctx = (
                    self.synth.synthesize() if hasattr(self.synth, "synthesize") else {}
                )
                if hasattr(ctx, "__dict__"):
                    state.metrics["context"] = {
                        k: str(v)[:100]
                        for k, v in vars(ctx).items()
                        if not k.startswith("_")
                    }
            except Exception as e:
                import logging

                logging.getLogger(__name__).debug("Exception silenced: %s", e)

        self.state = state
        return state

    def advance(self) -> CycleState:
        """Advance one cycle: gather state, advance zodiac, record activity."""
        self._cycle_count += 1
        self.metrics.total_cycles += 1

        # Gather current state
        state = self.gather_state()

        # Advance zodiacal round
        if self.zodiac and hasattr(self.zodiac, "advance_phase"):
            try:
                result = self.zodiac.advance_phase()
                if result:
                    state.events_emitted.append(
                        f"zodiac_advance:{state.zodiacal_phase}"
                    )
                    self.metrics.emergent_events.append(
                        {
                            "type": "zodiac_advance",
                            "phase": state.zodiacal_phase,
                            "cycle": self._cycle_count,
                            "ts": state.timestamp,
                        }
                    )
            except Exception as e:
                import logging

                logging.getLogger(__name__).debug("Exception silenced: %s", e)

        # Record yin-yang activity based on campaign phase
        if self.yy:
            try:
                category = (
                    "yang" if state.campaign_phase in ("action", "verify") else "yin"
                )
                if category == "yang":
                    self.metrics.yang_phases += 1
                else:
                    self.metrics.yin_phases += 1
                self.yy.record_activity(category, f"cycle_{self._cycle_count}")
            except Exception as e:
                import logging

                logging.getLogger(__name__).debug("Exception silenced: %s", e)

        # Track wu_xing element usage
        elem = state.wu_xing_element
        self.metrics.element_counts[elem] = self.metrics.element_counts.get(elem, 0) + 1

        # Gan Ying cross-system resonance chain: wu_xing → zodiac → yin_yang
        self._emit_resonance_chain(state)

        return state

    def _emit_resonance_chain(self, state: CycleState):
        """Emit Gan Ying events for cross-system resonance.

        Chain: wu_xing element change → zodiac phase advance → yin_yang balance update.
        Each system's state change ripples through to the others via the event bus.
        """
        if not self.gan_ying:
            return
        try:
            from whitemagic.core.resonance.gan_ying_enhanced import (
                EventType,
                ResonanceEvent,
            )

            # Wu Xing element event
            wu_xing_event = ResonanceEvent(
                source="cycle_engine.wu_xing",
                event_type=EventType.ELEMENT_SHIFT
                if hasattr(EventType, "ELEMENT_SHIFT")
                else EventType.SYSTEM_HEARTBEAT,
                data={
                    "element": state.wu_xing_element,
                    "campaign_phase": state.campaign_phase,
                    "cycle": self._cycle_count,
                },
                confidence=0.9,
            )
            self.gan_ying.emit(wu_xing_event, cascade=True)
            state.events_emitted.append(f"gan_ying:wu_xing:{state.wu_xing_element}")

            # Zodiac phase event
            zodiac_event = ResonanceEvent(
                source="cycle_engine.zodiac",
                event_type=EventType.ZODIAC_PHASE_CHANGE
                if hasattr(EventType, "ZODIAC_PHASE_CHANGE")
                else EventType.SYSTEM_HEARTBEAT,
                data={
                    "zodiacal_phase": state.zodiacal_phase,
                    "suggested_action": state.suggested_action,
                    "cycle": self._cycle_count,
                },
                confidence=0.9,
            )
            self.gan_ying.emit(zodiac_event, cascade=True)
            state.events_emitted.append(f"gan_ying:zodiac:{state.zodiacal_phase}")

            # Yin-Yang balance event
            yy_event = ResonanceEvent(
                source="cycle_engine.yin_yang",
                event_type=EventType.BALANCE_SHIFT
                if hasattr(EventType, "BALANCE_SHIFT")
                else EventType.SYSTEM_HEARTBEAT,
                data={
                    "balance": state.yin_yang_balance,
                    "burnout_risk": state.burnout_risk,
                    "cycle": self._cycle_count,
                },
                confidence=0.9,
            )
            self.gan_ying.emit(yy_event, cascade=True)
            state.events_emitted.append(
                f"gan_ying:yin_yang:balance={state.yin_yang_balance:.2f}"
            )

        except Exception as e:
            import logging

            logging.getLogger(__name__).debug("Exception silenced: %s", e)

    def run_rounds(self, n_rounds: int = 3, callback=None) -> CycleMetrics:
        """Run N full zodiacal rounds (each round = 12 phase advances).

        Args:
            n_rounds: Number of complete zodiacal rounds to execute.
            callback: Optional function called after each advance with (round, phase, state).

        Returns:
            CycleMetrics with accumulated statistics.
        """
        self.metrics.start_time = time.monotonic()
        self.metrics.total_rounds = n_rounds

        for round_num in range(1, n_rounds + 1):
            for phase_num in range(1, 13):
                # 12 zodiacal phases per round
                state = self.advance()

                if callback:
                    try:
                        callback(round_num, phase_num, state)
                    except Exception as e:
                        import logging

                        logging.getLogger(__name__).debug("Exception silenced: %s", e)

        self.metrics.elapsed_s = time.monotonic() - self.metrics.start_time
        return cast(CycleMetrics, self.metrics)

    def should_pause(self) -> bool:
        """Check if yin-yang balance suggests a pause (burnout prevention)."""
        if self.yy:
            try:
                summary = self.yy.get_summary()
                return cast(bool, summary.get("burnout_risk", 0.0) > 0.7)
            except Exception as e:
                import logging

                logging.getLogger(__name__).debug("Exception silenced: %s", e)
        return False

    def get_recommended_phase(self) -> str:
        """Get the currently recommended campaign phase based on all systems."""
        state = self.gather_state()

        if state.burnout_risk > 0.7:
            return "rest"

        # Zodiacal phase takes priority for action type
        if state.zodiacal_phase in ("SCORPIO", "ARIES", "LEO"):
            return "action"
        elif state.zodiacal_phase in ("LIBRA", "VIRGO"):
            return "verify"
        elif state.zodiacal_phase in ("PISCES", "CANCER"):
            return "rest"

        # Fall back to wu_xing element
        return state.campaign_phase

    def status(self) -> dict:
        """Return full engine status as a dict."""
        state = self.gather_state()
        return {
            "systems": self.systems_available,
            "cycle": self._cycle_count,
            "zodiacal_phase": state.zodiacal_phase,
            "wu_xing_element": state.wu_xing_element,
            "yin_yang_balance": state.yin_yang_balance,
            "burnout_risk": state.burnout_risk,
            "campaign_phase": state.campaign_phase,
            "suggested_action": state.suggested_action,
            "metrics": {
                "total_cycles": self.metrics.total_cycles,
                "yin_phases": self.metrics.yin_phases,
                "yang_phases": self.metrics.yang_phases,
                "element_counts": self.metrics.element_counts,
                "emergent_events": len(self.metrics.emergent_events),
            },
        }
