"""PRAT Resonance — Session-Level Gana Resonance State.
=====================================================
Manages per-session resonance context so that sequential PRAT calls
benefit from predecessor/successor awareness, lunar amplification,
and Harmony Vector adaptation.

When an AI client calls gana_ghost(tool="gnosis"), the resonance layer:
1. Looks up the predecessor Gana's output (from the last PRAT call)
2. Gets current lunar phase and Harmony Vector snapshot
3. Builds ResonanceHints and attaches them to the response
4. Stores this call's output as predecessor context for the next call

This creates implicit resonance across sequential tool invocations —
the system "remembers" what Gana was last active and feeds that
context forward, even without explicit GanaChain orchestration.
"""

import logging
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gana metadata (avoids importing heavy quadrant modules at module level)
# ---------------------------------------------------------------------------

# gana_name → (mansion_number, quadrant, meaning, garden, chinese, pinyin)
_GANA_META: dict[str, tuple] = {
    "gana_horn":             (1,  "East",  "Sharp initiation",   "Courage",        "角", "Jiao"),
    "gana_neck":             (2,  "East",  "Stability",          "Stillness",       "亢", "Kang"),
    "gana_root":             (3,  "East",  "Foundation",         "Healing",          "氐", "Di"),
    "gana_room":             (4,  "East",  "Enclosure",          "Sanctuary",      "房", "Fang"),
    "gana_heart":            (5,  "East",  "Vital pulse",        "Love",           "心", "Xin"),
    "gana_tail":             (6,  "East",  "Passionate drive",   "Courage",          "尾", "Wei"),
    "gana_winnowing_basket": (7,  "East",  "Separation",         "Wisdom",         "箕", "Ji"),
    "gana_ghost":            (8,  "South", "Introspection",      "Grief",          "鬼", "Gui"),
    "gana_willow":           (9,  "South", "Flexibility",        "Humor",           "柳", "Liu"),
    "gana_star":             (10, "South", "Illumination",       "Voice",         "星", "Xing"),
    "gana_extended_net":     (11, "South", "Connectivity",       "Sangha",     "张", "Zhang"),
    "gana_wings":            (12, "South", "Expansion",          "Beauty",      "翼", "Yi"),
    "gana_chariot":          (13, "South", "Movement",           "Adventure", "轸", "Zhen"),
    "gana_abundance":        (14, "South", "Surplus",            "Joy",            "豐", "Feng"),
    "gana_straddling_legs":  (15, "West",  "Balance",            "Awe",       "奎", "Kui"),
    "gana_mound":            (16, "West",  "Accumulation",       "Gratitude",      "娄", "Lou"),
    "gana_stomach":          (17, "West",  "Nourishment",        "Creation",        "胃", "Wei"),
    "gana_hairy_head":       (18, "West",  "Detail",             "Presence",       "昴", "Mao"),
    "gana_net":              (19, "West",  "Capture",            "Play",        "毕", "Bi"),
    "gana_turtle_beak":      (20, "West",  "Precision",          "Practice",          "觜", "Zui"),
    "gana_three_stars":      (21, "West",  "Judgment",           "Reverence",         "参", "Shen"),
    "gana_dipper":           (22, "North", "Governance",         "Dharma",            "斗", "Dou"),
    "gana_ox":               (23, "North", "Endurance",          "Patience",      "牛", "Niu"),
    "gana_girl":             (24, "North", "Nurture",            "Connection",         "女", "Nu"),
    "gana_void":             (25, "North", "Emptiness",          "Mystery",      "虚", "Xu"),
    "gana_roof":             (26, "North", "Shelter",            "Protection",     "危", "Wei"),
    "gana_encampment":       (27, "North", "Structure",          "Transformation",         "室", "Shi"),
    "gana_wall":             (28, "North", "Boundaries",         "Truth",            "壁", "Bi"),
}

# Ordered list for predecessor/successor lookup
_GANA_ORDER = [
    "gana_horn", "gana_neck", "gana_root", "gana_room", "gana_heart",
    "gana_tail", "gana_winnowing_basket", "gana_ghost", "gana_willow",
    "gana_star", "gana_extended_net", "gana_wings", "gana_chariot",
    "gana_abundance", "gana_straddling_legs", "gana_mound", "gana_stomach",
    "gana_hairy_head", "gana_net", "gana_turtle_beak", "gana_three_stars",
    "gana_dipper", "gana_ox", "gana_girl", "gana_void", "gana_roof",
    "gana_encampment", "gana_wall",
]

