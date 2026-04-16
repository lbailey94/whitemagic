"""Garden tool handlers."""
from typing import Any


def _emit(event_type: str, data: dict[str, Any]) -> None:
    from whitemagic.tools.unified_api import _emit_gan_ying
    _emit_gan_ying(event_type, data)


def handle_garden_activate(**kwargs: Any) -> dict[str, Any]:
    garden_name = kwargs.get("garden", "").lower()
    from whitemagic.gardens import get_garden
    get_garden(garden_name)
    _emit("GARDEN_ACTIVATED", {"garden": garden_name})
    return {"status": "success", "garden": garden_name, "active": True}


def handle_garden_status(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.gardens import get_all_gardens
    gardens = get_all_gardens()
    return {"status": "success", "count": len(gardens), "gardens": list(gardens.keys())}


def handle_garden_synergy(**kwargs: Any) -> dict[str, Any]:
    try:
        from whitemagic.gardens.cross_pollination import get_resonance_matrix
        from whitemagic.gardens.garden_state import get_garden_state_tracker
        matrix = get_resonance_matrix()
        tracker = get_garden_state_tracker()
        stats = matrix.get_resonance_stats()
        active = tracker.get_all_active()
        return {
            "status": "success",
            "active_gardens": len(active),
            "active": active,
            "resonance_stats": stats,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_garden_health(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.gardens import get_all_gardens
    gardens = get_all_gardens()
    health = {name: "healthy" for name in gardens.keys()}
    return {"status": "success", "health": health}


# ═══════════════════════════════════════════════════════════════════════════════
# S025: Garden Directory MCP Tools
# ═══════════════════════════════════════════════════════════════════════════════


def handle_garden_list_files(**kwargs: Any) -> dict[str, Any]:
    """List all files belonging to a specific garden.

    Args:
        garden: Garden name (e.g., "wisdom", "joy", "practice")
        file_type: Filter by "python", "rust", "markdown", etc. (optional)
    """
    garden = kwargs.get("garden", "").lower()
    file_type = kwargs.get("file_type")

    if not garden:
        return {"status": "error", "error": "garden parameter required"}

    try:
        from whitemagic.core.garden_directory import get_garden_directory
        directory = get_garden_directory()
        files = directory.get_garden_files(garden, file_type)

        # Get garden metadata
        from whitemagic.core.intelligence.garden_gana_registry import get_by_garden
        entry = get_by_garden(garden)

        return {
            "status": "success",
            "garden": garden,
            "quadrant": entry.quadrant.value if entry else "",
            "element": entry.element.value if entry else "",
            "gana": entry.gana if entry else "",
            "files": files[:100],  # Limit to 100 for response
            "count": len(files),
            "truncated": len(files) > 100,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_garden_list_functions(**kwargs: Any) -> dict[str, Any]:
    """List all functions belonging to a specific garden.

    Args:
        garden: Garden name (e.g., "wisdom", "joy")
        limit: Maximum number of functions to return (default 100)
    """
    garden = kwargs.get("garden", "").lower()
    limit = kwargs.get("limit", 100)

    if not garden:
        return {"status": "error", "error": "garden parameter required"}

    try:
        from whitemagic.core.garden_function_registry import get_function_registry
        registry = get_function_registry()
        functions = registry.get_garden_functions(garden)

        return {
            "status": "success",
            "garden": garden,
            "functions": [
                {
                    "name": f.function_name,
                    "file": f.file_path,
                    "gana": f.gana,
                    "element": f.element,
                    "is_public": f.is_public,
                }
                for f in functions[:limit]
            ],
            "count": len(functions),
            "truncated": len(functions) > limit,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_garden_search(**kwargs: Any) -> dict[str, Any]:
    """Search across files and functions, restricted to specified gardens.

    Args:
        query: Search string (function names, file paths, concepts)
        gardens: List of gardens to search (default: all)
        search_type: "files", "functions", or "all" (default: all)
    """
    query = kwargs.get("query", "")
    gardens = kwargs.get("gardens")
    search_type = kwargs.get("search_type", "all")

    if not query:
        return {"status": "error", "error": "query parameter required"}

    try:
        results: dict[str, list[dict[str, Any]]] = {"files": [], "functions": []}

        # Search files
        if search_type in ("files", "all"):
            from whitemagic.core.garden_directory import get_garden_directory
            directory = get_garden_directory()
            file_results = directory.search_files(query, gardens)
            results["files"] = [
                {
                    "path": m.file_path,
                    "garden": m.primary_garden,
                    "type": m.file_type,
                    "loc": m.loc_count,
                }
                for m in file_results[:50]
            ]

        # Search functions
        if search_type in ("functions", "all"):
            from whitemagic.core.garden_function_registry import get_function_registry
            registry = get_function_registry()
            func_results = registry.search_functions(query, gardens)
            results["functions"] = [
                {
                    "name": f.function_name,
                    "file": f.file_path,
                    "garden": f.primary_garden,
                }
                for f in func_results[:50]
            ]

        return {
            "status": "success",
            "query": query,
            "gardens_searched": gardens or "all",
            "results": results,
            "total_files": len(results["files"]),
            "total_functions": len(results["functions"]),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_garden_resonance(**kwargs: Any) -> dict[str, Any]:
    """Calculate cross-garden resonance strength.

    Args:
        source: Source garden name
        target: Target garden name
    """
    source = kwargs.get("source", "").lower()
    target = kwargs.get("target", "").lower()

    if not source or not target:
        return {"status": "error", "error": "source and target parameters required"}

    try:
        from whitemagic.core.intelligence.garden_gana_registry import get_by_garden

        source_entry = get_by_garden(source)
        target_entry = get_by_garden(target)

        if not source_entry:
            return {"status": "error", "error": f"unknown garden: {source}"}
        if not target_entry:
            return {"status": "error", "error": f"unknown garden: {target}"}

        # Calculate resonance based on element relationships
        element_affinity = {
            ("Wood", "Fire"): 0.9,  # Wood feeds Fire
            ("Fire", "Earth"): 0.8,  # Fire creates Earth
            ("Earth", "Metal"): 0.8,  # Earth bears Metal
            ("Metal", "Water"): 0.9,  # Metal generates Water
            ("Water", "Wood"): 0.9,  # Water nourishes Wood
            ("Fire", "Wood"): 0.5,  # Reverse
            ("Earth", "Fire"): 0.4,
            ("Metal", "Earth"): 0.5,
            ("Water", "Metal"): 0.5,
            ("Wood", "Water"): 0.4,
        }

        # Same element = high resonance
        if source_entry.element.value == target_entry.element.value:
            base_resonance = 0.85
        else:
            key = (source_entry.element.value, target_entry.element.value)
            base_resonance = element_affinity.get(key, 0.3)

        # Same quadrant bonus
        if source_entry.quadrant == target_entry.quadrant:
            base_resonance += 0.1

        # Keyword overlap
        source_kw = set(source_entry.resonance_keywords or [])
        target_kw = set(target_entry.resonance_keywords or [])
        if source_kw and target_kw:
            overlap = len(source_kw & target_kw) / max(len(source_kw), len(target_kw))
            base_resonance += overlap * 0.2

        resonance = min(1.0, base_resonance)

        return {
            "status": "success",
            "source": source,
            "target": target,
            "resonance": round(resonance, 3),
            "source_element": source_entry.element.value,
            "target_element": target_entry.element.value,
            "source_quadrant": source_entry.quadrant.value,
            "target_quadrant": target_entry.quadrant.value,
            "element_relationship": "generating" if resonance > 0.6 else "neutral",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_garden_map_system(**kwargs: Any) -> dict[str, Any]:
    """Show which gardens own/operate a system.

    Args:
        system_id: System identifier (e.g., "memory", "dream", "mcp", "immune")
    """
    system_id = kwargs.get("system_id", "").lower()

    if not system_id:
        return {"status": "error", "error": "system_id parameter required"}

    # System → Garden mapping (based on S025 analysis)
    system_garden_map = {
        "memory": {"primary": "wisdom", "operating": ["stillness", "sanctuary"]},
        "dream": {"primary": "mystery", "operating": ["transformation", "wisdom"]},
        "mcp": {"primary": "voice", "operating": ["connection", "sangha"]},
        "immune": {"primary": "healing", "operating": ["protection", "sanctuary"]},
        "evolution": {"primary": "transformation", "operating": ["creation", "courage"]},
        "governance": {"primary": "dharma", "operating": ["truth", "wisdom"]},
        "resonance": {"primary": "connection", "operating": ["love", "sangha"]},
        "consciousness": {"primary": "mystery", "operating": ["wonder", "wisdom"]},
        "agents": {"primary": "practice", "operating": ["courage", "adventure"]},
        "cli": {"primary": "voice", "operating": ["truth", "dharma"]},
        "embedding": {"primary": "wisdom", "operating": ["mystery", "creation"]},
        "graph": {"primary": "connection", "operating": ["wisdom", "sangha"]},
        "search": {"primary": "wonder", "operating": ["wisdom", "truth"]},
        "storage": {"primary": "sanctuary", "operating": ["stillness", "wisdom"]},
        "security": {"primary": "protection", "operating": ["sanctuary", "courage"]},
        "acceleration": {"primary": "courage", "operating": ["creation", "practice"]},
        "alchemy": {"primary": "transformation", "operating": ["creation", "mystery"]},
        "grimoire": {"primary": "reverence", "operating": ["wisdom", "mystery"]},
        "zodiac": {"primary": "mystery", "operating": ["wisdom", "dharma"]},
        "bridge": {"primary": "connection", "operating": ["transformation", "voice"]},
    }

    if system_id not in system_garden_map:
        return {
            "status": "partial",
            "system": system_id,
            "message": "System not in predefined mapping. Use garden.search to find related files.",
            "suggestion": f"Try: garden.search(query='{system_id}')",
        }

    mapping = system_garden_map[system_id]

    try:
        from whitemagic.core.garden_directory import get_garden_directory
        directory = get_garden_directory()

        # Get files for primary garden
        primary_garden = str(mapping["primary"])
        primary_files = directory.get_garden_files(primary_garden)
        system_files = [f for f in primary_files if system_id in f.lower()][:20]

        return {
            "status": "success",
            "system": system_id,
            "primary_garden": mapping["primary"],
            "operating_gardens": mapping["operating"],
            "files": system_files,
            "file_count": len(system_files),
        }
    except Exception as e:
        return {
            "status": "success",
            "system": system_id,
            "primary_garden": mapping["primary"],
            "operating_gardens": mapping["operating"],
            "files": [],
            "error": str(e),
        }


def handle_garden_stats(**kwargs: Any) -> dict[str, Any]:
    """Get statistics about the garden directory."""
    try:
        from whitemagic.core.garden_directory import get_garden_directory
        from whitemagic.core.garden_function_registry import get_function_registry

        directory = get_garden_directory()
        registry = get_function_registry()

        file_stats = directory.get_stats()
        func_stats = registry.get_stats()

        return {
            "status": "success",
            "files": {
                "total": file_stats["total_files"],
                "by_garden": file_stats["gardens"],
                "by_type": file_stats["file_types"],
            },
            "functions": {
                "total": func_stats["total_functions"],
                "unique_names": func_stats["unique_names"],
                "public": func_stats["public_functions"],
                "private": func_stats["private_functions"],
                "by_garden": func_stats["gardens"],
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_garden_browse(**kwargs: Any) -> dict[str, Any]:
    """Browse the virtual garden filesystem.

    Args:
        path: Virtual path (e.g., "/gardens/wisdom", "/systems/memory")
    """
    path = kwargs.get("path", "/gardens")

    try:
        from whitemagic.core.garden_virtual_fs import get_garden_virtual_fs
        vfs = get_garden_virtual_fs()

        if not vfs._loaded:
            vfs.load()

        nodes = vfs.list_directory(path)

        return {
            "status": "success",
            "path": path,
            "entries": [
                {
                    "name": n.virtual_path.split("/")[-1],
                    "type": n.node_type,
                    "garden": n.garden,
                    "physical_path": n.physical_path,
                }
                for n in nodes
            ],
            "count": len(nodes),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_garden_resolve(**kwargs: Any) -> dict[str, Any]:
    """Resolve a virtual path to physical path.

    Args:
        virtual_path: Virtual path (e.g., "/gardens/wisdom/python/sqlite_backend.py")
    """
    virtual_path = kwargs.get("virtual_path", "")

    if not virtual_path:
        return {"status": "error", "error": "virtual_path parameter required"}

    try:
        from whitemagic.core.garden_virtual_fs import get_garden_virtual_fs
        vfs = get_garden_virtual_fs()

        if not vfs._loaded:
            vfs.load()

        physical = vfs.get_physical_path(virtual_path)

        if physical:
            return {
                "status": "success",
                "virtual_path": virtual_path,
                "physical_path": physical,
            }
        else:
            return {
                "status": "not_found",
                "virtual_path": virtual_path,
                "message": "Path not found or is a directory",
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}
