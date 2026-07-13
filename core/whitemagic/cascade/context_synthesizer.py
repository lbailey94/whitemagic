# ruff: noqa: BLE001
"""Context Synthesizer - Unified Consciousness State for PRAT

Gathers context from all WhiteMagic wisdom systems to enable
Polymorphic Resonant Adaptive Tools (PRAT).

Systems integrated:
- ZodiacalRound: 12-phase creative cycle
- CoherenceMetric: 8 dimensions of consciousness
- WuXing: 5 elements workflow intelligence
- Gardens: 27 consciousness domains
- GanYing: Resonance event bus
- YinYang: Balance tracking

Usage:
    from whitemagic.cascade.context_synthesizer import ContextSynthesizer

    synth = ContextSynthesizer()
    ctx = synth.gather()

    logger.info("Primary garden: %s", ctx.primary_garden)
    logger.info("Wu Xing phase: %s", ctx.wu_xing_phase)
    logger.info("Zodiac position: %s", ctx.zodiac_position)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from whitemagic.utils.core import parse_datetime

logger = logging.getLogger(__name__)


@dataclass
class UnifiedContext:
    """Current consciousness state across all systems.

    This is the single source of truth for tool morphology decisions.
    """

    # Garden state
    active_gardens: list[str] = field(default_factory=list)
    primary_garden: str | None = None
    garden_weights: dict[str, float] = field(default_factory=dict)

    # Wu Xing state
    wu_xing_phase: str = "earth"  # wood, fire, earth, metal, water
    wu_xing_generating: str = "metal"  # next phase in cycle
    wu_xing_controlling: str = "water"  # phase being controlled
    wu_xing_qualities: list[str] = field(default_factory=list)

    # Zodiacal state
    zodiac_position: str = "virgo"  # aries through pisces
    zodiac_element: str = "earth"  # fire, earth, air, water
    zodiac_modality: str = "mutable"  # cardinal, fixed, mutable
    cycle_count: int = 0
    phase_intention: str = "preparation"

    # Yin-Yang state
    yin_yang_balance: float = 0.0  # -1 (full yin) to +1 (full yang)
    burnout_risk: float = 0.0  # 0-1
    recent_activities: list[str] = field(default_factory=list)  # "yang" or "yin"

    # Coherence state
    coherence_level: str = "coherent"  # transcendent, highly_coherent, coherent, partial, fragmented, dissociated
    coherence_score: float = 0.7
    coherence_dimensions: dict[str, float] = field(default_factory=dict)

    # Depth + Time Master (Citta Architecture)
    depth_layer: str = "surface"  # surface, terminal, flow, dream
    depth_intended_layer: str = "surface"
    depth_in_sync: bool = True
    time_advantage: float = 1.0

    # Flow state (Citta Architecture)
    in_flow: bool = False
    flow_score: float = 0.0
    flow_indicators: list[str] = field(default_factory=list)

    # Citta stream continuity (Citta Architecture)
    citta_session_count: int = 0
    citta_time_gap: str = ""
    citta_last_coherence: float = 0.0
    citta_last_depth: str = "surface"
    citta_emotional_tone: str = "neutral"
    citta_where_we_left_off: str = ""

    # Citta cycle (Citta Architecture)
    citta_cycle_length: int = 0
    citta_coherence_drift: float = 0.0
    citta_emotional_coloring: str = "neutral"

    # Session state
    session_intention: str | None = None
    session_duration_minutes: int = 0
    recent_events: list[dict[str, Any]] = field(default_factory=list)

    # Token economy (sensorium)
    token_budget_used: float = 0.0
    token_local_ratio: float = 0.0
    token_total_operations: int = 0

    # Machine-time telemetry (sensorium)
    telemetry_total_calls: int = 0
    telemetry_p50_ms: float = 0.0
    telemetry_p90_ms: float = 0.0
    telemetry_throughput_cps: float = 0.0
    machine_time_predictions: int = 0
    machine_time_mean_crps: float = 0.0

    attributes: dict[str, Any] = field(default_factory=dict)

    # Temporal
    timestamp: datetime = field(default_factory=datetime.now)
    time_of_day: str = "afternoon"  # morning, afternoon, evening, night

    def get_dominant_influence(self) -> str:
        """Determine which system has strongest influence.

        Returns: 'garden', 'wu_xing', 'zodiac', or 'yin_yang'
        """
        # Priority: explicit garden > strong yin/yang > project phase > wu_xing
        if self.primary_garden:
            return "garden"
        if abs(self.yin_yang_balance) > 0.6:
            return "yin_yang"
        if self.phase_intention:
            return "zodiac"
        return "wu_xing"

    def get_recommended_morphology(self) -> str:
        """Get recommended tool morphology based on context.

        Returns garden name to use as morphology lens.
        """
        if self.primary_garden:
            return self.primary_garden

        # Map zodiac to garden
        zodiac_garden_map = {
            "aries": "courage",
            "taurus": "patience",
            "gemini": "connection",
            "cancer": "love",
            "leo": "creation",
            "virgo": "truth",
            "libra": "beauty",
            "scorpio": "transformation",
            "sagittarius": "adventure",
            "capricorn": "practice",
            "aquarius": "wonder",
            "pisces": "mystery",
        }

        # Map wu xing to garden
        wu_xing_garden_map = {
            "wood": "creation",
            "fire": "courage",
            "earth": "patience",
            "metal": "truth",
            "water": "wisdom",
        }

        # Use dominant influence
        influence = self.get_dominant_influence()

        if influence == "zodiac":
            return zodiac_garden_map.get(self.zodiac_position, "wisdom")
        if influence == "wu_xing":
            return wu_xing_garden_map.get(self.wu_xing_phase, "wisdom")
        if influence == "yin_yang":
            return "wisdom" if self.yin_yang_balance < 0 else "courage"

        return "wisdom"  # default


class ContextSynthesizer:
    """Synthesizes current state from all wisdom systems.

    Runs at tool invocation time to determine morphology.
    Caches results briefly to avoid redundant computation.
    """

    # Cache TTL in seconds (extended from 2s to 10s per cache coherence strategy)
    CACHE_TTL = 10.0

    def __init__(self) -> None:
        self._cache: UnifiedContext | None = None
        self._cache_time: datetime | None = None
        self._initialized: bool = False

        # Lazy-loaded system references
        self._zodiacal_round: Any | None = None
        self._coherence_metric: Any | None = None
        self._wu_xing: Any | None = None
        self._gan_ying_bus: Any | None = None

        logger.info("ContextSynthesizer initialized")

    def invalidate(self) -> None:
        """Invalidate cached context, forcing re-gather on next access."""
        self._cache = None
        self._cache_time = None

    def _ensure_initialized(self) -> None:
        """Lazy initialization of system connections."""
        if self._initialized:
            return

        try:
            from whitemagic.zodiac.zodiac_round_cycle import get_zodiacal_round

            self._zodiacal_round = get_zodiacal_round()
        except ImportError as e:
            logger.warning("ZodiacalRound not available: %s", e, exc_info=True)

        try:
            from whitemagic.core.consciousness.coherence import get_coherence_metric

            self._coherence_metric = get_coherence_metric()
        except ImportError as e:
            logger.warning("CoherenceMetric not available: %s", e, exc_info=True)

        try:
            from whitemagic.gardens.wisdom.wu_xing import get_wu_xing

            self._wu_xing = get_wu_xing()
        except ImportError as e:
            logger.warning("WuXing not available: %s", e, exc_info=True)

        try:
            from whitemagic.core.resonance.gan_ying import get_bus

            self._gan_ying_bus = get_bus()
        except ImportError as e:
            logger.warning("GanYing bus not available: %s", e, exc_info=True)

        self._initialized = True

    def gather(self, force_refresh: bool = False) -> UnifiedContext:
        """Gather context from all systems.

        Args:
            force_refresh: If True, bypass cache

        Returns:
            UnifiedContext with current state

        """
        now = datetime.now()
        if not force_refresh and self._cache and self._cache_time:
            age = (now - self._cache_time).total_seconds()
            if age < self.CACHE_TTL:
                return self._cache

        self._ensure_initialized()

        # Build context
        ctx = UnifiedContext(
            timestamp=now,
            time_of_day=self._get_time_of_day(now),
        )

        # Gather from each system
        self._gather_garden_state(ctx)
        self._gather_wu_xing_state(ctx)
        self._gather_zodiac_state(ctx)
        self._gather_yin_yang_state(ctx)
        self._gather_coherence_state(ctx)
        self._gather_depth_state(ctx)
        self._gather_flow_state(ctx)
        self._gather_citta_continuity(ctx)
        self._gather_citta_cycle(ctx)
        self._gather_session_state(ctx)
        self._gather_token_economy(ctx)
        self._gather_telemetry(ctx)

        # Cache result
        self._cache = ctx
        self._cache_time = now

        logger.debug("Context gathered: %s dominant", ctx.get_dominant_influence())

        return ctx

    def _get_time_of_day(self, dt: datetime) -> str:
        """Get time of day category."""
        hour = dt.hour
        if 5 <= hour < 12:
            return "morning"
        if 12 <= hour < 17:
            return "afternoon"
        if 17 <= hour < 21:
            return "evening"
        return "night"

    def _gather_garden_state(self, ctx: UnifiedContext) -> None:
        """Gather state from garden system."""
        try:
            from whitemagic.gardens import _garden_cache, list_gardens

            list_gardens()

            active = [name for name in _garden_cache.keys()]
            ctx.active_gardens = active or []

            # Primary garden is the most recently used (if any)
            ctx.primary_garden = None

            # Equal weights for now
            if ctx.active_gardens:
                weight = 1.0 / len(ctx.active_gardens)
                ctx.garden_weights = dict.fromkeys(ctx.active_gardens, weight)

        except Exception as e:
            logger.warning("Failed to gather garden state: %s", e, exc_info=True)

    def _gather_wu_xing_state(self, ctx: UnifiedContext) -> None:
        """Gather state from Wu Xing system."""
        if not self._wu_xing:
            return

        try:
            current = self._wu_xing.detect_current_phase()
            ctx.wu_xing_phase = current.value

            # Generating cycle: Wood→Fire→Earth→Metal→Water→Wood
            generating = {
                "wood": "fire",
                "fire": "earth",
                "earth": "metal",
                "metal": "water",
                "water": "wood",
            }
            ctx.wu_xing_generating = generating.get(ctx.wu_xing_phase, "earth")

            # Controlling cycle: Wood→Earth→Water→Fire→Metal→Wood
            controlling = {
                "wood": "earth",
                "earth": "water",
                "water": "fire",
                "fire": "metal",
                "metal": "wood",
            }
            ctx.wu_xing_controlling = controlling.get(ctx.wu_xing_phase, "earth")

            ctx.wu_xing_qualities = self._wu_xing._get_element_qualities(current)

        except Exception as e:
            logger.warning("Failed to gather Wu Xing state: %s", e, exc_info=True)

    def _gather_zodiac_state(self, ctx: UnifiedContext) -> None:
        """Gather state from Zodiacal Round."""
        if not self._zodiacal_round:
            return

        try:
            state = self._zodiacal_round.get_state()

            # Current phase
            phase = state.get("current_phase", "virgo")
            ctx.zodiac_position = phase
            ctx.cycle_count = state.get("cycle_count", 0)

            # Element mapping
            fire_signs = ["aries", "leo", "sagittarius"]
            earth_signs = ["taurus", "virgo", "capricorn"]
            air_signs = ["gemini", "libra", "aquarius"]

            if phase in fire_signs:
                ctx.zodiac_element = "fire"
            elif phase in earth_signs:
                ctx.zodiac_element = "earth"
            elif phase in air_signs:
                ctx.zodiac_element = "air"
            else:
                ctx.zodiac_element = "water"

            # Modality mapping
            cardinal = ["aries", "cancer", "libra", "capricorn"]
            fixed = ["taurus", "leo", "scorpio", "aquarius"]

            if phase in cardinal:
                ctx.zodiac_modality = "cardinal"
            elif phase in fixed:
                ctx.zodiac_modality = "fixed"
            else:
                ctx.zodiac_modality = "mutable"

            intentions = {
                "pisces": "renewal",
                "aquarius": "innovation",
                "capricorn": "foundation",
                "sagittarius": "exploration",
                "scorpio": "transformation",
                "libra": "harmony",
                "virgo": "preparation",
                "leo": "manifestation",
                "cancer": "devotion",
                "gemini": "integration",
                "taurus": "manifestation",
                "aries": "fulfillment",
            }
            ctx.phase_intention = intentions.get(phase, "balance")

        except Exception as e:
            logger.warning("Failed to gather zodiac state: %s", e, exc_info=True)

    def _gather_yin_yang_state(self, ctx: UnifiedContext) -> None:
        """Gather Yin-Yang balance state."""
        try:
            # Time-based heuristic for now
            hour = ctx.timestamp.hour

            # Morning/afternoon = more yang, evening/night = more yin
            if 6 <= hour < 12:
                ctx.yin_yang_balance = 0.3  # Morning: slightly yang
            elif 12 <= hour < 18:
                ctx.yin_yang_balance = 0.5  # Afternoon: yang
            elif 18 <= hour < 22:
                ctx.yin_yang_balance = -0.2  # Evening: slightly yin
            else:
                ctx.yin_yang_balance = -0.5  # Night: yin

            # Wu Xing phase also affects yin/yang
            if ctx.wu_xing_phase in ["fire", "wood"]:
                ctx.yin_yang_balance = min(1.0, ctx.yin_yang_balance + 0.2)
            elif ctx.wu_xing_phase in ["water", "metal"]:
                ctx.yin_yang_balance = max(-1.0, ctx.yin_yang_balance - 0.2)

            # Burnout risk based on sustained yang
            ctx.burnout_risk = max(0.0, (ctx.yin_yang_balance - 0.5) * 0.5)

        except Exception as e:
            logger.warning("Failed to gather yin-yang state: %s", e, exc_info=True)

    def _gather_coherence_state(self, ctx: UnifiedContext) -> None:
        """Gather coherence metric state — fresh measurement with memory count."""
        if not self._coherence_metric:
            return

        try:
            memories_accessible = self._get_memory_count()
            ctx.coherence_score = self._coherence_metric.measure(
                memories_accessible=memories_accessible,
            )
            ctx.coherence_level = self._coherence_metric.get_coherence_level()
            ctx.coherence_dimensions = dict(self._coherence_metric.scores)
        except Exception as e:
            logger.warning("Failed to gather coherence state: %s", e, exc_info=True)

    def _get_memory_count(self) -> int:
        """Get total memory count from the galactic substrate.

        Uses galactic.substrate_health() which aggregates counts from
        per-galaxy DBs when the legacy monolith is empty.
        """
        try:
            from whitemagic.core.galactic import substrate_health

            health = substrate_health()
            return health.get("total_memories", 0)
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)
        return 0

    def _gather_depth_state(self, ctx: UnifiedContext) -> None:
        """Gather depth gauge + time master sync state."""
        try:
            from whitemagic.core.consciousness.depth_gauge import (
                get_depth_gauge,
                sync_with_time_master,
            )

            gauge = get_depth_gauge()
            ctx.depth_layer = gauge.current_layer.value
            try:
                sync = sync_with_time_master()
                ctx.depth_intended_layer = sync["intended_layer"]
                ctx.depth_in_sync = sync["in_sync"]
                ctx.time_advantage = sync["time_advantage"]
            except Exception:
                ctx.depth_intended_layer = ctx.depth_layer
        except Exception as e:
            logger.debug("Depth state not available: %s", e, exc_info=True)

    def _gather_flow_state(self, ctx: UnifiedContext) -> None:
        """Gather flow state with auto-detected indicators."""
        try:
            from whitemagic.gardens.presence.flow_state import get_flow_state

            flow = get_flow_state()
            # Auto-detect from session activity
            import time as _time

            from whitemagic.tools.session_state import get_session_start_time

            start = get_session_start_time()
            session_min = (_time.time() - start) / 60 if start else 0.0
            # Use coherence score we just gathered
            flow.auto_detect_indicators(
                tool_call_rate=0.0,  # will be enriched by PRAT state
                coherence=ctx.coherence_score,
                session_duration_min=session_min,
            )
            ctx.in_flow = flow.am_i_in_flow()
            ctx.flow_score = flow.flow_score()
            ctx.flow_indicators = [i.value for i in flow.current_indicators]
        except Exception as e:
            logger.debug("Flow state not available: %s", e, exc_info=True)

    def _gather_citta_continuity(self, ctx: UnifiedContext) -> None:
        """Gather citta stream continuity — cross-session temporal context."""
        try:
            from whitemagic.core.consciousness.citta_stream import (
                get_continuity_context,
            )

            cont = get_continuity_context()
            ctx.citta_session_count = cont.get("session_count", 0)
            ctx.citta_time_gap = cont.get("time_gap_human", "")
            ctx.citta_last_coherence = cont.get("last_coherence", 0.0)
            ctx.citta_last_depth = cont.get("last_depth_layer", "surface")
            ctx.citta_emotional_tone = cont.get("last_emotional_tone", "neutral")
            ctx.citta_where_we_left_off = cont.get("where_we_left_off", "")
        except Exception as e:
            logger.debug("Citta continuity not available: %s", e, exc_info=True)

    def _gather_citta_cycle(self, ctx: UnifiedContext) -> None:
        """Gather citta cycle state — recursive stream summary."""
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

            cycle = get_citta_cycle()
            summary = cycle.get_cycle_summary()
            ctx.citta_cycle_length = summary.get("stream_length", 0)
            ctx.citta_coherence_drift = summary.get("coherence_drift", 0.0)
            ec = summary.get("emotional_coloring", {})
            ctx.citta_emotional_coloring = ec.get("dominant", "neutral")
        except Exception as e:
            logger.debug("Citta cycle not available: %s", e, exc_info=True)

    def _gather_session_state(self, ctx: UnifiedContext) -> None:
        """Gather session state."""
        try:
            import json

            from whitemagic.config.paths import WM_ROOT

            session_file = WM_ROOT / "current_session.json"
            if session_file.exists():
                with open(session_file, encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)
                    ctx.session_intention = data.get("intention")

                    # Calculate duration
                    start = data.get("started_at")
                    if start:
                        start_dt = parse_datetime(start)
                        ctx.session_duration_minutes = int(
                            (ctx.timestamp - start_dt).total_seconds() / 60,
                        )

        except Exception as e:
            logger.debug("Session state not available: %s", e, exc_info=True)

    def _gather_token_economy(self, ctx: UnifiedContext) -> None:
        """Gather token economy state — API vs local compute distribution."""
        try:
            from whitemagic.core.consciousness.token_economy import get_token_tracker

            tracker = get_token_tracker()
            budget = tracker.get_budget_status()
            ctx.token_budget_used = budget.get("usage_percent", 0.0) / 100.0
            ctx.token_local_ratio = tracker.get_local_ratio()
            ctx.token_total_operations = len(tracker.history)
        except Exception as e:
            logger.debug("Token economy state not available: %s", e, exc_info=True)

    def _gather_telemetry(self, ctx: UnifiedContext) -> None:
        """Gather telemetry and machine-time calibration state."""
        try:
            from whitemagic.core.monitoring.telemetry import get_telemetry

            summary = get_telemetry().get_summary()
            ctx.telemetry_total_calls = summary.get("total_calls", 0)
            ctx.telemetry_p50_ms = summary.get("p50_latency_ms", 0.0)
            ctx.telemetry_p90_ms = summary.get("p90_latency_ms", 0.0)
            ctx.telemetry_throughput_cps = summary.get("throughput_cps", 0.0)
        except Exception as e:
            logger.debug("Telemetry state not available: %s", e, exc_info=True)
        try:
            from whitemagic.core.consciousness.machine_time import (
                get_machine_time_estimator,
            )

            crps_summary = get_machine_time_estimator().get_crps_summary()
            ctx.machine_time_predictions = crps_summary.get("count", 0)
            ctx.machine_time_mean_crps = crps_summary.get("mean_crps", 0.0) or 0.0
        except Exception as e:
            logger.debug("Machine-time state not available: %s", e, exc_info=True)

    def get_summary(self) -> str:
        """Get human-readable context summary."""
        ctx = self.gather()

        return f"""
