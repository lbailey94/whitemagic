"""Phase 5 — ProcessSupervisor fault-injection and lifecycle tests.

Tests the shared ProcessSupervisor abstraction against all 7 fault scenarios
from the hardening strategy:

1. Child process writes excessive stderr
2. Child process hangs during initialization
3. Child process hangs mid-request
4. Child process emits malformed JSON
5. Pool exhaustion under concurrent load
6. Shutdown while calls are active
7. Repeated crash/restart cycles

Plus basic lifecycle, lease, circuit breaker, and stats tests.
"""
from __future__ import annotations

import sys
import threading
import time

from whitemagic.core.acceleration.process_supervisor import (
    BridgeResult,
    BridgeStats,
    CapabilityState,
    ProcessSupervisor,
    list_supervisors,
    register,
    shutdown_all,
)

# ── Helper: create a mock bridge script ───────────────────────────


def _make_mock_bridge(tmp_path, script_content: str) -> str:
    """Write a Python script that acts as a mock bridge binary."""
    bridge_path = tmp_path / "mock_bridge.py"
    bridge_path.write_text(script_content)
    bridge_path.chmod(0o755)
    return str(bridge_path)


# ── Basic Lifecycle Tests ─────────────────────────────────────────


class TestProcessSupervisorLifecycle:
    """Basic lifecycle: start, call, close."""

    def test_start_and_call_ok(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys, json
print("started", flush=True)
for line in sys.stdin:
    req = json.loads(line)
    if req.get("op") == "quit":
        break
    resp = {"status": "ok", "result": {"echo": req.get("method")}}
    print(json.dumps(resp), flush=True)
""",
        )
        sup = ProcessSupervisor(
            name="test-ok",
            cmd=[sys.executable, bridge],
            startup_check="started",
        )
        try:
            assert sup.is_available()
            result = sup.call({"method": "ping"})
            assert result.ok
            assert result.data["status"] == "ok"
            assert result.data["result"]["echo"] == "ping"
            assert result.latency_ms > 0
        finally:
            sup.close()

    def test_binary_not_found(self):
        sup = ProcessSupervisor(
            name="test-nobin",
            cmd=["/nonexistent/binary"],
            binary_path="/nonexistent/binary",
            startup_check="started",
        )
        assert not sup.is_available()
        assert sup.health_state == CapabilityState.UNAVAILABLE

    def test_skip_env_var(self, tmp_path, monkeypatch):
        bridge = _make_mock_bridge(
            tmp_path,
            "import sys; print('started', flush=True)",
        )
        monkeypatch.setenv("WM_TEST_SKIP", "1")
        sup = ProcessSupervisor(
            name="test-skip",
            cmd=[sys.executable, bridge],
            startup_check="started",
            skip_env_var="WM_TEST_SKIP",
        )
        assert not sup.is_available()
        assert sup.health_state == CapabilityState.UNAVAILABLE

    def test_skip_polyglot(self, tmp_path, monkeypatch):
        bridge = _make_mock_bridge(
            tmp_path,
            "import sys; print('started', flush=True)",
        )
        monkeypatch.setenv("WM_SKIP_POLYGLOT", "1")
        sup = ProcessSupervisor(
            name="test-polyglot-skip",
            cmd=[sys.executable, bridge],
            startup_check="started",
            skip_polyglot=True,
        )
        assert not sup.is_available()

    def test_close_sets_unavailable(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            "import sys; print('started', flush=True); sys.stdin.read()",
        )
        sup = ProcessSupervisor(
            name="test-close",
            cmd=[sys.executable, bridge],
            startup_check="started",
        )
        sup.is_available()
        sup.close()
        assert sup.health_state == CapabilityState.UNAVAILABLE

    def test_health_check_dict(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys, json
print("started", flush=True)
for line in sys.stdin:
    req = json.loads(line)
    if req.get("op") == "quit":
        break
    print(json.dumps({"status": "ok"}), flush=True)
""",
        )
        sup = ProcessSupervisor(
            name="test-health",
            cmd=[sys.executable, bridge],
            startup_check="started",
        )
        try:
            sup.is_available()
            sup.call({"method": "ping"})
            hc = sup.health_check()
            assert hc["name"] == "test-health"
            assert hc["health_state"] == "healthy"
            assert hc["stats"]["total_calls"] == 1
            assert hc["stats"]["successful_calls"] == 1
        finally:
            sup.close()


# ── Fault 1: Excessive stderr ─────────────────────────────────────


