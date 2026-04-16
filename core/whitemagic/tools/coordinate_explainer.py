"""Coordinate Explainer — Simple tool to interpret 5D holographic coordinates.

Usage:
    from whitemagic.tools.coordinate_explainer import explain_coordinates, interpret_memory

    # Explain raw coordinates
    explanation = explain_coordinates(x=0.7, y=-0.3, z=0.1, w=1.2, v=0.8)
    print(explanation["summary"])

    # Interpret a memory's coordinates
    mem = memory.to_dict()
    interpretation = interpret_memory(mem)
    print(interpretation)
"""

from typing import Any, cast


def explain_coordinates(x: float, y: float, z: float, w: float, v: float) -> dict[str, Any]:
    """Convert raw 5D coordinates into human-readable interpretation.

    Args:
        x: Resonance (-1.0=emotion to +1.0=logic)
        y: Abstraction (-1.0=micro to +1.0=macro)
        z: Chronos (-1.0=past to +1.0=future)
        w: Gravity (0.0 to 2.0+, importance/weight)
        v: Vitality (0.0=edge to 1.0=core, aliveness)

    Returns:
        Dictionary with detailed interpretation
    """
    # X interpretation
    if x < -0.6:
        x_desc = "Deeply emotional / intuitive"
        x_emoji = "🧡"
    elif x < -0.2:
        x_desc = "Emotionally resonant"
        x_emoji = "💛"
    elif x < 0.2:
        x_desc = "Balanced logic/emotion"
        x_emoji = "⚖️"
    elif x < 0.6:
        x_desc = "Logically oriented"
        x_emoji = "🧠"
    else:
        x_desc = "Highly analytical / technical"
        x_emoji = "🔬"

    # Y interpretation
    if y < -0.6:
        y_desc = "Very concrete / specific"
        y_emoji = "🔍"
    elif y < -0.2:
        y_desc = "Detailed / operational"
        y_emoji = "📋"
    elif y < 0.2:
        y_desc = "Mid-level abstraction"
        y_emoji = "📊"
    elif y < 0.6:
        y_desc = "Abstract / strategic"
        y_emoji = "🗺️"
    else:
        y_desc = "Highly abstract / wisdom-level"
        y_emoji = "🔮"

    # Z interpretation
    if z < -0.6:
        z_desc = "Deep archive / historical"
        z_emoji = "📜"
    elif z < -0.2:
        z_desc = "Recent past"
        z_emoji = "📚"
    elif z < 0.2:
        z_desc = "Present moment"
        z_emoji = "📍"
    elif z < 0.6:
        z_desc = "Near future / upcoming"
        z_emoji = "🎯"
    else:
        z_desc = "Future vision / long-term"
        z_emoji = "🔭"

    # W interpretation
    if w < 0.3:
        w_desc = "Trivial / transient"
        w_emoji = "🍃"
    elif w < 0.7:
        w_desc = "Normal importance"
        w_emoji = "📄"
    elif w < 1.0:
        w_desc = "Important"
        w_emoji = "⭐"
    elif w < 1.5:
        w_desc = "Critical / high gravity"
        w_emoji = "🌟"
    else:
        w_desc = "Attractor / core significance"
        w_emoji = "🌑"

    # V interpretation (maps to galactic zones)
    if v >= 0.85:
        v_desc = "CORE — Hot, spotlight"
        v_emoji = "☀️"
        zone = "core"
    elif v >= 0.6:
        v_desc = "INNER_RIM — Stable, important"
        v_emoji = "🌕"
        zone = "inner_rim"
    elif v >= 0.35:
        v_desc = "MID_BAND — Moderate relevance"
        v_emoji = "🌗"
        zone = "mid_band"
    elif v >= 0.15:
        v_desc = "OUTER_RIM — Fading"
        v_emoji = "🌘"
        zone = "outer_rim"
    else:
        v_desc = "FAR_EDGE — Deep archive"
        v_emoji = "🌑"
        zone = "far_edge"

    # Build summary
    characteristics = []
    if abs(x) > 0.5:
        characteristics.append("emotional" if x < 0 else "analytical")
    if abs(y) > 0.5:
        characteristics.append("concrete" if y < 0 else "abstract")
    if abs(z) > 0.5:
        characteristics.append("past-focused" if z < 0 else "future-oriented")
    if w > 1.0:
        characteristics.append("high-priority")
    if v > 0.7:
        characteristics.append("active")
    elif v < 0.3:
        characteristics.append("archived")

    summary = f"{x_emoji} {y_emoji} {z_emoji} {w_emoji} {v_emoji} — A {', '.join(characteristics) if characteristics else 'balanced'} memory in the {zone.replace('_', ' ')}"

    return {
        "summary": summary,
        "characteristics": characteristics,
        "zone": zone,
        "axes": {
            "x": {"value": round(x, 3), "label": "Resonance", "description": x_desc, "emoji": x_emoji},
            "y": {"value": round(y, 3), "label": "Abstraction", "description": y_desc, "emoji": y_emoji},
            "z": {"value": round(z, 3), "label": "Chronos", "description": z_desc, "emoji": z_emoji},
            "w": {"value": round(w, 3), "label": "Gravity", "description": w_desc, "emoji": w_emoji},
            "v": {"value": round(v, 3), "label": "Vitality", "description": v_desc, "emoji": v_emoji},
        },
        "coordinate_vector": [round(x, 3), round(y, 3), round(z, 3), round(w, 3), round(v, 3)],
    }