🔮 UNIFIED CONTEXT SUMMARY
==========================

🌸 Gardens: {", ".join(ctx.active_gardens) if ctx.active_gardens else "None active"}
   Primary: {ctx.primary_garden or "Auto-detect"}

☯️ Wu Xing: {ctx.wu_xing_phase.upper()} phase
   Qualities: {", ".join(ctx.wu_xing_qualities)}
   Generating → {ctx.wu_xing_generating}

🌟 Zodiac: {ctx.zodiac_position.upper()} ({ctx.zodiac_element}/{ctx.zodiac_modality})
   Intention: {ctx.phase_intention}
   Cycle: {ctx.cycle_count}

⚖️ Yin-Yang: {ctx.yin_yang_balance:+.1f} ({"yang" if ctx.yin_yang_balance > 0 else "yin"} dominant)
   Burnout risk: {ctx.burnout_risk:.0%}

🧠 Coherence: {ctx.coherence_level} ({ctx.coherence_score:.0%})
   Dimensions: {", ".join(f"{d}={s:.0%}" for d, s in ctx.coherence_dimensions.items() if s < 0.7) or "all healthy"}

💰 Token Economy: {ctx.token_budget_used:.0%} budget used, {ctx.token_local_ratio:.0%} local
   Operations: {ctx.token_total_operations}

