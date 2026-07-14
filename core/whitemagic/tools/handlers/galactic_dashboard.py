# ruff: noqa: BLE001
"""Galactic dashboard handler — real-time galactic map visualization data."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_galactic_dashboard(**kwargs: Any) -> dict[str, Any]:
    """Return comprehensive galactic map visualization data.

    Fast path: reads meta galaxy summaries when available (per-galaxy
    memory counts, top tags) avoiding full GalacticMap scan of all 22 DBs.
    """
    # ── Fast path: meta galaxy summaries ──
    try:
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()
        summaries = um.search("", galaxy="meta", limit=30)
        # Filter to only Galaxy Summary entries
        summaries = [
            m for m in summaries
            if "Galaxy Summary" in str(getattr(m, "title", ""))
        ]
        if summaries:
            galaxy_stats: dict[str, dict[str, Any]] = {}
            total = 0
            for mem in summaries:
                title = getattr(mem, "title", "")
                content = getattr(mem, "content", "")
                if not content:
                    try:
                        content = getattr(mem, "_content", "")
                    except Exception:
                        logger.debug("Ignored error in galactic_dashboard.py:36")
                # Parse content dict from memory repr
                if isinstance(content, str) and content.startswith("{"):
                    try:
                        import ast
                        data = ast.literal_eval(content)
                    except (ValueError, SyntaxError):
                        try:
                            import json
                            data = json.loads(content.replace("'", '"'))
                        except Exception:
                            continue
                elif isinstance(content, dict):
                    data = content
                else:
                    continue
                name = data.get("name", "unknown")
                count = int(data.get("memory_count", 0))
                galaxy_stats[name] = {
                    "memory_count": count,
                    "top_tags": data.get("top_tags", [])[:5],
                }
                total += count
            if galaxy_stats:
                # Compute approximate zone distribution from counts
                zones = {"core": 0, "inner_rim": 0, "mid_band": 0, "outer_rim": 0, "far_edge": 0}
                distribution = {}
                if total > 0:
                    # Heuristic: distribute galaxy counts across zones
                    sorted_galaxies = sorted(galaxy_stats.items(), key=lambda x: x[1]["memory_count"], reverse=True)
                    n = len(sorted_galaxies)
                    for i, (_, info) in enumerate(sorted_galaxies):
                        frac = i / max(n - 1, 1)
                        count = info["memory_count"]
                        if frac < 0.2:
                            zones["core"] += count
                        elif frac < 0.4:
                            zones["inner_rim"] += count
                        elif frac < 0.6:
                            zones["mid_band"] += count
                        elif frac < 0.8:
                            zones["outer_rim"] += count
                        else:
                            zones["far_edge"] += count
                    distribution = {z: round(c / total, 4) for z, c in zones.items() if c > 0}
                return {
                    "status": "success",
                    "source": "meta_galaxy",
                    "galaxies": galaxy_stats,
                    "total_memories": total,
                    "zones": zones,
                    "distribution": distribution,
                }
    except Exception:
        logger.debug("Meta galaxy fast path skipped", exc_info=True)

    # ── Full path: GalacticMap scan ──
    try:
        from whitemagic.core.memory.galactic_map import GalacticMap

        gm = GalacticMap()
        zones = gm.get_zone_counts()
        total = sum(zones.values())

        # Compute distribution percentages
        distribution = {}
        if total > 0:
            distribution = {
                zone: round(count / total, 4) for zone, count in zones.items()
            }

        # Attempt to get constellation and distance stats
        constellations = 0
        avg_distance = 0.0
        try:
            constellations = (
                len(gm.constellations) if hasattr(gm, "constellations") else 0
            )
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass
        try:
            if hasattr(gm, "get_average_distance"):
                avg_distance = gm.get_average_distance()
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass

        return {
            "status": "success",
            "zones": zones,
            "total_memories": total,
            "distribution": distribution,
            "constellations": constellations,
            "avg_distance": round(avg_distance, 4),
            "zone_labels": {
                "core": "CORE (distance < 0.2)",
                "inner_rim": "INNER_RIM (0.2–0.4)",
                "mid_band": "MID_BAND (0.4–0.6)",
                "outer_rim": "OUTER_RIM (0.6–0.8)",
                "far_edge": "FAR_EDGE (> 0.8)",
            },
        }
    except ImportError:
        return {
            "status": "success",
            "zones": {
                "core": 0,
                "inner_rim": 0,
                "mid_band": 0,
                "outer_rim": 0,
                "far_edge": 0,
            },
            "total_memories": 0,
            "distribution": {},
            "constellations": 0,
            "avg_distance": 0.0,
            "note": "GalacticMap not initialized",
        }
    except Exception as exc:
        logger.warning("Galactic dashboard error: %s", exc)
        return {
            "status": "error",
            "error": str(exc),
            "error_code": "galactic_map_failure",
        }
