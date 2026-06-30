"""Shared utility patterns extracted from duplicate code across the codebase.

These patterns were duplicated across 40+ files. Centralizing them here
reduces maintenance burden and ensures consistent behavior.

Extracted patterns:
- _connect_to_gan_ying: GanYingBus connection (was in 10 files)
- _run_async: asyncio bridge for sync contexts (was in 6 files)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def connect_to_gan_ying(owner: str = "") -> Any:
    """Connect to the GanYingBus event system.

    Shared implementation — was duplicated across 10 garden/handler files.

    Args:
        owner: Optional owner name for the bus connection.

    Returns:
        GanYingBus instance or None if unavailable.
    """
    try:
        from whitemagic.core.resonance.gan_ying_async import GanYingBus

        bus = GanYingBus.get_instance()
        if owner:
            bus.owner = owner
        return bus
    except Exception as e:
        logger.debug("GanYingBus not available: %s", e)
        return None


def run_async(coro: Any) -> Any:
    """Run an async coroutine in a sync context.

    Shared implementation — was duplicated across 6 files.

    Handles three cases:
    1. No event loop running — create one and run
    2. Event loop already running — schedule in a thread
    3. Loop closed — create a new one
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import threading

            result: list[Any] = []
            error: list[Exception] = []

            def _run() -> None:
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result.append(new_loop.run_until_complete(coro))
                    new_loop.close()
                except Exception as e:
                    error.append(e)

            t = threading.Thread(target=_run)
            t.start()
            t.join()
            if error:
                raise error[0]
            return result[0] if result else None
        return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
