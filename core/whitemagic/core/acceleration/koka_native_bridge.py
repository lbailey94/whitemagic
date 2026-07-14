# ruff: noqa: BLE001
"""Koka Native Bridge — Python ↔ Koka via compiled binaries (S023)
=============================================================
High-performance bridge using compiled Koka native binaries.
Faster than subprocess-per-call by using persistent processes.

Phase 5: Migrated to ProcessSupervisor for bounded, observable, supervised I/O.
Replaces manual process pooling, readline timeout, and circuit breaker with
the shared ProcessSupervisor abstraction.

Usage:
    from whitemagic.core.acceleration.koka_native_bridge import (
        KokaNativeBridge, koka_dispatch
    )

    result = koka_dispatch("prat", "route", {"tool": "memory.create"})
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, cast

from whitemagic.core.acceleration.process_supervisor import (
    ProcessSupervisor,
    register,
)

logger = logging.getLogger(__name__)

# Build paths
_BASE_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "polyglot"
    / "whitemagic-koka"
)
_BUILD_DIR = _BASE_DIR  # Binaries are in root, not .koka_build/native
_DISPATCHER_BIN = _BASE_DIR / "orchestrator"  # Use orchestrator as dispatcher

# Module-specific binaries (in whitemagic-koka/ root)
_MODULE_BINS = {
    "prat": _BASE_DIR / "prat",
    "resonance": _BASE_DIR / "resonance",
    "gan_ying": _BASE_DIR / "gan_ying",
    "gana": _BASE_DIR / "gan_ying",  # gan_ying handles gana operations
    "circuit": _BASE_DIR / "circuit",
    "circuit_dispatch": _BASE_DIR / "circuit_dispatch",  # stateful circuit breaker
    "backpressure": _BASE_DIR / "backpressure",  # stateful backpressure handler
    "transactions": _BASE_DIR / "transactions",  # stateful transaction handler
    "timeout": _BASE_DIR / "timeout",  # stateful timeout handler
    "retry": _BASE_DIR / "retry",  # stateful retry logic handler
    "session": _BASE_DIR / "unified_runtime_v3",  # unified runtime for sessions
    "resources": _BASE_DIR / "ring_buffer",
    "dream": _BASE_DIR / "dream_cycle",
    "metrics": _BASE_DIR / "metrics",
    "hot_paths": _BASE_DIR / "hot_paths",
    "shm_search": _BASE_DIR / "shm_search",
    "karmic": _BASE_DIR / "karmic_effects",  # MandalaOS Phase C: karmic effect enforcement
}


class KokaNativeBridge:
    """High-performance bridge to compiled Koka native binaries.

    Uses ProcessSupervisor per module for persistent, supervised subprocesses
    with circuit breakers, process leases, stderr draining, and stats.
    """

    def __init__(self, max_connections: int = 4):
        self._lock = threading.RLock()
        self._max_connections = max_connections
        self._supervisors: dict[str, ProcessSupervisor] = {}
        self._binaries: dict[str, Path] = {}

        self._check_binaries()

    def _check_binaries(self) -> None:
        """Verify which Koka binaries are available and create supervisors."""
        for name, path in _MODULE_BINS.items():
            if path.exists() and os.access(path, os.X_OK):
                self._binaries[name] = path
                if name not in self._supervisors:
                    self._supervisors[name] = ProcessSupervisor(
                        name=f"koka-{name}",
                        cmd=["stdbuf", "-o0", "-i0", str(path)],
                        binary_path=str(path),
                        max_processes=self._max_connections,
                        startup_timeout=5.0,
                        call_timeout=5.0,
                        skip_polyglot=True,
                    )
                    register(self._supervisors[name])
                logger.info("Koka binary available: %s", name)
            else:
                logger.debug("Koka binary not found: %s", path)

        if _DISPATCHER_BIN.exists() and os.access(_DISPATCHER_BIN, os.X_OK):
            self._binaries["dispatcher"] = _DISPATCHER_BIN
            if "dispatcher" not in self._supervisors:
                self._supervisors["dispatcher"] = ProcessSupervisor(
                    name="koka-dispatcher",
                    cmd=["stdbuf", "-o0", "-i0", str(_DISPATCHER_BIN)],
                    binary_path=str(_DISPATCHER_BIN),
                    max_processes=self._max_connections,
                    startup_timeout=5.0,
                    call_timeout=5.0,
                    skip_polyglot=True,
                )
                register(self._supervisors["dispatcher"])
            logger.info("Koka dispatcher available")

    def is_available(self, module: str) -> bool:
        """Check if a Koka module is available and healthy."""
        sup = self._supervisors.get(module)
        if sup is None:
            return False
        return sup.is_available()

    def dispatch(
        self, module: str, operation: str, args: dict[str, Any], timeout: float = 5.0
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
        sup = self._supervisors.get(module)
        if sup is None:
            logger.debug("Koka module not available: %s", module)
            return None

        request = {
            "module": module,
            "operation": operation,
            "args": args,
            "timestamp": time.time(),
        }
        result = sup.call(request, timeout=timeout)
        if result.ok and result.data:
            data = cast(dict[str, Any], result.data)
            data["_koka_latency_ms"] = result.latency_ms
            return data
        if result.fallback:
            logger.debug(
                "Koka dispatch fallback for %s.%s: %s", module, operation, result.error
            )
        return None

    def dispatch_line(
        self, module: str, command: str, timeout: float = 5.0
    ) -> str | None:
        """Dispatch a line-protocol command to a Koka native module.

        Args:
            module: Koka module name (e.g., "circuit", "backpressure")
            command: Line protocol command (e.g., "check:default", "admit:1")
            timeout: Maximum seconds to wait for response

        Returns:
            Raw response string (e.g., "ok:closed") or None on failure
        """
        sup = self._supervisors.get(module)
        if sup is None:
            logger.debug("Koka module not available: %s", module)
            return None

        result = sup.call_line(command, timeout=timeout)
        if result.ok and result.data:
            return result.data.get("response")
        return None

    def dispatch_karmic(
        self,
        tool: str,
        params: dict[str, Any],
        declared_effects: list[dict[str, Any]] | None = None,
        actual_effects: list[dict[str, Any]] | None = None,
        timeout: float = 5.0,
    ) -> dict[str, Any] | None:
        """Dispatch through Koka with effect tracking (MandalaOS Phase C).

        Sends declared and actual effect signatures to the Koka karmic_effects
        module, which compares them using Koka's type system and returns
        mismatch information + debt calculation.
        """
        args = {
            "tool": tool,
            "params": params,
            "declared": declared_effects or [],
            "actual": actual_effects or [],
        }
        return self.dispatch("karmic", "compare", args, timeout=timeout)

    def close(self) -> None:
        """Close all Koka processes."""
        with self._lock:
            for sup in self._supervisors.values():
                sup.close()
            self._supervisors.clear()

    def backpressure_admit(self, priority: int = 0) -> bool | None:
        """Request admission under backpressure control."""
        resp = self.dispatch_line("backpressure", f"admit:{priority}")
        if resp and resp.startswith("ok:"):
            return resp == "ok:true"
        return None

    def backpressure_should_shed(self) -> bool | None:
        """Check if load shedding is needed."""
        resp = self.dispatch_line("backpressure", "should-shed")
        if resp and resp.startswith("ok:"):
            return resp == "ok:true"
        return None

    def backpressure_current_load(self) -> float | None:
        """Get current load factor (0.0-1.0)."""
        resp = self.dispatch_line("backpressure", "current-load")
        if resp and resp.startswith("ok:"):
            try:
                return float(resp[3:])
            except ValueError:
                return None
        return None

    def backpressure_set_threshold(self, threshold: float) -> bool:
        """Set the load shedding threshold."""
        resp = self.dispatch_line("backpressure", f"set-threshold:{threshold}")
        return resp == "ok:set"

    def timeout_set(self, ms: int) -> bool:
        """Set the timeout duration in milliseconds."""
        resp = self.dispatch_line("timeout", f"set:{ms}")
        return resp == "ok:set"

    def timeout_get(self) -> int | None:
        """Get the current timeout in milliseconds."""
        resp = self.dispatch_line("timeout", "get")
        if resp and resp.startswith("ok:"):
            try:
                return int(resp[3:])
            except ValueError:
                return None
        return None

    def timeout_is_timed_out(self) -> bool | None:
        """Check if the timeout has been reached."""
        resp = self.dispatch_line("timeout", "is-timed-out")
        if resp and resp.startswith("ok:"):
            return resp == "ok:true"
        return None

    def timeout_time_remaining(self) -> int | None:
        """Get remaining time in milliseconds."""
        resp = self.dispatch_line("timeout", "time-remaining")
        if resp and resp.startswith("ok:"):
            try:
                return int(resp[3:])
            except ValueError:
                return None
        return None

    def retry_attempt(self, description: str = "") -> int | None:
        """Record a retry attempt, returns attempt count."""
        resp = self.dispatch_line("retry", f"attempt:{description}")
        if resp and resp.startswith("ok:"):
            try:
                return int(resp[3:])
            except ValueError:
                return None
        return None

    def retry_should_retry(self) -> bool | None:
        """Check if another retry should be attempted."""
        resp = self.dispatch_line("retry", "should-retry")
        if resp and resp.startswith("ok:"):
            return resp == "ok:true"
        return None

    def retry_backoff_delay(self) -> int | None:
        """Get the current backoff delay in milliseconds."""
        resp = self.dispatch_line("retry", "backoff-delay")
        if resp and resp.startswith("ok:"):
            try:
                return int(resp[3:])
            except ValueError:
                return None
        return None

    def retry_set_strategy(
        self, strategy: str, base_ms: int = 100, max_ms: int = 30000
    ) -> bool:
        """Set the backoff strategy (e.g., 'exponential', 'linear')."""
        resp = self.dispatch_line(
            "retry", f"set-strategy:{strategy}:{base_ms}:{max_ms}"
        )
        return resp == "ok:set"

    def transaction_begin(self) -> str | None:
        """Begin a new transaction, returns transaction ID."""
        resp = self.dispatch_line("transactions", "begin")
        if resp and resp.startswith("ok:"):
            return resp[3:]
        return None

    def transaction_commit(self, tx_id: str) -> bool:
        """Commit a transaction."""
        resp = self.dispatch_line("transactions", f"commit:{tx_id}")
        return resp == "ok:true"

    def transaction_rollback(self, tx_id: str) -> bool:
        """Rollback a transaction."""
        resp = self.dispatch_line("transactions", f"rollback:{tx_id}")
        return resp == "ok:true"

    def transaction_status(self, tx_id: str) -> str | None:
        """Get transaction status (active, committed, rolled_back, unknown)."""
        resp = self.dispatch_line("transactions", f"status:{tx_id}")
        if resp and resp.startswith("ok:"):
            return resp[3:]
        return None

    def health_check(self) -> dict[str, Any]:
        """Return health check for all Koka modules."""
        modules = {}
        for name, sup in self._supervisors.items():
            modules[name] = sup.health_check()
        return {
            "available_modules": list(self._binaries.keys()),
            "max_connections": self._max_connections,
            "modules": modules,
        }


# Global bridge instance
_bridge: KokaNativeBridge | None = None
_bridge_lock = threading.RLock()


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
    timeout: float = 5.0,
) -> dict[str, Any] | None:
    """Convenience function to dispatch to Koka."""
    bridge = get_koka_bridge()
    return bridge.dispatch(module, operation, args or {}, timeout)


def koka_native_status() -> dict[str, Any]:
    """Get status of Koka native bridge."""
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
                    "total": len(sup._processes),
                    "available": len(sup._available),
                    "health": sup.health_state.value,
                    "stats": sup.stats.to_dict(),
                }
                for name, sup in bridge._supervisors.items()
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
        self, gana_name: str, tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Route a PRAT call through Koka handlers."""
        if not self._bridge.is_available("prat"):
            return None

        return koka_dispatch(
            "prat",
            "route-prat-call",
            {"gana": gana_name, "tool": tool_name, "args": args},
        )

    def get_resonance_via_koka(self, gana_name: str) -> dict[str, Any] | None:
        """Get resonance hints from Koka."""
        if not self._bridge.is_available("resonance"):
            return None

        return koka_dispatch("resonance", "generate-hints", {"gana": gana_name})


