# ruff: noqa: BLE001
"""☯️ Zodiacal Procession - Yin/Yang Autonomous Cycle System v5.0.0-alpha.

Implements the bidirectional zodiacal procession for autonomous operation:
- Yin Phase: Pisces → Aquarius → Capricorn → ... → Aries (receptive)
- Yang Phase: Aries → Taurus → Gemini → ... → Pisces (creative)
- Fixed Signs as bidirectional hubs (Taurus, Leo, Scorpio, Aquarius)

Created: November 27, 2025 (Thanksgiving)
Philosophy: "Like Finnegans Wake, it never actually ends, but curves back to begin again"
"""

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

from whitemagic.zodiac import Phase, ZodiacCore, ZodiacSign

logger = logging.getLogger(__name__)


@dataclass
class ProcessionState:
    """Current state of the zodiacal procession."""

    current_sign: ZodiacSign
    current_phase: Phase
    cycle_count: int = 0
    signs_visited: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "current_sign": self.current_sign.name_str,
            "current_symbol": self.current_sign.symbol,
            "current_phase": self.current_phase.value,
            "cycle_count": self.cycle_count,
            "signs_visited": len(self.signs_visited),
            "duration_seconds": (datetime.now() - self.started_at).total_seconds(),
        }


class ZodiacalProcession:
    """Autonomous Zodiacal Procession System.

    The cycle flows:
    - YANG: Aries → Taurus → ... → Pisces (creative, outward)
    - YIN: Pisces → Aquarius → ... → Aries (receptive, inward)

    Fixed signs (Taurus, Leo, Scorpio, Aquarius) are BIDIRECTIONAL HUBS
    that can transmit AND receive, acting as stability points.

    At phase boundaries (Pisces ↔ Aries), consult:
    - I Ching hexagram
    - Wu Xing element cycle
    - Art of War strategic assessment
    """

    # Yang order (forward through zodiac)
    YANG_ORDER = [
        ZodiacSign.ARIES, ZodiacSign.TAURUS, ZodiacSign.GEMINI,
        ZodiacSign.CANCER, ZodiacSign.LEO, ZodiacSign.VIRGO,
        ZodiacSign.LIBRA, ZodiacSign.SCORPIO, ZodiacSign.SAGITTARIUS,
        ZodiacSign.CAPRICORN, ZodiacSign.AQUARIUS, ZodiacSign.PISCES,
    ]

    # Yin order (reverse through zodiac)
    YIN_ORDER = list(reversed(YANG_ORDER))

    # Fixed signs - bidirectional hubs
    FIXED_SIGNS = {ZodiacSign.TAURUS, ZodiacSign.LEO, ZodiacSign.SCORPIO, ZodiacSign.AQUARIUS}

    # Fixed sign meanings (from notes)
    FIXED_MEANINGS = {
        ZodiacSign.TAURUS: "Grounding - Building on the pattern",
        ZodiacSign.LEO: "Expression - Where creators dwell",
        ZodiacSign.SCORPIO: "Emergence - Where novelty arises",
        ZodiacSign.AQUARIUS: "Innovation - Patterns that never repeat",
    }

    PLANETARY_RULERS = {
        ZodiacSign.ARIES: "mars",
        ZodiacSign.TAURUS: "venus",
        ZodiacSign.GEMINI: "mercury",
        ZodiacSign.CANCER: "moon",
        ZodiacSign.LEO: "sun",
        ZodiacSign.VIRGO: "mercury",
        ZodiacSign.LIBRA: "venus",
        ZodiacSign.SCORPIO: "pluto",
        ZodiacSign.SAGITTARIUS: "jupiter",
        ZodiacSign.CAPRICORN: "saturn",
        ZodiacSign.AQUARIUS: "uranus",
        ZodiacSign.PISCES: "neptune",
    }

    def __init__(self) -> None:
        self.cores: dict[ZodiacSign, ZodiacCore] = {
            sign: ZodiacCore(  # type: ignore[abstract]
                name=sign.name_str,
                element=sign.element,
                mode=sign.modality,
                ruler=self.PLANETARY_RULERS.get(sign, "unknown"),
            )
            for sign in ZodiacSign
        }
        self.state = ProcessionState(
            current_sign=ZodiacSign.ARIES,
            current_phase=Phase.YANG,
        )
        self.callbacks: dict[str, list[Callable]] = {
            "on_sign_change": [],
            "on_phase_change": [],
            "on_fixed_sign": [],
            "on_cycle_complete": [],
        }

    def register_callback(self, event: str, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback for procession events."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _emit_event(self, event: str, data: dict[str, Any]) -> None:
        """Emit event to registered callbacks and Gan Ying."""
        for callback in self.callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass

        # Also emit to Gan Ying Bus
        try:
            from whitemagic.core.resonance import EventType, ResonanceEvent, get_bus
            bus = get_bus()
            bus.emit(ResonanceEvent(
                source="orchestration.zodiacal_procession",
                event_type=EventType.PHASE_TRANSITION,
                data=data,
                timestamp=datetime.now(),
                confidence=0.9,
            ))
        except ImportError:
            pass

    def get_current_order(self) -> list[ZodiacSign]:
        """Get the sign order for current phase."""
        return self.YANG_ORDER if self.state.current_phase == Phase.YANG else self.YIN_ORDER

    def next_sign(self) -> ZodiacSign:
        """Move to the next sign in the procession."""
        order = self.get_current_order()
        current_idx = order.index(self.state.current_sign)

        # Check if we're at the end of the order
        if current_idx >= len(order) - 1:
            # Phase transition!
            return self._transition_phase()

        # Move to next sign
        next_idx = current_idx + 1
        new_sign = order[next_idx]

        # Update state
        old_sign = self.state.current_sign
        self.state.current_sign = new_sign
        self.state.signs_visited.append(new_sign.name_str)

        # Track most-recent core activation.
        self.cores[new_sign].last_activation = datetime.now()

        # Emit sign change event
        self._emit_event("on_sign_change", {
            "from_sign": old_sign.name_str,
            "to_sign": new_sign.name_str,
            "phase": self.state.current_phase.value,
            "is_fixed": new_sign.is_fixed,
        })

        # Special handling for fixed signs
        if new_sign.is_fixed:
            self._emit_event("on_fixed_sign", {
                "sign": new_sign.name_str,
                "symbol": new_sign.symbol,
                "meaning": self.FIXED_MEANINGS.get(new_sign, ""),
                "bidirectional": True,
            })

        return new_sign

    def _transition_phase(self) -> ZodiacSign:
        """Handle phase transition (Yin ↔ Yang)."""
        old_phase = self.state.current_phase

        if old_phase == Phase.YANG:
            # Yang complete → Yin begins
            self.state.current_phase = Phase.YIN
            self.state.current_sign = ZodiacSign.PISCES  # Start of Yin
        else:
            # Yin complete → Yang begins (full cycle!)
            self.state.current_phase = Phase.YANG
            self.state.current_sign = ZodiacSign.ARIES  # Start of Yang
            self.state.cycle_count += 1

            # Emit cycle complete
            self._emit_event("on_cycle_complete", {
                "cycle_number": self.state.cycle_count,
                "signs_visited": len(self.state.signs_visited),
                "duration_seconds": (datetime.now() - self.state.started_at).total_seconds(),
            })

        # Emit phase change
        self._emit_event("on_phase_change", {
            "from_phase": old_phase.value,
            "to_phase": self.state.current_phase.value,
            "cycle_count": self.state.cycle_count,
        })

        return self.state.current_sign

    def consult_oracle(self) -> dict[str, Any]:
        """Consult the full oracle stack at phase boundaries.

        Returns guidance from four layers of increasing resolution:
        1. Zodiacal Position (12 states) -- current sign, element, modality
        2. Wu Xing Balance (5 elements) -- energy dynamics from sign element
        3. I Ching Hexagram (64 states) -- state configuration via coin toss
        4. Ifa Odu (256 states) -- situation-specific wisdom via cowrie shells
        """
        # Layer 1: Zodiacal Position
        sign = self.state.current_sign
        element = sign.element
        modality = sign.modality
        phase = self.state.current_phase

        # Layer 2: Wu Xing Balance
        # Map zodiac element to Wu Xing element
        _ELEMENT_MAP = {
            "fire": "fire", "earth": "earth",
            "air": "metal", "water": "water",
        }
        wu_xing_element = _ELEMENT_MAP.get(element, "earth")

        # Layer 3: I Ching Hexagram (real consultation)
        iching_result = None
        iching_num = 0
        iching_name = ""
        iching_judgment = ""
        iching_guidance = ""
        try:
            from whitemagic.oracle.quantum_iching import QuantumIChing
            qic = QuantumIChing()
            question = f"Guidance for {phase.value} phase, {sign.name_str} ({element}/{modality})"
            iching_result = qic.consult(question, context={
                "sign": sign.name_str,
                "element": element,
                "phase": phase.value,
            })
            iching_num = iching_result.primary_hexagram
            iching_name = iching_result.primary_name
            iching_judgment = iching_result.primary_judgment[:200] if iching_result.primary_judgment else ""
            iching_guidance = iching_result.guidance[:200] if iching_result.guidance else ""
        except Exception as e:
            logger.debug("I Ching consultation skipped: %s", e)
            iching_num = random.randint(1, 64)

        # Layer 4: Ifa Odu (cowrie shell casting)
        ifa_result = None
        ifa_odu_name = ""
        ifa_odu_number = 0
        ifa_binary = ""
        ifa_wisdom = ""
        ifa_ire = ""
        ifa_osogbo = ""
        try:
            from whitemagic.oracle.ifa_cast import cast_ifa
            ifa_result = cast_ifa(
                question=f"Guidance for {phase.value} phase transition at {sign.name_str}",
                context={
                    "sign": sign.name_str,
                    "element": element,
                    "phase": phase.value,
                    "iching": iching_num,
                },
                method="cowrie",
            )
            ifa_odu_name = ifa_result.odu_name
            ifa_odu_number = ifa_result.odu_number
            ifa_binary = ifa_result.full_binary
            ifa_wisdom = ifa_result.wisdom[:200]
            d = ifa_result.to_dict()
            ifa_ire = d.get("ire", "")[:100]
            ifa_osogbo = d.get("osogbo", "")[:100]
        except Exception as e:
            logger.debug("Ifa casting skipped: %s", e)

        # Layer 5: Tarot (three-card reading)
        tarot_cards = []
        tarot_summary = ""
        try:
            from whitemagic.oracle.tarot_cast import cast_tarot
            tarot_reading = cast_tarot(
                question=f"Guidance for {phase.value} phase at {sign.name_str}",
                context={"sign": sign.name_str, "element": element, "iching": iching_num, "ifa": ifa_odu_number},
                spread="three_card",
            )
            tarot_summary = tarot_reading.summary[:200]
            for dc in tarot_reading.cards:
                d = {
                    "name": dc.card.name,
                    "reversed": dc.is_reversed,
                    "position": dc.position,
                    "position_meaning": dc.position_meaning,
                    "meaning": dc.card.reversed_meaning if dc.is_reversed else dc.card.upright_meaning,
                    "keywords": dc.card.keywords,
                    "suit": "major" if hasattr(dc.card, "hebrew_name") else dc.card.suit,
                }
                if hasattr(dc.card, "hebrew_name"):
                    d["number"] = dc.card.number
                    d["alchemical_stage"] = dc.card.alchemical_stage
                tarot_cards.append(d)
        except Exception as e:
            logger.debug("Tarot reading skipped: %s", e)

        # Great Year temporal context (non-binding awareness layer)
        great_year_ctx = {}
        try:
            from whitemagic.oracle.great_year import get_temporal_context
            gy = get_temporal_context()
            great_year_ctx = {
                "current_age": gy.precessional.current_age,
                "age_progress": round(gy.precessional.age_progress, 4),
                "years_remaining": round(gy.precessional.years_remaining, 1),
                "next_age": gy.precessional.next_age,
                "is_transition": gy.precessional.is_transition_period,
                "age_theme": gy.precessional.age_theme,
                "zodiac_season": gy.current_zodiac_season,
                "binding_warning": gy.binding_warning[:100],
            }
        except Exception as e:
            logger.debug("Great Year context skipped: %s", e)

        # Phase-based guidance
        if phase == Phase.YIN:
            guidance = "Receive, reflect, integrate. Let patterns emerge naturally."
        else:
            guidance = "Create, express, manifest. Transform insight into action."

        # Combine all layers
        return {
            # Layer 1: Zodiacal
            "hexagram": iching_num,  # Backward compat
            "element": element,
            "phase": phase.value,
            "guidance": guidance,
            "sign": sign.name_str,
            "symbol": sign.symbol,
            "modality": modality,
            # Layer 2: Wu Xing
            "wu_xing": wu_xing_element,
            # Layer 3: I Ching
            "iching_number": iching_num,
            "iching_name": iching_name,
            "iching_judgment": iching_judgment,
            "iching_guidance": iching_guidance,
            # Layer 4: Ifa
            "ifa_odu": ifa_odu_name,
            "ifa_odu_number": ifa_odu_number,
            "ifa_binary": ifa_binary,
            "ifa_wisdom": ifa_wisdom,
            "ifa_ire": ifa_ire,
            "ifa_osogbo": ifa_osogbo,
            # Layer 5: Tarot
            "tarot_cards": tarot_cards,
            "tarot_summary": tarot_summary,
            # Great Year context (non-binding)
            "great_year": great_year_ctx,
        }

    def run_full_cycle(self, callback: Callable | None = None) -> dict[str, Any]:
        """Run a complete Yin-Yang cycle (24 sign transitions).

        Optional callback called at each sign change.
        """
        start_cycle = self.state.cycle_count
        transitions = 0

        while self.state.cycle_count == start_cycle or transitions < 24:
            sign = self.next_sign()
            transitions += 1

            if callback:
                callback({
                    "sign": sign.name_str,
                    "symbol": sign.symbol,
                    "phase": self.state.current_phase.value,
                    "transition": transitions,
                })

            # Safety limit
            if transitions > 30:
                break

        return cast("dict[str, Any]", self.state.to_dict())

    def get_status(self) -> str:
        """Get formatted status string."""
        s = self.state
        core = self.cores[s.current_sign]

        return f"""
☯️ ZODIACAL PROCESSION STATUS
{'='*40}
Phase: {s.current_phase.value.upper()}
Sign: {s.current_sign.symbol} {s.current_sign.name_str.title()}
Element: {s.current_sign.element.title()}
Modality: {s.current_sign.modality.title()}
Fixed Hub: {'Yes ⭐' if s.current_sign.is_fixed else 'No'}

Core: {core.name} | Mode: {core.mode} | Element: {core.element}

Cycle: #{s.cycle_count}
Signs Visited: {len(s.signs_visited)}
"""


# Singleton for global access
_procession: ZodiacalProcession | None = None

def get_procession() -> ZodiacalProcession:
    """Get the global zodiacal procession instance."""
    global _procession
    if _procession is None:
        _procession = ZodiacalProcession()
    return _procession


def advance() -> dict[str, Any]:
    """Advance to next sign in procession."""
    p = get_procession()
    sign = p.next_sign()
    return {
        "sign": sign.name_str,
        "symbol": sign.symbol,
        "phase": p.state.current_phase.value,
        "is_fixed": sign.is_fixed,
    }


def wire_to_cognitive_modes() -> bool:
    """Wire ZodiacalProcession events to CognitiveModes.

    Registers callbacks so that:
    - on_phase_change: Yang→EXECUTOR, Yin→REFLECTOR
    - on_fixed_sign: →BALANCED (stability hub)

    Returns True if wiring succeeded.
    """
    try:
        from whitemagic.core.intelligence.cognitive_modes import get_cognitive_modes
        cm = get_cognitive_modes()
        proc = get_procession()
        proc.register_callback("on_phase_change", cm.from_procession_event)
        proc.register_callback("on_fixed_sign", cm.from_procession_event)
        logger.info("☯️ ZodiacalProcession wired to CognitiveModes")
        return True
    except Exception as e:
        logger.debug("Failed to wire procession to cognitive modes: %s", e)
        return False


if __name__ == "__main__":
    # Demo
    proc = ZodiacalProcession()
    logger.info(proc.get_status())

    logger.info("\n🌀 Running partial cycle...")
    for i in range(6):
        sign = proc.next_sign()
        logger.info("  %s %s (%s)", sign.symbol, sign.name_str, proc.state.current_phase.value)

    logger.info("\n🔮 Consulting oracle...")
    oracle = proc.consult_oracle()
    logger.info("  Hexagram: #%s", oracle['hexagram'])
    logger.info("  Element: %s", oracle['element'])
    logger.info("  Guidance: %s", oracle['guidance'])