class TestExcessiveStderr:
    """Child process writes excessive stderr — must not hang."""

    def test_excessive_stderr_does_not_hang(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys, json
# Write a lot of stderr before startup
for i in range(10000):
    sys.stderr.write(f"WARNING line {i}\\n")
sys.stderr.flush()
print("started", flush=True)
for line in sys.stdin:
    req = json.loads(line)
    if req.get("op") == "quit":
        break
    print(json.dumps({"status": "ok"}), flush=True)
""",
        )
        sup = ProcessSupervisor(
            name="test-stderr",
            cmd=[sys.executable, bridge],
            startup_check="started",
            startup_timeout=10.0,
        )
        try:
            assert sup.is_available()
            result = sup.call({"method": "ping"})
            assert result.ok
            # stderr should be captured but bounded
            assert len(sup.last_stderr) <= 128 * 1024  # within cap + overhead
        finally:
            sup.close()


# ── Fault 2: Hang during initialization ───────────────────────────


class TestInitHang:
    """Child process hangs during initialization — startup timeout fires."""

    def test_init_hang_times_out(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys, time
# Never print startup message
time.sleep(30)
""",
        )
        sup = ProcessSupervisor(
            name="test-inithang",
            cmd=[sys.executable, bridge],
            startup_check="started",
            startup_timeout=1.0,
            max_restarts=1,
        )
        try:
            assert not sup.is_available()
            assert sup.health_state in (
                CapabilityState.UNAVAILABLE,
                CapabilityState.CIRCUIT_OPEN,
            )
        finally:
            sup.close()


# ── Fault 3: Hang mid-request ─────────────────────────────────────


class TestMidRequestHang:
    """Child process hangs mid-request — call timeout fires, process discarded."""

    def test_mid_request_hang_times_out(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys, json, time
print("started", flush=True)
for line in sys.stdin:
    req = json.loads(line)
    if req.get("op") == "quit":
        break
    # Hang instead of responding
    time.sleep(30)
""",
        )
        sup = ProcessSupervisor(
            name="test-midhang",
            cmd=[sys.executable, bridge],
            startup_check="started",
            call_timeout=0.5,
        )
        try:
            assert sup.is_available()
            result = sup.call({"method": "ping"})
            assert not result.ok
            assert result.error == "timeout"
            assert result.fallback
            assert sup.stats.timeout_count == 1
        finally:
            sup.close()


# ── Fault 4: Malformed JSON ───────────────────────────────────────


class TestMalformedJson:
    """Child process emits malformed JSON — protocol error recorded."""

    def test_malformed_json_response(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys
print("started", flush=True)
for line in sys.stdin:
    # Respond with garbage
    print("not valid json {{{", flush=True)
""",
        )
        sup = ProcessSupervisor(
            name="test-malformed",
            cmd=[sys.executable, bridge],
            startup_check="started",
        )
        try:
            sup.is_available()
            result = sup.call({"method": "ping"})
            assert not result.ok
            assert "malformed_json" in result.error
            assert result.fallback
            assert sup.stats.protocol_error_count == 1
        finally:
            sup.close()

    def test_non_dict_response(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys, json
print("started", flush=True)
for line in sys.stdin:
    print(json.dumps([1, 2, 3]), flush=True)  # list, not dict
""",
        )
        sup = ProcessSupervisor(
            name="test-nondict",
            cmd=[sys.executable, bridge],
            startup_check="started",
        )
        try:
            sup.is_available()
            result = sup.call({"method": "ping"})
            assert not result.ok
            assert result.error == "non_dict_response"
            assert sup.stats.protocol_error_count == 1
        finally:
            sup.close()


# ── Fault 5: Pool exhaustion ──────────────────────────────────────


class TestPoolExhaustion:
    """Pool exhaustion under concurrent load — calls get fallback."""

    def test_pool_exhaustion_returns_fallback(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys, json, time
print("started", flush=True)
for line in sys.stdin:
    req = json.loads(line)
    if req.get("op") == "quit":
        break
    time.sleep(0.3)  # Slow response
    print(json.dumps({"status": "ok"}), flush=True)
""",
        )
        sup = ProcessSupervisor(
            name="test-pool",
            cmd=[sys.executable, bridge],
            startup_check="started",
            max_processes=1,
            call_timeout=2.0,
            lease_wait_timeout=0.05,
        )
        try:
            sup.is_available()
            results = []
            threads = []

            def _call():
                r = sup.call({"method": "ping"})
                results.append(r)

            # Launch 3 concurrent calls with only 1 process
            for _ in range(3):
                t = threading.Thread(target=_call)
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=5.0)

            # At least one should succeed, others may get fallback
            oks = [r for r in results if r.ok]
            fallbacks = [r for r in results if r.fallback]
            assert len(oks) >= 1
            # With 1 process and 3 concurrent, at least 1 should be fallback
            assert len(fallbacks) >= 1
        finally:
            sup.close()

    def test_multi_process_pool(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys, json, time
print("started", flush=True)
for line in sys.stdin:
    req = json.loads(line)
    if req.get("op") == "quit":
        break
    time.sleep(0.1)
    print(json.dumps({"status": "ok"}), flush=True)
""",
        )
        sup = ProcessSupervisor(
            name="test-mpool",
            cmd=[sys.executable, bridge],
            startup_check="started",
            max_processes=3,
            call_timeout=2.0,
        )
        try:
            sup.is_available()
            results = []
            threads = []

            def _call():
                r = sup.call({"method": "ping"})
                results.append(r)

            for _ in range(3):
                t = threading.Thread(target=_call)
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=5.0)

            oks = [r for r in results if r.ok]
            assert len(oks) == 3
        finally:
            sup.close()


# ── Fault 6: Shutdown while calls active ──────────────────────────


class TestShutdownDuringCalls:
    """Shutdown while calls are active — no deadlock, processes cleaned up."""

    def test_shutdown_during_active_call(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys, json, time
print("started", flush=True)
for line in sys.stdin:
    req = json.loads(line)
    if req.get("op") == "quit":
        break
    time.sleep(2.0)  # Long response
    print(json.dumps({"status": "ok"}), flush=True)
""",
        )
        sup = ProcessSupervisor(
            name="test-shutdown",
            cmd=[sys.executable, bridge],
            startup_check="started",
            call_timeout=5.0,
        )
        sup.is_available()

        # Start a call in background
        result_holder = []
        t = threading.Thread(
            target=lambda: result_holder.append(sup.call({"method": "ping"}))
        )
        t.start()

        # Give it a moment to start, then shut down
        time.sleep(0.1)
        sup.close()  # Should not deadlock

        t.join(timeout=3.0)
        assert sup.health_state == CapabilityState.UNAVAILABLE


