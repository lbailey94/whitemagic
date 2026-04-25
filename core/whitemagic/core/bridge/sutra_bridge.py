"""Sutra Bridge — Kernel acceleration bridge for SQLite backend.

Provides get_sutra_kernel() for the SQLite backend's optional
acceleration layer. Returns None when no kernel is available.
"""

from __future__ import annotations

from typing import Any


class _StubSutraKernel:
    """Stub sutra kernel that allows all operations."""

    def evaluate_action(self, **kwargs: Any) -> str:
        return "Allow"

    def check_harmony(self, **kwargs: Any) -> float:
        return 1.0


def get_sutra_kernel() -> Any | None:
    """Return the sutra kernel if available, None otherwise."""
    return _StubSutraKernel()
