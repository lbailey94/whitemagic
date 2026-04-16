"""
Archived Wrapper: `whitemagic.local_ml.engine`

The implementation has been archived and is no longer available.
"""

from __future__ import annotations

from typing import Any


def _disabled_error() -> RuntimeError:
    return RuntimeError(
        "Local ML Engine is archived and no longer available."
    )


class LocalMLEngine:  # pragma: no cover - legacy shim
    def __init__(self, *_: Any, **__: Any) -> None:
        raise _disabled_error()


def get_local_ml_engine() -> Any:
    raise _disabled_error()