def interpret_memory(memory: dict[str, Any]) -> dict[str, Any]:
    """Interpret a memory's holographic coordinates from its metadata.

    Args:
        memory: Memory dict with holographic_* or coordinate fields

    Returns:
        Same format as explain_coordinates(), with memory info added
    """
    # Extract coordinates from various possible field names
    x = memory.get("holographic_x", memory.get("x", 0.0))
    y = memory.get("holographic_y", memory.get("y", 0.0))
    z = memory.get("holographic_z", memory.get("z", 0.0))
    w = memory.get("holographic_w", memory.get("w", 0.5))
    v = memory.get("holographic_v", memory.get("v", 0.5))

    # Get galactic distance if available
    galactic_distance = memory.get("galactic_distance")

    result = explain_coordinates(x, y, z, w, v)
    result["memory"] = {
        "id": memory.get("id", "unknown")[:8] + "...",
        "title": memory.get("title", "Untitled"),
        "type": memory.get("memory_type", memory.get("type", "unknown")),
    }
    if galactic_distance is not None:
        result["memory"]["galactic_distance"] = round(galactic_distance, 3)

    return result


def quick_lookup(memory_or_coords: dict[str, Any] | list[float]) -> str:
    """Ultra-simple one-liner to interpret coordinates.

    Args:
        memory_or_coords: Either a memory dict or a [x, y, z, w, v] list

    Returns:
        Short human-readable summary string

    Example:
        >>> quick_lookup([0.7, 0.8, -0.3, 1.2, 0.9])
        '🧠 🗺️ 📚 ⭐ ☀️ — analytical, abstract, active memory in the core'
    """
    if isinstance(memory_or_coords, list):
        if len(memory_or_coords) != 5:
            return "Error: Need exactly 5 coordinates [x, y, z, w, v]"
        x, y, z, w, v = memory_or_coords
        return cast(str, explain_coordinates(x, y, z, w, v)["summary"])
    else:
        return cast(str, interpret_memory(memory_or_coords)["summary"])


# CLI support
if __name__ == "__main__":
    import sys

    if len(sys.argv) == 6:
        # python coordinate_explainer.py 0.7 -0.3 0.1 1.2 0.8
        x, y, z, w, v = map(float, sys.argv[1:6])
        result = explain_coordinates(x, y, z, w, v)
        print(result["summary"])
        print()
        for axis, info in result["axes"].items():
            print(f"  {info['emoji']} {axis.upper()} ({info['label']}): {info['value']:+.3f} — {info['description']}")
    else:
        print("Usage: python coordinate_explainer.py <x> <y> <z> <w> <v>")
        print("  x: Resonance    (-1.0=emotion to +1.0=logic)")
        print("  y: Abstraction  (-1.0=micro to +1.0=macro)")
        print("  z: Chronos      (-1.0=past to +1.0=future)")
        print("  w: Gravity      (0.0 to 2.0+, importance)")
        print("  v: Vitality     (0.0=edge to 1.0=core)")
        print()
        print("Example: python coordinate_explainer.py 0.7 -0.3 0.1 1.2 0.8")
