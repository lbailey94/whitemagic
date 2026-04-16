"""Campaign Metrics Tracker — Instrumentation for Shadow Clone Armies
====================================================================
Tracks per-army, per-objective, and per-lieutenant deployment metrics
for clone army operations. Generates unified after-action reports with
timing, clone counts, findings, and effectiveness ratings.

Designed for the 3-army deployment structure:
  - Army Alpha (10K clones) — Consensus voting
  - Army Beta  (70K clones) — Map-reduce batch processing
  - Army Gamma (240K+ clones) — Brute-force search/discovery

Usage:
    from whitemagic.agents.campaign_metrics import get_tracker, ArmyTier

    tracker = get_tracker()
    with tracker.track_objective("alpha", "security_classification") as obj:
        result = deploy_clones(...)
        obj.record_clones(10000, result["elapsed_ms"])
        obj.record_finding("SQL injection in db_manager.py", severity="high")
        obj.set_result(result)

    report = tracker.after_action_report()
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from whitemagic.utils.fast_json import dumps_str as _json_dumps

logger = logging.getLogger(__name__)


class ArmyTier(str, Enum):
    ALPHA = "alpha"    # 10K clones — consensus voting
    BETA = "beta"      # 70K clones — map-reduce
    GAMMA = "gamma"    # 240K+ clones — brute-force search


class ObjectiveStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    description: str
    severity: FindingSeverity = FindingSeverity.INFO
    category: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category,
            "details": self.details,
        }


@dataclass
class ObjectiveMetrics:
    """Metrics for a single objective within an army deployment."""

    name: str
    army: ArmyTier
    lieutenant: str = ""
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    start_time: float = 0.0
    end_time: float = 0.0
    clones_deployed: int = 0
    clone_batches: int = 0
    clone_deploy_ms: float = 0.0
    findings: list[Finding] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    phases_completed: int = 0
    phases_total: int = 0
    consensus_confidence: float = 0.0
    winner_strategy: str = ""

    @property
    def elapsed_seconds(self) -> float:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        if self.start_time:
            return time.time() - self.start_time
        return 0.0

    @property
    def clones_per_second(self) -> float:
        if self.clone_deploy_ms > 0:
            return self.clones_deployed / (self.clone_deploy_ms / 1000.0)
        return 0.0

    @property
    def findings_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
        return counts

    def record_clones(self, count: int, deploy_ms: float = 0.0) -> None:
        self.clones_deployed += count
        self.clone_deploy_ms += deploy_ms
        self.clone_batches += 1

    def record_finding(
        self,
        description: str,
        severity: str = "info",
        category: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.findings.append(Finding(
            description=description,
            severity=FindingSeverity(severity),
            category=category,
            details=details or {},
        ))

    def set_result(self, result: dict[str, Any]) -> None:
        self.result = result
        if "avg_confidence" in result:
            self.consensus_confidence = result["avg_confidence"]
        if "winner" in result:
            self.winner_strategy = str(result["winner"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "army": self.army.value,
            "lieutenant": self.lieutenant,
            "status": self.status.value,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "clones_deployed": self.clones_deployed,
            "clone_batches": self.clone_batches,
            "clone_deploy_ms": round(self.clone_deploy_ms, 2),
            "clones_per_second": round(self.clones_per_second, 0),
            "findings_count": len(self.findings),
            "findings_by_severity": self.findings_by_severity,
            "consensus_confidence": round(self.consensus_confidence, 4),
            "winner_strategy": self.winner_strategy,
            "phases": f"{self.phases_completed}/{self.phases_total}",
            "error": self.error,
        }


class ObjectiveContext:
    """Context manager for tracking an objective's execution."""

    def __init__(self, metrics: ObjectiveMetrics) -> None:
        self._metrics = metrics

    def __enter__(self) -> ObjectiveMetrics:
        self._metrics.status = ObjectiveStatus.RUNNING
        self._metrics.start_time = time.time()
        return self._metrics

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._metrics.end_time = time.time()
        if exc_type:
            self._metrics.status = ObjectiveStatus.FAILED
            self._metrics.error = str(exc_val)
        elif self._metrics.status == ObjectiveStatus.RUNNING:
            self._metrics.status = ObjectiveStatus.COMPLETED
        return None


@dataclass
class ArmyMetrics:
    """Aggregate metrics for an entire army tier."""

    tier: ArmyTier
    objectives: list[ObjectiveMetrics] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def total_clones(self) -> int:
        return sum(o.clones_deployed for o in self.objectives)

    @property
    def total_findings(self) -> int:
        return sum(len(o.findings) for o in self.objectives)

    @property
    def elapsed_seconds(self) -> float:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        if self.start_time:
            return time.time() - self.start_time
        return 0.0

    @property
    def completed_count(self) -> int:
        return sum(1 for o in self.objectives if o.status == ObjectiveStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for o in self.objectives if o.status == ObjectiveStatus.FAILED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value,
            "objectives_total": len(self.objectives),
            "objectives_completed": self.completed_count,
            "objectives_failed": self.failed_count,
            "total_clones_deployed": self.total_clones,
            "total_findings": self.total_findings,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "objectives": [o.to_dict() for o in self.objectives],
        }


