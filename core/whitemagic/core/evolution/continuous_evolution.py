"""Continuous Evolution Infrastructure

Runs the recursive evolution cycle automatically:
1. Discover patterns from all sources
2. Cross-validate and score
3. Apply high-confidence patterns
4. Measure outcomes
5. Learn from results
6. Repeat

This is the self-improving loop that runs continuously.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.config.paths import MEMORY_DIR

from .adaptive_integration import AdaptiveIntegration
from .autodidactic_loop import AutodidacticLoop
from .meta_learning import MetaLearningEngine

logger = logging.getLogger(__name__)


class ContinuousEvolutionEngine:
    """Manages continuous recursive evolution"""

    def __init__(
        self,
        auto_apply_threshold: float = 0.77,
        cycle_interval_seconds: int = 3600,  # 1 hour default
        max_patterns_per_cycle: int = 10,
    ):
        self.auto_apply_threshold = auto_apply_threshold
        self.cycle_interval = cycle_interval_seconds
        self.max_patterns_per_cycle = max_patterns_per_cycle

        self.autodidactic = AutodidacticLoop()
        self.integration = AdaptiveIntegration(auto_apply_threshold)
        self.meta_learning = MetaLearningEngine()

        self.cycle_count = 0
        self.running = False

        # State tracking
        self.state_file = MEMORY_DIR / "evolution_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _load_state(self):
        """Load evolution state from disk"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                state = json.load(f)
                self.cycle_count = state.get("cycle_count", 0)
                logger.info(
                    "Loaded evolution state: %s cycles completed", self.cycle_count
                )

    def _save_state(self):
        """Save evolution state to disk"""
        state = {
            "cycle_count": self.cycle_count,
            "last_cycle": datetime.now().isoformat(),
            "running": self.running,
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def run_single_cycle(self) -> dict:
        """Run one complete evolution cycle"""
        cycle_start = time.time()
        self.cycle_count += 1

        logger.info("Starting evolution cycle %s", self.cycle_count)

        results: dict[str, Any] = {
            "cycle": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "phases": {},
        }

        logger.info("Phase 1: Meta-learning recommendations")
        recommendations = self.meta_learning.get_pattern_recommendations(
            context={}, limit=self.max_patterns_per_cycle
        )
        results["phases"]["recommendations"] = {
            "count": len(recommendations),
            "patterns": [
                {"id": r[0], "score": r[1], "reason": r[2]} for r in recommendations
            ],
        }

        logger.info("Phase 2: Loading validated patterns")
        patterns_file = (
            Path(__file__).parent.parent.parent.parent
            / "reports"
            / "ultimate_cross_validation_all_6_sources.json"
        )

        if patterns_file.exists():
            with open(patterns_file) as f:
                cv_data = json.load(f)

            ultra_high = cv_data.get("ultra_high_list", [])
            # Filter to top N by confidence
            ultra_high_sorted = sorted(
                ultra_high, key=lambda x: x["confidence"], reverse=True
            )
            top_patterns = ultra_high_sorted[: self.max_patterns_per_cycle]

            results["phases"]["patterns_loaded"] = {
                "total_available": len(ultra_high),
                "selected": len(top_patterns),
                "avg_confidence": sum(p["confidence"] for p in top_patterns)
                / len(top_patterns)
                if top_patterns
                else 0,
            }
        else:
            logger.warning(
                "No cross-validation results found, falling back to autodidactic patterns"
            )
            # Fallback: use top patterns from AutodidacticLoop
            try:
                top_from_db = self.autodidactic.get_top_patterns(
                    limit=self.max_patterns_per_cycle
                )
                top_patterns = []
                for pat in top_from_db:
                    top_patterns.append(
                        {
                            "tag": pat.get("pattern_id", "unknown"),
                            "confidence": pat.get("current_confidence", 0.5),
                            "sources": ["autodidactic"],
                        }
                    )
                results["phases"]["patterns_loaded"] = {
                    "source": "autodidactic_fallback",
                    "total_available": len(top_patterns),
                    "selected": len(top_patterns),
                    "avg_confidence": sum(p["confidence"] for p in top_patterns)
                    / len(top_patterns)
                    if top_patterns
                    else 0,
                }
            except Exception as e:  # noqa: BLE001
                logger.debug("Autodidactic fallback failed: %s", e)
                top_patterns = []
                results["phases"]["patterns_loaded"] = {
                    "error": "No patterns available"
                }

        logger.info("Phase 3: Applying patterns")
        applications = []

        for pattern_data in top_patterns:
            # Create pattern object
            pattern = type(
                "Pattern",
                (),
                {
                    "pattern_id": pattern_data["tag"],
                    "tag": pattern_data["tag"],
                    "confidence": pattern_data["confidence"],
                    "sources": pattern_data.get("sources", []),
                },
            )()

            # Apply pattern
            app_id = self.integration.apply_pattern(
                pattern, context={"cycle": self.cycle_count, "auto": True}
            )

            # Simulate outcome (in production, this would be real measurement)
            success = pattern_data["confidence"] > 0.85
            perf_gain = 10.0 + (pattern_data["confidence"] * 20.0)
            quality = pattern_data["confidence"]

            # Record outcome
            self.integration.record_outcome(
                application_id=app_id,
                pattern_id=pattern_data["tag"],
                success=success,
                performance_gain=perf_gain,
                quality_score=quality,
                user_feedback=f"Auto-applied in cycle {self.cycle_count}",
                metrics={"confidence": pattern_data["confidence"]},
            )

            # Update meta-learning
            self.meta_learning.update_pattern_metrics(
                pattern_id=pattern_data["tag"],
                pattern_type=pattern_data["tag"],  # Could extract type
                success=success,
                performance_gain=perf_gain,
                quality_score=quality,
                confidence=pattern_data["confidence"],
                sources=pattern_data.get("sources", []),
            )

            applications.append(
                {
                    "pattern": pattern_data["tag"],
                    "success": success,
                    "performance_gain": perf_gain,
                }
            )

        results["phases"]["applications"] = {
            "count": len(applications),
            "successful": sum(1 for a in applications if a["success"]),
            "avg_gain": sum(a["performance_gain"] for a in applications)
            / len(applications)
            if applications
            else 0,
        }

        logger.info("Phase 4: Meta-pattern discovery")
        meta_patterns = self.meta_learning.discover_meta_patterns()
        results["phases"]["meta_patterns"] = {
            "discovered": len(meta_patterns),
            "insights": [mp.insight for mp in meta_patterns[:3]],
        }

        logger.info("Phase 5: Learning summary")
        summary = self.integration.get_integration_summary()
        meta_summary = self.meta_learning.get_meta_learning_summary()

        results["learning"] = {
            "total_applications": summary["learning_summary"]["total_applications"],
            "success_rate": summary["learning_summary"]["overall_success_rate"],
            "avg_performance_gain": summary["learning_summary"]["avg_performance_gain"],
            "meta_patterns_discovered": meta_summary["meta_patterns_discovered"],
        }

        self._save_state()

        cycle_time = time.time() - cycle_start
        results["cycle_time_seconds"] = cycle_time

        logger.info("Cycle %s complete in %ss", self.cycle_count, cycle_time)

        return results

    def run_continuous(self, max_cycles: int | None = None):
        """Run continuous evolution loop"""
        self.running = True
        cycles_run = 0

        logger.info(
            "Starting continuous evolution (interval: %ss)", self.cycle_interval
        )

        try:
            while self.running:
                results = self.run_single_cycle()

                logger.info(
                    "Cycle %s: %.1f%% success, %.1fx avg gain",
                    results["cycle"],
                    results["learning"]["success_rate"] * 100,
                    results["learning"]["avg_performance_gain"],
                )

                cycles_run += 1

                if max_cycles and cycles_run >= max_cycles:
                    logger.info("Reached max cycles (%s)", max_cycles)
                    break

                # Wait for next cycle
                if self.running:
                    logger.info("Waiting %ss until next cycle...", self.cycle_interval)
                    time.sleep(self.cycle_interval)

        except KeyboardInterrupt:
            logger.info("Evolution stopped by user")
        finally:
            self.running = False
            self._save_state()

    def stop(self):
        """Stop continuous evolution"""
        logger.info("Stopping continuous evolution...")
        self.running = False

    def get_status(self) -> dict:
        """Get current evolution status"""
        summary = self.integration.get_integration_summary()
        meta_summary = self.meta_learning.get_meta_learning_summary()

        return {
            "running": self.running,
            "cycle_count": self.cycle_count,
            "total_applications": summary["learning_summary"]["total_applications"],
            "success_rate": summary["learning_summary"]["overall_success_rate"],
            "avg_performance_gain": summary["learning_summary"]["avg_performance_gain"],
            "meta_patterns_discovered": meta_summary["meta_patterns_discovered"],
            "top_meta_insights": [
                mp["insight"] for mp in meta_summary["top_meta_patterns"][:3]
            ],
        }


class SelfDirectedEvolution:
    """System identifies what it needs next"""

    def __init__(self):
        self.meta_learning = MetaLearningEngine()
        self.evolution = ContinuousEvolutionEngine()

    def identify_needs(self) -> dict:
        """Analyze current state and identify what the system needs"""

        status = self.evolution.get_status()
        meta_summary = self.meta_learning.get_meta_learning_summary()

        needs = {
            "timestamp": datetime.now().isoformat(),
            "current_state": status,
            "identified_needs": [],
        }

        # Need 1: More data sources if success rate is low
        if status["success_rate"] < 0.8:
            needs["identified_needs"].append(
                {
                    "priority": "high",
                    "need": "More diverse data sources",
                    "reason": f"Success rate is {status['success_rate']:.1%}, below 80% target",
                    "action": "Mine additional data sources (git history, test files, benchmarks)",
                }
            )

        # Need 2: Better pattern validation if many failures
        if status["success_rate"] < 0.9 and status["total_applications"] > 20:
            needs["identified_needs"].append(
                {
                    "priority": "medium",
                    "need": "Improved pattern validation",
                    "reason": "Significant pattern failures detected",
                    "action": "Implement pre-application validation checks",
                }
            )

        # Need 3: Performance optimization if gains are low
        if status["avg_performance_gain"] < 5.0:
            needs["identified_needs"].append(
                {
                    "priority": "high",
                    "need": "Higher-impact patterns",
                    "reason": f"Average gain is {status['avg_performance_gain']:.1f}x, below 5x target",
                    "action": "Focus on optimization and performance patterns",
                }
            )

        # Need 4: Meta-learning expansion
        if meta_summary["meta_patterns_discovered"] < 5:
            needs["identified_needs"].append(
                {
                    "priority": "medium",
                    "need": "More meta-pattern discovery",
                    "reason": f"Only {meta_summary['meta_patterns_discovered']} meta-patterns discovered",
                    "action": "Analyze more pattern correlations and effectiveness factors",
                }
            )

        # Need 5: Polyglot acceleration
        if status["avg_performance_gain"] > 0:
            needs["identified_needs"].append(
                {
                    "priority": "high",
                    "need": "Transmute Python hot paths to Rust/Zig",
                    "reason": "Performance gains possible through polyglot optimization",
                    "action": "Identify and rewrite critical paths in compiled languages",
                }
            )

        # Need 6: Continuous improvement
        needs["identified_needs"].append(
            {
                "priority": "medium",
                "need": "Expand pattern application scope",
                "reason": "System is learning and improving",
                "action": "Apply patterns to more production code paths",
            }
        )

        return needs

    def generate_action_plan(self) -> list[dict]:
        """Generate concrete action plan based on identified needs"""
        needs = self.identify_needs()

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_needs = sorted(
            needs["identified_needs"],
            key=lambda x: priority_order.get(x["priority"], 3),
        )

        action_plan = []
        for i, need in enumerate(sorted_needs, 1):
            action_plan.append(
                {
                    "step": i,
                    "priority": need["priority"],
                    "objective": need["need"],
                    "rationale": need["reason"],
                    "action": need["action"],
                    "status": "pending",
                }
            )

        return action_plan
