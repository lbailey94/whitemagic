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
    query: str
    answer: str
    method: str
    confidence: float
    latency_ms: float
    tokens_saved: int = 0


class LocalLLM:  # pragma: no cover - legacy shim
    def __init__(self, *_: Any, **__: Any) -> None:
        raise _disabled_error()


class CascadingInference:  # pragma: no cover - legacy shim
    def __init__(self, *_: Any, **__: Any) -> None:
        raise _disabled_error()

    def get_cascade() -> Any:
        raise _disabled_error()

