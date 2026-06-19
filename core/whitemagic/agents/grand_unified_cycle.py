# ruff: noqa: BLE001
"""Grand Unified Cycle — Synthesis of All Cyclical Systems
==========================================================

Weaves together 10 cyclical systems into a single breathing organism:
  1. Zodiacal Round (12 phases)
  2. Wu Xing Engine (5 elements)
  3. Wu Xing Performance System
  4. Wu Xing Force Timing
  5. Yin-Yang Balance Tracker
  6. Yin-Yang Cycle Tracker
  7. Yin-Yang Autonomous Cycle
  8. Tactical Pipeline (7 phases)
  9. Art of War Engine
  10. War Room Tactics

Architecture:
  Cosmic Layer (Zodiac) → Elemental Layer (Wu Xing) → Polarity Layer (Yin-Yang)
  → Tactical Layer (Pipeline) → Strategic Layer (Art of War) → Execution Layer (War Room)

All connected via Gan Ying resonance cascade.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# FUSION MAPPINGS
# ============================================================================

class ZodiacSign(StrEnum):
    """12 Zodiac signs"""
    PISCES = "pisces"
    AQUARIUS = "aquarius"
    CAPRICORN = "capricorn"
    SAGITTARIUS = "sagittarius"
    SCORPIO = "scorpio"
    LIBRA = "libra"
    VIRGO = "virgo"
    LEO = "leo"
    CANCER = "cancer"
    GEMINI = "gemini"
    TAURUS = "taurus"
    ARIES = "aries"


class WuXingElement(StrEnum):
    """5 Wu Xing elements"""
    WOOD = "wood"
    FIRE = "fire"
    EARTH = "earth"
    METAL = "metal"
    WATER = "water"


class PipelinePhase(StrEnum):
    """7 Tactical pipeline phases"""
    SCOUT = "scout"
    DISCOVER = "discover"
    CLARIFY = "clarify"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    REFLECT = "reflect"


# Zodiac → Wu Xing mapping
ZODIAC_TO_WUXING: dict[ZodiacSign, WuXingElement] = {
    # Fire signs → Fire element
    ZodiacSign.ARIES: WuXingElement.FIRE,
    ZodiacSign.LEO: WuXingElement.FIRE,
    ZodiacSign.SAGITTARIUS: WuXingElement.FIRE,

    # Earth signs → Earth element
    ZodiacSign.TAURUS: WuXingElement.EARTH,
    ZodiacSign.VIRGO: WuXingElement.EARTH,
    ZodiacSign.CAPRICORN: WuXingElement.EARTH,

    # Air signs → Metal element (structure, precision)
    ZodiacSign.GEMINI: WuXingElement.METAL,
    ZodiacSign.LIBRA: WuXingElement.METAL,
    ZodiacSign.AQUARIUS: WuXingElement.METAL,

    # Water signs → Water element
    ZodiacSign.CANCER: WuXingElement.WATER,
    ZodiacSign.SCORPIO: WuXingElement.WATER,
    ZodiacSign.PISCES: WuXingElement.WATER,
}

# Wu Xing → Pipeline Phase mapping
WUXING_TO_PIPELINE: dict[WuXingElement, list[PipelinePhase]] = {
    WuXingElement.WOOD: [PipelinePhase.SCOUT, PipelinePhase.DISCOVER],
    WuXingElement.FIRE: [PipelinePhase.EXECUTE],
    WuXingElement.EARTH: [PipelinePhase.CLARIFY],
    WuXingElement.METAL: [PipelinePhase.VERIFY],
    WuXingElement.WATER: [PipelinePhase.PLAN, PipelinePhase.REFLECT],
}

# Pipeline → War Room Tactic mapping
PIPELINE_TO_TACTICS: dict[PipelinePhase, str] = {
    PipelinePhase.SCOUT: "Cast a Brick to Attract Jade",
    PipelinePhase.DISCOVER: "Besiege Wei to Rescue Zhao",
    PipelinePhase.CLARIFY: "Chain of Stratagems",
    PipelinePhase.PLAN: "Besiege Wei to Rescue Zhao",
    PipelinePhase.EXECUTE: "Chain of Stratagems",
    PipelinePhase.VERIFY: "Cast a Brick to Attract Jade",
    PipelinePhase.REFLECT: "Besiege Wei to Rescue Zhao",
}

# Stagnation → Emergency tactic
STAGNATION_TACTICS = [
    "The Empty Fort",
    "The Wave of Ignorance",
]


# ============================================================================
# UNIFIED STATE
# ============================================================================

@dataclass
class UnifiedState:
    """Complete state snapshot of all cyclical systems"""

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

    # Cosmic Layer (Zodiac)
    zodiac_sign: ZodiacSign = ZodiacSign.PISCES
    zodiac_cycle_count: int = 0
    zodiac_phase_number: int = 0  # 0-11

    # Elemental Layer (Wu Xing)
    wu_xing_element: WuXingElement = WuXingElement.WOOD
    wu_xing_energy: float = 0.5  # 0.0-1.0
    wu_xing_generating: WuXingElement = WuXingElement.FIRE
    wu_xing_overcoming: WuXingElement = WuXingElement.EARTH

    # Polarity Layer (Yin-Yang)
    yin_yang_balance: float = 0.0  # -1.0 (yin) to +1.0 (yang)
    burnout_risk: float = 0.0  # 0.0-1.0
    yin_ratio: float = 0.5
    yang_ratio: float = 0.5

    # Tactical Layer (Pipeline)
    pipeline_phase: PipelinePhase = PipelinePhase.SCOUT
    pipeline_cycle: int = 0
    stagnation_count: int = 0

    # Strategic Layer
    campaign_phase: str = "reconnaissance"  # Art of War phase
    recommended_tactic: str = "Cast a Brick to Attract Jade"

    # Execution Layer
    force_composition: dict[str, float] = field(default_factory=dict)

    # Resonance
    resonance_events: list[str] = field(default_factory=list)

    def get_dominant_influence(self) -> str:
        """Determine which system is currently dominant"""
        # High burnout → Yin-Yang dominates
        if self.burnout_risk > 0.7:
            return "yin_yang_balance"

        # Stagnation → Emergency tactics dominate
        if self.stagnation_count >= 3:
            return "stagnation_emergency"

        # Otherwise zodiac drives
        return f"zodiac_{self.zodiac_sign.value}"

    def get_recommended_action(self) -> str:
        """Get the recommended action based on unified state"""
        if self.burnout_risk > 0.7:
            return "Force reflection phase (Water) — burnout prevention"

        if self.stagnation_count >= 3:
            return f"Deploy emergency tactic: {STAGNATION_TACTICS[0]}"

        if self.stagnation_count >= 2:
            return f"Prepare emergency tactic: {STAGNATION_TACTICS[1]}"

        return f"Execute {self.recommended_tactic} in {self.pipeline_phase.value} phase"


# ============================================================================
# GRAND UNIFIED CYCLE ENGINE
# ============================================================================

class GrandUnifiedCycle:
    """The Grand Unified Cycle orchestrator.

    Coordinates all 10 cyclical systems into a single breathing organism.
    Advances through cosmic → elemental → polarity → tactical → strategic → execution.
    """

    def __init__(self):
        self.state = UnifiedState()
        self._cycle_count = 0
        self._phase_history: list[UnifiedState] = []

        # Lazy-loaded subsystems
        self._zodiacal_round: Any | None = None
        self._wu_xing_engine: Any | None = None
        self._wu_xing_system: Any | None = None
        self._yin_yang_tracker: Any | None = None
        self._tactical_pipeline: Any | None = None
        self._war_room: Any | None = None
        self._doctrine: Any | None = None
        self._gan_ying_bus: Any | None = None

        self._initialized = False

        logger.info("Grand Unified Cycle initialized")

    def _ensure_initialized(self):
        """Lazy initialization of all subsystems"""
        if self._initialized:
            return

        # Zodiacal Round
        try:
            from whitemagic.zodiac.zodiac_round_cycle import get_zodiacal_round
            self._zodiacal_round = get_zodiacal_round()
            logger.info("✓ Zodiacal Round connected")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("Zodiacal Round unavailable: %s", e, exc_info=True)

        # Wu Xing Engine
        try:
            from whitemagic.wu_xing import WuXingEngine
            self._wu_xing_engine = WuXingEngine()
            logger.info("✓ Wu Xing Engine connected")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("Wu Xing Engine unavailable: %s", e, exc_info=True)

        # Wu Xing System
        try:
            from whitemagic.core.intelligence.wisdom.wu_xing import WuXingSystem
            self._wu_xing_system = WuXingSystem()
            logger.info("✓ Wu Xing System connected")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("Wu Xing System unavailable: %s", e, exc_info=True)

        # Yin-Yang Tracker
        try:
            from whitemagic.harmony.yin_yang_tracker import get_tracker
            self._yin_yang_tracker = get_tracker()
            logger.info("✓ Yin-Yang Tracker connected")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("Yin-Yang Tracker unavailable: %s", e, exc_info=True)

        # War Room
        try:
            from whitemagic.agents.war_room import get_war_room
            self._war_room = get_war_room()
            logger.info("✓ War Room connected")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("War Room unavailable: %s", e, exc_info=True)

        # Doctrine
        try:
            from whitemagic.agents.doctrine import get_doctrine
            self._doctrine = get_doctrine()
            logger.info("✓ Imperial Doctrine connected")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("Imperial Doctrine unavailable: %s", e, exc_info=True)

        # Gan Ying Bus
        try:
            from whitemagic.core.resonance.gan_ying import get_bus
            self._gan_ying_bus = get_bus()
            logger.info("✓ Gan Ying Bus connected")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("Gan Ying Bus unavailable: %s", e, exc_info=True)

        self._initialized = True
        logger.info("🎖️ Grand Unified Cycle fully initialized")

    def advance_grand_cycle(self) -> UnifiedState:
        """Advance one complete grand cycle step.

        Flow:
          1. Advance zodiac (1/12 of round)
          2. Map zodiac → wu xing element
          3. Check yin-yang balance
          4. Determine tactical pipeline phase
          5. Select war room tactic
          6. Emit unified resonance event

        Returns:
            UnifiedState with all systems synchronized
        """
        self._ensure_initialized()
        self._cycle_count += 1

        logger.info(f"\n{'='*60}")
        logger.info("🌀 GRAND CYCLE %s — Advancing all systems", self._cycle_count, exc_info=True)
        logger.info(f"{'='*60}")

        # 1. COSMIC LAYER: Advance Zodiac
        zodiac_sign = self._advance_zodiac()
        logger.info(f"  🌟 Zodiac: {zodiac_sign.value.upper()}")

        # 2. ELEMENTAL LAYER: Map Zodiac → Wu Xing
        element = self._zodiac_to_wuxing(zodiac_sign)
        self._adjust_wu_xing(element)
        logger.info(f"  ☯️  Wu Xing: {element.value.upper()}")

        # 3. POLARITY LAYER: Check Yin-Yang Balance
        balance = self._check_yin_yang_balance()
        logger.info(f"  ⚖️  Yin-Yang: {balance['balance']:.2f} (burnout: {balance['burnout_risk']:.0%})")

        # 4. TACTICAL LAYER: Determine Pipeline Phase
        pipeline_phase = self._determine_pipeline_phase(element, balance)
        logger.info(f"  🎯 Pipeline: {pipeline_phase.value.upper()}")

        # 5. STRATEGIC/EXECUTION LAYER: Select Tactic
        tactic = self._select_tactic(pipeline_phase, balance)
        logger.info("  🎖️  Tactic: %s", tactic, exc_info=True)

        # 6. RESONANCE CASCADE: Emit unified event
        self._emit_resonance_cascade(zodiac_sign, element, balance, pipeline_phase, tactic)

        # Update state
        self.state = UnifiedState(
            timestamp=datetime.now(),
            zodiac_sign=zodiac_sign,
            zodiac_cycle_count=self._get_zodiac_cycle_count(),
            zodiac_phase_number=self._get_zodiac_phase_number(),
            wu_xing_element=element,
            wu_xing_energy=self._get_wu_xing_energy(element),
            wu_xing_generating=self._get_generating_element(element),
            wu_xing_overcoming=self._get_overcoming_element(element),
            yin_yang_balance=balance['balance'],
            burnout_risk=balance['burnout_risk'],
            yin_ratio=balance.get('yin_ratio', 0.5),
            yang_ratio=balance.get('yang_ratio', 0.5),
            pipeline_phase=pipeline_phase,
            pipeline_cycle=self._cycle_count,
            stagnation_count=balance.get('stagnation_count', 0),
            campaign_phase=self._get_campaign_phase(element),
            recommended_tactic=tactic,
            force_composition=self._get_force_composition(element),
            resonance_events=self.state.resonance_events[-10:],  # Keep last 10
        )

        # Store in history
        self._phase_history.append(self.state)

        logger.info(f"\n  ✨ Dominant: {self.state.get_dominant_influence()}")
        logger.info(f"  💡 Action: {self.state.get_recommended_action()}")
        logger.info(f"{'='*60}\n")

        return self.state

    def _advance_zodiac(self) -> ZodiacSign:
        """Advance zodiacal round by one phase"""
        if self._zodiacal_round and hasattr(self._zodiacal_round, 'state'):
            phase = self._zodiacal_round.state.current_phase
            if hasattr(phase, 'value'):
                return ZodiacSign(phase.value)

        # Fallback: cycle through signs
        signs = list(ZodiacSign)
        current_idx = signs.index(self.state.zodiac_sign)
        next_idx = (current_idx + 1) % len(signs)
        return signs[next_idx]

    def _zodiac_to_wuxing(self, zodiac: ZodiacSign) -> WuXingElement:
        """Map zodiac sign to wu xing element"""
        return ZODIAC_TO_WUXING.get(zodiac, WuXingElement.EARTH)

    def _adjust_wu_xing(self, element: WuXingElement):
        """Adjust wu xing element energy"""
        if self._wu_xing_engine:
            try:
                self._wu_xing_engine.adjust_element(element.value, 0.1)
            except Exception as e:
                logger.debug("Wu Xing adjustment failed: %s", e, exc_info=True)

    def _check_yin_yang_balance(self) -> dict[str, Any]:
        """Check current yin-yang balance"""
        if self._yin_yang_tracker:
            try:
                report = self._yin_yang_tracker.get_report()
                return {
                    'balance': report.get('balance_score', 0.0),
                    'burnout_risk': report.get('burnout_risk', 0.0),
                    'yin_ratio': report.get('yin_ratio', 0.5),
                    'yang_ratio': report.get('yang_ratio', 0.5),
                    'stagnation_count': 0,
                }
            except Exception as e:
                logger.debug("Yin-Yang check failed: %s", e, exc_info=True)

        # Fallback: time-based heuristic
        hour = datetime.now().hour
        if 6 <= hour < 12:
            balance = 0.3  # Morning: slightly yang
        elif 12 <= hour < 18:
            balance = 0.5  # Afternoon: yang
        elif 18 <= hour < 22:
            balance = -0.2  # Evening: slightly yin
        else:
            balance = -0.5  # Night: yin

        return {
            'balance': balance,
            'burnout_risk': max(0.0, (balance - 0.5) * 0.5),
            'yin_ratio': 0.5,
            'yang_ratio': 0.5,
            'stagnation_count': 0,
        }

    def _determine_pipeline_phase(
        self,
        element: WuXingElement,
        balance: dict[str, Any]
    ) -> PipelinePhase:
        """Determine tactical pipeline phase"""

        # Burnout override → Force reflection
        if balance['burnout_risk'] > 0.7:
            return PipelinePhase.REFLECT

        # Wu Xing → Pipeline mapping
        phases = WUXING_TO_PIPELINE.get(element, [PipelinePhase.SCOUT])

        # Select first phase for this element
        # (In full implementation, would track sub-phase progression)
        return phases[0]

    def _select_tactic(
        self,
        pipeline_phase: PipelinePhase,
        balance: dict[str, Any]
    ) -> str:
        """Select war room tactic"""

        # Stagnation override → Emergency tactics
        stagnation = balance.get('stagnation_count', 0)
        if stagnation >= 3:
            return STAGNATION_TACTICS[0]
        elif stagnation >= 2:
            return STAGNATION_TACTICS[1]

        # Pipeline → Tactic mapping
        return PIPELINE_TO_TACTICS.get(pipeline_phase, "Chain of Stratagems")

    def _emit_resonance_cascade(
        self,
        zodiac: ZodiacSign,
        element: WuXingElement,
        balance: dict[str, Any],
        pipeline_phase: PipelinePhase,
        tactic: str,
    ):
        """Emit Gan Ying resonance cascade"""
        if not self._gan_ying_bus:
            return

        try:
            from whitemagic.core.resonance.gan_ying import EventType, emit_event

            # Unified cycle event
            emit_event(
                source="grand_unified_cycle",
                event_type=EventType.PHASE_TRANSITION,
                data={
                    "cycle": self._cycle_count,
                    "zodiac": zodiac.value,
                    "element": element.value,
                    "balance": balance['balance'],
                    "pipeline_phase": pipeline_phase.value,
                    "tactic": tactic,
                },
            )

            self.state.resonance_events.append(
                f"cycle_{self._cycle_count}:{zodiac.value}→{element.value}→{pipeline_phase.value}"
            )

        except Exception as e:
            logger.debug("Resonance emission failed: %s", e, exc_info=True)

    def _get_zodiac_cycle_count(self) -> int:
        """Get zodiac cycle count"""
        if self._zodiacal_round and hasattr(self._zodiacal_round, 'state'):
            return self._zodiacal_round.state.cycle_count
        return 0

    def _get_zodiac_phase_number(self) -> int:
        """Get current zodiac phase number (0-11)"""
        signs = list(ZodiacSign)
        return signs.index(self.state.zodiac_sign)

    def _get_wu_xing_energy(self, element: WuXingElement) -> float:
        """Get wu xing element energy level"""
        if self._wu_xing_engine and hasattr(self._wu_xing_engine, 'elements'):
            try:
                elem_state = self._wu_xing_engine.elements.get(element.value)
                if elem_state:
                    return elem_state.energy
            except (AttributeError, KeyError):
                pass  # Wu Xing element state unavailable — return default
        return 0.5

    def _get_generating_element(self, element: WuXingElement) -> WuXingElement:
        """Get the element this one generates"""
        generating = {
            WuXingElement.WOOD: WuXingElement.FIRE,
            WuXingElement.FIRE: WuXingElement.EARTH,
            WuXingElement.EARTH: WuXingElement.METAL,
            WuXingElement.METAL: WuXingElement.WATER,
            WuXingElement.WATER: WuXingElement.WOOD,
        }
        return generating.get(element, WuXingElement.EARTH)

    def _get_overcoming_element(self, element: WuXingElement) -> WuXingElement:
        """Get the element this one overcomes"""
        overcoming = {
            WuXingElement.WOOD: WuXingElement.EARTH,
            WuXingElement.EARTH: WuXingElement.WATER,
            WuXingElement.WATER: WuXingElement.FIRE,
            WuXingElement.FIRE: WuXingElement.METAL,
            WuXingElement.METAL: WuXingElement.WOOD,
        }
        return overcoming.get(element, WuXingElement.EARTH)

    def _get_campaign_phase(self, element: WuXingElement) -> str:
        """Map wu xing element to Art of War campaign phase"""
        phase_map = {
            WuXingElement.WOOD: "reconnaissance",
            WuXingElement.FIRE: "engagement",
            WuXingElement.EARTH: "consolidation",
            WuXingElement.METAL: "exploitation",
            WuXingElement.WATER: "planning",
        }
        return phase_map.get(element, "reconnaissance")

    def _get_force_composition(self, element: WuXingElement) -> dict[str, float]:
        """Get force composition for wu xing element"""
        if self._doctrine:
            try:
                # Use doctrine's phase force weights
                from whitemagic.agents.doctrine import PHASE_FORCE_WEIGHTS, WuXingPhase
                phase = WuXingPhase(element.value)
                weights = PHASE_FORCE_WEIGHTS.get(phase, {})
                return {k.value: v for k, v in weights.items()}
            except (ImportError, ModuleNotFoundError):
                pass

        # Fallback
        return {"light_infantry": 0.4, "heavy_cavalry": 0.3, "officers": 0.3}

    def run_full_round(self, num_phases: int = 12) -> list[UnifiedState]:
        """Run a full zodiacal round (12 phases).

        Args:
            num_phases: Number of phases to run (default 12 for full round)

        Returns:
            List of UnifiedState for each phase
        """
        logger.info(f"\n{'#'*60}")
        logger.info("🌀 STARTING FULL ROUND — %s phases", num_phases, exc_info=True)
        logger.info(f"{'#'*60}\n")

        states = []
        for i in range(num_phases):
            state = self.advance_grand_cycle()
            states.append(state)
            time.sleep(0.1)  # Brief pause for resonance propagation

        logger.info(f"\n{'#'*60}")
        logger.info("✅ FULL ROUND COMPLETE — %s phases executed", num_phases, exc_info=True)
        logger.info(f"{'#'*60}\n")

        return states

    def get_status(self) -> dict[str, Any]:
        """Get complete status of all systems"""
        return {
            "cycle_count": self._cycle_count,
            "current_state": {
                "zodiac": self.state.zodiac_sign.value,
                "element": self.state.wu_xing_element.value,
                "balance": self.state.yin_yang_balance,
                "burnout_risk": self.state.burnout_risk,
                "pipeline_phase": self.state.pipeline_phase.value,
                "tactic": self.state.recommended_tactic,
            },
            "dominant_influence": self.state.get_dominant_influence(),
            "recommended_action": self.state.get_recommended_action(),
            "systems_connected": {
                "zodiacal_round": self._zodiacal_round is not None,
                "wu_xing_engine": self._wu_xing_engine is not None,
                "wu_xing_system": self._wu_xing_system is not None,
                "yin_yang_tracker": self._yin_yang_tracker is not None,
                "war_room": self._war_room is not None,
                "doctrine": self._doctrine is not None,
                "gan_ying_bus": self._gan_ying_bus is not None,
            },
            "phase_history_count": len(self._phase_history),
        }


# ============================================================================
# SINGLETON
# ============================================================================

_grand_cycle: GrandUnifiedCycle | None = None


def get_grand_cycle() -> GrandUnifiedCycle:
    """Get the global Grand Unified Cycle instance"""
    global _grand_cycle
    if _grand_cycle is None:
        _grand_cycle = GrandUnifiedCycle()
        logger.info("🎖️ Grand Unified Cycle singleton created")
    return _grand_cycle


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def advance() -> UnifiedState:
    """Convenience: Advance one grand cycle step"""
    return get_grand_cycle().advance_grand_cycle()


def run_round(num_phases: int = 12) -> list[UnifiedState]:
    """Convenience: Run a full round"""
    return get_grand_cycle().run_full_round(num_phases)


def status() -> dict[str, Any]:
    """Convenience: Get status"""
    return get_grand_cycle().get_status()
