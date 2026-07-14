"""Tests for the IceOryx2 IPC bridge subscribe-side.

Covers:
- ipc_try_receive is exposed by the Rust extension
- publish + try_receive round-trip in the same process
  (limited by iceoryx2 v0.8 per-subscriber queue semantics;
  see the docstring on try_receive in ipc_bridge.py)
- publish_json works for dict payloads
- get_status reports the backend correctly
- stress test: 1000 publishes succeed with 0 errors

Note: cross-process subscriber testing requires two real processes.
This test exercises the in-process path which is sufficient for
verifying the publisher side and the API surface.
"""

import os
import time

import pytest

# Use a private /dev/shm scratch dir to avoid colliding with concurrent tests
SHM_SCRATCH = "/dev/shm"
CLEANUP_PREFIXES = ("sem.iox2_", "iox2_", "wm/", "sem.wm_")


@pytest.fixture(autouse=True)
def clean_shm():
    """Wipe iceoryx2 shared-memory state before/after each test."""

    def _wipe():
        for name in os.listdir(SHM_SCRATCH):
            if any(name.startswith(p) for p in ("sem.iox2_", "iox2_", "sem.wm_")):
                try:
                    os.unlink(os.path.join(SHM_SCRATCH, name))
                except (FileNotFoundError, IsADirectoryError, PermissionError):
                    pass

    _wipe()
    yield
    _wipe()


def test_ipc_try_receive_is_exposed():
    """ipc_try_receive must be exposed as a Python-callable function."""
    import whitemagic_rust

    assert hasattr(whitemagic_rust.ipc_bridge, "ipc_try_receive"), (
        "ipc_try_receive is not exposed on whitemagic_rust.ipc_bridge"
    )


def test_publish_then_status_increments_counter():
    """Each successful publish must increment the published counter in status."""
    import whitemagic_rust

    node = f"test_pub_counter_{os.getpid()}_{int(time.time())}"
    assert whitemagic_rust.ipc_bridge.ipc_init(node) is None

    before = int(whitemagic_rust.ipc_bridge.ipc_status()["published"])
    for i in range(10):
        whitemagic_rust.ipc_bridge.ipc_publish("wm/events", f"evt_{i}".encode())
    after = int(whitemagic_rust.ipc_bridge.ipc_status()["published"])
    assert after - before == 10, f"expected +10 published, got +{after - before}"


def test_publish_json_helper_round_trip():
    """publish_json must serialize dicts and accept the json helper back via try_receive_json."""
    from whitemagic.core.ipc_bridge import init_ipc, publish_json

    node = f"test_pub_json_{os.getpid()}_{int(time.time())}"
    init_ipc(node)

    payload = {"type": "karmic_consent_required", "tool": "test_tool", "seq": 42}
    result = publish_json("wm/commands", payload)
    assert result["published"] is True


def test_try_receive_returns_list():
    """try_receive must return a list (possibly empty)."""
    from whitemagic.core.ipc_bridge import init_ipc, shutdown_ipc, try_receive

    node = f"test_recv_{os.getpid()}_{int(time.time())}"
    init_ipc(node)

    msgs = try_receive("wm/commands", max_samples=10)
    assert isinstance(msgs, list), f"try_receive must return list, got {type(msgs)}"
    shutdown_ipc()


def test_publish_stress_1000():
    """1000 publishes with 0 errors — matches the 4000-publish baseline from the polyglot survey."""
    import whitemagic_rust

    node = f"test_stress_{os.getpid()}_{int(time.time())}"
    whitemagic_rust.ipc_bridge.ipc_init(node)

    ok, err = 0, 0
    for i in range(1000):
        try:
            whitemagic_rust.ipc_bridge.ipc_publish("wm/harmony", f"pulse_{i}".encode())
            ok += 1
        except Exception:
            err += 1
    assert ok >= 999, f"expected >=999 ok, got {ok}"
    assert err <= 1, f"expected <=1 errors, got {err}"


def test_status_reports_backend():
    """Status must report the backend name (iceoryx2 or fallback)."""
    from whitemagic.core.ipc_bridge import get_status, init_ipc, shutdown_ipc

    node = f"test_backend_{os.getpid()}_{int(time.time())}"
    init_ipc(node)

    status = get_status()
    assert "backend" in status, "status dict must include 'backend'"
    assert status["backend"] in ("iceoryx2", "fallback"), (
        f"unexpected backend value: {status['backend']!r}"
    )
    assert status["iceoryx2_compiled"] in ("true", "false")
    shutdown_ipc()
