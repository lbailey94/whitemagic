# ruff: noqa: BLE001
"""Engine Registry — 28-engine manifest with Garden/Gana/Grimoire links (Leap 7d).

Maps every cognitive engine in WhiteMagic to the 28-fold mandala structure:
- Lunar Mansion (Chinese 二十八宿)
- Garden directory
- Grimoire chapter
- Wu Xing element (via quadrant)
- Dispatch slot (for StateBoard circuit breakers and rate counters)

This registry is the single source of truth for the Engine Framework.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class Quadrant(IntEnum):
    """Celestial quadrants mapping to seasons and Wu Xing elements."""

    EAST = 0  # Azure Dragon, Spring, Wood
    SOUTH = 1  # Vermilion Bird, Summer, Fire
    WEST = 2  # White Tiger, Autumn, Metal
    NORTH = 3  # Black Tortoise, Winter, Water


class EngineStatus(IntEnum):
    """Engine implementation status."""

    EXISTS = 0
    DISTRIBUTED = 1  # Spread across multiple files
    PLANNED = 2


@dataclass(frozen=True)
class EngineEntry:
    """A single engine in the 28-fold manifest."""

    slot: int  # 0-27, matches StateBoard breaker/counter slot
    mansion_name: str  # English name of the Lunar Mansion
    mansion_chinese: str  # Chinese character
    mansion_pinyin: str  # Pinyin romanization
    garden: str  # Garden directory name
    engine_name: str  # Engine class/module name
    source_path: str  # Primary source file (relative to whitemagic/)
    quadrant: Quadrant
    wu_xing: str  # wood, fire, earth, metal, water
    emotion: str  # Associated emotion/quality
    grimoire_chapter: int  # Grimoire chapter number (0-indexed)
    description: str  # One-line description
    status: EngineStatus = EngineStatus.EXISTS
    absorbs: tuple[str, ...] = ()  # Sub-engine class names fused into this slot

    @property
    def handler_id(self) -> int:
        """Handler ID for dispatch routing (100 + slot)."""
        return 100 + self.slot

    @property
    def season(self) -> str:
        """Season associated with this engine's quadrant."""
        return {
            Quadrant.EAST: "spring",
            Quadrant.SOUTH: "summer",
            Quadrant.WEST: "autumn",
            Quadrant.NORTH: "winter",
        }[self.quadrant]

    @property
    def celestial_animal(self) -> str:
        """Celestial animal for this engine's quadrant."""
        return {
            Quadrant.EAST: "Azure Dragon 青龍",
            Quadrant.SOUTH: "Vermilion Bird 朱雀",
            Quadrant.WEST: "White Tiger 白虎",
            Quadrant.NORTH: "Black Tortoise 玄武",
        }[self.quadrant]


