"""Granular Progress Tracker — Two-decimal-place progress bars with timestamps and logging.

Provides detailed progress tracking for campaigns, yin-yang cycles, batch operations,
and any long-running process. Logs issues/skips/warnings to file with system timestamps.

Usage:
    tracker = ProgressTracker("Association Typing", total=190243)
    for batch in batches:
        tracker.advance(len(batch), detail="typed SIBLING_OF")
        tracker.skip(5, reason="orphan associations")
        tracker.warn("Low confidence match", context={"id": "abc123"})
    tracker.finish()
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from whitemagic.config.paths import PROGRESS_LOGS_DIR
from whitemagic.utils.fast_json import dumps_str as _json_dumps

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    """Single progress event with timestamp."""

    timestamp: datetime
    elapsed_s: float
    event_type: str  # "advance", "skip", "warn", "error", "milestone", "finish"
    message: str
    count: int = 0
    detail: str | None = None
    context: dict[str, Any] | None = None


@dataclass
class ProgressStats:
    """Accumulated statistics for a progress tracker."""

    total: int = 0
    completed: int = 0
    skipped: int = 0
    warnings: int = 0
    errors: int = 0
    milestones: list[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float | None = None
    items_per_second: float = 0.0
    eta_seconds: float | None = None


class ProgressTracker:
    """Granular progress tracker with 00.00% precision, timestamps, and file logging.

    Features:
    - Two-decimal-place percentage display (00.00%)
    - System timestamps on every event (ISO 8601)
    - Skip/warning/error counting and logging
    - Items/sec throughput tracking with ETA
    - JSON log file output for post-analysis
    - Nested sub-trackers for hierarchical progress
    - Configurable output (stderr, file, or silent)
    """

    def __init__(
        self,
        name: str,
        total: int = 0,
        log_dir: Path | None = None,
        output: TextIO | None = None,
        parent: ProgressTracker | None = None,
        bar_width: int = 30,
        show_bar: bool = True,
    ) -> None:
        self.name = name
        self.total = total
        self.bar_width = bar_width
        self.show_bar = show_bar
        self.output = output or sys.stderr
        self.parent = parent

        # Stats
        self.completed = 0
        self.skipped = 0
        self.warnings = 0
        self.errors = 0
        self.milestones: list[str] = []
        self.start_time = time.monotonic()
        self.start_datetime = datetime.now()
        self.end_time: float | None = None

        # Events log
        self.events: list[ProgressEvent] = []

        # Log file
        self.log_dir = log_dir or PROGRESS_LOGS_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        ts = self.start_datetime.strftime("%Y%m%d_%H%M%S")
        safe_name = name.lower().replace(" ", "_").replace("/", "_")[:40]
        self.log_file = self.log_dir / f"{ts}_{safe_name}.jsonl"

        # Sub-trackers
        self.children: list[ProgressTracker] = []

        # Last display update (throttle to avoid flicker)
        self._last_display = 0.0
        self._display_interval = 0.1  # seconds

        # Write header
        self._log_event(
            ProgressEvent(
                timestamp=self.start_datetime,
                elapsed_s=0.0,
                event_type="start",
                message=f"Started: {name}",
                count=total,
                detail=f"total={total}",
            )
        )

    @property
    def percent(self) -> float:
        """Current progress as percentage (0.00 to 100.00)."""
        if self.total <= 0:
            return 0.0
        return min(100.0, (self.completed / self.total) * 100.0)

    @property
    def elapsed(self) -> float:
        """Elapsed time in seconds."""
        end = self.end_time or time.monotonic()
        return end - self.start_time

    @property
    def throughput(self) -> float:
        """Items per second."""
        e = self.elapsed
        if e <= 0:
            return 0.0
        return self.completed / e

    @property
    def eta_seconds(self) -> float | None:
        """Estimated time remaining in seconds."""
        if self.total <= 0 or self.completed <= 0:
            return None
        remaining = self.total - self.completed
        rate = self.throughput
        if rate <= 0:
            return None
        return remaining / rate

    def advance(self, count: int = 1, detail: str | None = None) -> None:
        """Record progress of `count` items."""
        self.completed += count
        now = time.monotonic()

        event = ProgressEvent(
            timestamp=datetime.now(),
            elapsed_s=now - self.start_time,
            event_type="advance",
            message=f"+{count:,}",
            count=count,
            detail=detail,
        )
        self.events.append(event)
        self._log_event(event)

        # Throttled display update
        if now - self._last_display >= self._display_interval:
            self._display()
            self._last_display = now

        # Update parent if nested
        if self.parent:
            self.parent._child_advanced(count)

    def skip(self, count: int = 1, reason: str = "") -> None:
        """Record `count` skipped items."""
        self.skipped += count
        event = ProgressEvent(
            timestamp=datetime.now(),
            elapsed_s=time.monotonic() - self.start_time,
            event_type="skip",
            message=f"Skipped {count:,}: {reason}",
            count=count,
            detail=reason,
        )
        self.events.append(event)
        self._log_event(event)

    def warn(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Record a warning."""
        self.warnings += 1
        event = ProgressEvent(
            timestamp=datetime.now(),
            elapsed_s=time.monotonic() - self.start_time,
            event_type="warn",
            message=message,
            context=context,
        )
        self.events.append(event)
        self._log_event(event)

    def error(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Record an error."""
        self.errors += 1
        event = ProgressEvent(
            timestamp=datetime.now(),
            elapsed_s=time.monotonic() - self.start_time,
            event_type="error",
            message=message,
            context=context,
        )
        self.events.append(event)
        self._log_event(event)

    def milestone(self, message: str) -> None:
        """Record a milestone achievement."""
        self.milestones.append(message)
        event = ProgressEvent(
            timestamp=datetime.now(),
            elapsed_s=time.monotonic() - self.start_time,
            event_type="milestone",
            message=message,
        )
        self.events.append(event)
        self._log_event(event)
        # Always display milestones
        self._display(force=True, milestone=message)

    def sub_tracker(self, name: str, total: int = 0) -> ProgressTracker:
        """Create a nested sub-tracker."""
        child = ProgressTracker(
            name=name,
            total=total,
            log_dir=self.log_dir,
            output=self.output,
            parent=self,
            bar_width=self.bar_width,
            show_bar=self.show_bar,
        )
        self.children.append(child)
        return child

    def finish(self, summary: str | None = None) -> ProgressStats:
        """Mark progress as complete and return stats."""
        self.end_time = time.monotonic()

        stats = ProgressStats(
            total=self.total,
            completed=self.completed,
            skipped=self.skipped,
            warnings=self.warnings,
            errors=self.errors,
            milestones=self.milestones,
            start_time=self.start_time,
            end_time=self.end_time,
            items_per_second=self.throughput,
        )

        event = ProgressEvent(
            timestamp=datetime.now(),
            elapsed_s=self.elapsed,
            event_type="finish",
            message=summary or f"Complete: {self.completed:,}/{self.total:,}",
            detail=f"skip={self.skipped:,} warn={self.warnings} err={self.errors}",
        )
        self.events.append(event)
        self._log_event(event)

        # Final display
        self._display(force=True, finished=True)

        return stats

    def get_stats(self) -> ProgressStats:
        """Get current stats without finishing."""
        return ProgressStats(
            total=self.total,
            completed=self.completed,
            skipped=self.skipped,
            warnings=self.warnings,
            errors=self.errors,
            milestones=self.milestones,
            start_time=self.start_time,
            end_time=self.end_time,
            items_per_second=self.throughput,
            eta_seconds=self.eta_seconds,
        )

    def _child_advanced(self, count: int) -> None:
        """Called when a child sub-tracker advances."""
        # Don't double-count, just trigger display refresh
        now = time.monotonic()
        if now - self._last_display >= self._display_interval:
            self._display()
            self._last_display = now

    def _display(
        self,
        force: bool = False,
        finished: bool = False,
        milestone: str | None = None,
    ) -> None:
        """Render progress bar to output stream."""
        if not self.show_bar:
            return

        now = datetime.now()
        ts = now.strftime("%H:%M:%S")
        pct = self.percent

        # Build progress bar
        filled = int(self.bar_width * pct / 100)
        bar = "█" * filled + "░" * (self.bar_width - filled)

        # Throughput and ETA
        rate = self.throughput
        eta = self.eta_seconds

        eta_str = ""
        if eta is not None and not finished:
            if eta < 60:
                eta_str = f" ETA {eta:.0f}s"
            elif eta < 3600:
                eta_str = f" ETA {eta / 60:.1f}m"
            else:
                eta_str = f" ETA {eta / 3600:.1f}h"

        rate_str = ""
        if rate > 0:
            if rate >= 1000:
                rate_str = f" {rate / 1000:.1f}K/s"
            else:
                rate_str = f" {rate:.0f}/s"

        # Counters
        skip_str = f" skip:{self.skipped}" if self.skipped else ""
        warn_str = f" warn:{self.warnings}" if self.warnings else ""
        err_str = f" ERR:{self.errors}" if self.errors else ""

        # Status icon
        if finished:
            icon = "✅" if self.errors == 0 else "⚠️"
        elif milestone:
            icon = "🏁"
        else:
            icon = "⏳"

        line = (
            f"\r{icon} [{ts}] {self.name}: |{bar}| "
            f"{pct:06.2f}% ({self.completed:,}/{self.total:,})"
            f"{rate_str}{eta_str}{skip_str}{warn_str}{err_str}"
        )

        if milestone:
            line += f" — {milestone}"

        if finished:
            line += f" [{self.elapsed:.1f}s]"
            self.output.write(line + "\n")
        else:
            self.output.write(line)
        self.output.flush()

    def _log_event(self, event: ProgressEvent) -> None:
        """Write event to JSONL log file."""
        try:
            record = {
                "ts": event.timestamp.isoformat(),
                "elapsed_s": round(event.elapsed_s, 3),
                "tracker": self.name,
                "type": event.event_type,
                "msg": event.message,
                "pct": round(self.percent, 2),
                "completed": self.completed,
                "total": self.total,
            }
            if event.count:
                record["count"] = event.count
            if event.detail:
                record["detail"] = event.detail
            if event.context:
                record["context"] = event.context

            with open(self.log_file, "a") as f:
                f.write(_json_dumps(record) + "\n")
        except (OSError, FileNotFoundError, PermissionError):
            pass  # Never crash on logging


class CampaignProgressTracker:
    """High-level tracker for campaign deployments with per-objective sub-tracking."""

    def __init__(self, campaign_name: str, total_objectives: int = 0) -> None:
        self.tracker = ProgressTracker(
            name=f"Campaign: {campaign_name}",
            total=total_objectives,
        )
        self.objective_trackers: dict[str, ProgressTracker] = {}
        self.campaign_name = campaign_name

    def start_objective(self, name: str, total: int = 0) -> ProgressTracker:
        """Start tracking a campaign objective."""
        sub = self.tracker.sub_tracker(name, total)
        self.objective_trackers[name] = sub
        return sub

    def finish(self) -> dict[str, Any]:
        """Finish campaign and return summary."""
        stats = self.tracker.finish()
        return {
            "campaign": self.campaign_name,
            "total": stats.total,
            "completed": stats.completed,
            "elapsed_s": round(self.tracker.elapsed, 2),
            "throughput": round(stats.items_per_second, 1),
            "skipped": stats.skipped,
            "warnings": stats.warnings,
            "errors": stats.errors,
            "milestones": stats.milestones,
            "log_file": str(self.tracker.log_file),
            "objectives": {
                name: {
                    "completed": t.completed,
                    "total": t.total,
                    "pct": round(t.percent, 2),
                    "skipped": t.skipped,
                    "warnings": t.warnings,
                }
                for name, t in self.objective_trackers.items()
            },
        }


class YinYangCycleTracker:
    """Specialized tracker for yin-yang cycle phases."""

    def __init__(self, campaign_name: str, max_cycles: int = 10) -> None:
        self.tracker = ProgressTracker(
            name=f"☯ {campaign_name}",
            total=max_cycles,
        )
        self.cycle_num = 0
        self.phase_trackers: list[ProgressTracker] = []

    def start_yin(self, detail: str = "recon") -> ProgressTracker:
        """Start a YIN (recon) phase."""
        self.tracker.milestone(f"☯ YIN Phase {self.cycle_num + 1}: {detail}")
        sub = self.tracker.sub_tracker(f"YIN-{self.cycle_num + 1}: {detail}")
        self.phase_trackers.append(sub)
        return sub

    def start_yang(self, detail: str = "action") -> ProgressTracker:
        """Start a YANG (action) phase."""
        self.tracker.milestone(f"☯ YANG Phase {self.cycle_num + 1}: {detail}")
        sub = self.tracker.sub_tracker(f"YANG-{self.cycle_num + 1}: {detail}")
        self.phase_trackers.append(sub)
        return sub

    def complete_cycle(self) -> None:
        """Mark one yin-yang cycle as complete."""
        self.cycle_num += 1
        self.tracker.advance(1, detail=f"cycle {self.cycle_num} complete")

    def finish(self) -> ProgressStats:
        """Finish and return stats."""
        return self.tracker.finish(summary=f"{self.cycle_num} cycles complete")
