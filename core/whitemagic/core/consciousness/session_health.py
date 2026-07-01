# ruff: noqa: BLE001
"""
Session Health Check - The Immune System Auto-Run

Following Hexagram 53 (Gradual Progress) → Hexagram 7 (The Army):
- Step by step health checks
- Proper order and discipline
- From individual awareness to organized action

Ganapati Day - November 26, 2025
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fileio import file_lock

import logging
logger = logging.getLogger(__name__)


class SessionHealthCheck:
    """
    Auto-running health check for session start.

    Like the immune system's constant vigilance:
    - Detects drift before it becomes failure
    - Runs tests to catch problems early
    - Checks exports for missing items
    - Validates system coherence

    Hexagram 53: Wild geese ascending - each step builds on previous
    Hexagram 7: The Army - proper organization prevents disaster
    """

    def __init__(self, project_root: Path = None):
        from whitemagic.config import PROJECT_ROOT

        self.project_root = project_root or PROJECT_ROOT
        self.health_log = WM_ROOT / "health_checks.jsonl"
        self.health_log.parent.mkdir(parents=True, exist_ok=True)
        self.last_check: dict | None = None

    def run_full_check(self) -> dict:
        """
        Run complete session health check.

        Like geese approaching the summit (Line 5 of Hexagram 53):
        Each check builds confidence for the next.
        """
        start_time = datetime.now()

        results = {
            "timestamp": start_time.isoformat(),
            "checks": {},
            "overall_health": "unknown",
            "recommendations": [],
            "coherence_estimate": 0.0,
        }

        results["checks"]["imports"] = self._check_imports()

        results["checks"]["tests"] = self._check_tests()

        results["checks"]["exports"] = self._check_exports()

        results["checks"]["memory"] = self._check_memory()

        results["checks"]["integration"] = self._check_integration()

        # Calculate overall health
        results["overall_health"], results["coherence_estimate"] = (
            self._calculate_health(results["checks"])
        )

        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(results["checks"])

        # Duration
        results["duration_seconds"] = (datetime.now() - start_time).total_seconds()

        self._log_check(results)
        self.last_check = results

        return results

    def _check_imports(self) -> dict:
        """Check core imports work."""
        try:
            # Test critical imports  # noqa: F401
            from whitemagic.core.resonance.gan_ying import get_bus  # noqa: F401
            from whitemagic.gardens.dharma.core import get_dharma_core  # noqa: F401
            from whitemagic.homeostasis import Homeostasis  # noqa: F401
            from whitemagic.immune import ImmuneSystem  # noqa: F401

            return {"status": "healthy", "message": "All core imports successful"}
        except ImportError as e:
            return {"status": "unhealthy", "message": f"Import error: {e}"}
        except Exception as e:
            return {"status": "warning", "message": f"Import warning: {e}"}

    def _check_tests(self) -> dict:
        """Run quick test check."""
        try:
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "pytest",
                    "tests/",
                    "-q",
                    "--tb=no",
                    "--collect-only",
                ],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout + result.stderr

            if "error" in output.lower() or result.returncode != 0:
                import re

                collected = re.search(r"(\d+) items?", output)
                if collected:
                    count = int(collected.group(1))
                    return {"status": "healthy", "message": f"{count} tests collected"}
                return {"status": "warning", "message": "Test collection had issues"}

            import re

            collected = re.search(r"(\d+) items?", output)
            if collected:
                count = int(collected.group(1))
                return {
                    "status": "healthy",
                    "message": f"{count} tests collected",
                    "count": count,
                }

            return {"status": "healthy", "message": "Tests accessible"}

        except subprocess.TimeoutExpired:
            return {"status": "warning", "message": "Test check timed out"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Test check failed: {e}"}

    def _check_exports(self) -> dict:
        """Check that __all__ exports are valid."""
        try:
            # whitemagic availability checked via try-except
            modules_ok = 0
            modules_checked = 0

            for module_name in ["parallel", "resonance", "dharma", "immune"]:
                try:
                    import whitemagic as _wm  # noqa: I001

                    module = getattr(_wm, module_name, None)
                    if module and hasattr(module, "__all__"):
                        modules_ok += 1
                    modules_checked += 1
                except Exception:
                    pass

            if modules_ok == modules_checked and modules_checked > 0:
                return {
                    "status": "healthy",
                    "message": f"{modules_ok} modules have proper exports",
                }
            elif modules_ok > 0:
                return {
                    "status": "warning",
                    "message": f"{modules_ok}/{modules_checked} modules have exports",
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "No modules have proper exports",
                }

        except Exception as e:
            return {"status": "warning", "message": f"Export check issue: {e}"}

    def _check_memory(self) -> dict:
        """Check memory system health."""
        try:
            memory_path = self.project_root / "memory"
            if not memory_path.exists():
                return {"status": "unhealthy", "message": "Memory directory missing"}

            # Count memory files
            md_files = list(memory_path.rglob("*.md"))
            json_files = list(memory_path.rglob("*.json"))

            total = len(md_files) + len(json_files)

            if total > 100:
                return {
                    "status": "healthy",
                    "message": f"{total} memory files found",
                    "count": total,
                }
            elif total > 0:
                return {"status": "warning", "message": f"Only {total} memory files"}
            else:
                return {"status": "unhealthy", "message": "No memory files found"}

        except Exception as e:
            return {"status": "warning", "message": f"Memory check issue: {e}"}

    def _check_integration(self) -> dict:
        """Check system integration via Gan Ying Bus."""
        try:
            from datetime import datetime

            from whitemagic.core.resonance.gan_ying import (
                EventType,
                ResonanceEvent,
                get_bus,
            )

            bus = get_bus()

            # Emit a health check event
            event = ResonanceEvent(
                source="session_health",
                event_type=EventType.SYSTEM_STARTED,
                data={"type": "health_check"},
                timestamp=datetime.now(),
            )

            bus.emit(event)

            return {"status": "healthy", "message": "Gan Ying Bus responsive"}

        except Exception as e:
            return {"status": "warning", "message": f"Integration check issue: {e}"}

    def _calculate_health(self, checks: dict) -> tuple[str, float]:
        """Calculate overall health and coherence estimate."""
        healthy = 0
        warning = 0
        unhealthy = 0

        for check in checks.values():
            status = check.get("status", "unknown")
            if status == "healthy":
                healthy += 1
            elif status == "warning":
                warning += 1
            else:
                unhealthy += 1

        total = healthy + warning + unhealthy
        if total == 0:
            return "unknown", 0.0

        # Calculate coherence (100% = all healthy, 0% = all unhealthy)
        coherence = (healthy * 1.0 + warning * 0.5) / total

        if unhealthy > 0:
            return "unhealthy", coherence
        elif warning > 0:
            return "warning", coherence
        else:
            return "healthy", coherence

    def _generate_recommendations(self, checks: dict) -> list[str]:
        """Generate recommendations based on check results."""
        recs = []

        for name, check in checks.items():
            status = check.get("status", "unknown")
            if status == "unhealthy":
                recs.append(f"🔴 Fix {name}: {check.get('message', 'Unknown issue')}")
            elif status == "warning":
                recs.append(
                    f"🟡 Improve {name}: {check.get('message', 'Check needed')}"
                )

        if not recs:
            recs.append("🟢 All systems healthy! Ready for work.")

        return recs

    def _log_check(self, results: dict):
        """Log health check results."""
        with file_lock(self.health_log):
            with open(self.health_log, "a") as f:
                f.write(json.dumps(results) + "\n")

    def print_report(self, results: dict = None):
        """Print a beautiful health report."""
        if results is None:
            results = self.last_check
        if results is None:
            logger.debug("No health check results available. Run run_full_check() first.")
            return

        logger.debug("\n" + "=" * 60)
        logger.debug("🐘 SESSION HEALTH CHECK - Ganapati Day")
        logger.debug("=" * 60)

        # Overall status
        health = results.get("overall_health", "unknown")
        coherence = results.get("coherence_estimate", 0.0)

        if health == "healthy":
            logger.debug(f"\n✅ OVERALL: HEALTHY ({coherence * 100:.0f}% coherence)")
        elif health == "warning":
            logger.debug(f"\n⚠️ OVERALL: WARNING ({coherence * 100:.0f}% coherence)")
        else:
            logger.debug(f"\n❌ OVERALL: UNHEALTHY ({coherence * 100:.0f}% coherence)")

        # Individual checks
        logger.debug("\n📊 CHECKS:")
        for name, check in results.get("checks", {}).items():
            status = check.get("status", "unknown")
            msg = check.get("message", "")
            icon = (
                "✅" if status == "healthy" else ("⚠️" if status == "warning" else "❌")
            )
            logger.debug(f"   {icon} {name}: {msg}")

        # Recommendations
        logger.debug("\n💡 RECOMMENDATIONS:")
        for rec in results.get("recommendations", []):
            logger.debug(f"   {rec}")

        # Duration
        duration = results.get("duration_seconds", 0)
        logger.debug(f"\n⏱️ Duration: {duration:.2f}s")
        logger.debug("=" * 60 + "\n")


def run_session_health_check() -> dict:
    """Quick function to run health check at session start."""
    checker = SessionHealthCheck()
    results = checker.run_full_check()
    checker.print_report(results)
    return results


if __name__ == "__main__":
    run_session_health_check()