class CampaignTracker:
    """Central metrics tracker for multi-army clone deployments.

    Tracks all three army tiers, their objectives, and generates
    unified after-action reports.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._armies: dict[ArmyTier, ArmyMetrics] = {
            ArmyTier.ALPHA: ArmyMetrics(tier=ArmyTier.ALPHA),
            ArmyTier.BETA: ArmyMetrics(tier=ArmyTier.BETA),
            ArmyTier.GAMMA: ArmyMetrics(tier=ArmyTier.GAMMA),
        }
        self._campaign_start: float = 0.0
        self._campaign_end: float = 0.0
        self._campaign_name: str = ""
        self._preflight: dict[str, Any] = {}

    def start_campaign(self, name: str = "Grand Army Deployment") -> None:
        self._campaign_start = time.time()
        self._campaign_name = name
        logger.info(f"Campaign '{name}' started")

    def end_campaign(self) -> None:
        self._campaign_end = time.time()

    def set_preflight(self, data: dict[str, Any]) -> None:
        self._preflight = data

    def track_objective(
        self,
        army: str | ArmyTier,
        name: str,
        lieutenant: str = "",
        phases_total: int = 1,
    ) -> ObjectiveContext:
        """Create a tracked objective context manager.

        Usage:
            with tracker.track_objective("alpha", "security_scan") as obj:
                obj.record_clones(10000, 17.5)
                obj.record_finding("Found vuln", severity="high")
        """
        tier = ArmyTier(army) if isinstance(army, str) else army
        metrics = ObjectiveMetrics(
            name=name,
            army=tier,
            lieutenant=lieutenant,
            phases_total=phases_total,
        )
        with self._lock:
            self._armies[tier].objectives.append(metrics)
        return ObjectiveContext(metrics)

    def start_army(self, army: str | ArmyTier) -> None:
        tier = ArmyTier(army) if isinstance(army, str) else army
        self._armies[tier].start_time = time.time()

    def end_army(self, army: str | ArmyTier) -> None:
        tier = ArmyTier(army) if isinstance(army, str) else army
        self._armies[tier].end_time = time.time()

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Quick summary of current campaign state."""
        total_clones = sum(a.total_clones for a in self._armies.values())
        total_findings = sum(a.total_findings for a in self._armies.values())
        total_objectives = sum(len(a.objectives) for a in self._armies.values())
        completed = sum(a.completed_count for a in self._armies.values())
        failed = sum(a.failed_count for a in self._armies.values())
        elapsed = (self._campaign_end or time.time()) - self._campaign_start if self._campaign_start else 0

        return {
            "campaign": self._campaign_name,
            "elapsed_seconds": round(elapsed, 2),
            "total_clones_deployed": total_clones,
            "total_findings": total_findings,
            "objectives": f"{completed}/{total_objectives} completed, {failed} failed",
            "armies": {
                tier.value: {
                    "clones": army.total_clones,
                    "findings": army.total_findings,
                    "completed": f"{army.completed_count}/{len(army.objectives)}",
                }
                for tier, army in self._armies.items()
            },
        }

    def after_action_report(self) -> dict[str, Any]:
        """Generate a full after-action report."""
        elapsed = (self._campaign_end or time.time()) - self._campaign_start if self._campaign_start else 0

        # Aggregate findings by severity
        all_findings: dict[str, int] = {}
        for army in self._armies.values():
            for obj in army.objectives:
                for f in obj.findings:
                    all_findings[f.severity.value] = all_findings.get(f.severity.value, 0) + 1

        # Top findings
        top_findings: list[dict[str, Any]] = []
        for army in self._armies.values():
            for obj in army.objectives:
                for f in obj.findings:
                    if f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH):
                        top_findings.append({
                            "objective": obj.name,
                            "army": obj.army.value,
                            **f.to_dict(),
                        })

        # Per-objective effectiveness
        effectiveness: list[dict[str, Any]] = []
        for army in self._armies.values():
            for obj in army.objectives:
                eff = {
                    "name": obj.name,
                    "army": obj.army.value,
                    "status": obj.status.value,
                    "clones": obj.clones_deployed,
                    "findings": len(obj.findings),
                    "elapsed_s": round(obj.elapsed_seconds, 2),
                    "clones_per_sec": round(obj.clones_per_second, 0),
                    "confidence": round(obj.consensus_confidence, 4),
                    "findings_per_1k_clones": round(
                        len(obj.findings) / max(obj.clones_deployed / 1000, 1), 2
                    ) if obj.clones_deployed else 0,
                }
                effectiveness.append(eff)

        return {
            "campaign": self._campaign_name,
            "timestamp": datetime.now().isoformat(),
            "total_elapsed_seconds": round(elapsed, 2),
            "preflight": self._preflight,
            "totals": {
                "clones_deployed": sum(a.total_clones for a in self._armies.values()),
                "findings": sum(a.total_findings for a in self._armies.values()),
                "objectives_completed": sum(a.completed_count for a in self._armies.values()),
                "objectives_failed": sum(a.failed_count for a in self._armies.values()),
                "objectives_total": sum(len(a.objectives) for a in self._armies.values()),
            },
            "findings_by_severity": all_findings,
            "top_findings": top_findings[:20],
            "armies": {tier.value: army.to_dict() for tier, army in self._armies.items()},
            "effectiveness": effectiveness,
        }

    def after_action_markdown(self) -> str:
        """Generate a Markdown after-action report."""
        report = self.after_action_report()
        totals = report["totals"]
        elapsed = report["total_elapsed_seconds"]

        md = f"""# After-Action Report — {report['campaign']}
**Generated**: {report['timestamp']}
**Total Elapsed**: {elapsed:.1f}s ({elapsed/60:.1f} min)

## Campaign Summary
| Metric | Value |
|--------|-------|
| Total Clones Deployed | {totals['clones_deployed']:,} |
| Total Findings | {totals['findings']:,} |
| Objectives Completed | {totals['objectives_completed']}/{totals['objectives_total']} |
| Objectives Failed | {totals['objectives_failed']} |

## Findings by Severity
| Severity | Count |
|----------|-------|
"""
        for sev in ["critical", "high", "medium", "low", "info"]:
            count = report["findings_by_severity"].get(sev, 0)
            if count:
                md += f"| {sev.upper()} | {count} |\n"

        md += "\n## Pre-Flight Status\n"
        for k, v in report.get("preflight", {}).items():
            md += f"- **{k}**: {v}\n"

        # Per-army sections
        for tier_name in ["alpha", "beta", "gamma"]:
            army = report["armies"].get(tier_name, {})
            tier_label = {"alpha": "Alpha (10K — Consensus)", "beta": "Beta (70K — Map-Reduce)", "gamma": "Gamma (240K+ — Brute Force)"}
            md += f"\n## Army {tier_label.get(tier_name, tier_name)}\n"
            md += f"- **Clones**: {army.get('total_clones_deployed', 0):,}\n"
            md += f"- **Findings**: {army.get('total_findings', 0)}\n"
            md += f"- **Elapsed**: {army.get('elapsed_seconds', 0):.1f}s\n"
            md += f"- **Completed**: {army.get('objectives_completed', 0)}/{army.get('objectives_total', 0)}\n\n"

            for obj in army.get("objectives", []):
                status_icon = {"completed": "✅", "failed": "❌", "running": "🔄", "pending": "⏳", "skipped": "⏭️"}
                icon = status_icon.get(obj["status"], "❓")
                md += f"### {icon} {obj['name']}\n"
                md += f"- Lieutenant: `{obj['lieutenant']}`\n"
                md += f"- Clones: {obj['clones_deployed']:,} ({obj['clones_per_second']:,.0f}/sec)\n"
                md += f"- Elapsed: {obj['elapsed_seconds']:.2f}s\n"
                md += f"- Findings: {obj['findings_count']} ({_json_dumps(obj['findings_by_severity'])})\n"
                if obj["consensus_confidence"]:
                    md += f"- Consensus: {obj['winner_strategy']} @ {obj['consensus_confidence']:.3f}\n"
                if obj["error"]:
                    md += f"- **Error**: {obj['error']}\n"
                md += "\n"

        # Effectiveness ranking
        md += "## Effectiveness Ranking\n"
        md += "| Objective | Army | Clones | Findings | Findings/1K Clones | Time | Confidence |\n"
        md += "|-----------|------|--------|----------|-------------------|------|------------|\n"
        for eff in sorted(report["effectiveness"], key=lambda x: -x.get("findings_per_1k_clones", 0)):
            md += (
                f"| {eff['name']} | {eff['army']} | {eff['clones']:,} | {eff['findings']} | "
                f"{eff['findings_per_1k_clones']:.2f} | {eff['elapsed_s']:.1f}s | "
                f"{eff['confidence']:.3f} |\n"
            )

        # Top findings
        if report["top_findings"]:
            md += "\n## Critical/High Findings\n"
            for f in report["top_findings"]:
                md += f"- **[{f['severity'].upper()}]** ({f['objective']}) {f['description']}\n"

        return md

    def save_reports(self, reports_dir: str | Path) -> tuple[Path, Path]:
        """Save both JSON and Markdown reports to disk."""
        reports_dir = Path(reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_path = reports_dir / f"grand_army_aar_{ts}.json"
        json_path.write_text(_json_dumps(self.after_action_report(), indent=2, default=str))

        md_path = reports_dir / f"grand_army_aar_{ts}.md"
        md_path.write_text(self.after_action_markdown())

        logger.info(f"After-action reports saved: {json_path}, {md_path}")
        return json_path, md_path


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_tracker: CampaignTracker | None = None
_tracker_lock = threading.Lock()


def get_tracker() -> CampaignTracker:
    """Get the global campaign metrics tracker."""
    global _tracker
    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                _tracker = CampaignTracker()
    return _tracker


def new_tracker() -> CampaignTracker:
    """Create a fresh tracker (for new campaign runs)."""
    global _tracker
    with _tracker_lock:
        _tracker = CampaignTracker()
    return _tracker
