"""Metrics bridge — Hologram and metric tracking."""
import logging
from typing import Any, cast

logger = logging.getLogger(__name__)


def get_metrics_summary() -> dict[str, Any]:
    """Get summary of all tracked metrics."""
    from whitemagic.core.memory.hologram import HologramCache

    cache = HologramCache()
    stats = cache.get_stats()

    return {
        "status": "success",
        "metrics": {
            "hologram_entries": stats.get("entry_count", 0),
            "cache_size_mb": stats.get("size_mb", 0.0),
            "hit_rate": stats.get("hit_rate", 0.0),
        }
    }


def track_metric(**kwargs: Any) -> dict[str, Any]:
    """Compatibility wrapper for metrics tracking."""
    from whitemagic.metrics import track_metric as _track_metric

    category = str(kwargs.get("category", "general"))
    metric = kwargs.get("metric")
    value = float(kwargs.get("value", 1.0))
    context = kwargs.get("context", "")

    return cast(
        dict[str, Any],
        _track_metric(category=category, metric=metric, value=value, context=context),
    )
