"""Galactic dashboard handler — real-time galactic map visualization data."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_galactic_dashboard(**kwargs: Any) -> dict[str, Any]:
    """Return comprehensive galactic map visualization data."""
    try:
        from whitemagic.core.memory.galactic_map import GalacticMap

        gm = GalacticMap()
        zones = gm.get_zone_counts()
        total = sum(zones.values())

        # Compute distribution percentages
        distribution = {}
        if total > 0:
            distribution = {
                zone: round(count / total, 4)
                for zone, count in zones.items()
            }

        # Attempt to get constellation and distance stats
        constellations = 0
        avg_distance = 0.0
        try:
            constellations = len(gm.constellations) if hasattr(gm, "constellations") else 0
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
            "zones": {"core": 0, "inner_rim": 0, "mid_band": 0, "outer_rim": 0, "far_edge": 0},
            "total_memories": 0,
            "distribution": {},
            "constellations": 0,
            "avg_distance": 0.0,
            "note": "GalacticMap not initialized",
        }
    except Exception as exc:
        logger.warning("Galactic dashboard error: %s", exc)
        return {"status": "error", "error": str(exc), "error_code": "galactic_map_failure"}