# ── Fault 7: Repeated crash/restart cycles ────────────────────────


class TestCrashRestartCycles:
    """Repeated crash/restart cycles — circuit breaker opens, max restarts enforced."""

    def test_crash_circuit_breaker_opens(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys
print("started", flush=True)
# Crash immediately after startup — exit on first read
sys.stdin.readline()
import os
os._exit(1)
""",
        )
        sup = ProcessSupervisor(
            name="test-crash",
            cmd=[sys.executable, bridge],
            startup_check="started",
            call_timeout=1.0,
            circuit_threshold=2,
            max_restarts=10,
        )
        try:
            sup.is_available()
            # First call — process crashes
            r1 = sup.call({"method": "ping"})
            assert not r1.ok
            # Second call — process crashes again
            r2 = sup.call({"method": "ping"})
            assert not r2.ok
            # Circuit breaker should be open now (2 failures)
            assert sup.health_state == CapabilityState.CIRCUIT_OPEN
            # Third call — blocked by circuit breaker
            r3 = sup.call({"method": "ping"})
            assert not r3.ok
            assert r3.fallback
        finally:
            sup.close()

    def test_max_restarts_exceeded(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys
# Print started then immediately exit
print("started", flush=True)
import os
os._exit(1)
""",
        )
        sup = ProcessSupervisor(
            name="test-maxrestart",
            cmd=[sys.executable, bridge],
            startup_check="started",
            max_restarts=2,
            circuit_threshold=100,  # High so circuit doesn't interfere
        )
        try:
            # First start succeeds (process starts, prints "started"), then exits
            assert sup.is_available()
            # Call fails (process is dead)
            r1 = sup.call({"method": "ping"})
            assert not r1.ok
            # Restart attempt 1
            sup._restart_count = 0  # reset for clean test
            assert sup.restart()
            r2 = sup.call({"method": "ping"})
            assert not r2.ok
            # Restart attempt 2
            assert sup.restart()
            r3 = sup.call({"method": "ping"})
            assert not r3.ok
            # Restart attempt 3 — should fail (max_restarts=2)
            assert not sup.restart()
            assert sup.health_state == CapabilityState.UNAVAILABLE
        finally:
            sup.close()