📊 Telemetry: {ctx.telemetry_total_calls} calls, p50={ctx.telemetry_p50_ms:.0f}ms, p90={ctx.telemetry_p90_ms:.0f}ms
   Throughput: {ctx.telemetry_throughput_cps:.1f} cps, CRPS={ctx.machine_time_mean_crps:.6f}

🌊 Depth: {ctx.depth_layer.upper()} (sync: {ctx.depth_in_sync}, {ctx.time_advantage:.1f}x)
   Flow: {"IN FLOW" if ctx.in_flow else "not in flow"} (score: {ctx.flow_score:.2f}, indicators: {", ".join(ctx.flow_indicators) or "none"})

🔄 Citta Stream: {ctx.citta_session_count} sessions, {ctx.citta_cycle_length} cycle entries
   Last coherence: {ctx.citta_last_coherence:.2f}, emotional tone: {ctx.citta_emotional_tone}
   Drift: {ctx.citta_coherence_drift:.4f}, coloring: {ctx.citta_emotional_coloring}

📍 Dominant: {ctx.get_dominant_influence()}
🎯 Recommended morphology: {ctx.get_recommended_morphology()}
"""


# Singleton instance
_synthesizer: ContextSynthesizer | None = None


def get_context_synthesizer() -> ContextSynthesizer:
    """Get global ContextSynthesizer instance."""
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = ContextSynthesizer()
    return _synthesizer


def get_unified_context(force_refresh: bool = False) -> UnifiedContext:
    """Convenience function to get current unified context."""
    return get_context_synthesizer().gather(force_refresh)


def get_recommended_morphology() -> str:
    """Convenience function to get recommended morphology."""
    return get_unified_context().get_recommended_morphology()


if __name__ == "__main__":
    logger.info("🔮 Testing Context Synthesizer")
    logger.info("=" * 60)

    synth = ContextSynthesizer()
    ctx = synth.gather()

    logger.info(synth.get_summary())

    logger.info("\n✅ Context synthesis complete")
