"""Spatial Memory Navigator — Query and navigate memories by 5D coordinates.

Provides tools to:
- Search memories by coordinate ranges (e.g., "find all emotional, abstract memories")
- Navigate from one memory to nearby memories in 5D space
- Find memories in specific galactic zones
- Discover "related but different" memories (close in some axes, far in others)

Usage:
    from whitemagic.tools.spatial_navigator import (
        find_by_zone, search_by_coordinates, find_neighbors, discover_related
    )

    # Find all memories in the CORE zone
    core_memories = find_by_zone("core", limit=10)

    # Search by coordinate ranges
    results = search_by_coordinates(
        x_range=(-1.0, -0.3),  # Emotional
        y_range=(0.5, 1.0),    # Abstract
        limit=10
    )

    # Find neighbors of a memory
    neighbors = find_neighbors("memory_id_123", k=5)

    # Discover memories related but different
    related = discover_related("memory_id_123", vary_axes=["y"])  # Same emotion/time, different abstraction
"""

from typing import Any


def find_by_zone(zone: str, limit: int = 20) -> list[dict[str, Any]]:
    """Find all memories in a specific galactic zone.

    Args:
        zone: One of "core", "inner_rim", "mid_band", "outer_rim", "far_edge"
        limit: Maximum results to return

    Returns:
        List of memory dicts with their coordinates
    """
    from whitemagic.core.memory.unified import get_unified_memory

    # Map zone name to distance range
    zone_ranges = {
        "core": (0.0, 0.15),
        "inner_rim": (0.15, 0.40),
        "inner": (0.15, 0.40),  # Alias
        "mid_band": (0.40, 0.65),
        "mid": (0.40, 0.65),  # Alias
        "outer_rim": (0.65, 0.85),
        "outer": (0.65, 0.85),  # Alias
        "far_edge": (0.85, 1.0),
        "edge": (0.85, 1.0),  # Alias
    }

    if zone not in zone_ranges:
        raise ValueError(f"Unknown zone: {zone}. Use: {list(zone_ranges.keys())}")

    min_dist, max_dist = zone_ranges[zone]

    um = get_unified_memory()
    results = []

    with um.backend.pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT m.id, m.title, m.content, m.memory_type,
                   hc.x, hc.y, hc.z, hc.w, hc.v,
                   m.galactic_distance
            FROM memories m
            JOIN holographic_coords hc ON m.id = hc.memory_id
            WHERE m.galactic_distance >= ? AND m.galactic_distance < ?
            ORDER BY m.galactic_distance
            LIMIT ?
            """,
            (min_dist, max_dist, limit),
        ).fetchall()

        for row in rows:
            results.append({
                "id": row[0],
                "title": row[1],
                "content_preview": row[2][:200] if row[2] else None,
                "type": row[3],
                "coordinates": {
                    "x": round(row[4], 3) if row[4] else None,
                    "y": round(row[5], 3) if row[5] else None,
                    "z": round(row[6], 3) if row[6] else None,
                    "w": round(row[7], 3) if row[7] else None,
                    "v": round(row[8], 3) if row[8] else None,
                },
                "galactic_distance": round(row[9], 3) if row[9] else None,
                "zone": zone,
            })

    return results


def search_by_coordinates(
    x_range: tuple[float, float] | None = None,
    y_range: tuple[float, float] | None = None,
    z_range: tuple[float, float] | None = None,
    w_range: tuple[float, float] | None = None,
    v_range: tuple[float, float] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search memories by 5D coordinate ranges.

    Args:
        x_range: (min, max) for Resonance (-1.0 to +1.0)
        y_range: (min, max) for Abstraction (-1.0 to +1.0)
        z_range: (min, max) for Chronos (-1.0 to +1.0)
        w_range: (min, max) for Gravity (0.0 to 2.0+)
        v_range: (min, max) for Vitality (0.0 to 1.0)
        limit: Maximum results

    Returns:
        List of matching memories with coordinates
    """
    from whitemagic.core.memory.unified import get_unified_memory

    um = get_unified_memory()

    # Build WHERE clause dynamically
    conditions: list[str] = []
    params: list[float] = []

    if x_range:
        conditions.append("hc.x >= ? AND hc.x <= ?")
        params.extend(x_range)
    if y_range:
        conditions.append("hc.y >= ? AND hc.y <= ?")
        params.extend(y_range)
    if z_range:
        conditions.append("hc.z >= ? AND hc.z <= ?")
        params.extend(z_range)
    if w_range:
        conditions.append("hc.w >= ? AND hc.w <= ?")
        params.extend(w_range)
    if v_range:
        conditions.append("hc.v >= ? AND hc.v <= ?")
        params.extend(v_range)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    results = []
    with um.backend.pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT m.id, m.title, m.content, m.memory_type,
                   hc.x, hc.y, hc.z, hc.w, hc.v,
                   m.galactic_distance
            FROM memories m
            JOIN holographic_coords hc ON m.id = hc.memory_id
            WHERE {where_clause}
            ORDER BY m.importance DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()

        for row in rows:
            results.append({
                "id": row[0],
                "title": row[1],
                "content_preview": row[2][:200] if row[2] else None,
                "type": row[3],
                "coordinates": {
                    "x": round(row[4], 3) if row[4] else None,
                    "y": round(row[5], 3) if row[5] else None,
                    "z": round(row[6], 3) if row[6] else None,
                    "w": round(row[7], 3) if row[7] else None,
                    "v": round(row[8], 3) if row[8] else None,
                },
                "galactic_distance": round(row[9], 3) if row[9] else None,
            })

    return results


