"""Shared ProcessSupervisor for native bridge subprocess management.

Phase 5 of the Codebase Hardening Strategy.

Replaces the duplicated _readline_timeout / _ensure_running / close pattern
across Rust, Julia, Elixir, Haskell, and Koka bridges with a single
supervised abstraction that provides:

- Bounded stderr draining (prevents pipe-full hangs)
- Process leases (no concurrent use of a single-process bridge)
- Circuit breaker (auto-open on repeated failures)
- Capability health states (unavailable → starting → healthy → degraded → circuit-open → stopping)
- Structured stats (startup latency, call latency, timeouts, restarts, protocol errors, fallbacks)
- Graceful shutdown with orphan cleanup
- Fallback exposure (callers can detect when Python fallback was used)

Usage::

    from whitemagic.core.acceleration.process_supervisor import (
        ProcessSupervisor, CapabilityState, BridgeResult,
    )

    sup = ProcessSupervisor(
        name="rust-evolution",
        cmd=["/path/to/evolution_bridge"],
        startup_timeout=5.0,
        call_timeout=5.0,
    )

    result = sup.call({"method": "ping", "params": {}})
    if result.ok:
        print(result.data)
    else:
        print(f"fallback={result.fallback}, error={result.error}")
"""
from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STDERR_CAP_BYTES = 64 * 1024  # 64 KB bounded stderr sink
_DEFAULT_STARTUP_TIMEOUT = 5.0
_DEFAULT_CALL_TIMEOUT = 5.0
_DEFAULT_MAX_RESTARTS = 5
_DEFAULT_CIRCUIT_THRESHOLD = 3
_DEFAULT_CIRCUIT_RESET_TIMEOUT = 30.0
_LEASE_WAIT_TIMEOUT = 2.0


class CapabilityState(str, Enum):
    """Health states for a native bridge capability."""

    UNAVAILABLE = "unavailable"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CIRCUIT_OPEN = "circuit_open"
    STOPPING = "stopping"


@dataclass
class BridgeStats:
    """Structured stats for a supervised bridge."""

    startup_latency_ms: list[float] = field(default_factory=list)
    call_latency_ms: list[float] = field(default_factory=list)
    timeout_count: int = 0
    restart_count: int = 0
    protocol_error_count: int = 0
    fallback_count: int = 0
    total_calls: int = 0
    successful_calls: int = 0
    last_startup_latency_ms: float = 0.0
    last_call_latency_ms: float = 0.0

    def record_startup(self, latency_s: float) -> None:
        ms = latency_s * 1000
        self.startup_latency_ms.append(ms)
        if len(self.startup_latency_ms) > 100:
            del self.startup_latency_ms[: len(self.startup_latency_ms) - 50]
        self.last_startup_latency_ms = ms

    def record_call(self, latency_s: float, success: bool) -> None:
        ms = latency_s * 1000
        self.call_latency_ms.append(ms)
        if len(self.call_latency_ms) > 200:
            del self.call_latency_ms[: len(self.call_latency_ms) - 100]
        self.last_call_latency_ms = ms
        self.total_calls += 1
        if success:
            self.successful_calls += 1

    def to_dict(self) -> dict[str, Any]:
        avg_startup = (
            sum(self.startup_latency_ms) / len(self.startup_latency_ms)
            if self.startup_latency_ms
            else 0.0
        )
        avg_call = (
            sum(self.call_latency_ms) / len(self.call_latency_ms)
            if self.call_latency_ms
            else 0.0
        )
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "timeout_count": self.timeout_count,
            "restart_count": self.restart_count,
            "protocol_error_count": self.protocol_error_count,
            "fallback_count": self.fallback_count,
            "avg_startup_latency_ms": round(avg_startup, 2),
            "avg_call_latency_ms": round(avg_call, 2),
            "last_startup_latency_ms": round(self.last_startup_latency_ms, 2),
            "last_call_latency_ms": round(self.last_call_latency_ms, 2),
        }


@dataclass
class BridgeResult:
    """Result from a supervised bridge call.

    Attributes:
        ok: Whether the call succeeded.
        data: Response dict on success.
        error: Error message on failure.
        fallback: True if Python fallback was used (bridge unavailable).
        latency_ms: Call latency in milliseconds.
    """

    ok: bool = False
    data: dict[str, Any] | None = None
    error: str | None = None
    fallback: bool = False
    latency_ms: float = 0.0


