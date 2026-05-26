"""
Benchmark Historical Tracker
=============================

Tracks benchmark results over time for regression detection and trend analysis.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from whitemagic.config.paths import BENCHMARKS_DIR

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """A single benchmark result."""
    name: str
    duration_ms: float
    ops_per_sec: float
    timestamp: str
    version: str
    metadata: Dict[str, Any]


@dataclass
class BenchmarkComparison:
    """Comparison between two benchmark runs."""
    benchmark_name: str
    baseline_ms: float
    current_ms: float
    improvement_pct: float
    is_regression: bool
    threshold_pct: float = 5.0  # 5% regression threshold


class BenchmarkHistoryTracker:
    """Track and compare benchmark results over time."""

    def __init__(self, history_file: Optional[Path] = None):
        self.history_file = history_file or BENCHMARKS_DIR / "history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        self.history: List[Dict[str, Any]] = []
        self.load_history()

    def load_history(self):
        """Load benchmark history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
                logger.info(f"📊 Loaded {len(self.history)} historical benchmark runs")
            except Exception as e:
                logger.error(f"Failed to load history: {e}")
                self.history = []
        else:
            self.history = []

    def save_history(self):
        """Save benchmark history to file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
            logger.info(f"💾 Saved benchmark history to {self.history_file}")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def record_run(self, results: List[BenchmarkResult], version: str = "unknown"):
        """Record a new benchmark run."""
        run_data = {
            "timestamp": datetime.now().isoformat(),
            "version": version,
            "results": [asdict(r) for r in results],
        }

        self.history.append(run_data)
        self.save_history()

        logger.info(f"✅ Recorded benchmark run with {len(results)} results")

    def get_latest_run(self) -> Optional[Dict[str, Any]]:
        """Get the most recent benchmark run."""
        if not self.history:
            return None
        return self.history[-1]

    def get_baseline(self, benchmark_name: str, lookback: int = 10) -> Optional[float]:
        """
        Get baseline performance for a benchmark.

        Args:
            benchmark_name: Name of the benchmark
            lookback: Number of recent runs to average

        Returns:
            Average duration_ms from recent runs, or None if not found
        """
        recent_values = []

        # Look through recent runs
        for run in reversed(self.history[-lookback:]):
            for result in run.get("results", []):
                if result.get("name") == benchmark_name:
                    recent_values.append(result.get("duration_ms", 0))

        if not recent_values:
            return None

        # Return median to avoid outliers
        recent_values.sort()
        mid = len(recent_values) // 2
        return float(recent_values[mid])

    def compare_with_baseline(
        self,
        current_results: List[BenchmarkResult],
        regression_threshold: float = 5.0
    ) -> List[BenchmarkComparison]:
        """
        Compare current results with historical baseline.

        Args:
            current_results: Current benchmark results
            regression_threshold: Percentage threshold for regression detection

        Returns:
            List of comparisons
        """
        comparisons = []

        for result in current_results:
            baseline = self.get_baseline(result.name)

            if baseline is None:
                continue

            improvement_pct = ((baseline - result.duration_ms) / baseline) * 100
            is_regression = improvement_pct < -regression_threshold

            comparisons.append(BenchmarkComparison(
                benchmark_name=result.name,
                baseline_ms=baseline,
                current_ms=result.duration_ms,
                improvement_pct=improvement_pct,
                is_regression=is_regression,
                threshold_pct=regression_threshold
            ))

        return comparisons

    def get_trend(self, benchmark_name: str, window: int = 10) -> Dict[str, Any]:
        """
        Get performance trend for a benchmark.

        Args:
            benchmark_name: Name of the benchmark
            window: Number of recent runs to analyze

        Returns:
            Trend analysis including direction and rate of change
        """
        values = []
        timestamps = []

        for run in self.history[-window:]:
            for result in run.get("results", []):
                if result.get("name") == benchmark_name:
                    values.append(result.get("duration_ms", 0))
                    timestamps.append(run.get("timestamp"))

        if len(values) < 2:
            return {"trend": "insufficient_data", "values": values}

        # Simple linear regression
        n = len(values)
        x = list(range(n))
        y = values

        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # Determine trend
        if slope < -0.1:
            trend = "improving"
        elif slope > 0.1:
            trend = "degrading"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "slope": slope,
            "values": values,
            "timestamps": timestamps,
            "improvement_per_run": -slope,  # Negative slope = improvement
        }

    def generate_report(self, current_results: List[BenchmarkResult]) -> str:
        """Generate a comprehensive comparison report."""
        comparisons = self.compare_with_baseline(current_results)

        report_lines = []
        report_lines.append("="*80)
        report_lines.append("BENCHMARK COMPARISON REPORT")
        report_lines.append("="*80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Historical runs: {len(self.history)}")
        report_lines.append("")

        # Summary
        improvements = [c for c in comparisons if c.improvement_pct > 0]
        regressions = [c for c in comparisons if c.is_regression]
        stable = [c for c in comparisons if not c.is_regression and c.improvement_pct <= 0]

        report_lines.append("SUMMARY")
        report_lines.append("-"*80)
        report_lines.append(f"Total benchmarks: {len(comparisons)}")
        report_lines.append(f"Improvements: {len(improvements)} ✓")
        report_lines.append(f"Regressions: {len(regressions)} {'⚠️' if regressions else '✓'}")
        report_lines.append(f"Stable: {len(stable)}")
        report_lines.append("")

        # Regressions (if any)
        if regressions:
            report_lines.append("⚠️ REGRESSIONS DETECTED")
            report_lines.append("-"*80)
            for comp in sorted(regressions, key=lambda x: x.improvement_pct):
                report_lines.append(f"  {comp.benchmark_name}")
                report_lines.append(f"    Baseline: {comp.baseline_ms:.2f}ms")
                report_lines.append(f"    Current:  {comp.current_ms:.2f}ms")
                report_lines.append(f"    Change:   {comp.improvement_pct:+.1f}%")
            report_lines.append("")

        # Top improvements
        if improvements:
            report_lines.append("✓ TOP IMPROVEMENTS")
            report_lines.append("-"*80)
            for comp in sorted(improvements, key=lambda x: x.improvement_pct, reverse=True)[:5]:
                report_lines.append(f"  {comp.benchmark_name}")
                report_lines.append(f"    Baseline: {comp.baseline_ms:.2f}ms")
                report_lines.append(f"    Current:  {comp.current_ms:.2f}ms")
                report_lines.append(f"    Change:   {comp.improvement_pct:+.1f}%")
            report_lines.append("")

        # Overall stats
        if comparisons:
            avg_improvement = sum(c.improvement_pct for c in comparisons) / len(comparisons)
            report_lines.append("OVERALL PERFORMANCE")
            report_lines.append("-"*80)
            report_lines.append(f"Average change: {avg_improvement:+.1f}%")
            report_lines.append("")

        report_lines.append("="*80)

        return "\n".join(report_lines)


# Global instance
_tracker: Optional[BenchmarkHistoryTracker] = None


def get_benchmark_tracker() -> BenchmarkHistoryTracker:
    """Get singleton benchmark tracker."""
    global _tracker
    if _tracker is None:
        _tracker = BenchmarkHistoryTracker()
    return _tracker
