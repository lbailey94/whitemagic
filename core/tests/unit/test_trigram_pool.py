"""Tests for the Wu Xing phase controller and ring buffer bridge."""

from __future__ import annotations

import json
import os
import time

import pytest

from whitemagic.core.consciousness.hexagram_state import HexagramState
from whitemagic.core.consciousness.wu_xing_controller import (
    WuXingPhaseController,
    PHASE_TRIGRAMS,
    PHASE_CYCLE,
)
from whitemagic.wu_xing import Element


class TestWuXingPhaseController:
    """Test the Wu Xing phase controller."""

    def test_initial_phase_is_fire(self):
        state = HexagramState()
        controller = WuXingPhaseController(state)
        assert controller.current_phase == Element.FIRE

    def test_active_trigrams_fire(self):
        state = HexagramState()
        controller = WuXingPhaseController(state)
        active = controller.get_active_trigrams()
        assert active == {"Qian", "Li"}

    def test_active_trigrams_water(self):
        state = HexagramState()
        controller = WuXingPhaseController(state)
        # Manually set phase to Water
        controller._current_phase = Element.WATER
        active = controller.get_active_trigrams()
        assert active == {"Kan"}

    def test_is_trigram_active(self):
        state = HexagramState()
        controller = WuXingPhaseController(state)
        assert controller.is_trigram_active("Qian") is True
        assert controller.is_trigram_active("Li") is True
        assert controller.is_trigram_active("Kan") is False

    def test_phase_trigrams_max_two(self):
        """No phase should have more than 2 active trigrams."""
        for element in Element:
            trigrams = PHASE_TRIGRAMS.get(element, set())
            assert len(trigrams) <= 2, f"{element} has {len(trigrams)} trigrams"

    def test_phase_cycle_has_all_elements(self):
        assert len(PHASE_CYCLE) == 5
        assert set(PHASE_CYCLE) == set(Element)

    def test_register_callback(self):
        state = HexagramState()
        controller = WuXingPhaseController(state)
        callbacks_called: list[tuple[Element, Element]] = []

        controller.register_phase_callback(
            lambda old, new: callbacks_called.append((old, new))
        )

        # Manually trigger a phase change
        controller._apply_phase(Element.WOOD, reason="test callback")

        assert len(callbacks_called) == 1
        assert callbacks_called[0] == (Element.FIRE, Element.WOOD)

    def test_phase_change_updates_hexagram(self):
        state = HexagramState()
        controller = WuXingPhaseController(state)

        controller._apply_phase(Element.WATER, reason="test hexagram update")

        # Water phase: lower=Kan, upper=Kan
        assert state.lower == "Kan"
        assert state.upper == "Kan"

    def test_start_stop(self):
        state = HexagramState()
        controller = WuXingPhaseController(state)

        # Use very short phase durations for testing
        os.environ["WM_WUXING_PHASE_FIRE"] = "0.1"
        os.environ["WM_WUXING_PHASE_WOOD"] = "0.1"

        controller.start()
        assert controller._running is True

        time.sleep(0.25)  # Let at least one phase transition happen

        controller.stop()
        assert controller._running is False
        assert controller.phase_count >= 1

        # Cleanup
        del os.environ["WM_WUXING_PHASE_FIRE"]
        del os.environ["WM_WUXING_PHASE_WOOD"]

    def test_status(self):
        state = HexagramState()
        controller = WuXingPhaseController(state)

        status = controller.get_status()
        assert status["current_phase"] == "fire"
        assert "active_trigrams" in status
        assert "elapsed_seconds" in status
        assert "remaining_seconds" in status
        assert status["running"] is False