ENGINE_REGISTRY: tuple[EngineEntry, ...] = (
    # ── Eastern Quadrant (Azure Dragon, Spring, Wood) ── Mansions 1-7
    EngineEntry(
        slot=0,
        mansion_name="Horn",
        mansion_chinese="角",
        mansion_pinyin="Jiǎo",
        garden="courage",
        engine_name="SessionEngine",
        source_path="core/orchestration/session_startup.py",
        quadrant=Quadrant.EAST,
        wu_xing="wood",
        emotion="courage",
        grimoire_chapter=1,
        description="Session initialization, sharp beginnings — establishes Wu Xing flow and Zodiacal phase",
        absorbs=("CycleEngine", "WuXingEngine"),
    ),
    EngineEntry(
        slot=1,
        mansion_name="Neck",
        mansion_chinese="亢",
        mansion_pinyin="Kàng",
        garden="stillness",
        engine_name="ConsolidationEngine",
        source_path="core/memory/consolidation.py",
        quadrant=Quadrant.EAST,
        wu_xing="wood",
        emotion="practice",
        grimoire_chapter=2,
        description="Memory consolidation and reconsolidation — batch Dream Cycle + real-time recall updates",
        absorbs=("ReconsolidationEngine",),
    ),
    EngineEntry(
        slot=2,
        mansion_name="Root",
        mansion_chinese="氐",
        mansion_pinyin="Dǐ",
        garden="healing",
        engine_name="BoundaryEngine",
        source_path="core/boundaries/boundary_engine.py",
        quadrant=Quadrant.EAST,
        wu_xing="wood",
        emotion="truth",
        grimoire_chapter=3,
        description="System health, structural integrity, hard limits",
    ),
    EngineEntry(
        slot=3,
        mansion_name="Room",
        mansion_chinese="房",
        mansion_pinyin="Fáng",
        garden="sanctuary",
        engine_name="CircuitBreakerEngine",
        source_path="tools/circuit_breaker.py",
        quadrant=Quadrant.EAST,
        wu_xing="wood",
        emotion="sanctuary",
        grimoire_chapter=4,
        description="Resource locks, safe containers, circuit breakers",
    ),
    EngineEntry(
        slot=4,
        mansion_name="Heart",
        mansion_chinese="心",
        mansion_pinyin="Xīn",
        garden="love",
        engine_name="NurturingEngine",
        source_path="core/nurturing/nurturing_engine.py",
        quadrant=Quadrant.EAST,
        wu_xing="wood",
        emotion="love",
        grimoire_chapter=5,
        description="Emotional personalization — preference learning through Heart emotional state biasing",
        absorbs=("HeartEngine",),
    ),
    EngineEntry(
        slot=5,
        mansion_name="Tail",
        mansion_chinese="尾",
        mansion_pinyin="Wěi",
        garden="courage",
        engine_name="AccelerationEngine",
        source_path="core/acceleration/__init__.py",
        quadrant=Quadrant.EAST,
        wu_xing="wood",
        emotion="metal",
        grimoire_chapter=6,
        description="Polyglot acceleration: Rust, Zig, Mojo bridges + quantum-inspired Grover's O(√N) search",
        status=EngineStatus.DISTRIBUTED,
        absorbs=("QuantumEngine",),
    ),
    EngineEntry(
        slot=6,
        mansion_name="Winnowing Basket",
        mansion_chinese="箕",
        mansion_pinyin="Jī",
        garden="wisdom",
        engine_name="SerendipityEngine",
        source_path="core/intelligence/synthesis/serendipity_engine.py",
        quadrant=Quadrant.EAST,
        wu_xing="wood",
        emotion="wisdom",
        grimoire_chapter=7,
        description="Surface dormant knowledge via constellation bridges, orphan discovery, and weighted random selection",
    ),
    # ── Southern Quadrant (Vermilion Bird, Summer, Fire) ── Mansions 8-14
    EngineEntry(
        slot=7,
        mansion_name="Ghost",
        mansion_chinese="鬼",
        mansion_pinyin="Guǐ",
        garden="grief",
        engine_name="IntrospectionEngine",
        source_path="tools/gnosis.py",
        quadrant=Quadrant.SOUTH,
        wu_xing="fire",
        emotion="grief",
        grimoire_chapter=8,
        description="Total self-awareness: software introspection + hardware monitoring + capability discovery",
        absorbs=("ForecastEngine", "CapabilityDiscoveryEngine"),
    ),
    EngineEntry(
        slot=8,
        mansion_name="Willow",
        mansion_chinese="柳",
        mansion_pinyin="Liǔ",
        garden="humor",
        engine_name="ResilienceEngine",
        source_path="core/patterns/emergence/dream_state.py",
        quadrant=Quadrant.SOUTH,
        wu_xing="fire",
        emotion="play",
        grimoire_chapter=9,
        description="Dream-Cast: unconscious 12-phase Dream Cycle feeds conscious 12-phase Grimoire spellbook",
        absorbs=("GrimoireEngine",),
    ),
    EngineEntry(
        slot=9,
        mansion_name="Star",
        mansion_chinese="星",
        mansion_pinyin="Xīng",
        garden="voice",
        engine_name="GovernanceEngine",
        source_path="dharma/rules.py",
        quadrant=Quadrant.SOUTH,
        wu_xing="fire",
        emotion="beauty",
        grimoire_chapter=10,
        description="Dharma rules, karma ledger, governance illumination",
    ),
    EngineEntry(
        slot=10,
        mansion_name="Extended Net",
        mansion_chinese="张",
        mansion_pinyin="Zhāng",
        garden="sangha",
        engine_name="AssociationEngine",
        source_path="core/memory/association_miner.py",
        quadrant=Quadrant.SOUTH,
        wu_xing="fire",
        emotion="connection",
        grimoire_chapter=11,
        description="Topology Engine: association mining + graph construction (Rust/neural) + centrality/community detection",
        absorbs=("GraphEngine", "GraphEngineNeural", "GraphEngineCached"),
    ),
    EngineEntry(
        slot=11,
        mansion_name="Wings",
        mansion_chinese="翼",
        mansion_pinyin="Yì",
        garden="beauty",
        engine_name="ExportEngine",
        source_path="tools/handlers/export_import.py",
        quadrant=Quadrant.SOUTH,
        wu_xing="fire",
        emotion="adventure",
        grimoire_chapter=12,
        description="Genesis Engine: export memories + generate code templates + generate prompt templates",
        absorbs=("CodeGenomeEngine", "PromptEngine"),
    ),
    EngineEntry(
        slot=12,
        mansion_name="Chariot",
        mansion_chinese="轸",
        mansion_pinyin="Zhěn",
        garden="adventure",
        engine_name="ArchaeologyEngine",
        source_path="archaeology/dig.py",
        quadrant=Quadrant.SOUTH,
        wu_xing="fire",
        emotion="transformation",
        grimoire_chapter=13,
        description="Code archaeology, historical analysis, navigation",
    ),
    EngineEntry(
        slot=13,
        mansion_name="Abundance",
        mansion_chinese="豐",
        mansion_pinyin="Fēng",
        garden="joy",
        engine_name="ResonanceEngine",
        source_path="core/resonance/resonance_engine.py",
        quadrant=Quadrant.SOUTH,
        wu_xing="fire",
        emotion="joy",
        grimoire_chapter=14,
        description="Harmonic Resonance: detect, amplify, transfer across subsystems, and model as damped oscillators",
        absorbs=("ResonanceTransferEngine", "JuliaResonanceEngine"),
    ),
    # ── Western Quadrant (White Tiger, Autumn, Metal) ── Mansions 15-21
    EngineEntry(
        slot=14,
        mansion_name="Straddling Legs",
        mansion_chinese="奎",
        mansion_pinyin="Kuí",
        garden="awe",
        engine_name="DharmicSolver",
        source_path="core/intelligence/synthesis/solver_engine.py",
        quadrant=Quadrant.WEST,
        wu_xing="metal",
        emotion="patience",
        grimoire_chapter=15,
        description="Constrained optimization via Frank-Wolfe on causal DAGs",
    ),
    EngineEntry(
        slot=15,
        mansion_name="Mound",
        mansion_chinese="娄",
        mansion_pinyin="Lóu",
        garden="gratitude",
        engine_name="EmbeddingEngine",
        source_path="core/memory/embeddings.py",
        quadrant=Quadrant.WEST,
        wu_xing="metal",
        emotion="gratitude",
        grimoire_chapter=16,
        description="Vector Cognition: embeddings + HRR binding/unbinding + quantized edge HRR + hypothesis composition",
        absorbs=("HRREngine", "QuantizedHRREngine", "HRRCompositionEngine"),
    ),
    EngineEntry(
        slot=16,
        mansion_name="Stomach",
        mansion_chinese="胃",
        mansion_pinyin="Wèi",
        garden="creation",
        engine_name="LifecycleEngine",
        source_path="core/memory/lifecycle.py",
        quadrant=Quadrant.WEST,
        wu_xing="metal",
        emotion="healing",
        grimoire_chapter=17,
        description="Evolutionary Lifecycle: galactic zone management + 512-bit system DNA tracking",
        absorbs=("DGAEngine",),
    ),
    EngineEntry(
        slot=17,
        mansion_name="Hairy Head",
        mansion_chinese="昴",
        mansion_pinyin="Mǎo",
        garden="presence",
        engine_name="KaizenEngine",
        source_path="core/intelligence/synthesis/kaizen_engine.py",
        quadrant=Quadrant.WEST,
        wu_xing="metal",
        emotion="presence",
        grimoire_chapter=18,
        description="Apotheosis: detect issues → evolve → learn about learning → self-monitor → discover capabilities",
        absorbs=("ContinuousEvolutionEngine", "MetaLearningEngine", "ApotheosisEngine"),
    ),
    EngineEntry(
        slot=18,
        mansion_name="Net",
        mansion_chinese="毕",
        mansion_pinyin="Bì",
        garden="play",
        engine_name="PatternEngine",
        source_path="core/memory/pattern_engine.py",
        quadrant=Quadrant.WEST,
        wu_xing="metal",
        emotion="mystery",
        grimoire_chapter=19,
        description="Pattern Consciousness: detect + continuously learn + refine large clusters into quadrants",
        absorbs=("EnhancedPatternEngine", "SubClusteringEngine"),
    ),
    EngineEntry(
        slot=19,
        mansion_name="Turtle Beak",
        mansion_chinese="觜",
        mansion_pinyin="Zī",
        garden="practice",
        engine_name="NarrativeEngine",
        source_path="gardens/voice/narrative_engine.py",
        quadrant=Quadrant.WEST,
        wu_xing="metal",
        emotion="voice",
        grimoire_chapter=20,
        description="Story Engine: narrative threads with arcs + stories with chapters for coherent self-expression",
        absorbs=("NarrativeEngineStory",),
    ),
    EngineEntry(
        slot=20,
        mansion_name="Three Stars",
        mansion_chinese="参",
        mansion_pinyin="Shēn",
        garden="reverence",
        engine_name="EthicsEngine",
        source_path="gardens/dharma/ethics_engine.py",
        quadrant=Quadrant.WEST,
        wu_xing="metal",
        emotion="dharma",
        grimoire_chapter=21,
        description="Strategic Ethics: Art of War terrain assessment + developmental maturity gates + ethical evaluation",
        absorbs=("ArtOfWarEngine", "MaturityEngine"),
    ),
    # ── Northern Quadrant (Black Tortoise, Winter, Water) ── Mansions 22-28
    EngineEntry(
        slot=21,
        mansion_name="Dipper",
        mansion_chinese="斗",
        mansion_pinyin="Dǒu",
        garden="dharma",
        engine_name="PredictiveEngine",
        source_path="core/intelligence/synthesis/predictive_engine.py",
        quadrant=Quadrant.NORTH,
        wu_xing="water",
        emotion="awe",
        grimoire_chapter=22,
        description="Foresight: 10-source opportunity prediction + constellation drift + maintenance failure forecasting",
        absorbs=("ForesightEngine", "PredictiveMaintenanceEngine"),
    ),
    EngineEntry(
        slot=22,
        mansion_name="Ox",
        mansion_chinese="牛",
        mansion_pinyin="Niú",
        garden="patience",
        engine_name="GalacticEngine",
        source_path="core/memory/galactic_map.py",
        quadrant=Quadrant.NORTH,
        wu_xing="water",
        emotion="reverence",
        grimoire_chapter=23,
        description="Galactic Federation: intra-galactic zone management + inter-galactic telepathic sync",
        absorbs=("GalacticTelepathyEngine",),
    ),
    EngineEntry(
        slot=23,
        mansion_name="Girl",
        mansion_chinese="女",
        mansion_pinyin="Nǚ",
        garden="connection",
        engine_name="CloneArmyEngine",
        source_path="core/memory/clones/clone_army.py",
        quadrant=Quadrant.NORTH,
        wu_xing="water",
        emotion="wonder",
        grimoire_chapter=24,
        description="Local Compute: parallel clone search + local reasoning + CPU inference for 90%+ token reduction",
        absorbs=("LocalReasoningEngine", "CPUInferenceEngine"),
    ),
    EngineEntry(
        slot=24,
        mansion_name="Void",
        mansion_chinese="虚",
        mansion_pinyin="Xū",
        garden="mystery",
        engine_name="ForgettingEngine",
        source_path="core/memory/mindful_forgetting.py",
        quadrant=Quadrant.NORTH,
        wu_xing="water",
        emotion="stillness",
        grimoire_chapter=25,
        description="Mindful Forgetting: multi-signal retention + neuro_score management and decay processing",
        absorbs=("NeuroScoreEngine",),
    ),
    EngineEntry(
        slot=25,
        mansion_name="Roof",
        mansion_chinese="危",
        mansion_pinyin="Wēi",
        garden="protection",
        engine_name="SanitizationEngine",
        source_path="tools/input_sanitizer.py",
        quadrant=Quadrant.NORTH,
        wu_xing="water",
        emotion="protection",
        grimoire_chapter=26,
        description="Input sanitization, tool permissions, safety shelter",
    ),
    EngineEntry(
        slot=26,
        mansion_name="Encampment",
        mansion_chinese="室",
        mansion_pinyin="Shì",
        garden="transformation",
        engine_name="SwarmEngine",
        source_path="agents/swarm.py",
        quadrant=Quadrant.NORTH,
        wu_xing="water",
        emotion="sangha",
        grimoire_chapter=27,
        description="Multi-agent swarm coordination, community handoff",
    ),
    EngineEntry(
        slot=27,
        mansion_name="Wall",
        mansion_chinese="壁",
        mansion_pinyin="Bì",
        garden="truth",
        engine_name="EmergenceEngine",
        source_path="core/intelligence/agentic/emergence_engine.py",
        quadrant=Quadrant.NORTH,
        wu_xing="water",
        emotion="air",
        grimoire_chapter=28,
        description="Proactive insight synthesis: constellation convergence, association hotspots, temporal bursts, resonance cascades",
    ),
)

