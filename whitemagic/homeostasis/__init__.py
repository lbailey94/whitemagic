"""
Homeostasis System - Self-Balancing Memory Management

Inspired by biological homeostasis (maintaining internal balance despite
external changes), this system monitors memory system metrics and applies
corrective feedback to maintain optimal equilibrium.

Philosophy: Like the human body maintaining temperature, pH, and blood sugar,
the memory system maintains optimal distributions of:
- Short-term vs long-term memories
- Tag diversity
- Memory age distributions
- Query performance
- Storage efficiency

Key Concepts:
- **Set Point**: Target value for a metric (e.g., 80% storage usage)
- **Deviation**: Current value vs set point
- **Feedback Loop**: Corrective actions to reduce deviation
- **Equilibrium**: Stable state where all metrics are within tolerance
"""

from whitemagic.homeostasis.metrics import (
    MetricType,
    SystemMetrics,
    collect_metrics,
    get_metric_value,
)

from whitemagic.homeostasis.feedback import (
    FeedbackAction,
    FeedbackController,
    apply_action,
    suggest_actions,
)

from whitemagic.homeostasis.equilibrium import (
    EquilibriumState,
    check_equilibrium,
    find_optimal_balance,
    equilibrium_report,
)

__all__ = [
    # Metrics
    "MetricType",
    "SystemMetrics",
    "collect_metrics",
    "get_metric_value",
    
    # Feedback
    "FeedbackAction",
    "FeedbackController",
    "apply_action",
    "suggest_actions",
    
    # Equilibrium
    "EquilibriumState",
    "check_equilibrium",
    "find_optimal_balance",
    "equilibrium_report",
]