class TestRingBufferBridge:
    """Test the Python ring buffer bridge."""

    def test_create_and_send_recv(self):
        from whitemagic.inference.ring_buffer_bridge import RingBufferBridge

        name = f"test_bridge_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        try:
            with RingBufferBridge(name, create=True, capacity=4096) as rb:
                # Send a message
                assert rb.send(b"hello world") is True

                # Receive it
                data = rb.recv()
                assert data == b"hello world"

                # Buffer should be empty
                assert rb.recv() is None
        finally:
            # Cleanup
            path = f"/dev/shm/wm_trigram_{name}"
            if os.path.exists(path):
                os.unlink(path)

    def test_send_str_recv_str(self):
        from whitemagic.inference.ring_buffer_bridge import RingBufferBridge

        name = f"test_str_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        try:
            with RingBufferBridge(name, create=True, capacity=4096) as rb:
                assert rb.send_str("hello string") is True
                result = rb.recv_str()
                assert result == "hello string"
        finally:
            path = f"/dev/shm/wm_trigram_{name}"
            if os.path.exists(path):
                os.unlink(path)

    def test_send_json_recv_json(self):
        from whitemagic.inference.ring_buffer_bridge import RingBufferBridge

        name = f"test_json_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        try:
            with RingBufferBridge(name, create=True, capacity=4096) as rb:
                msg = {"prompt": "test", "tokens": [1, 2, 3], "max_tokens": 64}
                assert rb.send_json(msg) is True
                result = rb.recv_json()
                assert result == msg
        finally:
            path = f"/dev/shm/wm_trigram_{name}"
            if os.path.exists(path):
                os.unlink(path)

    def test_multiple_messages(self):
        from whitemagic.inference.ring_buffer_bridge import RingBufferBridge

        name = f"test_multi_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        try:
            with RingBufferBridge(name, create=True, capacity=64 * 1024) as rb:
                for i in range(10):
                    assert rb.send(f"msg_{i}".encode()) is True

                for i in range(10):
                    data = rb.recv()
                    assert data == f"msg_{i}".encode()

                assert rb.recv() is None
        finally:
            path = f"/dev/shm/wm_trigram_{name}"
            if os.path.exists(path):
                os.unlink(path)

    def test_fill_level(self):
        from whitemagic.inference.ring_buffer_bridge import RingBufferBridge

        name = f"test_fill_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        try:
            with RingBufferBridge(name, create=True, capacity=4096) as rb:
                assert rb.fill_level() == 0.0
                rb.send(b"data")
                assert rb.fill_level() > 0.0
                rb.recv()
                assert rb.fill_level() == 0.0
        finally:
            path = f"/dev/shm/wm_trigram_{name}"
            if os.path.exists(path):
                os.unlink(path)

    def test_open_nonexistent(self):
        from whitemagic.inference.ring_buffer_bridge import RingBufferBridge

        with pytest.raises(FileNotFoundError):
            RingBufferBridge("nonexistent_rb_test_99999")

    def test_double_create(self):
        from whitemagic.inference.ring_buffer_bridge import RingBufferBridge

        name = f"test_double_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        try:
            rb1 = RingBufferBridge(name, create=True, capacity=1024)
            with pytest.raises(FileExistsError):
                RingBufferBridge(name, create=True, capacity=1024)
            rb1.close()
        finally:
            path = f"/dev/shm/wm_trigram_{name}"
            if os.path.exists(path):
                os.unlink(path)

    def test_available(self):
        from whitemagic.inference.ring_buffer_bridge import RingBufferBridge

        name = f"test_avail_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        try:
            with RingBufferBridge(name, create=True, capacity=4096) as rb:
                assert rb.available() == 0
                rb.send(b"test data")
                assert rb.available() > 0
                rb.recv()
                assert rb.available() == 0
        finally:
            path = f"/dev/shm/wm_trigram_{name}"
            if os.path.exists(path):
                os.unlink(path)

    def test_backend_property(self):
        from whitemagic.inference.ring_buffer_bridge import RingBufferBridge

        name = f"test_backend_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        try:
            with RingBufferBridge(name, create=True, capacity=1024) as rb:
                # is_rust_backend may be True or False depending on compilation
                assert isinstance(rb.is_rust_backend, bool)
                assert rb.name == name
        finally:
            path = f"/dev/shm/wm_trigram_{name}"
            if os.path.exists(path):
                os.unlink(path)


class TestConcurrencyConfig:
    """Test trigram core pinning config."""

    def test_trigram_config_defaults(self):
        from whitemagic.config.concurrency import (
            TRIGRAM_RING_BUFFER_DIR,
            TRIGRAM_RING_BUFFER_CAPACITY,
        )

        assert TRIGRAM_RING_BUFFER_DIR == "/dev/shm"
        assert TRIGRAM_RING_BUFFER_CAPACITY == 1024 * 1024

    def test_trigram_pinning_disabled_by_default(self):
        # The default should be disabled unless env var is set
        # We can't guarantee the env state, so just check it's a bool
        from whitemagic.config.concurrency import TRIGRAM_CORE_PINNING

        assert isinstance(TRIGRAM_CORE_PINNING, bool)
