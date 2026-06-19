# ruff: noqa: F403
"""Edge Local LLM (Archived)
========================

This module called a locally-running Ollama instance as part of the edge cascade.

The implementation has been archived and is no longer available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _disabled_error() -> RuntimeError:
    return RuntimeError(
        "Local LLM execution is archived and no longer available."
    )


@dataclass
class CascadeResult:  # pragma: no cover - legacy shim
    """CascadeResult: cascade result.

    Value object: equality and repr are field-based."""
    query: str
    answer: str
    method: str
    confidence: float
    latency_ms: float
    tokens_saved: int = 0


class LocalLLM:  # pragma: no cover - legacy shim
    """LocalLLM: local llm."""
    def __init__(self, *_: Any, **__: Any) -> None:
        raise _disabled_error()


class CascadingInference:  # pragma: no cover - legacy shim
    """CascadingInference: cascading inference."""
    def __init__(self, *_: Any, **__: Any) -> None:
        raise _disabled_error()

    def get_cascade() -> Any:  # type: ignore[misc]
        """
        Get the cascade.

        Returns:
            Any
        """
        raise _disabled_error()

