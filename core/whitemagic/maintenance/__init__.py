"""Maintenance Module - System Health and Technical Debt Management

Tools for keeping the cathedral in good repair.
"""

from .capability_harness import (
    CapabilityHarness,
    ComboResult,
    HarnessReport,
    run_harness,
)

try:
    from .garden_health import (
        GardenHealth,
        GardenHealthRegistry,
        HealthReport,
        run_health_check,
    )
except ImportError:
    GardenHealth = GardenHealthRegistry = HealthReport = run_health_check = None  # type: ignore[assignment,misc]

__all__ = [
    "CapabilityHarness",
    "ComboResult",
    "GardenHealth",
    "GardenHealthRegistry",
    "HarnessReport",
    "HealthReport",
    "run_harness",
    "run_health_check",
]
