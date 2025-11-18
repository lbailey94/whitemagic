"""Metrics collection for continuous self-improvement."""

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Token tracking
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


def estimate_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Estimate token count for text.

    Args:
        text: Text to estimate tokens for
        model: Model to use for encoding (default: gpt-3.5-turbo)

    Returns:
        Estimated token count
    """
    if TIKTOKEN_AVAILABLE:
        try:
            enc = tiktoken.encoding_for_model(model)
            return len(enc.encode(text))
        except Exception:
            # Fallback if model not recognized
            pass

    # Fallback: rough estimate (1 token ≈ 4 characters)
    return len(text) // 4


@dataclass
class TaskMetric:
    """Single task execution metric."""

    task_name: str
    duration_s: float
    tokens_used: int
    status: str
    timestamp: str
    phase: str = "unknown"
    error: str = ""


class MetricsCollector:
    """Collect and analyze execution metrics."""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path(".whitemagic/metrics.jsonl")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics: List[TaskMetric] = []
        self._context_buffer: List[str] = []  # Track text for token counting

    def add_context(self, text: str):
        """Add text to context buffer for token tracking.

        Call this when processing text (e.g., reading files, memories).
        """
        self._context_buffer.append(text)

    def clear_context(self):
        """Clear the context buffer."""
        self._context_buffer = []

    @contextmanager
    def track_task(self, task_name: str, phase: str = "unknown", track_tokens: bool = True):
        """Track task execution time and status.

        Args:
            task_name: Name of the task
            phase: Current phase (e.g., "search", "analyze")
            track_tokens: Whether to count tokens from context buffer
        """
        start = time.time()

        # Clear buffer at start of task
        self.clear_context()

        try:
            yield self  # Yield self so caller can use add_context()
            status = "success"
            error = ""
        except Exception as e:
            status = "failure"
            error = str(e)
            raise
        finally:
            duration = time.time() - start

            # Calculate tokens from buffered context
            tokens_used = 0
            if track_tokens and self._context_buffer:
                combined_text = "\n".join(self._context_buffer)
                tokens_used = estimate_tokens(combined_text)

            metric = TaskMetric(
                task_name=task_name,
                duration_s=duration,
                tokens_used=tokens_used,
                status=status,
                timestamp=datetime.now().isoformat(),
                phase=phase,
                error=error,
            )
            self.metrics.append(metric)
            self._save_metric(metric)

            # Clear buffer after task
            self.clear_context()

    def _save_metric(self, metric: TaskMetric):
        """Append metric to storage."""
        with open(self.storage_path, "a") as f:
            json.dump(metric.__dict__, f)
            f.write("\n")

    def get_summary(self, categories: List[str] = None) -> Dict[str, Any]:
        """Get metrics summary.

        Args:
            categories: Optional list of categories to filter by

        Returns:
            Dict with expected structure for CLI display
        """
        # Load all metrics from storage file
        all_metrics = []
        task_metrics = []

        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    for line in f:
                        if line.strip():
                            metric = json.loads(line.strip())
                            all_metrics.append(metric)
                            if "task_name" in metric:  # Task metric
                                task_metrics.append(metric)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # Group custom metrics by category
        summary = {}
        for metric in all_metrics:
            if "category" in metric:  # Custom metric
                category = metric.get("category", "unknown")
                if category not in summary:
                    summary[category] = {"count": 0, "latest": None}
                summary[category]["count"] += 1
                summary[category]["latest"] = metric

        # Add comprehensive task metrics summary
        if task_metrics or self.metrics:
            all_tasks = task_metrics + [m.__dict__ for m in self.metrics]

            total_tokens = sum(m.get("tokens_used", 0) for m in all_tasks)
            total_duration = sum(m.get("duration_s", 0) for m in all_tasks)
            success_count = sum(1 for m in all_tasks if m.get("status") == "success")

            summary["tasks"] = {
                "count": len(all_tasks),
                "total_tokens": total_tokens,
                "avg_tokens": total_tokens / len(all_tasks) if all_tasks else 0,
                "total_duration_s": total_duration,
                "avg_duration_s": total_duration / len(all_tasks) if all_tasks else 0,
                "success_rate": success_count / len(all_tasks) if all_tasks else 0,
                "latest": all_tasks[-1] if all_tasks else None,
            }

            # Add token tracking status
            summary["token_tracking"] = {
                "available": TIKTOKEN_AVAILABLE,
                "method": "tiktoken" if TIKTOKEN_AVAILABLE else "fallback (4 chars/token)",
            }

        return summary


# Global instance
_collector = MetricsCollector()


def track_task(task_name: str, phase: str = "unknown"):
    """Convenience function for tracking."""
    return _collector.track_task(task_name, phase)


def track_metric(category: str, metric: str, value: float, context: str = ""):
    """Track a custom metric value."""
    from datetime import datetime

    metric_data = {
        "category": category,
        "metric": metric,
        "value": value,
        "context": context,
        "timestamp": datetime.now().isoformat(),
    }

    # Save to metrics file
    with open(_collector.storage_path, "a") as f:
        json.dump(metric_data, f)
        f.write("\n")


def get_tracker():
    """Get the global metrics collector instance."""
    return _collector
