# ruff: noqa: BLE001
"""
Continuous Audit System - Autonomous Learning Loop

Wires together existing systems for moment-to-moment self-awareness:
- Project Homeostasis (structure health)
- Documentation Harmony (doc-code sync)
- Pattern Cascade (pattern discovery)
- Memory consolidation
- Immune system (antibody learning)

Instead of auditing every few hours/days, audit constantly:
- After significant changes
- On schedule (configurable interval)
- On demand (explicit trigger)

This is the "check before walking" system - constant awareness update.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from ..automation.consolidation import consolidate_memories
    from ..harmony.documentation_harmony import DocumentationHarmony
    from ..harmony.pattern_cascade import PatternCascade
    from ..harmony.project_homeostasis import ProjectHomeostasis
    from ..resonance.gan_ying import EventType, ResonanceEvent, get_bus
except ImportError:
    ProjectHomeostasis = None
    DocumentationHarmony = None
    PatternCascade = None
    consolidate_memories = None
    get_bus = None
    ResonanceEvent = None
    EventType = None


class ContinuousAudit:
    """
    Autonomous audit loop for constant self-awareness

    Pattern: Audit → Update → Synthesize → Learn → Repeat

    Frequency: Configurable (default every 10 minutes or on-demand)
    """

    def __init__(
        self,
        project_root: Path,
        audit_interval_minutes: int = 10,
        auto_fix: bool = False,
    ):
        """Initialize continuous audit system

        Args:
            project_root: Root of WhiteMagic project
            audit_interval_minutes: How often to run full audit
            auto_fix: Whether to automatically fix issues found
        """
        self.project_root = Path(project_root)
        self.audit_interval = timedelta(minutes=audit_interval_minutes)
        self.auto_fix = auto_fix
        self.last_audit: datetime | None = None

        self.homeostasis = (
            ProjectHomeostasis(str(project_root)) if ProjectHomeostasis else None
        )
        self.doc_harmony = (
            DocumentationHarmony(str(project_root)) if DocumentationHarmony else None
        )
        self.pattern_cascade = PatternCascade() if PatternCascade else None
        self.bus = get_bus() if get_bus else None

        # Metrics
        self.audits_run: int = 0
        self.issues_found: int = 0
        self.issues_fixed: int = 0
        self.patterns_discovered: int = 0

    def should_audit_now(self) -> bool:
        """Check if it's time for another audit"""
        if not self.last_audit:
            return True

        return datetime.now() - self.last_audit >= self.audit_interval

    def run_full_audit(self) -> dict[str, Any]:
        """Run complete audit cycle

        Returns:
            Audit results with findings and actions taken
        """
        audit_start = datetime.now()
        results = {
            "timestamp": audit_start.isoformat(),
            "systems_checked": [],
            "issues_found": [],
            "patterns_discovered": [],
            "actions_taken": [],
            "health_score": 1.0,
            "total_modules": 0,
            "gardens_count": 0,
            "systems_count": 0,
            "top_issues": [],
        }

        # Count modules
        try:
            whitemagic_dir = self.project_root / "whitemagic"
            if whitemagic_dir.exists():
                gardens = [
                    "joy",
                    "truth",
                    "love",
                    "mystery",
                    "beauty",
                    "dharma",
                    "voice",
                    "play",
                    "wonder",
                    "connection",
                    "practice",
                    "presence",
                    "sangha",
                    "wisdom",
                ]

                garden_count = 0
                system_count = 0
                total_modules = 0

                for item in whitemagic_dir.iterdir():
                    if item.is_dir() and not item.name.startswith("_"):
                        py_files = [
                            f for f in item.glob("*.py") if not f.name.startswith("_")
                        ]
                        if py_files:
                            total_modules += len(py_files)
                            if item.name in gardens:
                                garden_count += 1
                            else:
                                system_count += 1

                results["total_modules"] = total_modules
                results["gardens_count"] = garden_count
                results["systems_count"] = system_count
                results["systems_checked"].append("module_count")
        except Exception as e:
            results["issues_found"].append(f"Module counting failed: {e}")

        # Emit audit start
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(
                ResonanceEvent(
                    source="continuous_audit",
                    event_type=EventType.SYSTEM_HEALTH_CHECK,
                    data={"audit_type": "full", "auto_fix": self.auto_fix},
                    timestamp=audit_start,
                    confidence=1.0,
                )
            )

        # 1. Project Structure Health
        if self.homeostasis:
            health = self.homeostasis.check_health()
            results["systems_checked"].append("project_homeostasis")

            if health.get("needs_attention", []):
                results["issues_found"].extend(health["needs_attention"])
                self.issues_found += len(health["needs_attention"])

                if self.auto_fix:
                    # Auto-fix structural issues
                    for issue in health["needs_attention"]:
                        if self._can_auto_fix(issue):
                            self._fix_issue(issue)
                            results["actions_taken"].append(f"Fixed: {issue}")
                            self.issues_fixed += 1

            results["health_score"] *= health.get("health_score", 1.0)

        # 2. Documentation Harmony
        if self.doc_harmony:
            harmony = self.doc_harmony.audit_project()
            results["systems_checked"].append("documentation_harmony")

            if harmony.get("drift_issues", []):
                drift_count = len(harmony["drift_issues"])
                results["issues_found"].append(
                    f"{drift_count} documentation drift issues"
                )
                self.issues_found += drift_count

                if self.auto_fix:
                    fixed = self.doc_harmony.heal_project()
                    results["actions_taken"].append(f"Auto-healed {fixed} docs")
                    self.issues_fixed += fixed

            results["health_score"] *= harmony.get("harmony_score", 1.0)

        # 3. Pattern Discovery
        if self.pattern_cascade:
            # Discover patterns from recent work
            patterns = self.pattern_cascade.discover_micro_patterns(
                str(self.project_root / "memory")
            )

            if patterns:
                self.patterns_discovered += len(patterns)
                results["patterns_discovered"] = len(patterns)
                results["systems_checked"].append("pattern_cascade")
                results["actions_taken"].append(
                    f"Discovered {len(patterns)} new patterns"
                )

        # 4. Memory Consolidation (if available)
        if consolidate_memories:
            try:
                consolidate_memories()
                results["systems_checked"].append("memory_consolidation")
                results["actions_taken"].append("Consolidated memories")
            except Exception:
                pass

        # Update metrics
        self.last_audit = audit_start
        self.audits_run += 1

        # Calculate audit duration
        audit_duration = (datetime.now() - audit_start).total_seconds()
        results["duration_seconds"] = audit_duration

        # Summarize top issues
        if results["issues_found"]:
            results["top_issues"] = results["issues_found"][:5]

        # Emit audit complete
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(
                ResonanceEvent(
                    source="continuous_audit",
                    event_type=EventType.AUDIT_COMPLETE,
                    data=results,
                    timestamp=datetime.now(),
                    confidence=results["health_score"],
                )
            )

        return results

    def quick_check(self) -> dict[str, Any]:
        """Quick health check (faster than full audit)"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "type": "quick_check",
            "health": "good",
        }

        # Just check if major systems are responding
        if self.homeostasis:
            try:
                health = self.homeostasis.check_health()
                if health.get("health_score", 1.0) < 0.7:
                    results["health"] = "needs_attention"
            except Exception:
                results["health"] = "error"

        return results

    def _can_auto_fix(self, issue: str) -> bool:
        """Determine if issue can be safely auto-fixed"""
        # Conservative: only auto-fix safe issues
        safe_fixes = [
            "empty directory",
            "missing __init__",
            "outdated timestamp",
            "missing readme",
        ]

        return any(safe in issue.lower() for safe in safe_fixes)

    def _fix_issue(self, issue: str) -> dict[str, Any]:
        """Attempt to fix an issue by dispatching to the appropriate fixer.

        Only handles safe, well-defined fixes. Returns a result dict.
        """
        issue_lower = issue.lower()

        if "empty directory" in issue_lower:
            path = issue_lower.split("empty directory")[-1].strip().rstrip(".")
            try:
                from pathlib import Path

                p = Path(path)
                if p.exists() and p.is_dir() and not any(p.iterdir()):
                    (p / ".gitkeep").touch()
                    self.issues_fixed += 1
                    return {
                        "status": "fixed",
                        "action": "created .gitkeep",
                        "path": str(p),
                    }
            except Exception as e:
                return {"status": "failed", "error": str(e)}

        if "missing __init__" in issue_lower:
            path = issue_lower.split("missing __init__")[-1].strip().rstrip(".")
            try:
                from pathlib import Path

                p = Path(path)
                if p.exists() and p.is_dir():
                    init_file = p / "__init__.py"
                    if not init_file.exists():
                        init_file.touch()
                        self.issues_fixed += 1
                        return {
                            "status": "fixed",
                            "action": "created __init__.py",
                            "path": str(init_file),
                        }
            except Exception as e:
                return {"status": "failed", "error": str(e)}

        return {
            "status": "skipped",
            "reason": "no safe auto-fix available for this issue type",
        }

    def get_metrics(self) -> dict[str, Any]:
        """Get audit system metrics"""
        return {
            "audits_run": self.audits_run,
            "issues_found": self.issues_found,
            "issues_fixed": self.issues_fixed,
            "patterns_discovered": self.patterns_discovered,
            "auto_fix_enabled": self.auto_fix,
            "last_audit": self.last_audit.isoformat() if self.last_audit else None,
            "audit_interval_minutes": self.audit_interval.total_seconds() / 60,
        }


def run_continuous_audit(
    project_root: str = ".", interval_minutes: int = 10, auto_fix: bool = False
) -> dict[str, Any]:
    """Convenience function to run audit

    Args:
        project_root: Project root path
        interval_minutes: Audit frequency
        auto_fix: Enable auto-fixing

    Returns:
        Audit results
    """
    auditor = ContinuousAudit(Path(project_root), interval_minutes, auto_fix)

    return auditor.run_full_audit()