# Benchmark utilities
def benchmark_koka_dispatch(
    module: str, operation: str, args: dict[str, Any], iterations: int = 1000
) -> dict[str, Any]:
    """Benchmark Koka dispatch latency."""
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


class KokaCircuitDispatch:
    """Python bridge to the Koka circuit_dispatch binary.

    Uses ProcessSupervisor with line protocol for supervised I/O.
    State is maintained inside the Koka handler scope, so circuit
    breaker state persists across calls within the same process.

    Protocol: "op:name:args"
    Response: "ok:result" or "error:message"
    """

    _instance: KokaCircuitDispatch | None = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._supervisor: ProcessSupervisor | None = None

    @classmethod
    def get_instance(cls) -> KokaCircuitDispatch:
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = KokaCircuitDispatch()
        return cls._instance

    def _get_supervisor(self) -> ProcessSupervisor:
        if self._supervisor is None:
            self._supervisor = ProcessSupervisor(
                name="koka-circuit-dispatch",
                cmd=["stdbuf", "-o0", "-i0", str(_BASE_DIR / "circuit_dispatch")],
                binary_path=str(_BASE_DIR / "circuit_dispatch"),
                startup_timeout=5.0,
                call_timeout=5.0,
                skip_polyglot=True,
            )
            register(self._supervisor)
        return self._supervisor

    def _send(self, line: str) -> str | None:
        """Send a line and read the response."""
        result = self._get_supervisor().call_line(line)
        if result.ok and result.data:
            return result.data.get("response")
        return None

    def check(self, name: str) -> str:
        """Check circuit state. Returns 'closed', 'open', or 'half-open'."""
        resp = self._send(f"check:{name}")
        if resp and resp.startswith("ok:"):
            return resp[3:]
        return "closed"  # safe default

    def record_success(self, name: str) -> bool:
        resp = self._send(f"success:{name}")
        return resp == "ok:recorded"

    def record_failure(self, name: str) -> bool:
        resp = self._send(f"failure:{name}")
        return resp == "ok:recorded"

    def reset(self, name: str) -> bool:
        resp = self._send(f"reset:{name}")
        return resp == "ok:reset"

    def configure(
        self, name: str, threshold: int, timeout_ms: int, half_open_max: int
    ) -> bool:
        resp = self._send(f"configure:{name}:{threshold}:{timeout_ms}:{half_open_max}")
        return resp == "ok:configured"

    def is_open(self, name: str) -> bool:
        return self.check(name) == "open"

    def close(self) -> None:
        if self._supervisor is not None:
            self._supervisor.close()
            self._supervisor = None