class _CircuitBreaker:
    """Internal circuit breaker for a supervised bridge."""

    def __init__(
        self,
        failure_threshold: int = _DEFAULT_CIRCUIT_THRESHOLD,
        reset_timeout: float = _DEFAULT_CIRCUIT_RESET_TIMEOUT,
    ):
        self._failures = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._last_failure_time = 0.0
        self._state = CapabilityState.HEALTHY
        self._lock = threading.Lock()

    @property
    def state(self) -> CapabilityState:
        with self._lock:
            if self._state == CapabilityState.CIRCUIT_OPEN:
                if time.time() - self._last_failure_time > self._reset_timeout:
                    self._state = CapabilityState.DEGRADED
                    logger.info("Circuit breaker half-open (testing)")
            return self._state

    def allow_request(self) -> bool:
        with self._lock:
            if self._state == CapabilityState.CIRCUIT_OPEN:
                if time.time() - self._last_failure_time > self._reset_timeout:
                    self._state = CapabilityState.DEGRADED
                    logger.info("Circuit breaker half-open (testing)")
                    return True
                return False
            return True

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._failures >= self._failure_threshold:
                self._state = CapabilityState.CIRCUIT_OPEN
                logger.warning(
                    "Circuit breaker OPENED after %s failures", self._failures
                )

    def record_success(self) -> None:
        with self._lock:
            if self._state != CapabilityState.HEALTHY:
                logger.info("Circuit breaker RESET to HEALTHY")
            self._failures = 0
            self._state = CapabilityState.HEALTHY


class _ProcessLease:
    """Context manager for exclusive access to a subprocess."""

    def __init__(self, supervisor: ProcessSupervisor, proc: subprocess.Popen):
        self._supervisor = supervisor
        self._proc = proc
        self._released = False

    @property
    def proc(self) -> subprocess.Popen:
        return self._proc

    def release(self, healthy: bool = True) -> None:
        if self._released:
            return
        self._released = True
        self._supervisor._release_process(self._proc, healthy)

    def __enter__(self) -> subprocess.Popen:
        return self._proc

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        healthy = exc_type is None
        self.release(healthy=healthy)


