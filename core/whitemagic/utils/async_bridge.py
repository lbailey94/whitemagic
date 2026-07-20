"""Shared asyncio bridge for running coroutines from sync context.

Single canonical implementation — replaces 6 duplicate _run_async copies.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

T = TypeVar("T")


def run_async(coro: asyncio.Coroutine[Any, Any, T]) -> T:  # noqa: UP047  # TypeVar-based generics (not yet PEP 695)
    """Run a coroutine from synchronous context.

    If no event loop is running, uses asyncio.run directly.
    If an event loop is already running (e.g. inside Jupyter or async test),
    dispatches to a worker thread to avoid nested loop errors.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()
