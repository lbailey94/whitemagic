# ruff: noqa: BLE001
"""Introspection tool handlers — core system introspection + health report."""

import logging
import shutil
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from whitemagic.runtime_status import get_runtime_status
from whitemagic.tools import introspection as _core

logger = logging.getLogger(__name__)

_HEALTH_CACHE_TTL_S = 10.0
_HEALTH_CACHE: dict[str, tuple[float, Any]] = {}


def _ttl_get(key: str, ttl_s: float, loader: Callable[[], Any]) -> Any:
    now = time.monotonic()
    cached = _HEALTH_CACHE.get(key)
    if cached and (now - cached[0]) < ttl_s:
        return cached[1]
    value = loader()
    _HEALTH_CACHE[key] = (now, value)
    return value


def _load_cached_state_summary() -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        _ttl_get(
            "state_summary",
            _HEALTH_CACHE_TTL_S,
            lambda: _core.state_summary(include_sizes=True),
        ),
    )


def _load_cached_rust_status() -> dict[str, Any]:
    def _loader() -> dict[str, Any]:
        from whitemagic.tools.handlers.rust_bridge import handle_rust_status

        rust = handle_rust_status()
        return {
            "available": rust.get("available", False),
            "version": rust.get("version", "unknown"),
        }

    return cast("dict[str, Any]", _ttl_get("rust_status", _HEALTH_CACHE_TTL_S, _loader))


def _load_cached_garden_health() -> dict[str, Any]:
    def _loader() -> dict[str, Any]:
        from whitemagic.tools.handlers.garden import handle_garden_health

        gardens = handle_garden_health()
        return cast("dict[str, Any]", gardens.get("health", {}))

    return cast(
        "dict[str, Any]", _ttl_get("garden_health", _HEALTH_CACHE_TTL_S, _loader)
    )


def _load_cached_archaeology_stats() -> dict[str, Any]:
    def _loader() -> dict[str, Any]:
        from whitemagic.tools.handlers.archaeology import handle_archaeology_stats

        arch = handle_archaeology_stats()
        return {
            "files_tracked": arch.get("total_files", 0),
            "total_reads": arch.get("total_reads", 0),
        }

    return cast(
        "dict[str, Any]", _ttl_get("archaeology_stats", _HEALTH_CACHE_TTL_S, _loader)
    )


def _load_cached_yin_yang_balance() -> dict[str, Any]:
    def _loader() -> dict[str, Any]:
        from whitemagic.tools.handlers.balance import handle_get_yin_yang_balance

        balance = handle_get_yin_yang_balance()
        return cast("dict[str, Any]", balance.get("balance", {}))

    return cast(
        "dict[str, Any]", _ttl_get("yin_yang_balance", _HEALTH_CACHE_TTL_S, _loader)
    )


def _load_cached_db_stats() -> dict[str, Any]:
    from whitemagic.config.paths import DB_PATH

    def _loader() -> dict[str, Any]:
        db = Path(DB_PATH)
        if not db.exists():
            return {"path": str(db), "exists": False}
        conn = sqlite3.connect(str(db))
        try:
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        finally:
            conn.close()
        return {
            "path": str(db),
            "size_mb": round(db.stat().st_size / (1024 * 1024), 1),
            "memory_count": count,
        }

    return cast("dict[str, Any]", _ttl_get("db_stats", _HEALTH_CACHE_TTL_S, _loader))


def _load_cached_binary_status(binary_name: str, fallback_path: str) -> dict[str, Any]:
    key = f"binary::{binary_name}::{fallback_path}"

    def _loader() -> dict[str, Any]:
        binary_path = shutil.which(binary_name) or fallback_path
        return {"available": Path(binary_path).exists(), "path": binary_path}

    return cast("dict[str, Any]", _ttl_get(key, 60.0, _loader))