class ProcessSupervisor:
    """Supervised subprocess bridge with leases, circuit breaker, and stats.

    Manages a pool of subprocess.Popen processes for a single native bridge.
    Replaces the duplicated _readline_timeout / _ensure_running / close pattern.
    """

    def __init__(
        self,
        name: str,
        cmd: list[str],
        *,
        binary_path: str | Path | None = None,
        max_processes: int = 1,
        startup_timeout: float = _DEFAULT_STARTUP_TIMEOUT,
        call_timeout: float = _DEFAULT_CALL_TIMEOUT,
        startup_message: str | None = None,
        startup_check: str | None = None,
        env: dict[str, str] | None = None,
        cwd: str | Path | None = None,
        skip_env_var: str | None = None,
        skip_polyglot: bool = False,
        circuit_threshold: int = _DEFAULT_CIRCUIT_THRESHOLD,
        circuit_reset_timeout: float = _DEFAULT_CIRCUIT_RESET_TIMEOUT,
        max_restarts: int = _DEFAULT_MAX_RESTARTS,
        stderr_cap: int = _STDERR_CAP_BYTES,
        lease_wait_timeout: float = _LEASE_WAIT_TIMEOUT,
    ):
        """Initialize a ProcessSupervisor.

        Args:
            name: Human-readable bridge name (for logging/stats).
            cmd: Command list to start the subprocess.
            binary_path: Optional path to the binary (checked for existence before start).
            max_processes: Maximum number of concurrent processes in the pool.
            startup_timeout: Seconds to wait for startup handshake.
            call_timeout: Default seconds to wait for a call response.
            startup_message: Expected substring in startup line (e.g. "started").
            startup_check: Alternative to startup_message — if set, the startup
                line must contain this substring to be considered healthy.
            env: Additional environment variables for the subprocess.
            cwd: Working directory for the subprocess.
            skip_env_var: Environment variable name; if set to "1", bridge is skipped.
            skip_polyglot: If True, respect WM_SKIP_POLYGLOT env var.
            circuit_threshold: Failures before circuit breaker opens.
            circuit_reset_timeout: Seconds before circuit breaker half-opens.
            max_restarts: Maximum restart attempts before marking unavailable.
            stderr_cap: Maximum bytes of stderr to retain.
        """
        self.name = name
        self._cmd = cmd
        self._binary_path = str(binary_path) if binary_path else None
        self._max_processes = max(1, max_processes)
        self._startup_timeout = startup_timeout
        self._call_timeout = call_timeout
        self._startup_message = startup_message
        self._startup_check = startup_check or startup_message
        self._env = env
        self._cwd = str(cwd) if cwd else None
        self._skip_env_var = skip_env_var
        self._skip_polyglot = skip_polyglot
        self._max_restarts = max_restarts
        self._stderr_cap = stderr_cap
        self._lease_wait_timeout = lease_wait_timeout

        self._lock = threading.RLock()  # reentrant — _release_process calls _discard_process
        self._processes: list[subprocess.Popen] = []
        self._available: list[subprocess.Popen] = []
        self._stderr_buffers: dict[int, bytearray] = {}
        self._stderr_threads: dict[int, threading.Thread] = {}
        self._started = False

        self._breaker = _CircuitBreaker(circuit_threshold, circuit_reset_timeout)
        self._stats = BridgeStats()
        self._health = CapabilityState.UNAVAILABLE
        self._restart_count = 0
        self._last_stderr: str = ""

    # ── Health and Stats ──────────────────────────────────────────

    @property
    def health_state(self) -> CapabilityState:
        """Current capability health state."""
        if self._health in (CapabilityState.STOPPING, CapabilityState.UNAVAILABLE):
            return self._health
        breaker_state = self._breaker.state
        if breaker_state == CapabilityState.CIRCUIT_OPEN:
            return CapabilityState.CIRCUIT_OPEN
        if breaker_state == CapabilityState.DEGRADED:
            return CapabilityState.DEGRADED
        if self._started and self._available:
            return CapabilityState.HEALTHY
        if self._started and not self._available:
            return CapabilityState.DEGRADED
        return self._health

    @property
    def stats(self) -> BridgeStats:
        return self._stats

    @property
    def last_stderr(self) -> str:
        """Last captured stderr output (truncated to cap)."""
        return self._last_stderr

    # ── Availability ──────────────────────────────────────────────

    def is_available(self) -> bool:
        """Check if the bridge is available (starts it if needed)."""
        return self._ensure_running() is not None

    def _should_skip(self) -> bool:
        """Check skip conditions."""
        if self._skip_polyglot and os.environ.get("WM_SKIP_POLYGLOT", ""):
            return True
        if self._skip_env_var and os.environ.get(self._skip_env_var, ""):
            return True
        return False

    # ── Process Lifecycle ─────────────────────────────────────────

    def _ensure_running(self) -> subprocess.Popen | None:
        """Ensure at least one process is running; start if needed."""
        if self._should_skip():
            self._health = CapabilityState.UNAVAILABLE
            return None

        with self._lock:
            if self._started and self._available:
                return self._available[0]

            if self._binary_path and not os.path.isfile(self._binary_path):
                self._health = CapabilityState.UNAVAILABLE
                logger.debug("%s: binary not found at %s", self.name, self._binary_path)
                return None

            if self._restart_count > self._max_restarts:
                self._health = CapabilityState.UNAVAILABLE
                logger.warning(
                    "%s: max restarts (%d) exceeded, marking unavailable",
                    self.name,
                    self._max_restarts,
                )
                return None

            if not self._breaker.allow_request():
                return None

            proc = self._start_process()
            if proc is None:
                return None

            return proc

    def _start_process(self) -> subprocess.Popen | None:
        """Start a new subprocess and perform startup handshake."""
        self._health = CapabilityState.STARTING
        start_time = time.perf_counter()

        try:
            full_env = None
            if self._env:
                full_env = {**os.environ, **self._env}

            proc = subprocess.Popen(
                self._cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=full_env,
                cwd=self._cwd,
            )
        except Exception as e:
            logger.debug("%s: failed to start process: %s", self.name, e)
            self._health = CapabilityState.UNAVAILABLE
            self._breaker.record_failure()
            return None

        # Start stderr drain thread
        self._start_stderr_drain(proc)

        # Startup handshake
        if self._startup_check:
            line = self._readline_with_timeout(proc, timeout=self._startup_timeout)
            if not line or self._startup_check not in line:
                logger.warning(
                    "%s: startup handshake failed (expected %r, got %r)",
                    self.name,
                    self._startup_check,
                    (line or "")[:100],
                )
                self._kill_process(proc)
                self._health = CapabilityState.UNAVAILABLE
                self._breaker.record_failure()
                return None

        elapsed = time.perf_counter() - start_time
        self._stats.record_startup(elapsed)
        self._processes.append(proc)
        self._available.append(proc)
        self._started = True
        self._health = CapabilityState.HEALTHY
        logger.debug(
            "%s: process started in %.1fms (pid=%d)",
            self.name,
            elapsed * 1000,
            proc.pid,
        )
        return proc

    def _start_stderr_drain(self, proc: subprocess.Popen) -> None:
        """Start a daemon thread to drain stderr into a bounded buffer."""
        buf = bytearray()
        self._stderr_buffers[proc.pid] = buf

        def _drain() -> None:
            try:
                stderr = proc.stderr
                if stderr is None:
                    return
                while True:
                    chunk = stderr.read(4096)
                    if not chunk:
                        break
                    buf.extend(chunk.encode("utf-8", errors="replace") if isinstance(chunk, str) else chunk)
                    # Trim to cap, keeping the most recent bytes
                    if len(buf) > self._stderr_cap:
                        del buf[: len(buf) - self._stderr_cap]
            except Exception:
                logger.debug("Ignored error in process_supervisor.py:456")

        t = threading.Thread(
            target=_drain, name=f"wm-{self.name}-stderr", daemon=True
        )
        t.start()
        self._stderr_threads[proc.pid] = t

    def _get_stderr(self, proc: subprocess.Popen) -> str:
        """Get captured stderr for a process."""
        buf = self._stderr_buffers.get(proc.pid)
        if buf is None:
            return ""
        return buf.decode("utf-8", errors="replace")

    # ── Process Pool / Leases ─────────────────────────────────────

    def _get_process(self, timeout: float | None = None) -> subprocess.Popen | None:
        """Acquire a process from the pool (with lease)."""
        if timeout is None:
            timeout = self._lease_wait_timeout
        if not self._breaker.allow_request():
            return None

        with self._lock:
            if self._available:
                return self._available.pop(0)

            if len(self._processes) < self._max_processes:
                proc = self._start_process()
                if proc and self._available:
                    return self._available.pop(0)

        # Pool exhausted — brief wait
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if self._available:
                    return self._available.pop(0)
            time.sleep(0.05)

        return None

    def _release_process(self, proc: subprocess.Popen, healthy: bool = True) -> None:
        """Return a process to the pool or discard if unhealthy."""
        with self._lock:
            if not healthy or proc.poll() is not None:
                # Process died or was marked unhealthy — discard
                self._discard_process(proc)
            else:
                if proc not in self._available:
                    self._available.append(proc)

    def _discard_process(self, proc: subprocess.Popen) -> None:
        """Remove and terminate a process from the pool."""
        with self._lock:
            if proc in self._available:
                self._available.remove(proc)
            if proc in self._processes:
                self._processes.remove(proc)
        self._kill_process(proc)

    def _kill_process(self, proc: subprocess.Popen) -> None:
        """Kill a process and clean up resources."""
        try:
            proc.terminate()
            proc.wait(timeout=1.0)
        except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
            try:
                proc.kill()
            except (ProcessLookupError, OSError):
                logger.debug("Ignored ProcessLookupError, OSError in process_supervisor.py:527")
        # Clean up stderr tracking
        self._stderr_buffers.pop(proc.pid, None)
        self._stderr_threads.pop(proc.pid, None)

    # ── I/O ───────────────────────────────────────────────────────

    def _readline_with_timeout(
        self, proc: subprocess.Popen, timeout: float
    ) -> str | None:
        """Read a single line from proc.stdout with a hard timeout."""
        if proc.stdout is None:
            return None

        result_queue: queue.Queue[str | None] = queue.Queue(maxsize=1)

        def _reader() -> None:
            try:
                stdout = proc.stdout
                if stdout is not None:
                    line = stdout.readline()
                    result_queue.put(line)
                else:
                    result_queue.put(None)
            except Exception:
                result_queue.put(None)

        thread = threading.Thread(
            target=_reader, name=f"wm-{self.name}-readline", daemon=True
        )
        thread.start()

        try:
            res = result_queue.get(timeout=timeout)
            thread.join(0.1)
            return res
        except queue.Empty:
            return None

    # ── Public API ────────────────────────────────────────────────

    def acquire_lease(self, timeout: float | None = None) -> _ProcessLease | None:
        """Acquire an exclusive lease on a process.

        Returns a _ProcessLease context manager, or None if no process available.
        Use as::

            lease = sup.acquire_lease()
            if lease:
                with lease as proc:
                    proc.stdin.write(...)
        """
        proc = self._get_process(timeout=timeout)
        if proc is None:
            return None
        return _ProcessLease(self, proc)

    def call(
        self,
        request: dict[str, Any],
        *,
        timeout: float | None = None,
        raw_line: bool = False,
    ) -> BridgeResult:
        """Send a JSON request and receive a JSON response.

        Args:
            request: JSON-serializable dict to send.
            timeout: Override default call timeout.
            raw_line: If True, send raw string instead of JSON dict.
                      The request must be a str in this case.

        Returns:
            BridgeResult with ok=True on success, or ok=False with error/fallback.
        """
        call_timeout = timeout or self._call_timeout
        proc = self._get_process()
        if proc is None:
            self._stats.fallback_count += 1
            return BridgeResult(
                ok=False,
                error="no_process_available",
                fallback=True,
            )

        start = time.perf_counter()
        try:
            stdin = proc.stdin
            if stdin is None:
                self._stats.fallback_count += 1
                self._discard_process(proc)
                return BridgeResult(ok=False, error="stdin_unavailable", fallback=True)

            if raw_line:
                assert isinstance(request, str)
                stdin.write(request + "\n")
            else:
                stdin.write(json.dumps(request) + "\n")
            stdin.flush()

            line = self._readline_with_timeout(proc, timeout=call_timeout)
            elapsed = time.perf_counter() - start
            elapsed_ms = elapsed * 1000

            if not line:
                self._stats.timeout_count += 1
                self._stats.record_call(elapsed, success=False)
                self._breaker.record_failure()
                self._last_stderr = self._get_stderr(proc)
                self._discard_process(proc)
                return BridgeResult(
                    ok=False,
                    error="timeout",
                    fallback=True,
                    latency_ms=elapsed_ms,
                )

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                self._stats.protocol_error_count += 1
                self._stats.record_call(elapsed, success=False)
                self._breaker.record_failure()
                self._last_stderr = self._get_stderr(proc)
                logger.error(
                    "%s: malformed JSON response: %s (line=%r)",
                    self.name,
                    e,
                    line[:200],
                )
                self._discard_process(proc)
                return BridgeResult(
                    ok=False,
                    error=f"malformed_json: {e}",
                    fallback=True,
                    latency_ms=elapsed_ms,
                )

            if not isinstance(data, dict):
                self._stats.protocol_error_count += 1
                self._stats.record_call(elapsed, success=False)
                self._breaker.record_failure()
                self._discard_process(proc)
                return BridgeResult(
                    ok=False,
                    error="non_dict_response",
                    fallback=True,
                    latency_ms=elapsed_ms,
                )

            self._stats.record_call(elapsed, success=True)
            self._breaker.record_success()
            return BridgeResult(
                ok=True,
                data=data,
                latency_ms=elapsed_ms,
            )

        except BrokenPipeError as e:
            elapsed = time.perf_counter() - start
            self._stats.record_call(elapsed, success=False)
            self._breaker.record_failure()
            self._discard_process(proc)
            return BridgeResult(
                ok=False,
                error=f"broken_pipe: {e}",
                fallback=True,
                latency_ms=elapsed * 1000,
            )
        except Exception as e:
            elapsed = time.perf_counter() - start
            self._stats.record_call(elapsed, success=False)
            self._breaker.record_failure()
            logger.debug("%s: call error: %s", self.name, e, exc_info=True)
            self._discard_process(proc)
            return BridgeResult(
                ok=False,
                error=str(e),
                fallback=True,
                latency_ms=elapsed * 1000,
            )
        finally:
            if proc.poll() is None:
                self._release_process(proc)

    def call_line(
        self,
        command: str,
        *,
        timeout: float | None = None,
    ) -> BridgeResult:
        """Send a line-protocol command and receive a raw string response.

        Unlike call(), this does not parse JSON. Useful for line-protocol
        bridges (e.g. Koka circuit/backpressure).

        Args:
            command: Raw command string to send.
            timeout: Override default call timeout.

        Returns:
            BridgeResult with data={"response": str} on success.
        """
        call_timeout = timeout or self._call_timeout
        proc = self._get_process()
        if proc is None:
            self._stats.fallback_count += 1
            return BridgeResult(ok=False, error="no_process_available", fallback=True)

        start = time.perf_counter()
        try:
            stdin = proc.stdin
            if stdin is None:
                self._discard_process(proc)
                return BridgeResult(ok=False, error="stdin_unavailable", fallback=True)

            stdin.write(command + "\n")
            stdin.flush()

            line = self._readline_with_timeout(proc, timeout=call_timeout)
            elapsed = time.perf_counter() - start
            elapsed_ms = elapsed * 1000

            if not line:
                self._stats.timeout_count += 1
                self._stats.record_call(elapsed, success=False)
                self._breaker.record_failure()
                self._discard_process(proc)
                return BridgeResult(
                    ok=False, error="timeout", fallback=True, latency_ms=elapsed_ms
                )

            self._stats.record_call(elapsed, success=True)
            self._breaker.record_success()
            return BridgeResult(
                ok=True, data={"response": line.strip()}, latency_ms=elapsed_ms
            )
        except Exception as e:
            elapsed = time.perf_counter() - start
            self._stats.record_call(elapsed, success=False)
            self._breaker.record_failure()
            self._discard_process(proc)
            return BridgeResult(
                ok=False, error=str(e), fallback=True, latency_ms=elapsed * 1000
            )
        finally:
            if proc.poll() is None:
                self._release_process(proc)

    # ── Shutdown ──────────────────────────────────────────────────

    def close(self) -> None:
        """Gracefully shut down all processes."""
        self._health = CapabilityState.STOPPING
        with self._lock:
            for proc in list(self._processes):
                self._shutdown_process(proc)
            self._processes.clear()
            self._available.clear()
            self._started = False
        self._health = CapabilityState.UNAVAILABLE

    def _shutdown_process(self, proc: subprocess.Popen) -> None:
        """Send quit command, then terminate, then kill."""
        try:
            stdin = proc.stdin
            if stdin is not None:
                try:
                    stdin.write(json.dumps({"op": "quit"}) + "\n")
                    stdin.flush()
                except (BrokenPipeError, OSError):
                    logger.debug("Ignored BrokenPipeError, OSError in process_supervisor.py:798")
            proc.wait(timeout=2.0)
        except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
            try:
                proc.terminate()
                proc.wait(timeout=1.0)
            except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
                try:
                    proc.kill()
                except (ProcessLookupError, OSError):
                    logger.debug("Ignored ProcessLookupError, OSError in process_supervisor.py:808")
        # Capture final stderr
        self._last_stderr = self._get_stderr(proc)
        self._stderr_buffers.pop(proc.pid, None)
        self._stderr_threads.pop(proc.pid, None)

    def restart(self) -> bool:
        """Restart all processes (e.g. after circuit breaker reset)."""
        self.close()
        self._restart_count += 1
        self._stats.restart_count += 1
        self._breaker = _CircuitBreaker(
            self._breaker._failure_threshold, self._breaker._reset_timeout
        )
        return self._ensure_running() is not None

    def health_check(self) -> dict[str, Any]:
        """Return a health check dict."""
        return {
            "name": self.name,
            "health_state": self.health_state.value,
            "available": self._started and bool(self._available),
            "processes": len(self._processes),
            "available_processes": len(self._available),
            "stats": self._stats.to_dict(),
            "last_stderr": self._last_stderr[:500] if self._last_stderr else "",
        }


# ── Global Registry for Shutdown ──────────────────────────────────

_registry_lock = threading.Lock()
_registry: list[ProcessSupervisor] = []
_atexit_registered = False


def register(supervisor: ProcessSupervisor) -> None:
    """Register a supervisor for global shutdown."""
    global _atexit_registered
    with _registry_lock:
        _registry.append(supervisor)
        if not _atexit_registered:
            import atexit

            atexit.register(shutdown_all)
            _atexit_registered = True


def shutdown_all() -> None:
    """Shut down all registered supervisors (atexit handler)."""
    with _registry_lock:
        supervisors = list(_registry)
        _registry.clear()
    for sup in supervisors:
        try:
            sup.close()
        except Exception:
            logger.debug("Error shutting down %s", sup.name, exc_info=True)


def list_supervisors() -> list[ProcessSupervisor]:
    """List all registered supervisors."""
    with _registry_lock:
        return list(_registry)
