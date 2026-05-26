"""Koka Native Bridge — Python ↔ Koka via compiled binaries (S023)
=============================================================
High-performance bridge using compiled Koka native binaries.
Faster than subprocess-per-call by using persistent processes.

Usage:
    from whitemagic.core.acceleration.koka_native_bridge import (
        KokaNativeBridge, koka_dispatch
    )

    result = koka_dispatch("prat", "route", {"tool": "memory.create"})
"""
from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, cast

from whitemagic.utils.fast_json import dumps_str as _json_dumps, loads as _json_loads

logger = logging.getLogger(__name__)

# Build paths
_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "whitemagic-koka"
_BUILD_DIR = _BASE_DIR  # Binaries are in root, not .koka_build/native
_DISPATCHER_BIN = _BASE_DIR / "orchestrator"  # Use orchestrator as dispatcher

# Module-specific binaries (in whitemagic-koka/ root)
_MODULE_BINS = {
    "prat": _BASE_DIR / "prat",
    "resonance": _BASE_DIR / "resonance",
    "gan_ying": _BASE_DIR / "gan_ying",
    "gana": _BASE_DIR / "gan_ying",  # gan_ying handles gana operations
    "circuit": _BASE_DIR / "circuit",
    "retry": _BASE_DIR / "circuit",  # circuit handles retry logic
    "session": _BASE_DIR / "unified_runtime_v3",  # unified runtime for sessions
"resources": _BASE_DIR / "ring_buffer",
    "dream": _BASE_DIR / "dream_cycle",
    "metrics": _BASE_DIR / "metrics",
    "hot_paths": _BASE_DIR / "hot_paths",
    "shm_search": _BASE_DIR / "shm_search",
}



class KokaCircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 30.0):
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0.0
        self.state = "CLOSED" # CLOSED (ok), OPEN (failing), HALF_OPEN (testing)
        self.lock = threading.Lock()

    def record_failure(self):
        with self.lock:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Koka circuit breaker OPENED after {self.failures} failures")

    def record_success(self):
        with self.lock:
            self.failures = 0
            if self.state != "CLOSED":
                self.state = "CLOSED"
                logger.info("Koka circuit breaker RESET to CLOSED")

    def allow_request(self) -> bool:
        with self.lock:
            if self.state == "CLOSED":
                return True
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.reset_timeout:
                    self.state = "HALF_OPEN"
                    return True
                return False
            # HALF_OPEN allows 1 request through
            return True