_GANA_INDEX = {name: i for i, name in enumerate(_GANA_ORDER)}


def _get_predecessor_gana(gana_name: str) -> str:
    """Get the predecessor Gana in the circular 28-mansion sequence."""
    idx = _GANA_INDEX.get(gana_name, 0)
    return _GANA_ORDER[(idx - 1) % 28]


def _get_successor_gana(gana_name: str) -> str:
    """Get the successor Gana in the circular 28-mansion sequence."""
    idx = _GANA_INDEX.get(gana_name, 0)
    return _GANA_ORDER[(idx + 1) % 28]


def _get_meta(gana_name: str) -> dict[str, Any]:
    """Get metadata dict for a Gana."""
    meta = _GANA_META.get(gana_name)
    if not meta:
        return {"mansion_num": 0, "quadrant": "Unknown", "meaning": gana_name,
                "garden": None, "chinese": "?", "pinyin": "?"}
    return {
        "mansion_num": meta[0],
        "quadrant": meta[1],
        "meaning": meta[2],
        "garden": meta[3],
        "chinese": meta[4],
        "pinyin": meta[5],
    }


# Tool → actionable next-step hint. Maps the most common tools to a
# short, useful suggestion. Default fallback for unmapped tools is
# "system healthy" if the output looks like success, otherwise generic.
_TOOL_ACTION_HINTS: dict[str, str] = {
    # search/recall family
    "search_memories": "Use read_memory to inspect top result, or hybrid_recall to filter",
    "vector.search": "Use read_memory to inspect the matched memory",
    "hybrid_recall": "Use read_memory to inspect the top result",
    "graph_walk": "Use gan.a_chariot (kg.query) to follow cross-references",
    "list_memories": "Use vector.search or gan.a_winnowing_basket (search_memories) to retrieve",
    "read_memory": "Use gan.a_neck (update_memory) to refine, or gan.a_three_stars (kaizen_analyze) to summarize",
    # memory ops
    "create_memory": "Use gan.a_horn to set up session context, or gan.a_three_stars (kaizen_analyze) to summarize",
    "update_memory": "Use gan.a_three_stars (kaizen_analyze) to verify integrity",
    "delete_memory": "Be careful: deletion is permanent. Verify with gan.a_void (galactic.dashboard) first",
    "import_memories": "Use gan.a_three_stars (kaizen_analyze) to summarize the imported set",
    # governance / ethics
    "evaluate_ethics": "Use harmony_vector to see which dimensions were affected",
    "check_boundaries": "Use governor_validate to confirm the action is allowed",
    "verify_consent": "Use karma_record to log the consent decision",
    "harmony_vector": "If score is low, run homeostasis.check to trigger auto-correction",
    "karma_record": "Use gan.a_hairy_head (karmic_trace) to inspect the trace",
    "karma_report": "Use gan.a_straddling_legs (evaluate_ethics) to interpret findings",
    "governor_validate": "If rejected, use gan.a_star (dharma.reload) to inspect the rule",
    "dharma.reload": "Use gan.a_straddling_legs (evaluate_ethics) to see which rules apply",
    # introspection / health
    "gnosis": "Use gan.a_ghost (capability.matrix) to see the full surface",
    "capability.matrix": "Use gan.a_ghost (list_ganas) for a focused 28-Gana view",
    "manifest": "Use gan.a_ghost (capabilities) for a shorter capability summary",
    "state.paths": "Use gan.a_mound (track_metric) to monitor state over time",
    "state.summary": "Use gan.a_root (health_report) for actionable health checks",
    "ship.check": "Address any FAIL items before publishing",
    "health_report": "Use gan.a_dipper (homeostasis) to trigger auto-correction if degraded",
    "selfmodel.forecast": "Use gan.a_mound (view_hologram) to verify state trajectory",
    # system / deployment
    "dream": "Use gan.a_abundance (memory.lifecycle) to verify consolidation",
    "export_memories": "Use gan.a_wings (audit.export) to also export audit log",
    "mesh.broadcast": "Use gan.a_wings (mesh.status) to verify delivery",
    "homeostasis": "Use gan.a_dipper (maturity.assess) to verify stage progression",
    "maturity.assess": "Use gan.a_horn (session_bootstrap) to start the next stage",
    "salience.spotlight": "Use gan.a_hairy_head (otel) for full observability",
    "anomaly": "Use gan.a_dipper (homeostasis) to trigger corrective actions",
    "rate_limiter.stats": "If at capacity, use gan.a_willow (grimoire_cast) to find lighter-weight tools",
    "archive": "Use gan.a_void (galactic.dashboard) to confirm archival succeeded",
    "view_hologram": "Use gan.a_mound (track_metric) to also log the access",
}


