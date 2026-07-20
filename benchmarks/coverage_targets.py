"""P8.4 — Coverage by risk configuration.

Defines branch coverage thresholds per critical package, classifying
packages by risk level. Global coverage stays informational until
experimental/archive scope is separated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CoverageTarget:
    """Coverage target for a package or package group."""

    packages: list[str]
    risk: RiskLevel
    branch_threshold: float  # minimum branch coverage %
    line_threshold: float  # minimum line coverage %
    description: str = ""
    current: float | None = None  # filled in after measurement


# ─── Risk-based coverage targets ───────────────────────────────────────
#
# Critical packages (safety, permissions, transactions) have the highest
# thresholds. Experimental/research packages have lower thresholds.
# Global coverage is informational only.

COVERAGE_TARGETS: list[CoverageTarget] = [
    # Critical: Safety, permissions, effects
    CoverageTarget(
        packages=[
            "whitemagic.tools.dispatch_security",
            "whitemagic.security",
            "whitemagic.dharma",
            "whitemagic.shelter",
        ],
        risk=RiskLevel.CRITICAL,
        branch_threshold=80.0,
        line_threshold=85.0,
        description="Safety, permissions, effects, and shelter isolation",
    ),
    # Critical: Memory CRUD and migrations
    CoverageTarget(
        packages=[
            "whitemagic.core.memory.sqlite_backend",
            "whitemagic.core.memory.unified",
            "whitemagic.core.memory.galaxy_router",
        ],
        risk=RiskLevel.CRITICAL,
        branch_threshold=75.0,
        line_threshold=80.0,
        description="Memory CRUD, galaxy routing, and data integrity",
    ),
    # High: Runtime lifecycle and dispatch
    CoverageTarget(
        packages=[
            "whitemagic.tools.unified_api",
            "whitemagic.tools.dispatch_table",
            "whitemagic.tools.middleware",
            "whitemagic.core.worker_registry",
        ],
        risk=RiskLevel.HIGH,
        branch_threshold=70.0,
        line_threshold=75.0,
        description="Runtime dispatch, middleware pipeline, and worker lifecycle",
    ),
    # High: Tool registry and contracts
    CoverageTarget(
        packages=[
            "whitemagic.tools.registry",
            "whitemagic.tools.tool_catalog",
            "whitemagic.tools.tool_types",
        ],
        risk=RiskLevel.HIGH,
        branch_threshold=75.0,
        line_threshold=80.0,
        description="Tool registry, safety classification, and contract enforcement",
    ),
    # High: Configuration
    CoverageTarget(
        packages=[
            "whitemagic.config",
        ],
        risk=RiskLevel.HIGH,
        branch_threshold=70.0,
        line_threshold=75.0,
        description="Configuration management and env var registry",
    ),
    # Medium: Consciousness and cognitive systems
    CoverageTarget(
        packages=[
            "whitemagic.core.consciousness",
            "whitemagic.core.intelligence",
            "whitemagic.core.dreaming",
        ],
        risk=RiskLevel.MEDIUM,
        branch_threshold=50.0,
        line_threshold=60.0,
        description="Consciousness, intelligence, and dreaming (experimental)",
    ),
    # Medium: Gardens, zodiac, resonance
    CoverageTarget(
        packages=[
            "whitemagic.gardens",
            "whitemagic.zodiac",
            "whitemagic.resonance",
        ],
        risk=RiskLevel.MEDIUM,
        branch_threshold=40.0,
        line_threshold=50.0,
        description="Gardens, zodiac, and resonance (experimental)",
    ),
    # Low: Research and experimental
    CoverageTarget(
        packages=[
            "whitemagic.core.evolution",
            "whitemagic.forecasting",
            "whitemagic.agents",
        ],
        risk=RiskLevel.LOW,
        branch_threshold=30.0,
        line_threshold=40.0,
        description="Research, forecasting, and agent systems (experimental)",
    ),
]


# Global coverage is informational only — experimental/archive scope inflates denominator
GLOBAL_INFORMATIONAL_THRESHOLD = 25.0


def get_critical_packages() -> list[str]:
    """Get all critical-risk package names."""
    packages = []
    for t in COVERAGE_TARGETS:
        if t.risk == RiskLevel.CRITICAL:
            packages.extend(t.packages)
    return packages


def get_high_risk_packages() -> list[str]:
    packages = []
    for t in COVERAGE_TARGETS:
        if t.risk in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            packages.extend(t.packages)
    return packages


def get_coverage_config() -> dict:
    """Get coverage configuration for pytest-cov."""
    return {
        "global_threshold": GLOBAL_INFORMATIONAL_THRESHOLD,
        "targets": [
            {
                "packages": t.packages,
                "risk": t.risk.value,
                "branch_threshold": t.branch_threshold,
                "line_threshold": t.line_threshold,
                "description": t.description,
            }
            for t in COVERAGE_TARGETS
        ],
        "critical_package_count": len(get_critical_packages()),
        "high_risk_package_count": len(get_high_risk_packages()),
    }
