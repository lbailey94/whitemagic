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
    return cast('dict[str, Any]', _ttl_get('state_summary', _HEALTH_CACHE_TTL_S, lambda: _core.state_summary(include_sizes=True)))


def _load_cached_rust_status() -> dict[str, Any]:
    def _loader() -> dict[str, Any]:
        from whitemagic.tools.handlers.rust_bridge import handle_rust_status
        rust = handle_rust_status()
        return {
            'available': rust.get('available', False),
            'version': rust.get('version', 'unknown'),
        }
    return cast('dict[str, Any]', _ttl_get('rust_status', _HEALTH_CACHE_TTL_S, _loader))


def _load_cached_garden_health() -> dict[str, Any]:
    def _loader() -> dict[str, Any]:
        from whitemagic.tools.handlers.garden import handle_garden_health
        gardens = handle_garden_health()
        return cast('dict[str, Any]', gardens.get('health', {}))
    return cast('dict[str, Any]', _ttl_get('garden_health', _HEALTH_CACHE_TTL_S, _loader))


def _load_cached_archaeology_stats() -> dict[str, Any]:
    def _loader() -> dict[str, Any]:
        from whitemagic.tools.handlers.archaeology import handle_archaeology_stats
        arch = handle_archaeology_stats()
        return {
            'files_tracked': arch.get('total_files', 0),
            'total_reads': arch.get('total_reads', 0),
        }
    return cast('dict[str, Any]', _ttl_get('archaeology_stats', _HEALTH_CACHE_TTL_S, _loader))


def _load_cached_yin_yang_balance() -> dict[str, Any]:
    def _loader() -> dict[str, Any]:
        from whitemagic.tools.handlers.balance import handle_get_yin_yang_balance
        balance = handle_get_yin_yang_balance()
        return cast('dict[str, Any]', balance.get('balance', {}))
    return cast('dict[str, Any]', _ttl_get('yin_yang_balance', _HEALTH_CACHE_TTL_S, _loader))


def _load_cached_db_stats() -> dict[str, Any]:
    from whitemagic.config.paths import DB_PATH
    def _loader() -> dict[str, Any]:
        db = Path(DB_PATH)
        if not db.exists():
            return {'path': str(db), 'exists': False}
        conn = sqlite3.connect(str(db))
        try:
            count = conn.execute('SELECT COUNT(*) FROM memories').fetchone()[0]
        finally:
            conn.close()
        return {
            'path': str(db),
            'size_mb': round(db.stat().st_size / (1024 * 1024), 1),
            'memory_count': count,
        }
    return cast('dict[str, Any]', _ttl_get('db_stats', _HEALTH_CACHE_TTL_S, _loader))


def _load_cached_binary_status(binary_name: str, fallback_path: str) -> dict[str, Any]:
    key = f'binary::{binary_name}::{fallback_path}'
    def _loader() -> dict[str, Any]:
        binary_path = shutil.which(binary_name) or fallback_path
        return {'available': Path(binary_path).exists(), 'path': binary_path}
    return cast('dict[str, Any]', _ttl_get(key, 60.0, _loader))

def handle_capabilities(**kwargs: Any) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        _core.capabilities(
        include_tools=bool(kwargs.get("include_tools", True)),
        include_schemas=bool(kwargs.get("include_schemas", False)),
        include_env=bool(kwargs.get("include_env", True)),
        ),
    )

def handle_manifest(**kwargs: Any) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        _core.manifest(
        format=str(kwargs.get("format", "summary")),
        include_schemas=bool(kwargs.get("include_schemas", False)),
        ),
    )

def handle_state_paths(**kwargs: Any) -> dict[str, Any]:
    return cast("dict[str, Any]", _core.state_paths())

def handle_state_summary(**kwargs: Any) -> dict[str, Any]:
    return cast("dict[str, Any]", _core.state_summary(include_sizes=bool(kwargs.get("include_sizes", True))))

def handle_repo_summary(**kwargs: Any) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        _core.repo_summary(
        max_files=int(kwargs.get("max_files", 2500)),
        max_matches=int(kwargs.get("max_matches", 25)),
        ),
    )

def handle_ship_check(**kwargs: Any) -> dict[str, Any]:
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
        caps = _core.capabilities(include_tools=False, include_schemas=False, include_env=False)
        report["version"] = caps.get("package_version", caps.get("version", "unknown"))
        runtime = caps.get("runtime", {})
        report["python_version"] = runtime.get("python", runtime.get("python_version", "unknown"))
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
    except Exception:
        report["julia"] = {"available": False}

    # 9. Haskell bridge
    try:
        import os
        report["haskell"] = _load_cached_binary_status("ghc",
                # Tool discovery: GHC compiler path (legitimate expanduser)
                os.path.expanduser("~/.ghcup/bin/ghc"))
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
    computed_health = "healthy" if health_score >= 0.8 else "degraded" if health_score >= 0.5 else "critical"
    if runtime_status.get("degraded_mode") and computed_health == "healthy":
        computed_health = "degraded"
    report["health_status"] = computed_health
    report["degraded_mode"] = runtime_status.get("degraded_mode", False)
    report["degraded_reasons"] = runtime_status.get("degraded_reasons", [])
    report["debug_enabled"] = runtime_status.get("debug_enabled", False)

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