def find_neighbors(memory_id: str, k: int = 5, radius: float | None = None, weights: dict[str, float] | None = None) -> list[dict[str, Any]]:
    """Find nearest neighbors of a memory in 5D space.

    Args:
        memory_id: The reference memory ID
        k: Number of neighbors to return
        radius: Optional max distance (overrides k if specified)
        weights: Optional axis weights for the query (x, y, z, w, v)

    Returns:
        List of neighboring memories with distances
    """
    from whitemagic.core.memory.holographic import get_holographic_memory
    from whitemagic.core.memory.unified import get_unified_memory
    from whitemagic.tools.coordinate_explainer import interpret_memory

    # Get reference memory coordinates
    um = get_unified_memory()
    ref_mem = um.recall(memory_id)

    if not ref_mem:
        return []

    # Use holographic index for efficient search
    holo = get_holographic_memory()

    # Build query from reference memory
    query_data = ref_mem.to_dict()

    if radius:
        raw_results = holo.query_radius(query_data, radius=radius, weights=weights)
    else:
        raw_results = holo.query_nearest(query_data, k=k + 1, weights=weights)  # +1 to exclude self

    # Filter out self and fetch details
    results = []
    for result in raw_results:
        if result.memory_id == memory_id:
            continue

        neighbor = um.recall(result.memory_id)
        if neighbor:
            interp = interpret_memory(neighbor.to_dict())
            results.append({
                "id": result.memory_id,
                "title": neighbor.title,
                "distance": round(result.distance, 4),
                "interpretation": interp["summary"],
                "zone": interp["zone"],
            })

    return results[:k]


