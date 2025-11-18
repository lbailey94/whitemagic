"""
Metrics tracking system for WhiteMagic.

Enables quantitative self-assessment and continuous improvement.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MetricsTracker:
    """Track and analyze performance metrics across sessions."""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize metrics tracker.

        Args:
            base_dir: Base directory for metrics storage
        """
        if base_dir is None:
            base_dir = Path.home() / ".whitemagic"

        self.base_dir = Path(base_dir)
        self.metrics_dir = self.base_dir / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def track(
        self,
        category: str,
        metric: str,
        value: float,
        context: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Record a metric.

        Args:
            category: Metric category (e.g., "token_efficiency")
            metric: Metric name (e.g., "usage_percent")
            value: Metric value
            context: Optional context (e.g., "v2.2.3 Phase 1")
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        entry = {
            "timestamp": timestamp.isoformat(),
            "category": category,
            "metric": metric,
            "value": value,
            "context": context,
        }

        # Append to metrics file
        metrics_file = self.metrics_dir / f"{category}.jsonl"
        with open(metrics_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_metrics(
        self, category: str, metric: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent metrics for a category.

        Args:
            category: Metric category
            metric: Optional specific metric name
            limit: Maximum number of entries to return

        Returns:
            List of metric entries (newest first)
        """
        metrics_file = self.metrics_dir / f"{category}.jsonl"

        if not metrics_file.exists():
            return []

        entries = []
        with open(metrics_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if metric is None or entry.get("metric") == metric:
                        entries.append(entry)
                except Exception:
                    continue

        # Return newest first
        return sorted(entries, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_summary(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get summary of all metrics.

        Args:
            categories: Optional list of categories to include

        Returns:
            Dict with summary statistics
        """
        if categories is None:
            categories = ["token_efficiency", "strategic", "tactical", "learning", "performance"]

        summary = {}

        for category in categories:
            metrics_file = self.metrics_dir / f"{category}.jsonl"

            if not metrics_file.exists():
                summary[category] = {"count": 0, "latest": None}
                continue

            entries = self.get_metrics(category, limit=10)

            if entries:
                summary[category] = {
                    "count": len(entries),
                    "latest": entries[0],
                    "average": sum(
                        e["value"] for e in entries if isinstance(e.get("value"), (int, float))
                    )
                    / len(entries),
                }
            else:
                summary[category] = {"count": 0, "latest": None}

        return summary


# Global tracker instance
_tracker = None


def get_tracker() -> MetricsTracker:
    """Get global metrics tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = MetricsTracker()
    return _tracker


def track_metric(category: str, metric: str, value: float, context: Optional[str] = None):
    """
    Convenience function to track a metric.

    Args:
        category: Metric category
        metric: Metric name
        value: Metric value
        context: Optional context
    """
    tracker = get_tracker()
    tracker.track(category, metric, value, context)