class KokaNativeBridge:
    """High-performance bridge to compiled Koka native binaries.

    Uses persistent subprocesses to avoid process startup overhead.
    Thread-safe with connection pooling.
    """

    def __init__(self, max_connections: int = 4):
        self._lock = threading.Lock()
        self._max_connections = max_connections
        self._processes: dict[str, list[subprocess.Popen]] = {}
        self._available: dict[str, list[subprocess.Popen]] = {}
        self._binaries: dict[str, Path] = {}
        self._breakers: dict[str, KokaCircuitBreaker] = {}

        self._check_binaries()

    def _check_binaries(self) -> None:
        """Verify which Koka binaries are available."""
        for name, path in _MODULE_BINS.items():
            if path.exists() and os.access(path, os.X_OK):
                self._binaries[name] = path
                self._available[name] = []
                if name not in self._breakers:
                    self._breakers[name] = KokaCircuitBreaker()
                logger.info("Koka binary available: %s", name)
            else:
                logger.debug("Koka binary not found: %s", path)

        # Check dispatcher
        if _DISPATCHER_BIN.exists() and os.access(_DISPATCHER_BIN, os.X_OK):
            self._binaries["dispatcher"] = _DISPATCHER_BIN
            self._available["dispatcher"] = []
            if "dispatcher" not in self._breakers:
                self._breakers["dispatcher"] = KokaCircuitBreaker()
            logger.info("Koka dispatcher available")

    def is_available(self, module: str) -> bool:
        """Check if a Koka module is available and healthy."""
        if module not in self._binaries:
            return False

        with self._lock:
            # Check for dead processes and prune them
            if module in self._processes:
                dead_procs = [p for p in self._processes[module] if p.poll() is not None]
                for p in dead_procs:
                    self._processes[module].remove(p)
                    if module in self._available and p in self._available[module]:
                        self._available[module].remove(p)

            # If we have living processes or room to grow, we are available
            current_alive = len(self._processes.get(module, []))
            return current_alive > 0 or current_alive < self._max_connections

    def _get_process(self, module: str) -> subprocess.Popen | None:
        """Get or create a subprocess for the module."""
        with self._lock:
            # Clean dead processes from available pool first
            if self._available.get(module):
                valid_procs = [p for p in self._available[module] if p.poll() is None]
                self._available[module] = valid_procs
                if valid_procs:
                    return self._available[module].pop()

            # Check if we can create more
            # Clean dead processes from total tracked
            if module in self._processes:
                self._processes[module] = [p for p in self._processes[module] if p.poll() is None]

            current = len(self._processes.get(module, []))
            if current >= self._max_connections:
                return None  # Pool exhausted


            # Create new process
            binary = self._binaries.get(module)
            if not binary:
                return None

            try:
                proc = subprocess.Popen(
                    ['stdbuf', '-o0', '-i0', str(binary)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1  # Line buffered
                )

                # Consume initialization line with timeout
                init_line = self._readline_with_timeout(proc, 2.0)
                if not init_line:
                    logger.error("Koka init timed out for %s", module)
                    self._discard_process(module, proc)
                    return None
                logger.debug("Koka init: %s", init_line.strip())

                if module not in self._processes:
                    self._processes[module] = []
                self._processes[module].append(proc)


                return proc
            except Exception as e:
                logger.error("Failed to start Koka process for %s: %s", module, e)
                return None

    def _return_process(self, module: str, proc: subprocess.Popen) -> None:
        """Return a process to the available pool."""
        with self._lock:
            if proc.poll() is None:  # Still running
                self._available[module].append(proc)

    def _discard_process(self, module: str, proc: subprocess.Popen) -> None:
        """Remove and terminate a process that timed out or became unhealthy."""
        with self._lock:
            if module in self._available and proc in self._available[module]:
                self._available[module].remove(proc)
            if module in self._processes and proc in self._processes[module]:
                self._processes[module].remove(proc)
        try:
            proc.terminate()
            proc.wait(timeout=1.0)
        except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
            try:
                proc.kill()
            except (ProcessLookupError, OSError):
                pass

    def _readline_with_timeout(self, proc: subprocess.Popen, timeout: float) -> str | None:
        """Read a single line from a process stdout with a hard timeout."""
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

        thread = threading.Thread(target=_reader, name='wm-koka-readline', daemon=True)
        thread.start()
        # Add thread join with a slightly longer timeout just to avoid leaking threads
        try:
            res = result_queue.get(timeout=timeout)
            # Give thread a chance to finish cleanly
            thread.join(0.1)
            return res
        except queue.Empty:
            return None

    def dispatch(
        self,
        module: str,
        operation: str,
        args: dict[str, Any],
        timeout: float = 5.0
    ) -> dict[str, Any] | None:
        """Dispatch a call to a Koka native module.

        Args:
            module: Koka module name (e.g., "prat", "gana")
            operation: Effect operation to invoke
            args: Arguments as JSON-serializable dict
            timeout: Maximum seconds to wait for response

        Returns:
            Parsed JSON response or None on failure
        """

        if not self.is_available(module):
            logger.debug("Koka module not available: %s", module)
            return None

        breaker = self._breakers.get(module)
        if breaker and not breaker.allow_request():
            logger.warning("Koka circuit breaker OPEN for %s - skipping dispatch", module)
            return None


        proc = self._get_process(module)
        if not proc:
            logger.warning("Koka process pool exhausted for %s", module)
            return None

        try:
            # Build request
            request = {
                "module": module,
                "operation": operation,
                "args": args,
                "timestamp": time.time()
            }

            # Send request
            request_json = _json_dumps(request)
            if proc.stdin is not None:
                proc.stdin.write(request_json + "\n")
                proc.stdin.flush()
            else:
                logger.error("Koka process stdin is None for %s", module)
                return None

            # Read response with timeout
            start = time.time()
            response_line = self._readline_with_timeout(proc, timeout)
            elapsed = time.time() - start

            if not response_line:
                logger.error("Koka process timed out or returned no response for %s.%s", module, operation)
                if breaker:
                    breaker.record_failure()
                self._discard_process(module, proc)
                return None

            # Parse response
            try:
                response = _json_loads(response_line)
                if isinstance(response, dict):
                    response["_koka_latency_ms"] = elapsed * 1000
                    if breaker:
                        breaker.record_success()
                    return cast(dict[str, Any], response)
                return None
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON from Koka: %s", e)
                if breaker:
                    breaker.record_failure()
                return None

        except subprocess.TimeoutExpired:
            logger.error("Koka call timed out: %s.%s", module, operation)
            if breaker:
                    breaker.record_failure()
            return None
        except Exception as e:
            logger.error("Koka dispatch error: %s", e)
            if breaker:
                    breaker.record_failure()
            return None
        finally:
            if proc.poll() is None:
                self._return_process(module, proc)

    def close(self) -> None:
        """Close all Koka processes."""
        with self._lock:
            for module, procs in self._processes.items():
                for proc in procs:
                    try:
                        proc.terminate()
                        proc.wait(timeout=1.0)
                    except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
                        proc.kill()
            self._processes.clear()
            self._available.clear()


# Global bridge instance
_bridge: KokaNativeBridge | None = None
_bridge_lock = threading.Lock()


def get_koka_bridge() -> KokaNativeBridge:
    """Get or create the global Koka native bridge."""
    global _bridge
    if _bridge is None:
        with _bridge_lock:
            if _bridge is None:
                _bridge = KokaNativeBridge()
    return _bridge


def koka_dispatch(
    module: str,
    operation: str,
    args: dict[str, Any] | None = None,
    timeout: float = 5.0
) -> dict[str, Any] | None:
    """Convenience function to dispatch to Koka.

    Args:
        module: Koka module name
        operation: Effect operation
        args: Arguments dict (default: empty)
        timeout: Maximum wait time

    Returns:
        Response dict or None on failure
    """
    bridge = get_koka_bridge()
    return bridge.dispatch(module, operation, args or {}, timeout)


def koka_native_status() -> dict[str, Any]:
    """Get status of Koka native bridge.

    Returns:
        Dict with available modules, process counts, etc.
    """
    bridge = get_koka_bridge()

    # Also check hybrid dispatcher status
    hybrid_status = {}
    try:
        from whitemagic.core.acceleration.hybrid_dispatcher_v2 import get_dispatcher
        dispatcher = get_dispatcher()
        hybrid_status = {
            "available": True,
            "mode": dispatcher.mode.value,
            "stats": dispatcher.stats(),
        }
    except ImportError:
        hybrid_status = {"available": False, "reason": "not_installed"}

    with bridge._lock:
        return {
            "available_modules": list(bridge._binaries.keys()),
            "process_pools": {
                name: {
                    "total": len(procs),
                    "available": len(bridge._available.get(name, []))
                }
                for name, procs in bridge._processes.items()
            },
            "max_connections": bridge._max_connections,
            "hybrid_dispatcher": hybrid_status,
        }


def close_koka_bridge() -> None:
    """Close the global Koka bridge (cleanup)."""
    global _bridge
    if _bridge:
        _bridge.close()
        _bridge = None


# PRAT Router Integration
class KokaPratRouter:
    """Drop-in replacement for PRAT routing using Koka effects."""

    def __init__(self):
        self._bridge = get_koka_bridge()

    def route_via_koka(
        self,
        gana_name: str,
        tool_name: str,
        args: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Route a PRAT call through Koka handlers.

        Falls back to Python if Koka unavailable.
        """
        if not self._bridge.is_available("prat"):
            return None

        return koka_dispatch(
            "prat",
            "route-prat-call",
            {
                "gana": gana_name,
                "tool": tool_name,
                "args": args
            }
        )

    def get_resonance_via_koka(self, gana_name: str) -> dict[str, Any] | None:
        """Get resonance hints from Koka."""
        if not self._bridge.is_available("resonance"):
            return None

        return koka_dispatch(
            "resonance",
            "generate-hints",
            {"gana": gana_name}
        )


# Benchmark utilities
def benchmark_koka_dispatch(
    module: str,
    operation: str,
    args: dict[str, Any],
    iterations: int = 1000
) -> dict[str, Any]:
    """Benchmark Koka dispatch latency.

    Returns:
        Dict with min, max, avg, p50, p99 latencies in microseconds
    """
    bridge = get_koka_bridge()

    if not bridge.is_available(module):
        return {"error": f"Module {module} not available"}

    latencies: list[float] = []

    # Warmup
    for _ in range(10):
        bridge.dispatch(module, operation, args, timeout=5.0)

    # Benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        result = bridge.dispatch(module, operation, args, timeout=5.0)
        elapsed = (time.perf_counter() - start) * 1_000_000  # microseconds

        if result is not None:
            latencies.append(elapsed)

    if not latencies:
        return {"error": "All calls failed"}

    latencies.sort()
    n = len(latencies)

    return {
        "iterations": n,
        "min_us": latencies[0],
        "max_us": latencies[-1],
        "avg_us": sum(latencies) / n,
        "p50_us": latencies[n // 2],
        "p95_us": latencies[int(n * 0.95)],
        "p99_us": latencies[int(n * 0.99)],
    }