def handle_capabilities(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a capabilities event.

    Returns:
        dict[str, Any]
    """
    return cast(
        "dict[str, Any]",
        _core.capabilities(
            include_tools=bool(kwargs.get("include_tools", True)),
            include_schemas=bool(kwargs.get("include_schemas", False)),
            include_env=bool(kwargs.get("include_env", True)),
        ),
    )


def handle_manifest(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a manifest event.

    Returns:
        dict[str, Any]
    """
    return cast(
        "dict[str, Any]",
        _core.manifest(
            format=str(kwargs.get("format", "summary")),
            include_schemas=bool(kwargs.get("include_schemas", False)),
        ),
    )


def handle_state_paths(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a state paths event.

    Returns:
        dict[str, Any]
    """
    return cast("dict[str, Any]", _core.state_paths())


def handle_state_summary(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a state summary event.

    Returns:
        dict[str, Any]
    """
    return cast(
        "dict[str, Any]",
        _core.state_summary(include_sizes=bool(kwargs.get("include_sizes", True))),
    )


def handle_repo_summary(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a repo summary event.

    Returns:
        dict[str, Any]
    """
    return cast(
        "dict[str, Any]",
        _core.repo_summary(
            max_files=int(kwargs.get("max_files", 2500)),
            max_matches=int(kwargs.get("max_matches", 25)),
        ),
    )


def handle_ship_check(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a ship check event.

    Returns:
        dict[str, Any]
    """
    return cast(
        "dict[str, Any]",
        _core.ship_check(
            max_files=int(kwargs.get("max_files", 4000)),
            max_large_files=int(kwargs.get("max_large_files", 25)),
            large_file_mb=int(kwargs.get("large_file_mb", 10)),
            max_matches=int(kwargs.get("max_matches", 50)),
        ),
    )


def handle_get_telemetry_summary(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a get telemetry summary event.

    Returns:
        dict[str, Any]
    """
    return cast("dict[str, Any]", _core.telemetry_summary())


def handle_gnosis(**kwargs: Any) -> dict[str, Any]:
    """Gnosis Portal — unified introspection across all Whitemagic subsystems."""
    from whitemagic.tools.gnosis import gnosis_snapshot

    compact = kwargs.get("compact", False)
    snap = gnosis_snapshot(compact=compact)
    return {"status": "success", "gnosis": snap}


def handle_health_report(**kwargs: Any) -> dict[str, Any]:
    """Consolidated system health report aggregating multiple subsystems."""
    report: dict[str, Any] = {"status": "success"}
    runtime_status = get_runtime_status()
    report["runtime"] = runtime_status

    # 1. Capabilities / version info
    try:
        caps = _core.capabilities(
            include_tools=False, include_schemas=False, include_env=False
        )
        report["version"] = caps.get("package_version", caps.get("version", "unknown"))
        runtime = caps.get("runtime", {})
        report["python_version"] = runtime.get(
            "python", runtime.get("python_version", "unknown")
        )
        report["tool_count"] = caps.get("surface_counts", {}).get("callable_tools", 0)
        report["features"] = caps.get("features", {})
    except Exception as e:
        report["capabilities_error"] = str(e)

    # 2. State summary
    try:
        state = _load_cached_state_summary()
        sizes = state.get("sizes_bytes", {})
        total_bytes = sum(sizes.values()) if isinstance(sizes, dict) else 0
        report["state"] = {
            "root": state.get("wm_state_root", ""),
            "exists": state.get("exists", False),
            "total_size_mb": round(total_bytes / (1024 * 1024), 1),
        }
    except Exception as e:
        report["state_error"] = str(e)

    # 3. Rust bridge
    try:
        report["rust"] = _load_cached_rust_status()
    except Exception as e:
        report["rust"] = {"available": False, "error": str(e)}

    # 4. Garden health
    try:
        report["gardens"] = _load_cached_garden_health()
    except Exception as e:
        report["gardens_error"] = str(e)

    # 5. Archaeology stats
    try:
        report["archaeology"] = _load_cached_archaeology_stats()
    except Exception as e:
        report["archaeology_error"] = str(e)

    # 6. Yin-Yang balance
    try:
        report["yin_yang"] = _load_cached_yin_yang_balance()
    except Exception as e:
        report["yin_yang_error"] = str(e)

    # 7. DB stats
    try:
        report["db"] = _load_cached_db_stats()
    except Exception as e:
        report["db_error"] = str(e)

    # 8. Julia bridge
    try:
        report["julia"] = _load_cached_binary_status("julia", "/snap/bin/julia")
    except Exception as e:
        logger.debug("Operation failed: %s", e)
        report["julia"] = {"available": False}

    # 9. Haskell bridge
    try:
        import os

        report["haskell"] = _load_cached_binary_status(
            "ghc",
            # Tool discovery: GHC compiler path (legitimate expanduser)
            os.path.expanduser("~/.ghcup/bin/ghc"),
        )
    except (ImportError, ModuleNotFoundError):
        report["haskell"] = {"available": False}

    # Compute overall health score
    checks = []
    checks.append(report.get("rust", {}).get("available", False))
    checks.append(report.get("db", {}).get("memory_count", 0) > 0)
    checks.append(report.get("julia", {}).get("available", False))
    checks.append("state" in report)
    checks.append("gardens" in report)
    health_score = sum(1 for c in checks if c) / max(len(checks), 1)
    report["health_score"] = round(health_score, 2)
    computed_health = (
        "healthy"
        if health_score >= 0.8
        else "degraded"
        if health_score >= 0.5
        else "critical"
    )
    if runtime_status.get("degraded_mode") and computed_health == "healthy":
        computed_health = "degraded"
    report["health_status"] = computed_health
    report["degraded_mode"] = runtime_status.get("degraded_mode", False)
    report["degraded_reasons"] = runtime_status.get("degraded_reasons", [])
    report["debug_enabled"] = runtime_status.get("debug_enabled", False)

    # 10. Physical health (laptop-optimizer integration)
    try:
        from whitemagic.harmony.physical_metrics import get_physical_metrics_source

        source = get_physical_metrics_source()
        metrics = source.get_metrics()
        if metrics.is_available:
            report["physical_health"] = {
                "cpu_temp": metrics.cpu_temp,
                "cpu_usage": metrics.cpu_usage,
                "battery_percent": metrics.battery_percent,
                "battery_status": metrics.battery_status,
                "memory_percent": metrics.memory_percent,
                "swap_percent": metrics.swap_percent,
                "disk_usage": metrics.disk_usage,
                "power_draw": metrics.power_draw,
                "fan_rpm": metrics.fan_rpm,
                "thermal_throttling": metrics.thermal_throttling,
                "laptop_optimizer_score": metrics.health_score,
            }
            # Thermal forecast
            forecast = source.get_thermal_forecast()
            if forecast:
                report["physical_health"]["thermal_forecast"] = {
                    "predicted_5min": forecast.predicted_5min,
                    "predicted_15min": forecast.predicted_15min,
                    "confidence": forecast.confidence,
                }
            # Adaptive targets
            targets = source.get_adaptive_targets()
            report["physical_health"]["adaptive_targets"] = {
                "cpu_temp_max": targets.cpu_temp_max,
                "battery_min": targets.battery_min,
                "memory_max": targets.memory_max,
            }
    except Exception:
        pass

    return report


def handle_capability_matrix(**kwargs: Any) -> dict[str, Any]:
    """Return the full capability matrix: subsystems, fusions, unexplored opportunities."""
    from whitemagic.tools.capability_matrix import get_capability_matrix

    return cast(
        "dict[str, Any]",
        get_capability_matrix(
            category=kwargs.get("category"),
            include_unexplored=bool(kwargs.get("include_unexplored", True)),
        ),
    )


def handle_capability_status(**kwargs: Any) -> dict[str, Any]:
    """Get live status for a specific subsystem."""
    from whitemagic.tools.capability_matrix import get_subsystem_status

    subsystem_id = kwargs.get("subsystem_id", "")
    if not subsystem_id:
        return {"status": "error", "error": "subsystem_id is required"}
    return cast("dict[str, Any]", get_subsystem_status(subsystem_id))


def handle_capability_suggest(**kwargs: Any) -> dict[str, Any]:
    """Suggest the next best fusion to wire."""
    from whitemagic.tools.capability_matrix import suggest_next_fusion

    return cast("dict[str, Any]", suggest_next_fusion())


_GANA_28_SURFACE: list[dict[str, Any]] = [
    # Eastern Quadrant — Azure Dragon (Spring)
    {
        "id": "gana_horn",
        "n": 1,
        "chinese": "角",
        "pinyin": "Jiao",
        "meaning": "Sharp initiation",
        "quadrant": "East",
        "element": "Wood",
        "garden": "Courage",
        "purpose": "Bootstrap new sessions, initialize state, hand off between agents.",
        "example_tools": [
            "session_bootstrap",
            "create_session",
            "resume_session",
            "checkpoint_session",
        ],
    },
    {
        "id": "gana_neck",
        "n": 2,
        "chinese": "亢",
        "pinyin": "Kang",
        "meaning": "Stability",
        "quadrant": "East",
        "element": "Wood",
        "garden": "Stillness",
        "purpose": "Create, read, update, delete memories. The core memory surface.",
        "example_tools": [
            "create_memory",
            "read_memory",
            "update_memory",
            "delete_memory",
            "remember",
        ],
    },
    {
        "id": "gana_root",
        "n": 3,
        "chinese": "氐",
        "pinyin": "Di",
        "meaning": "Foundation",
        "quadrant": "East",
        "element": "Wood",
        "garden": "Healing",
        "purpose": "System health, foundations, hygiene, ship-checks.",
        "example_tools": [
            "health_report",
            "ship.check",
            "state.paths",
            "state.summary",
        ],
    },
    {
        "id": "gana_room",
        "n": 4,
        "chinese": "房",
        "pinyin": "Fang",
        "meaning": "Enclosure",
        "quadrant": "East",
        "element": "Wood",
        "garden": "Sanctuary",
        "purpose": "Resource locks, sandbox, security alerts, MCP integrity.",
        "example_tools": [
            "sangha_lock",
            "sandbox.set_limits",
            "security.alerts",
            "mcp_integrity.snapshot",
        ],
    },
    {
        "id": "gana_heart",
        "n": 5,
        "chinese": "心",
        "pinyin": "Xin",
        "meaning": "Vital pulse",
        "quadrant": "East",
        "element": "Fire",
        "garden": "Love",
        "purpose": "Session context, working memory, scratchpad, handoff.",
        "example_tools": [
            "scratchpad",
            "session.handoff",
            "context.pack",
            "context.status",
        ],
    },
    {
        "id": "gana_tail",
        "n": 6,
        "chinese": "尾",
        "pinyin": "Wei",
        "meaning": "Passionate drive",
        "quadrant": "East",
        "element": "Fire",
        "garden": "Courage",
        "purpose": "Performance acceleration, SIMD, cascade execution.",
        "example_tools": [
            "simd.cosine",
            "simd.batch",
            "execute_cascade",
            "list_cascade_patterns",
        ],
    },
    {
        "id": "gana_winnowing_basket",
        "n": 7,
        "chinese": "箕",
        "pinyin": "Ji",
        "meaning": "Separation",
        "quadrant": "East",
        "element": "Fire",
        "garden": "Wisdom",
        "purpose": "Search, recall, vector search, knowledge graph walks.",
        "example_tools": [
            "search_memories",
            "vector.search",
            "hybrid_recall",
            "graph_walk",
            "list_memories",
        ],
    },
    # Southern Quadrant — Vermilion Bird (Summer)
    {
        "id": "gana_ghost",
        "n": 8,
        "chinese": "鬼",
        "pinyin": "Gui",
        "meaning": "Introspection",
        "quadrant": "South",
        "element": "Water",
        "garden": "Grief",
        "purpose": "Introspection, telemetry, capability matrix, manifest, self-model.",
        "example_tools": [
            "gnosis",
            "capability.matrix",
            "manifest",
            "selfmodel.forecast",
            "list_ganas",
            "vitality",
            "discover",
        ],
    },
    {
        "id": "gana_willow",
        "n": 9,
        "chinese": "柳",
        "pinyin": "Liu",
        "meaning": "Flexibility",
        "quadrant": "South",
        "element": "Water",
        "garden": "Humor",
        "purpose": "Rate limiting, grimoire navigation, prompt templating.",
        "example_tools": [
            "rate_limiter.stats",
            "grimoire_cast",
            "prompt.render",
            "prompt.list",
        ],
    },
    {
        "id": "gana_star",
        "n": 10,
        "chinese": "星",
        "pinyin": "Xing",
        "meaning": "Illumination",
        "quadrant": "South",
        "element": "Fire",
        "garden": "Voice",
        "purpose": "Governance, dharma profile, governor validation.",
        "example_tools": [
            "governor_validate",
            "governor_set_goal",
            "dharma.reload",
            "set_dharma_profile",
        ],
    },
    {
        "id": "gana_extended_net",
        "n": 11,
        "chinese": "张",
        "pinyin": "Zhang",
        "meaning": "Connectivity",
        "quadrant": "South",
        "element": "Water",
        "garden": "Sangha",
        "purpose": "Pattern search, learning, cluster stats, tool graphs.",
        "example_tools": [
            "pattern_search",
            "cluster_stats",
            "tool.graph",
            "learning.patterns",
        ],
    },
    {
        "id": "gana_wings",
        "n": 12,
        "chinese": "翼",
        "pinyin": "Yi",
        "meaning": "Expansion",
        "quadrant": "South",
        "element": "Fire",
        "garden": "Beauty",
        "purpose": "Export memories, audit exports, mesh broadcast, deployment.",
        "example_tools": [
            "export_memories",
            "audit.export",
            "mesh.broadcast",
            "mesh.status",
        ],
    },
    {
        "id": "gana_chariot",
        "n": 13,
        "chinese": "轸",
        "pinyin": "Zhen",
        "meaning": "Movement",
        "quadrant": "South",
        "element": "Water",
        "garden": "Adventure",
        "purpose": "Codebase archaeology, knowledge graph, embeddings.",
        "example_tools": [
            "archaeology",
            "kg.extract",
            "kg.query",
            "embedding.daemon_start",
        ],
    },
    {
        "id": "gana_abundance",
        "n": 14,
        "chinese": "豐",
        "pinyin": "Fēng",
        "meaning": "Surplus",
        "quadrant": "South",
        "element": "Fire",
        "garden": "Joy",
        "purpose": "Dream cycle, memory lifecycle, serendipity, gratitude.",
        "example_tools": [
            "dream",
            "memory.lifecycle",
            "serendipity_surface",
            "gratitude.stats",
        ],
    },
    # Western Quadrant — White Tiger (Autumn)
    {
        "id": "gana_straddling_legs",
        "n": 15,
        "chinese": "奎",
        "pinyin": "Kui",
        "meaning": "Balance",
        "quadrant": "West",
        "element": "Metal",
        "garden": "Awe",
        "purpose": "Ethics evaluation, boundaries, consent, harmony, karma.",
        "example_tools": [
            "evaluate_ethics",
            "check_boundaries",
            "verify_consent",
            "harmony_vector",
            "karma_record",
        ],
    },
    {
        "id": "gana_mound",
        "n": 16,
        "chinese": "娄",
        "pinyin": "Lou",
        "meaning": "Accumulation",
        "quadrant": "West",
        "element": "Earth",
        "garden": "Gratitude",
        "purpose": "Metrics, cache, hologram viewing, yin-yang tracking.",
        "example_tools": [
            "track_metric",
            "get_metrics_summary",
            "cache.flush",
            "view_hologram",
        ],
    },
    {
        "id": "gana_stomach",
        "n": 17,
        "chinese": "胃",
        "pinyin": "Wei",
        "meaning": "Nourishment",
        "quadrant": "West",
        "element": "Earth",
        "garden": "Creation",
        "purpose": "Task pipeline, distribution, smart routing, completion.",
        "example_tools": [
            "pipeline",
            "task.distribute",
            "task.status",
            "task.route_smart",
            "task.complete",
        ],
    },
    {
        "id": "gana_hairy_head",
        "n": 18,
        "chinese": "昴",
        "pinyin": "Mao",
        "meaning": "Detail",
        "quadrant": "West",
        "element": "Metal",
        "garden": "Presence",
        "purpose": "Debug, salience, anomaly, telemetry, dharma rules.",
        "example_tools": ["salience.spotlight", "anomaly", "otel", "dharma_rules"],
    },
    {
        "id": "gana_net",
        "n": 19,
        "chinese": "毕",
        "pinyin": "Bi",
        "meaning": "Capture",
        "quadrant": "West",
        "element": "Metal",
        "garden": "Play",
        "purpose": "Prompt render, karma chain verification.",
        "example_tools": ["prompt.render", "prompt.list", "karma.verify_chain"],
    },
    {
        "id": "gana_turtle_beak",
        "n": 20,
        "chinese": "觜",
        "pinyin": "Zui",
        "meaning": "Precision",
        "quadrant": "West",
        "element": "Metal",
        "garden": "Practice",
        "purpose": "Edge inference, BitNet, precision validation.",
        "example_tools": [
            "edge_infer",
            "edge_batch_infer",
            "bitnet_infer",
            "bitnet_status",
        ],
    },
    {
        "id": "gana_three_stars",
        "n": 21,
        "chinese": "参",
        "pinyin": "Shen",
        "meaning": "Judgment",
        "quadrant": "West",
        "element": "Fire",
        "garden": "Reverence",
        "purpose": "Bicameral reasoning, ensembles, optimization, kaizen.",
        "example_tools": [
            "reasoning.bicameral",
            "ensemble",
            "solve_optimization",
            "kaizen_analyze",
        ],
    },
    # Northern Quadrant — Black Tortoise (Winter)
    {
        "id": "gana_dipper",
        "n": 22,
        "chinese": "斗",
        "pinyin": "Dou",
        "meaning": "Governance",
        "quadrant": "North",
        "element": "Fire",
        "garden": "Dharma",
        "purpose": "Homeostasis, maturity assessment, starter packs, astro.",
        "example_tools": [
            "homeostasis",
            "maturity.assess",
            "starter_packs",
            "astro_status",
        ],
    },
    {
        "id": "gana_ox",
        "n": 23,
        "chinese": "牛",
        "pinyin": "Niu",
        "meaning": "Endurance",
        "quadrant": "North",
        "element": "Earth",
        "garden": "Patience",
        "purpose": "Swarm decomposition, routing, voting, planning.",
        "example_tools": ["swarm.decompose", "swarm.route", "swarm.vote", "swarm.plan"],
    },
    {
        "id": "gana_girl",
        "n": 24,
        "chinese": "女",
        "pinyin": "Nü",
        "meaning": "Nurture",
        "quadrant": "North",
        "element": "Earth",
        "garden": "Connection",
        "purpose": "Agent registry, heartbeats, capabilities, trust.",
        "example_tools": [
            "agent.register",
            "agent.heartbeat",
            "agent.list",
            "agent.capabilities",
            "agent.trust",
        ],
    },
    {
        "id": "gana_void",
        "n": 25,
        "chinese": "虚",
        "pinyin": "Xu",
        "meaning": "Emptiness",
        "quadrant": "North",
        "element": "Water",
        "garden": "Mystery",
        "purpose": "Galactic dashboard, garden activation, galaxies.",
        "example_tools": [
            "galactic.dashboard",
            "garden_activate",
            "galaxy.create",
            "galaxy.switch",
        ],
    },
    {
        "id": "gana_roof",
        "n": 26,
        "chinese": "危",
        "pinyin": "Wei",
        "meaning": "Shelter",
        "quadrant": "North",
        "element": "Earth",
        "garden": "Protection",
        "purpose": "Ollama local models, zodiac, model registry.",
        "example_tools": [
            "ollama.models",
            "ollama.generate",
            "ollama.chat",
            "zodiac.status",
            "model.register",
        ],
    },
    {
        "id": "gana_encampment",
        "n": 27,
        "chinese": "室",
        "pinyin": "Shi",
        "meaning": "Structure",
        "quadrant": "North",
        "element": "Fire",
        "garden": "Transformation",
        "purpose": "Sangha chat, broker publish, history, status.",
        "example_tools": [
            "sangha_chat_send",
            "broker.publish",
            "broker.history",
            "broker.status",
        ],
    },
    {
        "id": "gana_wall",
        "n": 28,
        "chinese": "壁",
        "pinyin": "Bi",
        "meaning": "Boundaries",
        "quadrant": "North",
        "element": "Earth",
        "garden": "Truth",
        "purpose": "Voting, engagement tokens, alerts.",
        "example_tools": [
            "vote.create",
            "vote.cast",
            "vote.analyze",
            "engagement.issue",
            "engagement.validate",
        ],
    },
]


def handle_list_ganas(**kwargs: Any) -> dict[str, Any]:
    """One-shot discovery of the 28 Gana surface.

    Returns a compact, machine-readable catalog of all 28 Ganas with their
    purpose, quadrant, element, garden, and example tools. An agent can
    model the entire PRAT surface in a single call and pick the right
    Gana for its next action without having to introspect each one.

    Optional kwargs:
      quadrant: filter to one quadrant (East/South/West/North)
      search:   substring match against purpose / meaning / example_tools
    """
    quadrant = kwargs.get("quadrant")
    search = kwargs.get("search")
    out = _GANA_28_SURFACE
    if quadrant:
        out = [g for g in out if g["quadrant"].lower() == quadrant.lower()]
    if search:
        needle = search.lower()
        out = [
            g
            for g in out
            if needle in g["purpose"].lower()
            or needle in g["meaning"].lower()
            or needle in g["id"].lower()
            or any(needle in t.lower() for t in g["example_tools"])
        ]
    return {
        "status": "success",
        "ganas": out,
        "total": len(out),
        "filter": {"quadrant": quadrant, "search": search},
        "groups": {
            "East": [g["id"] for g in _GANA_28_SURFACE if g["quadrant"] == "East"],
            "South": [g["id"] for g in _GANA_28_SURFACE if g["quadrant"] == "South"],
            "West": [g["id"] for g in _GANA_28_SURFACE if g["quadrant"] == "West"],
            "North": [g["id"] for g in _GANA_28_SURFACE if g["quadrant"] == "North"],
        }
        if not (quadrant or search)
        else None,
        "note": "Source: grimoire/TRUTH_TABLE.md. Cross-reference for narrative.",
    }


def handle_vitality(**kwargs: Any) -> dict[str, Any]:
    """Reputation / vitality of one or all 28 Ganas.

    Returns success rate, average latency, and a vitality warning for
    each Gana based on the in-process practice resonance state. Agents
    can use this to avoid routing to degraded tools.

    Optional kwargs:
      gana: specific gana id (e.g. "gana_ghost"). Omit for all.
    """
    target = kwargs.get("gana")
    out: dict[str, Any] = {}
    try:
        from whitemagic.tools.prat_resonance import get_vitality

        for g in _GANA_28_SURFACE:
            gid = g["id"]
            if target and gid != target:
                continue
            try:
                v = get_vitality(gid) if callable(get_vitality) else None
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                v = None
            if isinstance(v, dict):
                out[gid] = v
            else:
                out[gid] = {
                    "gana": gid,
                    "success_rate": 1.0,
                    "avg_latency_ms": None,
                    "call_count": 0,
                    "vitality_warning": None,
                }
    except Exception as e:
        return {"status": "error", "error_code": "internal_error", "message": str(e)}
    return {
        "status": "success",
        "reputation": out if target else out,
        "target": target,
        "note": "Use this before routing tool calls to avoid degraded Ganas.",
    }


def handle_discover(**kwargs: Any) -> dict[str, Any]:
    """First-call bundle: gnosis(compact) + capability summary + gana index.

    Designed as the canonical 'what is this system and what can I do' tool
    for an agent's first interaction. Returns three sections in one
    envelope, so a new agent can model the surface in a single round-trip
    without separately calling gnosis, capability.matrix, and list_ganas.
    """
    out: dict[str, Any] = {"status": "success"}
    out["gnosis"] = handle_gnosis(compact=True).get("gnosis", {})
    out["capability_summary"] = handle_capabilities().get("summary", {})
    out["gana_index"] = handle_list_ganas().get("ganas", [])
    out["next_actions"] = [
        {
            "tool": "gana_ghost",
            "args": {"tool": "list_ganas"},
            "reason": "Inspect any single Gana",
        },
        {
            "tool": "gana_ghost",
            "args": {"tool": "vitality"},
            "reason": "Check vitality before routing",
        },
        {
            "tool": "gana_ghost",
            "args": {"tool": "gnosis", "args": {"compact": True}},
            "reason": "Periodic health check",
        },
    ]
    out["note"] = (
        "discover() is the recommended first call. Single round-trip models the surface."
    )
    return out
