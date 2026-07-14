"""Reusable progress bar utility for CLI scripts, benchmarks, and gauntlets.

Shows a real-time progress bar with percentage, elapsed time, ETA, and custom counters.
Uses a background thread for live updates during long-running operations.

Usage:
    bar = ProgressBar(total=1000, label="Benching")
    for i in range(1000):
        do_work()
        bar.advance()
    bar.finish()

    # With custom counter
    bar = ProgressBar(total=500, label="Tests", counters={"pass": 0, "fail": 0})
    bar.advance(pass=1)  # increments pass counter
"""

from __future__ import annotations

import sys
import threading
import time


class ProgressBar:
    """Thread-safe progress bar with live elapsed-time updates.

    Renders to stderr using carriage return for in-place updates.
    A background thread refreshes the bar every `update_interval` seconds
    so elapsed time ticks even when no advance() is called.
    """

    __slots__ = (
        "total",
        "completed",
        "label",
        "counters",
        "start_time",
        "stream",
        "_bar_width",
        "_lock",
        "_timer",
        "_stopped",
        "_last_label",
        "update_interval",
    )

    def __init__(
        self,
        total: int,
        label: str = "",
        counters: dict[str, int] | None = None,
        stream=None,
        bar_width: int = 40,
        update_interval: float = 0.1,
    ) -> None:
        self.total = total
        self.completed = 0
        self.label = label
        self.counters = counters or {}
        self.start_time = time.monotonic()
        self.stream = stream or sys.stderr
        self._bar_width = bar_width
        self._lock = threading.RLock()
        self._timer: threading.Timer | None = None
        self._stopped = False
        self._last_label = ""
        self.update_interval = update_interval

    def advance(self, **counter_deltas: int) -> None:
        """Advance completed count and optionally update counters."""
        with self._lock:
            self.completed += 1
            for key, delta in counter_deltas.items():
                self.counters[key] = self.counters.get(key, 0) + delta
            self._render()

    def set_label(self, label: str) -> None:
        """Update the current item label."""
        with self._lock:
            self._last_label = label
            self._render()

    def update_counters(self, **counters: int) -> None:
        """Set counter values directly."""
        with self._lock:
            self.counters.update(counters)
            self._render()

    def _start_timer(self) -> None:
        """Start the background refresh thread."""
        if self._timer is not None:
            return

        def _tick():
            if self._stopped:
                return
            with self._lock:
                self._render()
            self._timer = threading.Timer(self.update_interval, _tick)
            self._timer.daemon = True
            self._timer.start()

        self._timer = threading.Timer(self.update_interval, _tick)
        self._timer.daemon = True
        self._timer.start()

    def _render(self) -> None:
        if self._stopped:
            return
        pct = (self.completed / self.total * 100) if self.total > 0 else 0.0
        elapsed = time.monotonic() - self.start_time

        # ETA
        if self.completed > 0 and self.completed < self.total:
            rate = self.completed / elapsed if elapsed > 0 else 0
            eta = (self.total - self.completed) / rate if rate > 0 else 0
            eta_str = f"ETA {eta:5.1f}s"
        elif self.completed >= self.total:
            eta_str = "   done"
        else:
            eta_str = "ETA   --"

        # Bar
        filled = (
            int(self._bar_width * self.completed / self.total) if self.total > 0 else 0
        )
        bar = "\u2588" * filled + "\u2591" * (self._bar_width - filled)

        # Counters
        counter_str = " ".join(f"{k}:{v}" for k, v in self.counters.items() if v != 0)

        # Label
        name = self._last_label or self.label
        if len(name) > 45:
            name = "..." + name[-42:]

        line = (
            f"\r  [{bar}] {pct:6.2f}% | {self.completed}/{self.total} | "
            f"{elapsed:6.1f}s | {eta_str}"
        )
        if counter_str:
            line += f" | {counter_str}"
        if name:
            line += f" | {name}"

        line += " " * max(0, 130 - len(line))
        self.stream.write(line)
        self.stream.flush()

    def start(self) -> None:
        """Start the progress bar and background timer."""
        self._start_timer()
        with self._lock:
            self._render()

    def finish(self) -> None:
        """Stop the progress bar and print a newline."""
        with self._lock:
            self._stopped = True
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        with self._lock:
            self._render()
        self.stream.write("\n")
        self.stream.flush()


def progress_range(
    total: int,
    label: str = "",
    counters: dict[str, int] | None = None,
) -> tuple[ProgressBar, range]:
    """Convenience: returns (bar, range) so you can do:

    bar, items = progress_range(100, "Processing")
    for i in items:
        do_work(i)
        bar.advance()
    bar.finish()
    """
    bar = ProgressBar(total=total, label=label, counters=counters)
    bar.start()
    return bar, range(total)