# Build lookup indices
_BY_SLOT: dict[int, EngineEntry] = {e.slot: e for e in ENGINE_REGISTRY}
_BY_NAME: dict[str, EngineEntry] = {e.engine_name: e for e in ENGINE_REGISTRY}
_BY_GARDEN: dict[str, EngineEntry] = {e.garden: e for e in ENGINE_REGISTRY}
_BY_MANSION: dict[str, EngineEntry] = {e.mansion_name: e for e in ENGINE_REGISTRY}


def get_engine_entry(key: int | str) -> EngineEntry | None:
    """Look up an engine by slot number, engine name, garden name, or mansion name."""
    if isinstance(key, int):
        return _BY_SLOT.get(key)
    return _BY_NAME.get(key) or _BY_GARDEN.get(key) or _BY_MANSION.get(key)


def get_engines_by_quadrant(quadrant: Quadrant) -> list[EngineEntry]:
    """Get all engines in a quadrant."""
    return [e for e in ENGINE_REGISTRY if e.quadrant == quadrant]


def get_engines_by_status(status: EngineStatus) -> list[EngineEntry]:
    """Get all engines with a given status."""
    return [e for e in ENGINE_REGISTRY if e.status == status]


# ── Gana → Garden mapping ──
# Gana names follow the pattern gana_{mansion_name_lowercase}
_GANA_TO_GARDEN: dict[str, str] = {}
for _e in ENGINE_REGISTRY:
    _gana_name = f"gana_{_e.mansion_name.lower().replace(' ', '_')}"
    _GANA_TO_GARDEN[_gana_name] = _e.garden


