"""Constellation Explainer — Understand memory clusters in 5D space.

Provides tools to:
- Explain what a constellation represents conceptually
- Find which constellation a memory belongs to
- Discover constellations in specific regions of 5D space
- Compare constellations

Usage:
    from whitemagic.tools.constellation_explainer import (
        explain_constellation, find_constellation_for_memory,
        list_constellations_in_region, compare_constellations
    )
"""

from typing import Any


def explain_constellation(constellation_name: str) -> dict[str, Any]:
    """Get a human-readable explanation of what a constellation represents.

    Args:
        constellation_name: Name of the constellation

    Returns:
        Explanation of the constellation's meaning and characteristics
    """
    from whitemagic.core.memory.constellations import get_constellation_detector

    detector = get_constellation_detector()
    constellations = detector.list_constellations()

    # Find the constellation
    constellation = None
    for c in constellations:
        if c.name == constellation_name:
            constellation = c
            break

    if not constellation:
        return {"error": f"Constellation '{constellation_name}' not found"}

    # Interpret the centroid coordinates
    from whitemagic.tools.coordinate_explainer import explain_coordinates

    x, y, z, w, v = constellation.centroid
    coord_interp = explain_coordinates(x, y, z, w, v)

    # Analyze what this cluster represents
    characteristics = []

    if len(constellation.member_ids) < 3:
        characteristics.append("small emergent cluster")
    elif len(constellation.member_ids) < 10:
        characteristics.append("medium-sized theme")
    else:
        characteristics.append("major thematic constellation")

    if constellation.stability > 0.7:
        characteristics.append("highly stable")
    elif constellation.stability > 0.3:
        characteristics.append("moderately stable")
    else:
        characteristics.append("emerging/dynamic")

    # What the constellation represents based on coordinates
    representation = []

    # X-axis insight
    if x < -0.5:
        representation.append("emotional/intuitive content")
    elif x > 0.5:
        representation.append("analytical/technical content")
    else:
        representation.append("balanced perspective")

    # Y-axis insight
    if y < -0.5:
        representation.append("concrete details and specifics")
    elif y > 0.5:
        representation.append("abstract patterns and principles")
    else:
        representation.append("mixed detail levels")

    # Z-axis insight
    if z < -0.5:
        representation.append("historical/archived material")
    elif z > 0.5:
        representation.append("future-oriented/vision content")
    else:
        representation.append("current/present focus")

    # V-axis insight (zone)
    if v > 0.7:
        representation.append("actively used memories")
    elif v < 0.3:
        representation.append("archived but preserved")

    return {
        "name": constellation.name,
        "size": len(constellation.member_ids),
        "centroid": coord_interp["axes"],
        "summary": coord_interp["summary"],
        "zone": coord_interp["zone"],
        "characteristics": characteristics,
        "represents": representation,
        "dominant_tags": constellation.dominant_tags[:5],
        "dominant_type": constellation.dominant_type,
        "stability": round(constellation.stability, 2),
        "radius": round(constellation.radius, 3),
        "avg_importance": round(constellation.avg_importance, 2),
    }


def find_constellation_for_memory(memory_id: str) -> dict[str, Any] | None:
    """Find which constellation(s) a memory belongs to.

    Args:
        memory_id: The memory to look up

    Returns:
        Constellation info or None if not in any constellation
    """
    from whitemagic.core.memory.constellations import get_constellation_detector

    detector = get_constellation_detector()
    constellations = detector.list_constellations()

    memberships = []
    for c in constellations:
        if memory_id in c.member_ids:
            memberships.append({
                "name": c.name,
                "size": len(c.member_ids),
                "centroid": {
                    "x": round(c.centroid[0], 3),
                    "y": round(c.centroid[1], 3),
                    "z": round(c.centroid[2], 3),
                },
            })

    if not memberships:
        return None

    return {
        "memory_id": memory_id,
        "constellation_count": len(memberships),
        "constellations": memberships,
    }


