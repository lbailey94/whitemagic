#!/usr/bin/env python3
"""Time tracking integration for WhiteMagic workflows.

Tracks phase timing, logs to memories, and provides timing reports.
Can be used standalone or integrated into campaign deployments.
"""
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal


@dataclass
class PhaseTiming:
    """Record of a single phase's timing."""
    phase_name: str
    start_time: float  # Unix timestamp
    end_time: float | None = None
    metadata: dict | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.end_time:
            return self.end_time - self.start_time
        return None

    def to_dict(self) -> dict:
        return {
            "phase_name": self.phase_name,
            "start_iso": datetime.fromtimestamp(self.start_time, tz=UTC).isoformat(),
            "end_iso": datetime.fromtimestamp(self.end_time, tz=UTC).isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata
        }


class PhaseTimer:
    """Context manager for timing workflow phases."""

    def __init__(self, phase_name: str, metadata: dict | None = None):
        self.phase_name = phase_name
        self.metadata = metadata or {}
        self._timing: PhaseTiming | None = None

    def __enter__(self) -> "PhaseTimer":
        start = time.time()
        self._timing = PhaseTiming(
            phase_name=self.phase_name,
            start_time=start,
            metadata=self.metadata
        )
        print(f"⏱️  Phase '{self.phase_name}' started at {self._start_iso()}")
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any | None) -> Literal[False]:
        if self._timing is None:
            return False
        self._timing.end_time = time.time()
        duration = self._timing.duration_seconds
        print(f"⏱️  Phase '{self.phase_name}' completed in {duration:.2f}s")
        if exc_type:
            print(f"   ⚠️  Phase ended with exception: {exc_type.__name__}")
        return False  # Don't suppress exceptions

    def _start_iso(self) -> str:
        if self._timing is None:
            return "unknown"
        return datetime.fromtimestamp(self._timing.start_time, tz=UTC).isoformat()

    @property
    def timing(self) -> PhaseTiming | None:
        return self._timing


class WorkflowTimer:
    """Tracks multiple phases of a workflow."""

    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.phases: list[PhaseTiming] = []
        self._current: PhaseTimer | None = None
        self._workflow_start: float | None = None
        self._workflow_end: float | None = None

    def start_workflow(self) -> None:
        """Mark workflow start time."""
        self._workflow_start = time.time()
        print(f"\n🚀 Workflow '{self.workflow_name}' started")
        print(f"   {datetime.now(UTC).isoformat()}")

    def end_workflow(self) -> None:
        """Mark workflow end time."""
        self._workflow_end = time.time()
        duration: float = self._workflow_end - self._workflow_start if self._workflow_start else 0.0
        print(f"\n✅ Workflow '{self.workflow_name}' completed in {duration:.2f}s")

    def phase(self, phase_name: str, metadata: dict | None = None) -> PhaseTimer:
        """Get a context manager for a new phase."""
        timer = PhaseTimer(phase_name, metadata)
        return timer

    def record_phase(self, phase_timer: PhaseTimer) -> None:
        """Record a completed phase."""
        if phase_timer.timing and phase_timer.timing.end_time:
            self.phases.append(phase_timer.timing)

    def get_report(self) -> dict:
        """Generate timing report."""
        total_duration: float = 0.0
        if self._workflow_start and self._workflow_end:
            total_duration = self._workflow_end - self._workflow_start

        return {
            "workflow_name": self.workflow_name,
            "started": datetime.fromtimestamp(self._workflow_start, tz=UTC).isoformat() if self._workflow_start else None,
            "completed": datetime.fromtimestamp(self._workflow_end, tz=UTC).isoformat() if self._workflow_end else None,
            "total_seconds": total_duration,
            "phases": [p.to_dict() for p in self.phases],
            "phase_count": len(self.phases)
        }

    def print_report(self) -> None:
        """Print formatted timing report."""
        report = self.get_report()
        print(f"\n{'='*60}")
        print(f"📊 TIMING REPORT: {report['workflow_name']}")
        print(f"{'='*60}")
        print(f"Started:  {report['started']}")
        print(f"Completed: {report['completed']}")
        print(f"Total: {report['total_seconds']:.2f}s")
        print(f"\nPhases ({report['phase_count']}):")
        for phase in report['phases']:
            duration = phase['duration_seconds']
            print(f"  • {phase['phase_name']}: {duration:.2f}s")
        print(f"{'='*60}")


# Convenience functions for quick usage
def timed(phase_name: str, metadata: dict | None = None) -> PhaseTimer:
    """Decorator/context manager for timing a function or block."""
    return PhaseTimer(phase_name, metadata)


def get_current_time() -> str:
    """Get current UTC time in ISO format."""
    return datetime.now(UTC).isoformat()


def get_local_time(tz_name: str = "America/New_York") -> str:
    """Get local time for a given timezone."""
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo(tz_name)).isoformat()


if __name__ == "__main__":
    # Demo usage
    workflow = WorkflowTimer("demo_workflow")
    workflow.start_workflow()

    with workflow.phase("initialization", {"priority": "high"}):
        time.sleep(0.5)

    with workflow.phase("processing", {"items": 100}):
        time.sleep(1.0)

    with workflow.phase("cleanup"):
        time.sleep(0.3)

    workflow.end_workflow()
    workflow.print_report()