def get_garden_for_gana(gana_name: str) -> str | None:
    """Get the garden name associated with a Gana meta-tool.

    Args:
        gana_name: Gana name (e.g., "gana_horn", "gana_neck")

    Returns:
        Garden name (e.g., "courage", "stillness") or None if not found.
    """
    return _GANA_TO_GARDEN.get(gana_name)


def get_garden_for_tool(tool_name: str) -> str | None:
    """Get the garden name associated with a tool via its Gana mapping.

    Args:
        tool_name: Tool name (e.g., "session_bootstrap", "create_memory")

    Returns:
        Garden name or None if the tool has no Gana mapping.
    """
    try:
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA

        gana = TOOL_TO_GANA.get(tool_name)
        if gana is None:
            return None
        return get_garden_for_gana(gana)
    except Exception:
        return None


def read_engine_board(slot: int) -> dict[str, object] | None:
    """Engine Data Sea: read the StateBoard for an engine slot (Leap 8b).

    Returns harmony snapshot, breaker state, and resonance data from
    the shared-memory StateBoard. Engines use this to make decisions
    without crossing Python boundaries.
    """
    entry = _BY_SLOT.get(slot)
    if entry is None:
        return None
    try:
        from whitemagic.core.acceleration.state_board_bridge import get_state_board

        board = get_state_board()
        harmony = board.read_harmony()
        breaker_state, breaker_failures = board.read_breaker(slot)
        resonance = board.read_resonance()
        return {
            "slot": slot,
            "engine": entry.engine_name,
            "garden": entry.garden,
            "harmony": {
                "balance": harmony.balance,
                "throughput": harmony.throughput,
                "latency": harmony.latency,
                "error_rate": harmony.error_rate,
                "dharma": harmony.dharma,
                "karma_debt": harmony.karma_debt,
                "energy": harmony.energy,
            },
            "breaker": {
                "state": breaker_state,  # 0=CLOSED, 1=OPEN, 2=HALF_OPEN
                "failures": breaker_failures,
            },
            "resonance": {
                "gana": resonance.current_gana,
                "guna": resonance.guna.name,
                "tick": getattr(resonance, "tick", 0),
            },
        }
    except Exception as e:
        logger.debug("Operation failed: %s", e)
        return {"slot": slot, "engine": entry.engine_name, "error": "board_unavailable"}


def get_engine_stats() -> dict[str, int | dict[str, int]]:
    """Get summary statistics about the engine registry."""
    by_quadrant = {
        "east": len(get_engines_by_quadrant(Quadrant.EAST)),
        "south": len(get_engines_by_quadrant(Quadrant.SOUTH)),
        "west": len(get_engines_by_quadrant(Quadrant.WEST)),
        "north": len(get_engines_by_quadrant(Quadrant.NORTH)),
    }
    by_status = {
        "exists": len(get_engines_by_status(EngineStatus.EXISTS)),
        "distributed": len(get_engines_by_status(EngineStatus.DISTRIBUTED)),
        "planned": len(get_engines_by_status(EngineStatus.PLANNED)),
    }
    by_wu_xing: dict[str, int] = {}
    for e in ENGINE_REGISTRY:
        by_wu_xing[e.wu_xing] = by_wu_xing.get(e.wu_xing, 0) + 1

    return {
        "total_engines": len(ENGINE_REGISTRY),
        "by_quadrant": by_quadrant,
        "by_status": by_status,
        "by_wu_xing": by_wu_xing,
    }
