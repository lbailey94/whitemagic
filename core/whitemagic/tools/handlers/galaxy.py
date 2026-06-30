# ruff: noqa: BLE001
"""Galaxy management tool handlers.

Provides MCP tools for creating, switching, listing, and ingesting
into project-scoped memory galaxies.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_galaxy_create(**kwargs: Any) -> dict[str, Any]:
    """Create a new galaxy (project-scoped memory database)."""
    name = kwargs.get("name")
    if not name:
        return {"status": "error", "error": "name is required"}

    from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

    try:
        gm = get_galaxy_manager()
        info = gm.create_galaxy(
            name=name,
            project_path=kwargs.get("path"),
            description=kwargs.get("description", ""),
            tags=kwargs.get("tags", []),
            user_id=kwargs.get("user_id"),
        )
        return {
            "status": "success",
            "message": f"Galaxy '{name}' created",
            **info.to_dict(),
        }
    except ValueError as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_switch(**kwargs: Any) -> dict[str, Any]:
    """Switch the active galaxy."""
    name = kwargs.get("name")
    if not name:
        return {"status": "error", "error": "name is required"}

    from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

    try:
        gm = get_galaxy_manager()
        info = gm.switch_galaxy(name, user_id=kwargs.get("user_id"))
        return {
            "status": "success",
            "message": f"Switched to galaxy '{name}'",
            **info.to_dict(),
        }
    except ValueError as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_list(**kwargs: Any) -> dict[str, Any]:
    """List all known galaxies with caching."""
    # Try cache first
    try:
        from whitemagic.core.memory.query_cache import get_query_cache
        cache = get_query_cache()
        cached = cache.get("galaxy_list")
        if cached is not None:
            return cached
    except (ImportError, ModuleNotFoundError) as e:
        logger.debug("Silenced galaxy fast_read cache error: %s", e, exc_info=True)

    from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

    gm = get_galaxy_manager()
    galaxies = gm.list_galaxies(user_id=kwargs.get("user_id"))
    result = {
        "status": "success",
        "active": gm.get_active().name,
        "count": len(galaxies),
        "galaxies": galaxies,
    }

    # Cache the result
    try:
        cache.set("galaxy_list", result, ttl=30)
    except Exception as e:
        logger.debug("Silenced galaxy list cache error: %s", e, exc_info=True)

    return result


def handle_galaxy_status(**kwargs: Any) -> dict[str, Any]:
    """Get galaxy manager status with caching."""
    # Try cache first
    try:
        from whitemagic.core.memory.query_cache import get_query_cache
        cache = get_query_cache()
        cached = cache.get("galaxy_status")
        if cached is not None:
            return cached
    except (ImportError, ModuleNotFoundError) as e:
        logger.debug("Silenced galaxy get_status cache check error: %s", e, exc_info=True)

    from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

    gm = get_galaxy_manager()
    result = {"status": "success", **gm.status(user_id=kwargs.get("user_id"))}

    # Cache the result
    try:
        cache.set("galaxy_status", result, ttl=30)
    except Exception as e:
        logger.debug("Silenced galaxy get_status cache write error: %s", e, exc_info=True)

    return result


def handle_galaxy_ingest(**kwargs: Any) -> dict[str, Any]:
    """Ingest files from a directory into a galaxy."""
    name = kwargs.get("name") or kwargs.get("galaxy")
    source_path = kwargs.get("source_path") or kwargs.get("path")

    if not name:
        return {"status": "error", "error": "name (galaxy name) is required"}
    if not source_path:
        return {"status": "error", "error": "source_path is required"}

    from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

    try:
        gm = get_galaxy_manager()
        result = gm.ingest_files(
            galaxy_name=name,
            source_path=source_path,
            pattern=kwargs.get("pattern", "**/*.md"),
            max_files=kwargs.get("max_files", 500),
            tags=kwargs.get("tags", []),
            user_id=kwargs.get("user_id"),
        )
        return {"status": "success", **result}
    except (ValueError, FileNotFoundError) as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_delete(**kwargs: Any) -> dict[str, Any]:
    """Remove a galaxy from the registry (database file is preserved)."""
    name = kwargs.get("name")
    if not name:
        return {"status": "error", "error": "name is required"}

    from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

    try:
        gm = get_galaxy_manager()
        gm.delete_galaxy(name, user_id=kwargs.get("user_id"))
        return {"status": "success", "message": f"Galaxy '{name}' removed from registry"}
    except ValueError as e:
        return {"status": "error", "error": str(e)}


# ── v15.3 Galactic Telepathy ────────────────────────────────────


def handle_galaxy_transfer(**kwargs: Any) -> dict[str, Any]:
    """Transfer memories between galaxies with coordinate re-mapping and dedup."""
    source = kwargs.get("source") or kwargs.get("source_galaxy")
    target = kwargs.get("target") or kwargs.get("target_galaxy")

    if not source:
        return {"status": "error", "error": "source galaxy name is required"}
    if not target:
        return {"status": "error", "error": "target galaxy name is required"}

    from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

    try:
        gm = get_galaxy_manager()
        result = gm.transfer_memories(
            source_galaxy=source,
            target_galaxy=target,
            query=kwargs.get("query"),
            tags=kwargs.get("tags"),
            min_importance=float(kwargs.get("min_importance", 0.0)),
            max_galactic_distance=float(kwargs.get("max_galactic_distance", 1.0)),
            limit=int(kwargs.get("limit", 500)),
            copy=kwargs.get("copy", True),
        )
        return {"status": "success", **result}
    except ValueError as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_merge(**kwargs: Any) -> dict[str, Any]:
    """Merge all memories from a source galaxy into a target galaxy."""
    source = kwargs.get("source") or kwargs.get("source_galaxy")
    target = kwargs.get("target") or kwargs.get("target_galaxy") or "local/default"

    if not source:
        return {"status": "error", "error": "source galaxy name is required"}

    from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

    try:
        gm = get_galaxy_manager()
        result = gm.merge_galaxy(
            source_galaxy=source,
            target_galaxy=target,
            delete_after=kwargs.get("delete_after", False),
        )
        return {"status": "success", **result}
    except ValueError as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_sync(**kwargs: Any) -> dict[str, Any]:
    """Bidirectional sync between two galaxies (content-hash dedup)."""
    galaxy_a = kwargs.get("galaxy_a") or kwargs.get("source")
    galaxy_b = kwargs.get("galaxy_b") or kwargs.get("target")

    if not galaxy_a or not galaxy_b:
        return {"status": "error", "error": "galaxy_a and galaxy_b are required"}

    from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

    try:
        gm = get_galaxy_manager()
        result = gm.sync_galaxies(
            galaxy_a=galaxy_a,
            galaxy_b=galaxy_b,
            tags=kwargs.get("tags"),
            min_importance=float(kwargs.get("min_importance", 0.0)),
        )
        return {"status": "success", **result}
    except ValueError as e:
        return {"status": "error", "error": str(e)}


# ── v15.4 Phylogenetic Lineage ──────────────────────────────────────


def handle_galaxy_lineage(**kwargs: Any) -> dict[str, Any]:
    """Build the phylogenetic lineage tree for a memory (ancestors + descendants)."""
    memory_id = kwargs.get("memory_id")
    if not memory_id:
        return {"status": "error", "error": "memory_id is required"}

    from whitemagic.core.memory.phylogenetics import get_phylogenetics

    try:
        pg = get_phylogenetics()
        tree = pg.build_lineage_tree(
            memory_id=memory_id,
            max_depth=int(kwargs.get("max_depth", 10)),
        )
        return {"status": "success", **tree}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_taxonomy(**kwargs: Any) -> dict[str, Any]:
    """Classify a memory using taxonomic ranks (species, genus, family, order, kingdom)."""
    memory_id = kwargs.get("memory_id")
    if not memory_id:
        return {"status": "error", "error": "memory_id is required"}

    from whitemagic.core.memory.phylogenetics import get_phylogenetics

    try:
        pg = get_phylogenetics()
        rank = pg.classify_memory(
            memory_id=memory_id,
            galaxy_name=kwargs.get("galaxy", "default"),
        )
        return {"status": "success", "full_name": rank.full_name, **rank.to_dict()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_lineage_stats(**kwargs: Any) -> dict[str, Any]:
    """Return statistics about the phylogenetic lineage graph."""
    from whitemagic.core.memory.phylogenetics import get_phylogenetics

    try:
        pg = get_phylogenetics()
        stats = pg.get_stats()
        return {"status": "success", **stats}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── v23.1: 6D Holographic Galaxy Router ──────────────────────────


def handle_galaxy_route(**kwargs: Any) -> dict[str, Any]:
    """Determine which cognitive galaxy a subsystem's memory belongs to."""
    subsystem = kwargs.get("subsystem")
    if not subsystem:
        return {"status": "error", "error": "subsystem is required"}

    from whitemagic.core.memory.galaxy_router import get_galaxy_router

    try:
        router = get_galaxy_router()
        galaxy = router.route(subsystem, metadata=kwargs.get("metadata"))
        return {
            "status": "success",
            "subsystem": subsystem,
            "galaxy": galaxy,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_stats(**kwargs: Any) -> dict[str, Any]:
    """Get statistics for a specific cognitive galaxy."""
    galaxy = kwargs.get("galaxy", "universal")

    from whitemagic.core.memory.galaxy_router import get_galaxy_router

    try:
        router = get_galaxy_router()
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
        stats = router.get_galaxy_stats(galaxy, um)
        return {"status": "success", **stats}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_migrate(**kwargs: Any) -> dict[str, Any]:
    """Migrate a memory from one cognitive galaxy to another."""
    memory_id = kwargs.get("memory_id")
    target_galaxy = kwargs.get("target_galaxy")

    if not memory_id:
        return {"status": "error", "error": "memory_id is required"}
    if not target_galaxy:
        return {"status": "error", "error": "target_galaxy is required"}

    from whitemagic.core.memory.galaxy_router import get_galaxy_router

    try:
        router = get_galaxy_router()
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
        success = router.migrate(memory_id, target_galaxy, um)
        if success:
            return {"status": "success", "message": f"Migrated {memory_id} to galaxy '{target_galaxy}'"}
        return {"status": "error", "error": "Migration failed (see logs)"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_list_types(**kwargs: Any) -> dict[str, Any]:
    """List all registered cognitive galaxy types."""
    from whitemagic.core.memory.galaxy_router import get_galaxy_router

    try:
        router = get_galaxy_router()
        galaxies = router.list_galaxies()
        return {
            "status": "success",
            "count": len(galaxies),
            "galaxies": {
                name: {
                    "description": info.description,
                    "color": info.color,
                    "decay_multiplier": info.decay_multiplier,
                }
                for name, info in galaxies.items()
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_galaxy_export(params: dict) -> dict:
    """Export memories from a galaxy as Arrow IPC bytes (base64-encoded)."""
    try:
        import base64

        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()

        galaxy = params.get("galaxy", "universal")
        memory_type_str = params.get("memory_type")
        limit = params.get("limit", 10000)

        memory_type = None
        if memory_type_str:
            from whitemagic.core.memory.unified_types import MemoryType
            try:
                memory_type = MemoryType[memory_type_str.upper()]
            except (KeyError, ValueError):
                pass

        ipc_bytes = um.arrow_export(memory_type=memory_type, limit=limit, galaxy=galaxy)
        if ipc_bytes is None:
            return {
                "status": "success",
                "galaxy": galaxy,
                "exported": 0,
                "ipc_bytes_b64": None,
                "message": "Arrow bridge unavailable or no memories found",
            }

        return {
            "status": "success",
            "galaxy": galaxy,
            "exported": len(ipc_bytes),
            "ipc_bytes_b64": base64.b64encode(ipc_bytes).decode("ascii"),
            "size_bytes": len(ipc_bytes),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_galaxy_import(params: dict) -> dict:
    """Import memories from base64-encoded Arrow IPC bytes."""
    try:
        import base64

        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()

        ipc_b64 = params.get("ipc_bytes_b64", "")
        if not ipc_b64:
            return {"status": "error", "error": "Missing ipc_bytes_b64 parameter"}

        ipc_bytes = base64.b64decode(ipc_b64)
        count = um.arrow_import(ipc_bytes)

        return {
            "status": "success",
            "imported": count,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_galaxy_canonical_taxonomy(**kwargs: Any) -> dict[str, Any]:
    """List the canonical galaxy taxonomy with descriptions and memory counts."""
    from whitemagic.core.memory.galaxy_taxonomy import GALAXY_DESCRIPTIONS, GALAXY_ORDER

    try:
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
        stats = um.get_stats()
        galaxy_counts = stats.get("by_galaxy", {}) if isinstance(stats, dict) else {}
    except Exception:
        galaxy_counts = {}

    galaxies = []
    for name in GALAXY_ORDER:
        galaxies.append({
            "name": name,
            "description": GALAXY_DESCRIPTIONS.get(name, ""),
            "memory_count": galaxy_counts.get(name, 0),
        })

    return {
        "status": "success",
        "galaxies": galaxies,
        "total_galaxies": len(galaxies),
    }


def handle_galaxy_export_tutorial(**kwargs: Any) -> dict[str, Any]:
    """Export tutorial galaxy memories as JSON for public repo synchronization."""
    import json
    from pathlib import Path

    try:
        from whitemagic.config.paths import MEMORY_DIR
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()
        memories = um.search(galaxy="tutorial", limit=100)

        tutorials = []
        for m in memories:
            tutorials.append({
                "id": m.id if hasattr(m, "id") else str(getattr(m, "id", "")),
                "title": m.title if hasattr(m, "title") else "",
                "content": m.content if hasattr(m, "content") else "",
                "tags": list(m.tags) if hasattr(m, "tags") and m.tags else [],
                "memory_type": m.memory_type.name if hasattr(m, "memory_type") and hasattr(m.memory_type, "name") else str(getattr(m, "memory_type", "")),
                "importance": m.importance if hasattr(m, "importance") else 0.5,
                "galaxy": "tutorial",
            })

        export_path = MEMORY_DIR / "tutorial_export.json"
        export_path.write_text(json.dumps(tutorials, indent=2, ensure_ascii=False))

        return {
            "status": "success",
            "exported": len(tutorials),
            "path": str(export_path),
            "size_bytes": export_path.stat().st_size,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
