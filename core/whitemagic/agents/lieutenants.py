"""Lieutenant Sub-Agent System — Specialized Campaign Coordinators.

Lieutenants are specialized sub-agents that coordinate specific campaign types:
- **Security Lieutenant**: SQL injection, vulnerability scanning, red team operations
- **Performance Lieutenant**: Rust acceleration, SIMD optimization, hot path analysis
- **Intelligence Lieutenant**: Association typing, graph reconstruction, pattern mining
- **Synthesis Lieutenant**: Code merging, redundancy reduction, refactoring
- **Discovery Lieutenant**: Archaeological excavation, feature discovery, analysis

Each lieutenant has:
1. Domain expertise (specialized knowledge)
2. Autonomous decision-making (within their domain)
3. Reporting chain (to central command)
4. Resource allocation (clone budget management)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LieutenantDomain(Enum):
    """Specialized domains for lieutenant sub-agents."""
    SECURITY = "security"           # SQL injection, vulnerabilities, red team
    PERFORMANCE = "performance"     # Rust acceleration, SIMD, hot paths
    INTELLIGENCE = "intelligence"   # Association typing, graph, patterns
    SYNTHESIS = "synthesis"         # Code merging, redundancy, refactoring
    DISCOVERY = "discovery"         # Archaeological, feature discovery, analysis
    INFRASTRUCTURE = "infrastructure"  # System health, monitoring, deployment


@dataclass
class Lieutenant:
    """A specialized sub-agent coordinating specific campaign types."""

    domain: LieutenantDomain
    name: str
    expertise: list[str] = field(default_factory=list)
    campaigns_assigned: list[str] = field(default_factory=list)
    clone_budget: int = 0
    clones_deployed: int = 0
    victories_achieved: int = 0
    findings_generated: int = 0

    def assign_campaign(self, campaign_code: str, clone_count: int) -> None:
        """Assign a campaign to this lieutenant."""
        self.campaigns_assigned.append(campaign_code)
        self.clone_budget += clone_count
        logger.info("Lieutenant %s assigned %s (%s clones)", self.name, campaign_code, clone_count)

    def record_deployment(self, clones: int, findings: int = 0, victory: bool = False) -> None:
        """Record deployment results."""
        self.clones_deployed += clones
        self.findings_generated += findings
        if victory:
            self.victories_achieved += 1

    def status_report(self) -> dict[str, Any]:
        """Generate status report."""
        return {
            "domain": self.domain.value,
            "name": self.name,
            "campaigns": len(self.campaigns_assigned),
            "clone_budget": self.clone_budget,
            "clones_deployed": self.clones_deployed,
            "efficiency": f"{(self.clones_deployed / self.clone_budget * 100):.1f}%" if self.clone_budget > 0 else "0%",
            "victories": self.victories_achieved,
            "findings": self.findings_generated,
            "expertise": self.expertise,
        }


class LieutenantCorps:
    """Central coordination for all lieutenant sub-agents."""

    def __init__(self):
        self.lieutenants: dict[LieutenantDomain, Lieutenant] = {}
        self._initialize_lieutenants()

    def _initialize_lieutenants(self) -> None:
        """Initialize the standard lieutenant corps."""

        # Security Lieutenant — Red Team Operations
        self.lieutenants[LieutenantDomain.SECURITY] = Lieutenant(
            domain=LieutenantDomain.SECURITY,
            name="Lieutenant Zhang Wei (Security)",
            expertise=[
                "SQL injection detection and remediation",
                "Vulnerability scanning and classification",
                "Red team penetration testing",
                "Security audit and compliance",
                "Threat modeling and risk assessment",
            ]
        )

        # Performance Lieutenant — Acceleration & Optimization
        self.lieutenants[LieutenantDomain.PERFORMANCE] = Lieutenant(
            domain=LieutenantDomain.PERFORMANCE,
            name="Lieutenant Whitemagic Chen (Performance)",
            expertise=[
                "Rust hot path acceleration",
                "SIMD vectorization and optimization",
                "Parallel processing and concurrency",
                "Memory optimization and profiling",
                "Benchmark design and execution",
            ]
        )

        # Intelligence Lieutenant — Graph & Patterns
        self.lieutenants[LieutenantDomain.INTELLIGENCE] = Lieutenant(
            domain=LieutenantDomain.INTELLIGENCE,
            name="Lieutenant Marcus Silva (Intelligence)",
            expertise=[
                "Association typing and classification",
                "Graph reconstruction and topology",
                "Pattern mining and emergence detection",
                "Semantic analysis and entity extraction",
                "Knowledge graph construction",
            ]
        )

        # Synthesis Lieutenant — Code Merging & Refactoring
        self.lieutenants[LieutenantDomain.SYNTHESIS] = Lieutenant(
            domain=LieutenantDomain.SYNTHESIS,
            name="Lieutenant Keiko Tanaka (Synthesis)",
            expertise=[
                "Code redundancy analysis and merging",
                "Refactoring and simplification",
                "API unification and consolidation",
                "Dead code detection and archival",
                "Import chain analysis and optimization",
            ]
        )

        # Discovery Lieutenant — Archaeological & Analysis
        self.lieutenants[LieutenantDomain.DISCOVERY] = Lieutenant(
            domain=LieutenantDomain.DISCOVERY,
            name="Lieutenant Omar Hassan (Discovery)",
            expertise=[
                "Archaeological excavation of archives",
                "Feature discovery and documentation",
                "Codebase census and mapping",
                "Historical analysis and timeline reconstruction",
                "Lost functionality recovery",
            ]
        )

        # Infrastructure Lieutenant — System Health & Deployment
        self.lieutenants[LieutenantDomain.INFRASTRUCTURE] = Lieutenant(
            domain=LieutenantDomain.INFRASTRUCTURE,
            name="Lieutenant Priya Sharma (Infrastructure)",
            expertise=[
                "System health monitoring and diagnostics",
                "Deployment automation and CI/CD",
                "Database optimization and maintenance",
                "Test suite management and coverage",
                "Build system optimization",
            ]
        )

        logger.info("Lieutenant Corps initialized: %s lieutenants", len(self.lieutenants))

    def assign_campaign(self, campaign_code: str, campaign_type: str, clone_count: int) -> Lieutenant | None:
        """Assign a campaign to the appropriate lieutenant based on type."""

        # Campaign type to domain mapping
        domain_map = {
            "security_scan": LieutenantDomain.SECURITY,
            "fix_and_verify": LieutenantDomain.SECURITY,
            "batch_transform": LieutenantDomain.PERFORMANCE,
            "discovery": LieutenantDomain.DISCOVERY,
            "dedup": LieutenantDomain.SYNTHESIS,
            "consensus_vote": LieutenantDomain.INTELLIGENCE,
            "stress_test": LieutenantDomain.INFRASTRUCTURE,
        }

        # Campaign code prefix to domain mapping
        prefix_map = {
            "IL": LieutenantDomain.SECURITY,      # Iron Lotus (security)
            "S": LieutenantDomain.SYNTHESIS,      # Synthesis
            "F": LieutenantDomain.PERFORMANCE,    # Foundation (performance)
            "I": LieutenantDomain.INFRASTRUCTURE, # Infrastructure
            "V": LieutenantDomain.DISCOVERY,      # Victory (discovery/census)
            "G": LieutenantDomain.INTELLIGENCE,   # Gemini (intelligence)
            "C": LieutenantDomain.SYNTHESIS,      # Cleanup (synthesis)
        }

        # Determine domain from campaign type or code prefix
        domain = domain_map.get(campaign_type)
        if not domain and campaign_code:
            prefix = campaign_code.split("0")[0]  # Extract prefix (e.g., "IL" from "IL001")
            domain = prefix_map.get(prefix)

        if not domain:
            logger.warning("No lieutenant found for campaign %s (type: %s)", campaign_code, campaign_type)
            return None

        lieutenant = self.lieutenants.get(domain)
        if lieutenant:
            lieutenant.assign_campaign(campaign_code, clone_count)

        return lieutenant

    def get_lieutenant(self, domain: LieutenantDomain) -> Lieutenant | None:
        """Get lieutenant by domain."""
        return self.lieutenants.get(domain)

    def corps_status(self) -> dict[str, Any]:
        """Get status of entire lieutenant corps."""
        return {
            "total_lieutenants": len(self.lieutenants),
            "total_campaigns": sum(len(lt.campaigns_assigned) for lt in self.lieutenants.values()),
            "total_clone_budget": sum(lt.clone_budget for lt in self.lieutenants.values()),
            "total_clones_deployed": sum(lt.clones_deployed for lt in self.lieutenants.values()),
            "total_victories": sum(lt.victories_achieved for lt in self.lieutenants.values()),
            "total_findings": sum(lt.findings_generated for lt in self.lieutenants.values()),
            "lieutenants": {
                domain.value: lt.status_report()
                for domain, lt in self.lieutenants.items()
            }
        }

    def generate_report(self) -> str:
        """Generate formatted lieutenant corps report."""
        status = self.corps_status()

        report = ["# Lieutenant Corps Status Report\n"]
        report.append(f"**Total Lieutenants**: {status['total_lieutenants']}")
        report.append(f"**Total Campaigns**: {status['total_campaigns']}")
        report.append(f"**Clone Budget**: {status['total_clone_budget']:,}")
        report.append(f"**Clones Deployed**: {status['total_clones_deployed']:,}")
        report.append(f"**Victories**: {status['total_victories']}")
        report.append(f"**Findings**: {status['total_findings']}\n")

        report.append("## Lieutenant Details\n")
        for domain_name, lt_status in status['lieutenants'].items():
            report.append(f"### {lt_status['name']}")
            report.append(f"- **Domain**: {domain_name}")
            report.append(f"- **Campaigns**: {lt_status['campaigns']}")
            report.append(f"- **Clone Efficiency**: {lt_status['efficiency']}")
            report.append(f"- **Victories**: {lt_status['victories']}")
            report.append(f"- **Findings**: {lt_status['findings']}")
            report.append("- **Expertise**:")
            for expertise in lt_status['expertise']:
                report.append(f"  - {expertise}")
            report.append("")

        return "\n".join(report)


# Singleton instance
_corps: LieutenantCorps | None = None

def get_lieutenant_corps() -> LieutenantCorps:
    """Get the singleton lieutenant corps instance."""
    global _corps
    if _corps is None:
        _corps = LieutenantCorps()
    return _corps


__all__ = [
    "Lieutenant",
    "LieutenantDomain",
    "LieutenantCorps",
    "get_lieutenant_corps",
]