def discover_related(
    memory_id: str,
    vary_axes: list[str] | None = None,
    preserve_axes: list[str] | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """Find memories that are similar but differ in specific dimensions.

    This is useful for finding "related but different" perspectives:
    - Same emotion, different abstraction level (vary_axes=["y"])
    - Same concept, different time orientation (vary_axes=["z"])
    - Same type, different emotional resonance (vary_axes=["x"])

    Args:
        memory_id: Reference memory
        vary_axes: List of axes to vary (x, y, z, w, v)
        preserve_axes: List of axes to keep similar (alternative to vary_axes)
        k: Number of results

    Returns:
        List of related memories with similarity scores
    """
    from whitemagic.core.memory.unified import get_unified_memory

    if vary_axes is None and preserve_axes is None:
        vary_axes = ["y"]  # Default: vary abstraction level

    um = get_unified_memory()

    # Get reference coordinates
    with um.backend.pool.connection() as conn:
        row = conn.execute(
            "SELECT x, y, z, w, v FROM holographic_coords WHERE memory_id = ?",
            (memory_id,),
        ).fetchone()

        if not row:
            return []

        ref_coords = {"x": row[0], "y": row[1], "z": row[2], "w": row[3], "v": row[4]}

    # Build query based on what to preserve vs vary
    all_axes = ["x", "y", "z", "w", "v"]

    if vary_axes:
        preserve = [a for a in all_axes if a not in vary_axes]
    else:
        preserve = preserve_axes or []
        vary_axes = [a for a in all_axes if a not in preserve]

    # Build ranges for preserved axes (tight) and varied axes (loose/default)
    ranges = {}
    for axis in preserve:
        val = ref_coords[axis]
        if val is not None:
            ranges[f"{axis}_range"] = (val - 0.2, val + 0.2)

    # Search with those ranges
    results = search_by_coordinates(**ranges, limit=k * 2)

    # Filter out self and calculate "difference score"
    filtered = []
    for mem in results:
        if mem["id"] == memory_id:
            continue

        coords = mem["coordinates"]
        diff_score = 0.0
        diff_explanation = []

        for axis in vary_axes:
            ref_val = ref_coords.get(axis, 0)
            mem_val = coords.get(axis, 0) if coords else 0
            if ref_val is not None and mem_val is not None:
                diff = abs(ref_val - mem_val)
                diff_score += diff
                if diff > 0.3:
                    axis_names = {"x": "resonance", "y": "abstraction", "z": "time", "w": "gravity", "v": "vitality"}
                    diff_explanation.append(f"different {axis_names.get(axis, axis)}")

        filtered.append({
            **mem,
            "difference_score": round(diff_score, 3),
            "varied_axes": vary_axes,
            "preserved_axes": preserve,
            "key_differences": diff_explanation,
        })

    # Sort by difference score (most interesting variations first)
    filtered.sort(key=lambda x: x["difference_score"], reverse=True)

    return filtered[:k]


def analyze_position(memory_id: str) -> dict[str, Any]:
    """Full coordinate analysis of a single memory.

    Returns comprehensive information about where a memory sits in 5D space
    and what that position means.
    """
    from whitemagic.core.memory.galactic_map import classify_zone
    from whitemagic.core.memory.unified import get_unified_memory
    from whitemagic.tools.coordinate_explainer import explain_coordinates

    um = get_unified_memory()
    mem = um.recall(memory_id)

    if not mem:
        return {"error": f"Memory {memory_id} not found"}

    # Get coordinates
    with um.backend.pool.connection() as conn:
        row = conn.execute(
            "SELECT x, y, z, w, v FROM holographic_coords WHERE memory_id = ?",
            (memory_id,),
        ).fetchone()

        if not row:
            return {"error": "No coordinates found for this memory"}

        x, y, z, w, v = row

    # Basic interpretation
    interp = explain_coordinates(x or 0, y or 0, z or 0, w or 0.5, v or 0.5)

    # Zone classification
    zone = classify_zone(mem.galactic_distance or 0.5)

    # Find neighbors
    neighbors = find_neighbors(memory_id, k=3)

    # Count memories in similar position
    with um.backend.pool.connection() as conn:
        similar_count = conn.execute(
            """
            SELECT COUNT(*) FROM holographic_coords
            WHERE ABS(x - ?) < 0.3 AND ABS(y - ?) < 0.3 AND ABS(z - ?) < 0.3
            """,
            (x, y, z),
        ).fetchone()[0]

    return {
        "memory": {
            "id": memory_id,
            "title": mem.title,
            "type": mem.memory_type,
        },
        "coordinates": interp["axes"],
        "summary": interp["summary"],
        "zone": zone.value,
        "galactic_distance": round(mem.galactic_distance or 0.5, 3),
        "nearest_neighbors": neighbors,
        "similar_memories_count": similar_count,
        "characteristics": interp["characteristics"],
    }


# CLI support
if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python spatial_navigator.py zone <zone_name> [limit]")
        print("  python spatial_navigator.py analyze <memory_id>")
        print("  python spatial_navigator.py neighbors <memory_id> [k]")
        print("")
        print("Zones: core, inner_rim, mid_band, outer_rim, far_edge")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "zone":
        zone_name = sys.argv[2] if len(sys.argv) > 2 else "core"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        results = find_by_zone(zone_name, limit)
        print(json.dumps(results, indent=2))

    elif cmd == "analyze":
        mem_id = sys.argv[2] if len(sys.argv) > 2 else None
        if not mem_id:
            print("Error: memory_id required")
            sys.exit(1)
        result = analyze_position(mem_id)
        print(json.dumps(result, indent=2))

    elif cmd == "neighbors":
        mem_id = sys.argv[2] if len(sys.argv) > 2 else None
        if not mem_id:
            print("Error: memory_id required")
            sys.exit(1)
        k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        results = find_neighbors(mem_id, k=k)
        print(json.dumps(results, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
