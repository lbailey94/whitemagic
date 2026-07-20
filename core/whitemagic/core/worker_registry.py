"""Worker Registry — Centralized tracking of all background workers.

Every background thread, executor, timer, and daemon in WhiteMagic must
register here so that test teardown can stop them deterministically.

Usage by workers:
    from whitemagic.core.worker_registry import register_worker, unregister_worker

    class MyDaemon:
        def start(self):
            self._thread = threading.Thread(...)
            self._thread.start()
            register_worker("my_daemon", self._thread, stop_fn=self.stop)

        def stop(self):
            self._running = False
            if self._thread:
                self._thread.join(timeout=5)

Usage by test teardown:
    from whitemagic.core.worker_registry import stop_all_workers, get_active_workers
    stop_all_workers()  # stop everything registered
    active = get_active_workers()  # check for leaks
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WorkerEntry:
    """Track a single background worker."""

    name: str
    thread: threading.Thread | None = None
    stop_fn: Callable[[], None] | None = None
    owner: str = ""  # module path that registered it
    daemon: bool = True


class WorkerRegistry:
    """Centralized registry for background workers."""

    _workers: dict[str, WorkerEntry] = {}
    _lock = threading.RLock()

    @classmethod
    def register(
        cls,
        name: str,
        thread: threading.Thread | None = None,
        stop_fn: Callable[[], None] | None = None,
        owner: str = "",
    ) -> None:
        with cls._lock:
            cls._workers[name] = WorkerEntry(
                name=name,
                thread=thread,
                stop_fn=stop_fn,
                owner=owner,
                daemon=thread.daemon if thread else True,
            )
            logger.debug("Registered worker: %s (owner=%s)", name, owner)

    @classmethod
    def unregister(cls, name: str) -> None:
        with cls._lock:
            cls._workers.pop(name, None)

    @classmethod
    def stop_all(cls, timeout: float = 5.0) -> list[str]:
        """Stop all registered workers. Returns list of stopped names."""
        stopped: list[str] = []
        with cls._lock:
            entries = list(cls._workers.items())

        for name, entry in entries:
            if entry.stop_fn is not None:
                try:
                    entry.stop_fn()
                    if entry.thread is not None and entry.thread.is_alive():
                        entry.thread.join(timeout=timeout)
                    stopped.append(name)
                except Exception:  # noqa: BLE001
                    logger.debug("Error stopping worker %s", name, exc_info=True)
            elif entry.thread is not None and entry.thread.is_alive():
                entry.thread.join(timeout=timeout)
                if not entry.thread.is_alive():
                    stopped.append(name)

        with cls._lock:
            cls._workers.clear()
        return stopped

    @classmethod
    def get_active(cls) -> dict[str, WorkerEntry]:
        """Get all workers whose threads are still alive."""
        active: dict[str, WorkerEntry] = {}
        with cls._lock:
            for name, entry in cls._workers.items():
                if entry.thread is not None and entry.thread.is_alive():
                    active[name] = entry
        return active

    @classmethod
    def get_registered_names(cls) -> list[str]:
        with cls._lock:
            return list(cls._workers.keys())

    @classmethod
    def reset(cls) -> None:
        """Clear registry without stopping (for test reset after stop_all)."""
        with cls._lock:
            cls._workers.clear()


def register_worker(
    name: str,
    thread: threading.Thread | None = None,
    stop_fn: Callable[[], None] | None = None,
    owner: str = "",
) -> None:
    """Register a background worker."""
    WorkerRegistry.register(name, thread, stop_fn, owner)


def unregister_worker(name: str) -> None:
    """Unregister a background worker."""
    WorkerRegistry.unregister(name)


def stop_all_workers(timeout: float = 5.0) -> list[str]:
    """Stop all registered workers. Returns list of stopped names."""
    return WorkerRegistry.stop_all(timeout=timeout)


def get_active_workers() -> dict[str, WorkerEntry]:
    """Get all workers whose threads are still alive."""
    return WorkerRegistry.get_active()


def get_registered_workers() -> list[str]:
    """Get list of all registered worker names."""
    return WorkerRegistry.get_registered_names()