# ── Lease Tests ───────────────────────────────────────────────────


class TestProcessLease:
    """Process lease exclusive access."""

    def test_lease_acquire_and_release(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys, json
print("started", flush=True)
for line in sys.stdin:
    req = json.loads(line)
    if req.get("op") == "quit":
        break
    print(json.dumps({"status": "ok"}), flush=True)
""",
        )
        sup = ProcessSupervisor(
            name="test-lease",
            cmd=[sys.executable, bridge],
            startup_check="started",
            max_processes=1,
        )
        try:
            sup.is_available()
            lease = sup.acquire_lease()
            assert lease is not None
            with lease as proc:
                assert proc.poll() is None
                # While lease is held, second acquire should fail (pool=1)
                lease2 = sup.acquire_lease(timeout=0.1)
                assert lease2 is None
            # After release, should be available again
            lease3 = sup.acquire_lease(timeout=0.5)
            assert lease3 is not None
            lease3.release()
        finally:
            sup.close()

    def test_lease_release_on_exception(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            "import sys; print('started', flush=True); sys.stdin.read()",
        )
        sup = ProcessSupervisor(
            name="test-lease-exc",
            cmd=[sys.executable, bridge],
            startup_check="started",
            max_processes=1,
        )
        try:
            sup.is_available()
            lease = sup.acquire_lease()
            assert lease is not None
            try:
                with lease:
                    raise ValueError("test error")
            except ValueError:
                pass
            # Lease should be released (marked unhealthy)
            # Process should be discarded
            assert len(sup._processes) == 0 or lease._released
        finally:
            sup.close()


# ── Stats Tests ───────────────────────────────────────────────────


class TestBridgeStats:
    """Stats recording and serialization."""

    def test_stats_to_dict(self):
        stats = BridgeStats()
        stats.record_startup(0.005)
        stats.record_call(0.002, success=True)
        stats.record_call(0.003, success=False)
        stats.timeout_count = 1
        d = stats.to_dict()
        assert d["total_calls"] == 2
        assert d["successful_calls"] == 1
        assert d["timeout_count"] == 1
        assert d["avg_startup_latency_ms"] == 5.0
        assert d["avg_call_latency_ms"] == 2.5
        assert d["last_startup_latency_ms"] == 5.0
        assert d["last_call_latency_ms"] == 3.0

    def test_stats_trim_lists(self):
        stats = BridgeStats()
        for i in range(150):
            stats.record_startup(0.001 * i)
        # Trim triggers when len > 100, keeping last 50; then grows again
        assert len(stats.startup_latency_ms) <= 100


# ── Line Protocol Tests ───────────────────────────────────────────


class TestCallLine:
    """Line-protocol call (non-JSON)."""

    def test_call_line_ok(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            """
import sys
print("started", flush=True)
for line in sys.stdin:
    cmd = line.strip()
    if cmd == "quit":
        break
    print(f"ok:{cmd}", flush=True)
""",
        )
        sup = ProcessSupervisor(
            name="test-line",
            cmd=[sys.executable, bridge],
            startup_check="started",
        )
        try:
            sup.is_available()
            result = sup.call_line("check:default")
            assert result.ok
            assert result.data["response"] == "ok:check:default"
        finally:
            sup.close()


# ── Global Registry Tests ─────────────────────────────────────────


class TestGlobalRegistry:
    """Global shutdown registry."""

    def test_register_and_shutdown_all(self, tmp_path):
        bridge = _make_mock_bridge(
            tmp_path,
            "import sys; print('started', flush=True); sys.stdin.read()",
        )
        sup = ProcessSupervisor(
            name="test-registry",
            cmd=[sys.executable, bridge],
            startup_check="started",
        )
        register(sup)
        assert sup in list_supervisors()
        sup.is_available()
        shutdown_all()
        assert sup.health_state == CapabilityState.UNAVAILABLE
        assert sup not in list_supervisors()


# ── BridgeResult Tests ────────────────────────────────────────────


class TestBridgeResult:
    """BridgeResult dataclass."""

    def test_ok_result(self):
        r = BridgeResult(ok=True, data={"status": "ok"}, latency_ms=1.5)
        assert r.ok
        assert r.data["status"] == "ok"
        assert not r.fallback

    def test_fallback_result(self):
        r = BridgeResult(ok=False, error="timeout", fallback=True)
        assert not r.ok
        assert r.fallback
        assert r.error == "timeout"
        assert r.data is None
