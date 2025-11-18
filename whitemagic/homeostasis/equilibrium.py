"""
Homeostasis Equilibrium - Find and Maintain Optimal Balance

Implements equilibrium detection and optimization. The system is in
equilibrium when all metrics are within their tolerance ranges and
the rate of change is minimal.

Philosophy: Dynamic equilibrium (like riding a bicycle) requires
constant micro-adjustments, not perfect stillness.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
from datetime import datetime

from whitemagic.homeostasis.metrics import SystemMetrics, MetricType, MetricValue
from whitemagic.homeostasis.feedback import FeedbackAction, suggest_actions


class EquilibriumState(Enum):
    """System equilibrium states"""
    BALANCED = "balanced"  # All metrics within tolerance
    MINOR_DEVIATION = "minor_deviation"  # 1-2 metrics slightly off
    MAJOR_DEVIATION = "major_deviation"  # 3+ metrics off or critical metric way off
    CRISIS = "crisis"  # Multiple critical metrics severely out of range


@dataclass
class EquilibriumReport:
    """Complete equilibrium analysis"""
    state: EquilibriumState
    timestamp: datetime
    
    # Metrics summary
    total_metrics: int
    balanced_metrics: int
    deviated_metrics: int
    
    # Deviations
    deviations: List[MetricValue]
    
    # Recommended actions
    actions: List[FeedbackAction]
    
    # Equilibrium score (0-100, higher = better)
    score: float
    
    def __str__(self) -> str:
        """Human-readable report"""
        lines = [
            f"\n{'='*60}",
            f"HOMEOSTASIS EQUILIBRIUM REPORT",
            f"{'='*60}",
            f"Timestamp: {self.timestamp.isoformat()}",
            f"State: {self.state.value.upper()}",
            f"Score: {self.score:.1f}/100",
            f"",
            f"Metrics: {self.balanced_metrics}/{self.total_metrics} balanced",
            f"",
        ]
        
        if self.deviations:
            lines.append("DEVIATIONS:")
            for dev in self.deviations:
                deviation = abs(dev.value - (dev.set_point or 0))
                pct = (deviation / (dev.tolerance or 1)) * 100
                lines.append(
                    f"  • {dev.metric_type.value}: {dev.value:.2f} {dev.unit} "
                    f"(target: {dev.set_point:.2f}, {pct:.0f}% over tolerance)"
                )
            lines.append("")
        
        if self.actions:
            lines.append(f"RECOMMENDED ACTIONS ({len(self.actions)}):")
            for i, action in enumerate(self.actions[:5], 1):  # Show top 5
                lines.append(
                    f"  {i}. [{action.priority}/10] {action.action_type.value}"
                )
                lines.append(f"     Reason: {action.reason}")
                lines.append(f"     Impact: {action.expected_impact}")
                lines.append(f"     Time: ~{action.estimated_time_seconds}s")
                lines.append("")
        else:
            lines.append("✅ NO ACTIONS NEEDED - System is in equilibrium")
            lines.append("")
        
        lines.append(f"{'='*60}\n")
        return "\n".join(lines)


def check_equilibrium(metrics: SystemMetrics) -> EquilibriumState:
    """
    Determine equilibrium state from metrics.
    
    Args:
        metrics: Current system metrics
        
    Returns:
        Equilibrium state classification
    """
    deviations = metrics.get_deviations()
    
    if not deviations:
        return EquilibriumState.BALANCED
    
    # Count severity of deviations
    minor_count = 0
    major_count = 0
    critical_count = 0
    
    for dev in deviations:
        if dev.set_point is None or dev.tolerance is None:
            continue
        
        deviation_ratio = abs(dev.value - dev.set_point) / dev.tolerance
        
        if deviation_ratio < 1.5:
            minor_count += 1
        elif deviation_ratio < 3.0:
            major_count += 1
        else:
            critical_count += 1
    
    # Classify state
    if critical_count >= 2 or (critical_count >= 1 and major_count >= 2):
        return EquilibriumState.CRISIS
    elif major_count >= 3 or critical_count >= 1:
        return EquilibriumState.MAJOR_DEVIATION
    elif minor_count <= 2:
        return EquilibriumState.MINOR_DEVIATION
    else:
        return EquilibriumState.MAJOR_DEVIATION


def calculate_score(metrics: SystemMetrics) -> float:
    """
    Calculate equilibrium score (0-100).
    
    Score is based on:
    - Percentage of metrics in range (50%)
    - Average deviation from set points (30%)
    - Worst-case deviation (20%)
    """
    metrics_with_targets = [
        m for m in metrics.metrics.values()
        if m.set_point is not None and m.tolerance is not None
    ]
    
    if not metrics_with_targets:
        return 100.0  # No targets set, assume perfect
    
    # Component 1: Percentage in range (50 points)
    in_range_count = 0
    for m in metrics_with_targets:
        if abs(m.value - m.set_point) <= m.tolerance:
            in_range_count += 1
    
    pct_in_range = in_range_count / len(metrics_with_targets)
    range_score = pct_in_range * 50
    
    # Component 2: Average deviation (30 points)
    avg_deviation_ratio = sum(
        abs(m.value - m.set_point) / m.tolerance
        for m in metrics_with_targets
    ) / len(metrics_with_targets)
    
    # Normalize: 0 deviation = 30 points, 2x tolerance = 0 points
    avg_score = max(0, 30 * (1 - avg_deviation_ratio / 2))
    
    # Component 3: Worst deviation (20 points)
    max_deviation_ratio = max(
        abs(m.value - m.set_point) / m.tolerance
        for m in metrics_with_targets
    )
    
    # Normalize: 0 deviation = 20 points, 3x tolerance = 0 points
    worst_score = max(0, 20 * (1 - max_deviation_ratio / 3))
    
    total_score = range_score + avg_score + worst_score
    return min(100.0, max(0.0, total_score))


def equilibrium_report(metrics: SystemMetrics, gain: float = 1.0) -> EquilibriumReport:
    """
    Generate complete equilibrium report with recommendations.
    
    Args:
        metrics: Current system metrics
        gain: Feedback controller gain
        
    Returns:
        Complete equilibrium analysis and recommendations
    """
    state = check_equilibrium(metrics)
    deviations = metrics.get_deviations()
    actions = suggest_actions(metrics, gain=gain)
    score = calculate_score(metrics)
    
    total_metrics = len([m for m in metrics.metrics.values() 
                        if m.set_point is not None])
    balanced_metrics = total_metrics - len(deviations)
    
    return EquilibriumReport(
        state=state,
        timestamp=metrics.timestamp,
        total_metrics=total_metrics,
        balanced_metrics=balanced_metrics,
        deviated_metrics=len(deviations),
        deviations=deviations,
        actions=actions,
        score=score
    )


def find_optimal_balance(
    metrics_history: List[SystemMetrics],
    window_size: int = 5
) -> Tuple[float, float]:
    """
    Analyze historical metrics to find optimal set points.
    
    This is a simple implementation that looks at the most stable
    periods in history and recommends those values as targets.
    
    Args:
        metrics_history: Historical metrics (most recent first)
        window_size: Number of measurements to consider for stability
        
    Returns:
        Tuple of (recommended_ratio, recommended_age) for key metrics
    """
    if len(metrics_history) < window_size:
        return (0.5, 15.0)  # Default values
    
    # Find most stable window (lowest variance)
    best_window_idx = 0
    best_variance = float('inf')
    
    for i in range(len(metrics_history) - window_size + 1):
        window = metrics_history[i:i+window_size]
        
        # Calculate variance of memory ratio in this window
        ratios = []
        for m in window:
            ratio_metric = m.metrics.get(MetricType.MEMORY_RATIO)
            if ratio_metric:
                ratios.append(ratio_metric.value)
        
        if ratios:
            mean = sum(ratios) / len(ratios)
            variance = sum((r - mean) ** 2 for r in ratios) / len(ratios)
            
            if variance < best_variance:
                best_variance = variance
                best_window_idx = i
    
    # Get average values from best window
    best_window = metrics_history[best_window_idx:best_window_idx+window_size]
    
    avg_ratio = 0.5
    avg_age = 15.0
    
    ratio_values = []
    age_values = []
    
    for m in best_window:
        ratio_metric = m.metrics.get(MetricType.MEMORY_RATIO)
        age_metric = m.metrics.get(MetricType.AVG_MEMORY_AGE_DAYS)
        
        if ratio_metric:
            ratio_values.append(ratio_metric.value)
        if age_metric:
            age_values.append(age_metric.value)
    
    if ratio_values:
        avg_ratio = sum(ratio_values) / len(ratio_values)
    if age_values:
        avg_age = sum(age_values) / len(age_values)
    
    return (avg_ratio, avg_age)