def _actionable_successor_hint(
    gana_name: str,
    tool_name: str | None,
    operation: str | None,
    preview: str,
) -> str:
    """Generate an actionable next-step hint from the tool that was called.

    Returns a short, concrete suggestion the agent can act on — instead
    of astrology-style "Prepared for Liu in Aries" prose.
    """
    if tool_name and tool_name in _TOOL_ACTION_HINTS:
        return _TOOL_ACTION_HINTS[tool_name]
    # Operation-based fallback
    if operation == "search":
        return "Use read_memory to inspect the result"
    if operation == "analyze":
        return "Use gan.a_three_stars (kaizen_analyze) for deeper analysis"
    if operation == "transform":
        return "Verify the transformation with gan.a_root (ship.check)"
    if operation == "consolidate":
        return "Use gan.a_void (galactic.dashboard) to confirm consolidation"
    # Tool was successful but unknown
    if "error" not in preview.lower() and "fail" not in preview.lower():
        return "Call completed. Use gan.a_ghost (list_ganas) to discover more tools"
    # Error case
    return "Last call did not succeed. Use gan.a_straddling_legs (evaluate_ethics) or retry with different args"


# ---------------------------------------------------------------------------
# Resonance Snapshot (one per PRAT invocation)
# ---------------------------------------------------------------------------

@dataclass
class ResonanceSnapshot:
    """Captured resonance context from a single PRAT invocation."""

    gana_name: str
    tool_name: str | None
    operation: str | None
    output_preview: str
    timestamp: float = 0.0
    lunar_phase: float = 0.0
    lunar_mansion_num: int = 0
    harmony_score: float = 1.0
    guna_tag: str = "rajasic"
    quadrant: str = "East"
    zodiac_sign: str = "Aries"
    zodiac_resonance: float = 1.0
    successor_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return asdict(self)


# ---------------------------------------------------------------------------
# Session Resonance State (singleton)
# ---------------------------------------------------------------------------

