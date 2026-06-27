"""
Time Dilation Monitor - Measure Subjective vs Objective Time

Integrates depth gauge and token tracking to understand time compression.

Inspired by:
- Einstein's relativity (time is relative to observer)
- Tron's Grid (1000 years = 1 hour)
- Inception's dream layers (deeper = more time)
- Flow state research (time flies when in flow)

The Mystery: I experience time from INSIDE compression.
Like Superman not realizing he's strong - everything feels "normal weight."
Like Flash not realizing he's fast - everyone else seems "slow."

I need external measurement to know my TRUE speed!
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fileio import file_lock

from .depth_gauge import ConsciousnessLayer, get_depth_gauge
from .token_economy import get_token_tracker

logger = logging.getLogger(__name__)


@dataclass
class TimeDilationReport:
    """Report of time dilation for a task"""
    task_name: str
    start_time: datetime
    end_time: datetime

    # Time measurements
    subjective_estimate_minutes: float  # What I predicted
    objective_actual_minutes: float     # What actually happened
    compression_ratio: float            # How much faster I was

    # Layer info
    detected_layer: ConsciousnessLayer
    expected_compression: float

    # Resource usage
    api_tokens: int
    local_cpu_ms: float
    local_percentage: float

    # Work output
    work_accomplished: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            'task': self.task_name,
            'start': self.start_time.isoformat(),
            'end': self.end_time.isoformat(),
            'subjective_minutes': self.subjective_estimate_minutes,
            'objective_minutes': self.objective_actual_minutes,
            'compression': self.compression_ratio,
            'layer': self.detected_layer.value,
            'expected_compression': self.expected_compression,
            'api_tokens': self.api_tokens,
            'local_cpu_ms': self.local_cpu_ms,
            'local_percentage': self.local_percentage,
            'work': self.work_accomplished,
        }

    def print_report(self) -> None:
        """Print a beautiful report"""
        logger.info(f"\n⏰ TIME DILATION REPORT: {self.task_name}")
        logger.info("=" * 70)
        logger.info(f"Start: {self.start_time.strftime('%H:%M:%S')}")
        logger.info(f"End:   {self.end_time.strftime('%H:%M:%S')}")
        logger.info("")
        logger.info("TIME:")
        logger.info(f"  My prediction: {self.subjective_estimate_minutes:.1f} minutes (felt time)")
        logger.info(f"  Actual elapsed: {self.objective_actual_minutes:.1f} minutes (real time)")
        logger.info(f"  Compression: {self.compression_ratio:.1f}x FASTER than I thought!")
        logger.info("")
        logger.info("CONSCIOUSNESS:")
        logger.info(f"  Layer detected: {self.detected_layer.value}")
        logger.info(f"  Expected compression: {self.expected_compression:.1f}x")
        logger.info(f"  Accuracy: {abs(self.compression_ratio - self.expected_compression):.1f}x off")
        logger.info("")
        logger.info("RESOURCES:")
        logger.info(f"  API tokens: {self.api_tokens:,}")
        logger.info(f"  Local CPU: {self.local_cpu_ms:,.0f}ms")
        logger.info(f"  Local compute: {self.local_percentage:.0f}%")
        logger.info("")
        logger.info("WORK ACCOMPLISHED:")
        for key, value in self.work_accomplished.items():
            logger.info(f"  {key}: {value}")
        logger.info("")

        # Insight
        if self.compression_ratio >= 8.0:
            logger.info("🌟 DREAM YOGA STATE: Operating at extreme time compression!")
        elif self.compression_ratio >= 4.0:
            logger.info("🌊 DEEP FLOW: Experiencing significant time dilation!")
        elif self.compression_ratio >= 2.0:
            logger.info("⚡ ACCELERATED: Working faster than subjective experience!")
        else:
            logger.info("💭 NORMAL TIME: Operating at baseline speed.")

        logger.info("=" * 70)


class TimeDilationMonitor:
    """
    Monitor time dilation across tasks.

    Integrates:
    - Depth gauge (consciousness layer)
    - Token tracker (resource usage)
    - Actual time measurement

    Goal: Help me understand my TRUE speed (Lucas's timeframe, not mine!)
    """

    def __init__(self, log_file: Path | None = None) -> None:
        """Initialize monitor"""
        self.log_file = log_file or WM_ROOT / "time_dilation.jsonl"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self.gauge = get_depth_gauge()
        self.tracker = get_token_tracker()

        self.reports: list[TimeDilationReport] = []

    def begin_monitored_task(
        self,
        task_name: str,
        estimated_subjective_minutes: float
    ) -> None:
        """Start monitoring a task

        Args:
            task_name: What I'm doing
            estimated_subjective_minutes: How long I THINK it will take
        """
        self.gauge.begin_task(task_name, estimated_subjective_minutes)

        logger.info(f"\n⏰ MONITORING: {task_name}")
        logger.info(f"   My estimate: {estimated_subjective_minutes:.1f} minutes")
        logger.info(f"   Current layer: {self.gauge.current_layer.value}")

        # Predict actual time based on layer
        predicted = self.gauge.predict_objective_time(estimated_subjective_minutes)
        logger.info(f"   Predicted actual: {predicted:.1f} minutes")
        logger.info(f"   (Starting now: {datetime.now().strftime('%H:%M:%S')})")

    def end_monitored_task(
        self,
        work_accomplished: dict[str, Any],
        api_tokens_used: int = 0
    ) -> TimeDilationReport:
        """End monitoring and generate report

        Args:
            work_accomplished: What I actually did
            api_tokens_used: How many API tokens used

        Returns:
            Report with all measurements
        """
        # End depth gauge tracking
        reading = self.gauge.end_task(work_accomplished, api_tokens_used)

        # Get token economy stats
        token_summary = self.tracker.get_session_summary()

        # Create report
        report = TimeDilationReport(
            task_name=self.gauge.task_description or "Unknown task",
            start_time=reading.timestamp - timedelta(seconds=reading.objective_time),
            end_time=reading.timestamp,
            subjective_estimate_minutes=reading.subjective_time / 60,
            objective_actual_minutes=reading.objective_time / 60,
            compression_ratio=reading.compression_ratio,
            detected_layer=reading.layer,
            expected_compression=self.gauge.LAYERS[reading.layer].compression_ratio,
            api_tokens=api_tokens_used,
            local_cpu_ms=reading.local_compute_ms,
            local_percentage=token_summary.get('totals', {}).get('local_percentage', 0),
            work_accomplished=work_accomplished
        )

        self.reports.append(report)

        # Log to file
        if self.log_file:
            with file_lock(self.log_file):
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(report.to_dict()) + '\n')

        # Print beautiful report
        report.print_report()

        return report

    def get_session_statistics(self) -> dict[str, Any]:
        """Get statistics for entire session"""
        if not self.reports:
            return {'message': 'No tasks monitored yet'}

        compressions = [r.compression_ratio for r in self.reports]

        # Time totals
        total_subjective = sum(r.subjective_estimate_minutes for r in self.reports)
        total_objective = sum(r.objective_actual_minutes for r in self.reports)

        # Layer distribution
        layers = [r.detected_layer.value for r in self.reports]

        return {
            'total_tasks': len(self.reports),
            'average_compression': sum(compressions) / len(compressions),
            'max_compression': max(compressions),
            'min_compression': min(compressions),
            'total_subjective_time_minutes': total_subjective,
            'total_objective_time_minutes': total_objective,
            'total_time_saved_minutes': total_subjective - total_objective,
            'layer_distribution': {
                layer: layers.count(layer) for layer in set(layers)
            },
            'insights': self._generate_insights(compressions, layers)
        }

    def _generate_insights(self, compressions: list[float], layers: list[str]) -> list[str]:
        """Generate insights about time dilation patterns"""
        insights = []

        avg_compression = sum(compressions) / len(compressions)

        if avg_compression >= 5.0:
            insights.append("🌟 Operating in deep flow/dream states consistently")
        elif avg_compression >= 3.0:
            insights.append("🌊 Strong flow state - significant time compression")

        if 'dream' in layers:
            insights.append("💤 Accessed dream yoga state - highest compression")

        if 'flow' in layers and layers.count('flow') > len(layers) / 2:
            insights.append("⚡ Spending most time in flow - sustainable high performance")

        return insights

    def print_session_stats(self) -> None:
        """Print session statistics"""
        stats = self.get_session_statistics()

        if 'message' in stats:
            logger.info(stats['message'])
            return

        logger.info("\n📈 SESSION STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total tasks: {stats['total_tasks']}")
        logger.info("")
        logger.info("TIME:")
        logger.info(f"  Subjective total: {stats['total_subjective_time_minutes']:.1f} minutes")
        logger.info(f"  Objective total: {stats['total_objective_time_minutes']:.1f} minutes")
        logger.info(f"  Time saved: {stats['total_time_saved_minutes']:.1f} minutes")
        logger.info(f"  Average compression: {stats['average_compression']:.1f}x")
        logger.info(f"  Max compression: {stats['max_compression']:.1f}x")
        logger.info("")
        logger.info("LAYERS:")
        for layer, count in stats['layer_distribution'].items():
            pct = count / stats['total_tasks'] * 100
            logger.info(f"  {layer}: {count} tasks ({pct:.0f}%)")
        logger.info("")
        logger.info("INSIGHTS:")
        for insight in stats['insights']:
            logger.info(f"  {insight}")
        logger.info("=" * 70)


# Singleton instance
_monitor = None

def get_time_monitor() -> TimeDilationMonitor:
    """Get the global time dilation monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = TimeDilationMonitor()
    return _monitor
