# ruff: noqa: BLE001
"""
Parallel Cognition — Multiple thought streams.

Manages parallel cognitive processes for complex problem-solving.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger(__name__)


class ParallelCognition:
    """Manages parallel thought streams."""

    def __init__(self, max_streams: int = 4) -> None:
        self.max_streams = max_streams
        self._executor = ThreadPoolExecutor(max_workers=max_streams)
        self._active: int = 0

    def think_parallel(
        self,
        problems: list[Callable[[], Any]],
    ) -> list[Any]:
        """Run multiple cognitive tasks in parallel."""
        self._active = len(problems)
        futures = {
            self._executor.submit(p): i
            for i, p in enumerate(problems)
        }
        results: list[Any] = [None] * len(problems)
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.debug("Parallel cognition error: %s", e)
                results[idx] = None
        self._active = 0
        return results

    def summary(self) -> dict[str, Any]:
        return {
            "max_streams": self.max_streams,
            "active_streams": self._active,
        }

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


_cognition: ParallelCognition | None = None


def get_parallel_cognition() -> ParallelCognition:
    global _cognition
    if _cognition is None:
        _cognition = ParallelCognition()
    return _cognition
