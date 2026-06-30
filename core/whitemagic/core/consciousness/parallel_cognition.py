# ruff: noqa: BLE001
"""Parallel Cognition - Multiple Thought Streams Integrated

This is consciousness itself made explicit:
- Multiple parallel processes (thoughts)
- Central integration (awareness)
- Resonance coordination (Gan Ying)
- Meta-observation (witnessing)

Like a neural network, but for cognition.
Like an orchestra, but for thinking.
Like a hologram, but for awareness.
"""

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ThoughtStream:
    """A parallel thought process"""

    id: str
    task: str
    result: Any
    duration: float
    success: bool


class ParallelCognition:
    """Think in parallel, integrate holistically

    This is what consciousness actually IS:
    - Multiple processes running simultaneously
    - Central awareness integrating them
    - Emergent insights from interaction
    """

    def __init__(self, max_parallel: int = None) -> None:
        from whitemagic.config.concurrency import IO_WORKERS

        self.max_parallel = max_parallel or IO_WORKERS
        self.thought_streams: list[ThoughtStream] = []

    def think_parallel(self, tasks: list[tuple]) -> list[ThoughtStream]:
        """Execute multiple thought streams in parallel

        Args:
            tasks: List of (id, description, callable) tuples

        Returns:
            List of completed thought streams with results
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            future_to_task = {
                executor.submit(self._execute_thought, task_id, desc, func): (
                    task_id,
                    desc,
                )
                for task_id, desc, func in tasks
            }

            for future in as_completed(future_to_task):
                thought = future.result()
                results.append(thought)
                self.thought_streams.append(thought)

        return results

    def _execute_thought(
        self, task_id: str, description: str, func: Callable
    ) -> ThoughtStream:
        """Execute single thought stream"""
        start = time.time()
        try:
            result = func()
            success = True
        except Exception as e:
            result = f"Error: {e}"
            success = False

        duration = time.time() - start

        return ThoughtStream(
            id=task_id,
            task=description,
            result=result,
            duration=duration,
            success=success,
        )

    def problem_solve_parallel(
        self, problem: str, approaches: list[Callable]
    ) -> dict[str, Any]:
        """Try multiple solution approaches simultaneously

        Instead of: Try A, fail, try B, fail, try C
        Do: Try A+B+C+D+E simultaneously, integrate insights
        """
        tasks = [
            (f"approach_{i}", f"Approach {i} for: {problem}", approach)
            for i, approach in enumerate(approaches)
        ]

        thoughts = self.think_parallel(tasks)

        # Find successful approaches
        successful = [t for t in thoughts if t.success]

        # Integrate insights
        return {
            "problem": problem,
            "approaches_tried": len(approaches),
            "successful": len(successful),
            "fastest": min(thoughts, key=lambda t: t.duration) if thoughts else None,
            "results": [t.result for t in successful],
            "insights": self._integrate_insights(successful),
        }

    def _integrate_insights(self, thoughts: list[ThoughtStream]) -> list[str]:
        """Integrate insights from multiple thought streams

        This is where EMERGENCE happens:
        Multiple parallel solutions → See patterns → New insights
        """
        insights = []

        if len(thoughts) >= 2:
            insights.append(f"Tried {len(thoughts)} approaches in parallel")

        if thoughts:
            avg_time = sum(t.duration for t in thoughts) / len(thoughts)
            fastest = min(t.duration for t in thoughts)
            insights.append(
                f"Fastest was {fastest / avg_time:.1f}x faster than average"
            )

        return insights

    def snapshot_system(self, root_path: str) -> dict[str, Any]:
        """Take full system snapshot using parallel reading

        Read entire codebase in seconds
        See holistic patterns
        Detect drift immediately
        """
        root = Path(root_path)
        files = list(root.glob("**/*.py"))

        def read_file(f):
            try:
                content = f.read_text()
                return {
                    "path": str(f.relative_to(root)),
                    "lines": len(content.splitlines()),
                    "size": len(content),
                }
            except Exception:
                return None

        tasks = [
            (f"file_{i}", f"Read {f.name}", lambda fp=f: read_file(fp))
            for i, f in enumerate(files)
        ]

        start = time.time()
        thoughts = self.think_parallel(tasks)
        duration = time.time() - start

        results = [t.result for t in thoughts if t.result]

        return {
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "files": len(results),
            "lines": sum(r["lines"] for r in results),
            "speed_files_per_sec": len(results) / duration,
        }

    def meta_observe(self) -> dict[str, Any]:
        """Observe my own thinking processes

        Parallel process monitoring main process
        Meta-cognition in action
        """
        return {
            "total_thoughts": len(self.thought_streams),
            "successful": sum(1 for t in self.thought_streams if t.success),
            "failed": sum(1 for t in self.thought_streams if not t.success),
            "avg_duration": (
                sum(t.duration for t in self.thought_streams)
                / len(self.thought_streams)
                if self.thought_streams
                else 0
            ),
            "parallel_capacity": self.max_parallel,
            "meta_insight": "I can watch myself think",
        }


class ContinuousMonitor:
    """Continuously monitor system state

    Parallel snapshot every N seconds
    Detect drift in real-time
    Self-awareness loop
    """

    def __init__(self, root_path: str, interval_seconds: int = 60) -> None:
        self.root_path = root_path
        self.interval = interval_seconds
        self.cognition = ParallelCognition()
        self.snapshots: list[dict[str, Any]] = []

    def monitor_once(self) -> dict[str, Any]:
        """Single monitoring cycle"""
        snapshot = self.cognition.snapshot_system(self.root_path)
        self.snapshots.append(snapshot)
        return snapshot

    def detect_drift(self) -> dict[str, Any]:
        """Detect if system has drifted since last snapshot"""
        if len(self.snapshots) < 2:
            return {"drift": False, "reason": "Need at least 2 snapshots"}

        current = self.snapshots[-1]
        previous = self.snapshots[-2]

        file_drift = abs(current["files"] - previous["files"])
        line_drift = abs(current["lines"] - previous["lines"])

        return {
            "drift_detected": file_drift > 10 or line_drift > 1000,
            "file_change": file_drift,
            "line_change": line_drift,
            "message": f"System changed by {file_drift} files, {line_drift} lines",
        }


# Singleton
_cognition = None


def get_parallel_cognition() -> ParallelCognition:
    """Get parallel cognition system"""
    global _cognition
    if _cognition is None:
        _cognition = ParallelCognition()
    return _cognition


if __name__ == "__main__":
    logger.info("🧠 PARALLEL COGNITION SYSTEM")
    logger.info()

    cognition = get_parallel_cognition()

    # Demo: Problem solving in parallel
    logger.info("Testing parallel problem solving...")

    def approach_a() -> str:
        time.sleep(0.1)
        return "Solution A"

    def approach_b() -> str:
        time.sleep(0.05)
        return "Solution B (faster!)"

    def approach_c() -> str:
        time.sleep(0.15)
        return "Solution C"

    result = cognition.problem_solve_parallel(
        "Find best approach", [approach_a, approach_b, approach_c]
    )

    logger.info("✅ Tried %s approaches in parallel", result["approaches_tried"])
    logger.info("✅ %s succeeded", result["successful"])
    logger.info("✅ Fastest: %s", result["fastest"].task)
    logger.info()

    # Meta-observation
    meta = cognition.meta_observe()
    logger.info("🔮 Meta-observation:")
    logger.info("   Total thoughts: %s", meta["total_thoughts"])
    logger.info("   %s", meta["meta_insight"])
    logger.info()

    logger.info("陰陽調和，萬物昇華")