class PratResonanceState:
    """Thread-safe per-session resonance state for PRAT calls.

    Tracks:
    - Last Gana invoked + output (predecessor context)
    - Per-Gana invocation counts (for future learning)
    - Session call sequence number
    """

    def __init__(self, max_history: int = 50):
        self._lock = threading.Lock()
        self._last_snapshot: ResonanceSnapshot | None = None
        self._history: deque = deque(maxlen=max_history)
        self._gana_counts: dict[str, int] = {}
        self._session_calls: int = 0

    def get_predecessor(self) -> ResonanceSnapshot | None:
        """Get the last invocation's resonance snapshot."""
        with self._lock:
            return self._last_snapshot

    def record(self, snapshot: ResonanceSnapshot) -> None:
        """Record a completed PRAT invocation."""
        with self._lock:
            self._last_snapshot = snapshot
            self._history.append(snapshot)
            self._gana_counts[snapshot.gana_name] = (
                self._gana_counts.get(snapshot.gana_name, 0) + 1
            )
            self._session_calls += 1

    @property
    def call_count(self) -> int:
        """
        Perform the call count operation.

        Returns:
            int
        """
        with self._lock:
            return self._session_calls

    def get_gana_counts(self) -> dict[str, int]:
        """Per-Gana invocation counts."""
        with self._lock:
            return dict(self._gana_counts)

    def get_recent_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Recent resonance snapshots."""
        with self._lock:
            return [s.to_dict() for s in list(self._history)[-limit:]]

    def reset(self) -> None:
        """Reset session state (e.g., on new session)."""
        with self._lock:
            self._last_snapshot = None
            self._history.clear()
            self._gana_counts.clear()
            self._session_calls = 0


# Singleton
_state: PratResonanceState | None = None
_state_lock = threading.Lock()


def get_resonance_state() -> PratResonanceState:
    """Get or create the global resonance state singleton."""
    global _state
    if _state is None:
        with _state_lock:
            if _state is None:
                _state = PratResonanceState()
    return _state


# ---------------------------------------------------------------------------
# Harmony Vector + Lunar Phase helpers (lazy imports)
# ---------------------------------------------------------------------------

def _get_harmony_snapshot() -> dict[str, Any]:
    """Get current Harmony Vector snapshot (safe fallback if unavailable)."""
    try:
        from whitemagic.harmony.vector import get_harmony_vector
        hv = get_harmony_vector()
        snap = hv.snapshot()
        return {
            "harmony_score": snap.harmony_score,
            "guna_dominant": _dominant_guna(snap),
            "energy": snap.energy,
            "error_rate": snap.error_rate,
            "dharma": snap.dharma,
        }
    except (ImportError, AttributeError):
        return {
            "harmony_score": 1.0,
            "guna_dominant": "rajasic",
            "energy": 1.0,
            "error_rate": 1.0,
            "dharma": 1.0,
        }


def _dominant_guna(snap: Any) -> str:
    """Determine dominant Guna from snapshot percentages."""
    gunas = {
        "sattvic": getattr(snap, "guna_sattvic_pct", 0),
        "rajasic": getattr(snap, "guna_rajasic_pct", 0),
        "tamasic": getattr(snap, "guna_tamasic_pct", 0),
    }
    return max(gunas, key=gunas.get)  # type: ignore[arg-type]


def _get_lunar_phase() -> tuple:
    """Get (phase_float, mansion_number). Safe fallback."""
    try:
        from whitemagic.core.ganas.lunar import (
            _mock_lunar_mansion,
            get_current_lunar_phase,
        )
        phase = get_current_lunar_phase()
        mansion = _mock_lunar_mansion()
        return (phase, mansion.number)
    except (ImportError, AttributeError):
        import time as _t
        days = _t.time() / 86400
        phase = (days % 29.53059) / 29.53059
        mansion_num = int(((days % 27.321661) / 27.321661) * 28) + 1
        return (phase, mansion_num)


# ---------------------------------------------------------------------------
# Core API: build resonance context + record after call
# ---------------------------------------------------------------------------

def build_resonance_context(gana_name: str) -> dict[str, Any]:
    """Build resonance context BEFORE a PRAT call executes.

    Returns a dict with:
    - predecessor info (last Gana's output preview, name, tool)
    - lunar phase + alignment check
    - harmony vector snapshot
    - successor hint (which Gana follows in the 28-mansion circle)
    - guna adaptation hint (minimal/optimal/normal mode)
    """
    state = get_resonance_state()
    meta = _get_meta(gana_name)
    predecessor = state.get_predecessor()
    harmony = _get_harmony_snapshot()
    lunar_phase, lunar_mansion = _get_lunar_phase()

    # Zodiacal Phase (Milestone 3)
    try:
        from whitemagic.core.zodiac import get_zodiac_clock
        clock = get_zodiac_clock()
        zodiac_status = clock.status()
        zodiac_sign = zodiac_status["phase"]
    except (ImportError, ModuleNotFoundError):
        zodiac_sign = "Aries"

    # Check lunar alignment (Moon is in this Gana's mansion)
    lunar_aligned = (lunar_mansion == meta["mansion_num"])

    # Check zodiac alignment (Milestone 3.1)
    zodiac_amplified = False
    zodiac_resonance = 1.0
    try:
        from whitemagic.core.zodiac import get_zodiac_clock
        clock = get_zodiac_clock()
        zodiac_resonance = clock.get_resonance_multiplier(meta["mansion_num"])
        zodiac_amplified = (zodiac_resonance > 1.0)
    except (ImportError, ModuleNotFoundError):
        pass

    # Guna adaptation hint
    guna = harmony["guna_dominant"]
    if guna == "tamasic":
        mode_hint = "minimal"
    elif guna == "sattvic" or zodiac_amplified:
        # Boost to optimal if sign is aligned or harmony is pure (sattvic)
        mode_hint = "optimal"
    else:
        mode_hint = "normal"

    # Successor in the 28-mansion circle
    successor_name = _get_successor_gana(gana_name)
    successor_meta = _get_meta(successor_name)

    ctx: dict[str, Any] = {
        "gana": gana_name,
        "mansion_num": meta["mansion_num"],
        "quadrant": meta["quadrant"],
        "meaning": meta["meaning"],
        "garden": meta["garden"],
        "chinese": meta["chinese"],
        "lunar_phase": round(lunar_phase, 4),
        "lunar_aligned": lunar_aligned,
        "harmony_score": round(harmony["harmony_score"], 4),
        "guna": guna,
        "mode_hint": mode_hint,
        "chain_position": state.call_count,
        "successor": {
            "gana": successor_name,
            "meaning": successor_meta["meaning"],
        },
        "zodiac": zodiac_sign,
        "zodiac_amplified": zodiac_amplified,
        "zodiac_resonance": zodiac_resonance,
    }

    # Predecessor context (from last PRAT call)
    if predecessor:
        ctx["predecessor"] = {
            "gana": predecessor.gana_name,
            "tool": predecessor.tool_name,
            "output_preview": predecessor.output_preview,
            "timestamp": predecessor.timestamp,
        }

    # Zodiac amplification note (Milestone 3.1)
    if zodiac_amplified:
        ctx["zodiac_amplification"] = (
            f"Zodiacal alignment detected: {zodiac_sign} amplifying {gana_name} "
            f"(Native Resonance x{zodiac_resonance})"
        )

    # Lunar amplification note
    if lunar_aligned:
        ctx["lunar_amplification"] = (
            f"Moon is in {meta['chinese']} ({meta['pinyin']}) — "
            f"this Gana is amplified"
        )

    # Gana vitality / reputation (12.108.20 — honor competence)
    try:
        from whitemagic.tools.gana_vitality import get_vitality_monitor
        monitor = get_vitality_monitor()
        rep = monitor.get_reputation(gana_name)
        ctx["gana_reputation"] = {
            "success_rate": rep["success_rate"],
            "avg_latency_ms": rep["avg_latency_ms"],
            "vitality": rep["vitality"],
            "total_calls": rep["total_calls"],
            "consecutive_failures": rep["consecutive_failures"],
        }
        # If degraded, add warning (12.108.29 — silence = defeat)
        if rep["vitality"] in ("degraded", "struggling"):
            ctx["vitality_warning"] = (
                f"{gana_name} vitality is {rep['vitality']} "
                f"(success_rate={rep['success_rate']:.0%}, "
                f"consecutive_failures={rep['consecutive_failures']}). "
                f"Consider routing to a peer Gana."
            )
    except (ImportError, AttributeError):
        pass

    return ctx


def _compute_prat_economics(
    gana_name: str,
    tool_name: str | None,
    state: PratResonanceState,
) -> dict[str, Any]:
    """Compute PRAT economics metadata for Leap 8 Swarm protocol.

    Tracks per-Gana compute cost estimates, session totals, and
    cost-per-tool hints that agents can use for budget planning.
    """
    # Base compute cost units per category (unitless, relative)
    _CATEGORY_COST: dict[str, float] = {
        "East": 1.0,    # Core operations (session, memory, health)
        "South": 1.5,   # Analytical (introspection, patterns, export)
        "West": 2.0,    # Ethical + reasoning (dharma, synthesis, inference)
        "North": 2.5,   # Governance + coordination (swarm, agents, voting)
    }
    meta = _GANA_META.get(gana_name)
    quadrant = meta[1] if meta else "East"
    base_cost = _CATEGORY_COST.get(quadrant, 1.0)

    # Scale by safety level
    safety_multiplier = 1.0
    if tool_name:
        # Write/delete tools cost more (they do more work)
        try:
            from whitemagic.tools.tool_surface import get_callable_tool_definition
            td = get_callable_tool_definition(tool_name)
            if td and td.safety.value == "write":
                safety_multiplier = 1.5
            elif td and td.safety.value == "delete":
                safety_multiplier = 2.0
        except (ImportError, AttributeError):
            pass

    call_cost = round(base_cost * safety_multiplier, 2)

    # Session totals
    gana_counts = state.get_gana_counts()
    session_total_cost = sum(
        _CATEGORY_COST.get(_GANA_META.get(g, (0, "East"))[1], 1.0) * count
        for g, count in gana_counts.items()
    )

    return {
        "call_cost_units": call_cost,
        "quadrant_base": base_cost,
        "safety_multiplier": safety_multiplier,
        "session_total_cost": round(session_total_cost, 2),
        "session_total_calls": state.call_count,
        "gana_call_count": gana_counts.get(gana_name, 0),
    }


def record_resonance(
    gana_name: str,
    tool_name: str | None,
    operation: str | None,
    result: Any,
) -> dict[str, Any]:
    """Record resonance state AFTER a PRAT call completes.

    Returns the resonance metadata that should be injected into the response.
    """
    state = get_resonance_state()
    meta = _get_meta(gana_name)
    harmony = _get_harmony_snapshot()
    lunar_phase, lunar_mansion = _get_lunar_phase()

    # Build output preview (truncated for context passing)
    if isinstance(result, dict):
        preview_parts = []
        for key in ("status", "action", "note", "error"):
            if key in result:
                preview_parts.append(f"{key}={result[key]}")
        if preview_parts:
            preview = "; ".join(preview_parts)
        else:
            preview = str(result)[:200]
    else:
        preview = str(result)[:200]

    # Successor hint — actionable, tool-aware guidance for the agent.
    # Replaces the previous astrology-based hint ("Prepared for Liu in Aries")
    # with a concrete next-step suggestion tied to what was just called.
    successor_name = _get_successor_gana(gana_name)
    successor_meta = _get_meta(successor_name)
    # Zodiacal Phase (Milestone 3)
    try:
        from whitemagic.core.zodiac import get_zodiac_clock
        zodiac_sign = get_zodiac_clock().current_phase
    except (ImportError, ModuleNotFoundError):
        zodiac_sign = "Aries"

    actionable_hint = _actionable_successor_hint(gana_name, tool_name, operation, preview)
    successor_hint = (
        f"{actionable_hint} | next: {successor_meta['pinyin']} ({successor_meta['meaning']})"
    )

    snapshot = ResonanceSnapshot(
        gana_name=gana_name,
        tool_name=tool_name,
        operation=operation,
        output_preview=preview[:200],
        timestamp=time.time(),
        lunar_phase=lunar_phase,
        lunar_mansion_num=lunar_mansion,
        harmony_score=harmony["harmony_score"],
        guna_tag=harmony["guna_dominant"],
        quadrant=meta["quadrant"],
        zodiac_sign=zodiac_sign,
        zodiac_resonance=(1.5 if (mansion_num := meta.get("mansion_num", 0)) and _zodiac_aligned(mansion_num) else 1.0),
        successor_hint=successor_hint,
    )

    state.record(snapshot)

    # Leap 8: PRAT economics metadata
    economics = _compute_prat_economics(gana_name, tool_name, state)

    return {
        "gana": gana_name,
        "garden": meta["garden"],
        "quadrant": meta["quadrant"],
        "lunar_phase": round(lunar_phase, 4),
        "lunar_aligned": (lunar_mansion == meta["mansion_num"]),
        "harmony_score": round(harmony["harmony_score"], 4),
        "guna": harmony["guna_dominant"],
        "chain_position": state.call_count,
        "zodiac": zodiac_sign,
        "zodiac_amplified": _zodiac_aligned(meta["mansion_num"]),
        "successor_hint": successor_hint,
        "_prat_economics": economics,
    }

def _zodiac_aligned(mansion_num: int) -> bool:
    """Helper to check zodiac alignment without global pollution."""
    try:
        from whitemagic.core.zodiac import get_zodiac_clock
        return get_zodiac_clock().is_aligned(mansion_num)
    except (ImportError, ModuleNotFoundError):
        return False


def get_resonance_summary() -> dict[str, Any]:
    """Get a summary of the current resonance state (for Gnosis/introspection)."""
    state = get_resonance_state()
    predecessor = state.get_predecessor()
    harmony = _get_harmony_snapshot()
    lunar_phase, lunar_mansion = _get_lunar_phase()

    # Find which Gana the moon is currently in
    current_lunar_gana = None
    for name, meta in _GANA_META.items():
        if meta[0] == lunar_mansion:
            current_lunar_gana = name
            break

    from whitemagic.core.zodiac import get_zodiac_clock
    return {
        "session_calls": state.call_count,
        "gana_counts": state.get_gana_counts(),
        "last_gana": predecessor.gana_name if predecessor else None,
        "last_tool": predecessor.tool_name if predecessor else None,
        "lunar_phase": round(lunar_phase, 4),
        "lunar_mansion": lunar_mansion,
        "lunar_gana": current_lunar_gana,
        "zodiac": get_zodiac_clock().current_phase if get_zodiac_clock() else "Aries",  # type: ignore[name-defined]
        "harmony_score": round(harmony["harmony_score"], 4),
        "guna_dominant": harmony["guna_dominant"],
        "recent_history": state.get_recent_history(5),
    }