def list_constellations_in_region(
    x_range: tuple[float, float] | None = None,
    y_range: tuple[float, float] | None = None,
    z_range: tuple[float, float] | None = None,
) -> list[dict[str, Any]]:
    """Find constellations whose centroids fall within a 5D region.

    Args:
        x_range: (min, max) for Resonance
        y_range: (min, max) for Abstraction
        z_range: (min, max) for Chronos

    Returns:
        List of constellations in that region
    """
    from whitemagic.core.memory.constellations import get_constellation_detector

    detector = get_constellation_detector()
    constellations = detector.list_constellations()

    results = []
    for c in constellations:
        x, y, z, w, v = c.centroid

        # Check if in range
        in_range = True
        if x_range and not (x_range[0] <= x <= x_range[1]):
            in_range = False
        if y_range and not (y_range[0] <= y <= y_range[1]):
            in_range = False
        if z_range and not (z_range[0] <= z <= z_range[1]):
            in_range = False

        if in_range:
            results.append({
                "name": c.name,
                "size": len(c.member_ids),
                "centroid": {
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "z": round(z, 3),
                },
                "dominant_tags": c.dominant_tags[:3],
            })

    return results


def compare_constellations(name1: str, name2: str) -> dict[str, Any]:
    """Compare two constellations to understand their relationship.

    Args:
        name1: First constellation name
        name2: Second constellation name

    Returns:
        Comparison analysis
    """
    from whitemagic.core.memory.constellations import get_constellation_detector
    from whitemagic.tools.coordinate_explainer import explain_coordinates

    detector = get_constellation_detector()
    constellations = detector.list_constellations()

    c1 = None
    c2 = None
    for c in constellations:
        if c.name == name1:
            c1 = c
        if c.name == name2:
            c2 = c

    if not c1:
        return {"error": f"Constellation '{name1}' not found"}
    if not c2:
        return {"error": f"Constellation '{name2}' not found"}

    # Calculate centroid distance
    x1, y1, z1, w1, v1 = c1.centroid
    x2, y2, z2, w2, v2 = c2.centroid

    distance = ((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2 + (w1-w2)**2 + (v1-v2)**2) ** 0.5

    # Differences per axis
    axis_diffs = {
        "x": round(abs(x1 - x2), 3),  # Resonance difference
        "y": round(abs(y1 - y2), 3),  # Abstraction difference
        "z": round(abs(z1 - z2), 3),  # Chronos difference
        "w": round(abs(w1 - w2), 3),  # Gravity difference
        "v": round(abs(v1 - v2), 3),  # Vitality difference
    }

    # Interpret the relationship
    relationship = []

    if axis_diffs["x"] > 0.5:
        relationship.append("different emotional/logical resonance")
    if axis_diffs["y"] > 0.5:
        relationship.append("different abstraction levels")
    if axis_diffs["z"] > 0.5:
        relationship.append("different temporal orientations")
    if axis_diffs["v"] > 0.5:
        relationship.append("different lifecycle zones")

    if not relationship:
        relationship.append("closely related themes")

    # Get interpretations
    interp1 = explain_coordinates(x1, y1, z1, w1, v1)
    interp2 = explain_coordinates(x2, y2, z2, w2, v2)

    return {
        "constellation_1": {
            "name": name1,
            "summary": interp1["summary"],
            "size": len(c1.member_ids),
        },
        "constellation_2": {
            "name": name2,
            "summary": interp2["summary"],
            "size": len(c2.member_ids),
        },
        "centroid_distance": round(distance, 3),
        "axis_differences": axis_diffs,
        "relationship": relationship,
        "shared_tags": list(set(c1.dominant_tags) & set(c2.dominant_tags)),
    }


def get_constellation_summary() -> dict[str, Any]:
    """Get a high-level summary of all constellations in the system."""
    from whitemagic.core.memory.constellations import get_constellation_detector
    from whitemagic.tools.coordinate_explainer import explain_coordinates

    detector = get_constellation_detector()
    constellations = detector.list_constellations()

    if not constellations:
        return {"count": 0, "note": "No constellations detected yet"}

    # Calculate aggregate statistics
    zones = {"core": 0, "inner_rim": 0, "mid_band": 0, "outer_rim": 0, "far_edge": 0}
    total_memories = 0

    summaries = []
    for c in constellations:
        x, y, z, w, v = c.centroid
        interp = explain_coordinates(x, y, z, w, v)
        zone = interp["zone"]
        zones[zone] = zones.get(zone, 0) + 1
        total_memories += len(c.member_ids)

        summaries.append({
            "name": c.name,
            "size": len(c.member_ids),
            "zone": zone,
            "summary": interp["summary"],
        })

    return {
        "constellation_count": len(constellations),
        "total_memories_in_constellations": total_memories,
        "zone_distribution": zones,
        "constellations": summaries,
    }
