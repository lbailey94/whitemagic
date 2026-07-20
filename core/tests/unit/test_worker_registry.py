"""Tests for worker registry — ensures no background workers leak across tests.

P3.1 acceptance: imports start no background work, test teardown leaves no workers.
"""

from __future__ import annotations

import threading
import time

import pytest

from whitemagic.core.worker_registry import (
    WorkerRegistry,
    get_active_workers,
    get_registered_workers,
    register_worker,
    stop_all_workers,
    unregister_worker,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensure clean registry state before and after each test."""
    stop_all_workers(timeout=2.0)
    WorkerRegistry.reset()
    yield
    stop_all_workers(timeout=2.0)
    WorkerRegistry.reset()


class TestWorkerRegistry:
    """Unit tests for the WorkerRegistry."""

    def test_register_and_unregister(self):
        """Register a worker, verify it appears, then unregister."""
        stop_evt = threading.Event()

        def _dummy_loop():
            while not stop_evt.is_set():
                stop_evt.wait(0.1)

        t = threading.Thread(target=_dummy_loop, daemon=True, name="test-dummy")
        t.start()
        register_worker("test_dummy", t, stop_fn=lambda: stop_evt.set(), owner="test")

        assert "test_dummy" in get_registered_workers()
        active = get_active_workers()
        assert "test_dummy" in active
        assert active["test_dummy"].thread is t

        unregister_worker("test_dummy")
        assert "test_dummy" not in get_registered_workers()
        stop_evt.set()
        t.join(timeout=2.0)

    def test_stop_all_stops_registered_workers(self):
        """stop_all_workers should call stop_fn for each registered worker."""
        stop_evt = threading.Event()

        def _dummy_loop():
            while not stop_evt.is_set():
                stop_evt.wait(0.1)

        t = threading.Thread(target=_dummy_loop, daemon=True, name="test-stop")
        t.start()
        register_worker("test_stop", t, stop_fn=lambda: stop_evt.set(), owner="test")

        stopped = stop_all_workers(timeout=2.0)
        assert "test_stop" in stopped
        assert not t.is_alive()

    def test_get_active_filters_dead_threads(self):
        """get_active_workers should only return workers with alive threads."""
        t = threading.Thread(target=lambda: None, daemon=True, name="test-dead")
        t.start()
        t.join(timeout=1.0)
        assert not t.is_alive()

        register_worker("test_dead", t, owner="test")
        active = get_active_workers()
        assert "test_dead" not in active
        unregister_worker("test_dead")

    def test_reset_clears_without_stopping(self):
        """reset() should clear registry without calling stop_fn."""
        stop_evt = threading.Event()

        def _dummy_loop():
            while not stop_evt.is_set():
                stop_evt.wait(0.1)

        t = threading.Thread(target=_dummy_loop, daemon=True, name="test-reset")
        t.start()
        register_worker("test_reset", t, owner="test")

        WorkerRegistry.reset()
        assert get_registered_workers() == []
        # Thread is still alive — caller must stop it
        stop_evt.set()
        t.join(timeout=2.0)

    def test_no_workers_running_after_import(self):
        """Importing whitemagic modules should not start any background workers."""
        # The registry should be empty if no explicit start() was called
        # This test validates the P3.1 acceptance criterion:
        # "Imports start no background work"
        active = get_active_workers()
        assert len(active) == 0, (
            f"Workers active after import: {list(active.keys())}"
        )


class TestWorkerLeakDetection:
    """Verify that key daemons register with the worker registry."""

    def test_decay_daemon_registers(self):
        """DecayDaemon should register with WorkerRegistry on start()."""
        from whitemagic.core.memory.neural.decay_daemon import DecayDaemon

        daemon = DecayDaemon(interval_hours=999)
        daemon.start()
        try:
            assert "decay_daemon" in get_registered_workers()
        finally:
            daemon.stop()

    def test_embedding_daemon_registers(self):
        """EmbeddingDaemon should register with WorkerRegistry on start()."""
        from whitemagic.core.memory.embedding_daemon import EmbeddingDaemon

        # Clear singleton to get fresh instance
        EmbeddingDaemon._instance = None
        daemon = EmbeddingDaemon()
        daemon.start()
        try:
            assert "embedding_daemon" in get_registered_workers()
        finally:
            daemon.stop()
            EmbeddingDaemon._instance = None

    def test_dream_cycle_registers(self):
        """DreamCycle should register with WorkerRegistry on start()."""
        from whitemagic.core.dreaming.dream_cycle import DreamCycle

        dc = DreamCycle()
        dc.start()
        try:
            assert "dream_cycle" in get_registered_workers()
        finally:
            dc.stop()

    def test_consolidation_daemon_registers(self):
        """ConsolidationDaemon should register with WorkerRegistry on start()."""
        from whitemagic.core.memory.consolidation import ConsolidationDaemon

        daemon = ConsolidationDaemon(interval_seconds=999)
        daemon.start()
        try:
            assert "consolidation_daemon" in get_registered_workers()
        finally:
            daemon.stop()

    def test_ambient_sensorium_registers(self):
        """AmbientSensorium should register with WorkerRegistry on start_background()."""
        from whitemagic.core.consciousness.ambient_sensorium import AmbientSensorium

        sensorium = AmbientSensorium()
        sensorium.start_background()
        try:
            assert "ambient_sensorium" in get_registered_workers()
        finally:
            sensorium.stop_background()

    def test_stop_all_workers_clears_everything(self):
        """stop_all_workers should stop all registered daemons."""
        from whitemagic.core.memory.neural.decay_daemon import DecayDaemon
        from whitemagic.core.dreaming.dream_cycle import DreamCycle

        d = DecayDaemon(interval_hours=999)
        d.start()
        dc = DreamCycle()
        dc.start()

        assert len(get_registered_workers()) >= 2

        stopped = stop_all_workers(timeout=5.0)
        assert "decay_daemon" in stopped
        assert "dream_cycle" in stopped
        assert len(get_active_workers()) == 0
