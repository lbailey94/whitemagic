"""Enhanced Hybrid Adaptive Dispatcher with runtime adaptation, batching, and pooling.

Features:
- Runtime latency monitoring with auto-switch
- Batch operations for chained Koka calls
- Process pooling for parallel operations
- Warm start for pre-initializing Koka processes
- Integration-ready API
"""

import json
import logging
import queue
import subprocess
import threading
import time
from collections import deque
from collections.abc import Generator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast

import whitemagic_rust as rs

logger = logging.getLogger(__name__)

KOKA_DIR = Path(__file__).parent.parent.parent.parent / "whitemagic-koka"
_DEFAULT_PARALLEL_CALL_TIMEOUT_S = 8.0
_DEFAULT_KOKA_PROCESS_TIMEOUT_S = 5.0


class DispatchMode(Enum):
    """DispatchMode: dispatch mode.
    
    Enumeration.
    
    Members:
        SPEED
        SAFETY
        ADAPTIVE"""
    SPEED = "speed"      # Python in-memory only
    SAFETY = "safety"    # Koka IPC only
    ADAPTIVE = "adaptive"  # Choose based on complexity + runtime perf


@dataclass
class LatencyStats:
    """Rolling latency statistics for runtime adaptation."""
    samples: deque = field(default_factory=lambda: deque(maxlen=100))
    total_calls: int = 0
    total_time_us: float = 0.0

    def record(self, latency_us: float) -> None:
        """
        Perform the record operation.
        
        Args:
            latency_us: Parameter description.
        
        Returns:
            None
        """
        self.samples.append(latency_us)
        self.total_calls += 1
        self.total_time_us += latency_us

    def avg_us(self) -> float:
        """
        Perform the avg us operation.
        
        Returns:
            float
        """
        if not self.samples:
            return 0.0
        return float(sum(self.samples) / len(self.samples))

    def p95_us(self) -> float:
        """
        Perform the p95 us operation.
        
        Returns:
            float
        """
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * 0.95)
        return float(sorted_samples[min(idx, len(sorted_samples) - 1)])


@dataclass
class OperationProfile:
    """Profile for operation complexity."""
    name: str
    has_state: bool
    has_effects: bool
    chain_benefit: bool
    base_complexity: float  # 0.0-1.0
    latency_stats: LatencyStats = field(default_factory=LatencyStats)

    @property
    def complexity_score(self) -> float:
        """Dynamic complexity based on runtime performance."""
        # If Koka is slow (>100µs), reduce complexity score to prefer Python
        avg = self.latency_stats.avg_us()
        if avg > 100:
            return self.base_complexity * 0.5
        elif avg > 50:
            return self.base_complexity * 0.8
        return self.base_complexity


# Predefined operation profiles
OPERATION_PROFILES = {
    # Simple lookups - Python fast path
    "prat_route": OperationProfile("prat_route", False, False, False, 0.1),
    "resonance_predecessor": OperationProfile("resonance_predecessor", False, False, False, 0.1),
    "resonance_successor": OperationProfile("resonance_successor", False, False, False, 0.1),

    # Stateful operations - Koka safe path
    "circuit_check": OperationProfile("circuit_check", True, True, False, 0.6),
    "circuit_record": OperationProfile("circuit_record", True, True, False, 0.7),
    "dream_phase": OperationProfile("dream_phase", True, True, True, 0.9),
    "dream_run": OperationProfile("dream_run", True, True, True, 0.95),
}


class PythonFastPath:
    """Python in-memory implementations for simple operations."""

    TOOL_TO_GANA = {
        "search_memories": "gana_winnowing_basket",
        "gnosis": "gana_ghost",
        "health_report": "gana_horn",
        "create_memory": "gana_heart",
        "cluster_stats": "gana_dipper",
        "consolidate": "gana_abundance",
        "synthesize": "gana_three_stars",
    }

    GANA_ORDER = [
        "gana_horn", "gana_neck", "gana_root", "gana_room", "gana_heart",
        "gana_tail", "gana_winnowing_basket", "gana_ghost", "gana_willow",
        "gana_star", "gana_extended_net", "gana_wings", "gana_chariot",
        "gana_abundance", "gana_straddling_legs", "gana_mound", "gana_stomach",
        "gana_hairy_head", "gana_net", "gana_turtle_beak", "gana_three_stars",
        "gana_dipper", "gana_ox", "gana_girl", "gana_void", "gana_roof",
        "gana_encampment", "gana_wall"
    ]
    GANA_INDEX = {name: i for i, name in enumerate(GANA_ORDER)}

    circuit_state = {"state": "closed", "failures": 0, "successes": 0, "threshold": 5}
    dream_state = {"phase": "dormant", "cycles": 0, "memories": 0, "insights": 0}

    @classmethod
    def prat_route(cls, tool: str) -> str:
        """
        Perform the prat route operation.
        
        Args:
            cls: Parameter description.
            tool: Parameter description.
        
        Returns:
            str
        """
        try:
            from whitemagic.optimization import rust_accelerators
            if hasattr(rust_accelerators, "prat_route"):
                return str(rust_accelerators.prat_route(tool))
            return cls.TOOL_TO_GANA.get(tool, "gana_ghost")
        except (ImportError, ModuleNotFoundError):
            return cls.TOOL_TO_GANA.get(tool, "gana_ghost")

    @classmethod
    def get_predecessor(cls, gana: str) -> str:
        """
        Get the predecessor.
        
        Args:
            cls: Parameter description.
            gana: Parameter description.
        
        Returns:
            str
        """
        try:
            from whitemagic.optimization import rust_accelerators
            if hasattr(rust_accelerators, "resonance_predecessor"):
                return str(rust_accelerators.resonance_predecessor(gana))
            idx = cls.GANA_INDEX.get(gana, 0)
            return cls.GANA_ORDER[(idx - 1) % 28]
        except (ImportError, ModuleNotFoundError):
            idx = cls.GANA_INDEX.get(gana, 0)
            return cls.GANA_ORDER[(idx - 1) % 28]

    @classmethod
    def get_successor(cls, gana: str) -> str:
        """
        Get the successor.
        
        Args:
            cls: Parameter description.
            gana: Parameter description.
        
        Returns:
            str
        """
        try:
            from whitemagic.optimization import rust_accelerators
            if hasattr(rust_accelerators, "resonance_successor"):
                return str(rust_accelerators.resonance_successor(gana))
            idx = cls.GANA_INDEX.get(gana, 0)
            return cls.GANA_ORDER[(idx + 1) % 28]
        except (ImportError, ModuleNotFoundError):
            idx = cls.GANA_INDEX.get(gana, 0)
            return cls.GANA_ORDER[(idx + 1) % 28]

    @classmethod
    def circuit_check(cls) -> str:
        """
        Perform the circuit check operation.
        
        Args:
            cls: Parameter description.
        
        Returns:
            str
        """
        return cast(str, cls.circuit_state["state"])

    @classmethod
    def circuit_record_success(cls) -> str:
        """
        Perform the circuit record success operation.
        
        Args:
            cls: Parameter description.
        
        Returns:
            str
        """
        successes = cast(int, cls.circuit_state["successes"])
        cls.circuit_state["successes"] = successes + 1
        if cls.circuit_state["state"] == "half-open" and cast(int, cls.circuit_state["successes"]) >= 3:
            cls.circuit_state["state"] = "closed"
            cls.circuit_state["failures"] = 0
        return "ok"

    @classmethod
    def circuit_record_failure(cls) -> str:
        """
        Perform the circuit record failure operation.
        
        Args:
            cls: Parameter description.
        
        Returns:
            str
        """
        failures = cast(int, cls.circuit_state["failures"])
        cls.circuit_state["failures"] = failures + 1
        threshold = cast(int, cls.circuit_state["threshold"])
        if cls.circuit_state["state"] == "closed" and cast(int, cls.circuit_state["failures"]) >= threshold:
            cls.circuit_state["state"] = "open"
        elif cls.circuit_state["state"] == "half-open":
            cls.circuit_state["state"] = "open"
        return "ok"


class KokaProcess:
    """Manages a persistent Koka IPC process with health tracking."""

    def __init__(self, binary_name: str, pool_id: int = 0):
        self.binary_name = binary_name
        self.binary_path = KOKA_DIR / binary_name
        self.pool_id = pool_id
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._healthy = True
        self._call_count = 0
        self._last_error: str | None = None

    def start(self) -> bool:
        """Start the persistent process. Returns True if started."""
        with self._lock:
            if self._proc is None and self.binary_path.exists():
                try:
                    self._proc = subprocess.Popen(
                        [str(self.binary_path)],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    return True
                except Exception as e:
                    self._healthy = False
                    self._last_error = str(e)
                    return False
        return self._proc is not None

    def _readline_with_timeout(self, timeout: float = _DEFAULT_KOKA_PROCESS_TIMEOUT_S) -> str | None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return None

        result_queue: queue.Queue[str | None] = queue.Queue(maxsize=1)

        def _reader() -> None:
            try:
                # Use local reference to avoid None check after start
                stdout = proc.stdout
                if stdout is not None:
                    result_queue.put(stdout.readline())
                else:
                    result_queue.put(None)
            except (OSError, ValueError) as e:
                logger.debug("Koka stdout read failed: %s", e)
                result_queue.put(None)

        thread = threading.Thread(target=_reader, name=f"hybrid-koka-{self.binary_name}-{self.pool_id}", daemon=True)
        thread.start()

        try:
            return result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _reset_process(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=1.0)
            except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
                try:
                    self._proc.kill()
                except (ProcessLookupError, OSError):
                    pass
        self._proc = None

    def call(self, request: dict) -> dict:
        """Send request and get response."""
        with self._lock:
            proc = self._proc
            if proc is None:
                if not self.start():
                    return {"error": "Process not available", "healthy": False}
                proc = self._proc

            if proc is None or proc.stdin is None:
                return {"error": "Process or stdin not available", "healthy": False}

            try:
                proc.stdin.write(json.dumps(request) + '\n')
                proc.stdin.flush()
                response = self._readline_with_timeout()
                self._call_count += 1
                if response:
                    return cast(dict, json.loads(response))
                self._healthy = False
                self._last_error = "timeout/no response"
                self._reset_process()
                return {"error": "no response", "healthy": False}
            except (json.JSONDecodeError, TypeError) as e:
                self._healthy = False
                self._last_error = str(e)
                self._reset_process()
                return {"error": str(e), "healthy": False}

    def batch(self, requests: list[dict]) -> list[dict]:
        """Send multiple requests in sequence (single IPC overhead)."""
        results = []
        with self._lock:
            proc = self._proc
            if proc is None and not self.start():
                return [{"error": "Process not available"} for _ in requests]

            proc = self._proc
            if proc is None or proc.stdin is None:
                return [{"error": "Process or stdin not available"} for _ in requests]

            try:
                for req in requests:
                    proc.stdin.write(json.dumps(req) + '\n')
                    proc.stdin.flush()
                    response = self._readline_with_timeout()
                    if response:
                        results.append(json.loads(response))
                    else:
                        self._healthy = False
                        self._last_error = "timeout/no response"
                        self._reset_process()
                        results.append({"error": "no response"})
                    self._call_count += 1
            except Exception as e:
                self._healthy = False
                self._last_error = str(e)
                self._reset_process()
                # Fill remaining with errors
                while len(results) < len(requests):
                    results.append({"error": str(e)})

        return results

    @property
    def is_healthy(self) -> bool:
        """
        Check whether the healthy condition holds.
        
        Returns:
            bool
        """
        return self._healthy and self._proc is not None

    def stop(self) -> None:
        """
        Perform the stop operation.
        
        Returns:
            None
        """
        with self._lock:
            if self._proc:
                try:
                    self._proc.terminate()
                except OSError as e:
                    logger.debug("Koka process terminate failed: %s", e)
                self._proc = None
            self._healthy = False

    def stats(self) -> dict:
        """
        Perform the stats operation.
        
        Returns:
            dict
        """
        return {
            "binary": self.binary_name,
            "pool_id": self.pool_id,
            "healthy": self._healthy,
            "call_count": self._call_count,
            "last_error": self._last_error,
        }


class KokaProcessPool:
    """Pool of Koka processes for parallel execution."""

    def __init__(self, binary_name: str, pool_size: int = 2):
        self.binary_name = binary_name
        self.pool_size = pool_size
        self._processes: list[KokaProcess] = []
        self._executor = ThreadPoolExecutor(max_workers=pool_size)
        self._current_idx = 0
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start all processes in pool."""
        for i in range(self.pool_size):
            proc = KokaProcess(self.binary_name, pool_id=i)
            proc.start()
            self._processes.append(proc)

    def call(self, request: dict) -> dict:
        """Route to next available process (round-robin)."""
        with self._lock:
            if not self._processes:
                self.start()

            # Find healthy process
            for _ in range(len(self._processes)):
                proc = self._processes[self._current_idx]
                self._current_idx = (self._current_idx + 1) % len(self._processes)
                if proc.is_healthy:
                    return proc.call(request)

            # All unhealthy, try restart
            for proc in self._processes:
                proc.start()
                if proc.is_healthy:
                    return proc.call(request)

            return {"error": "No healthy processes"}

    def call_parallel(self, requests: list[dict]) -> list[dict]:
        """Execute multiple requests in parallel across pool."""
        if not self._processes:
            self.start()

        futures: list[tuple[int, Future]] = []
        results: list[Any] = [None] * len(requests)

        for i, req in enumerate(requests):
            proc_idx = i % len(self._processes)
            future = self._executor.submit(self._processes[proc_idx].call, req)
            futures.append((i, future))

        for i, future in futures:
            try:
                results[i] = future.result(timeout=_DEFAULT_PARALLEL_CALL_TIMEOUT_S)
            except Exception as e:
                results[i] = {"error": f"parallel call failed: {e}"}

        return cast(list[dict], results)

    def stop(self) -> None:
        """
        Perform the stop operation.
        
        Returns:
            None
        """
        for proc in self._processes:
            proc.stop()
        self._processes.clear()
        self._executor.shutdown(wait=False)

    def stats(self) -> dict:
        """
        Perform the stats operation.
        
        Returns:
            dict
        """
        return {
            "binary": self.binary_name,
            "pool_size": self.pool_size,
            "processes": [p.stats() for p in self._processes],
        }


class HybridDispatcherV2:
    """Enhanced adaptive dispatcher with runtime adaptation, batching, and pooling."""

    def __init__(
        self,
        mode: DispatchMode = DispatchMode.ADAPTIVE,
        pool_size: int = 2,
        warm_start: bool = True,
        latency_threshold_us: float = 100.0,
        enable_predictive_warm: bool = True,
    ):
        self.mode = mode
        self.pool_size = pool_size
        self.latency_threshold = latency_threshold_us
        self.enable_predictive_warm = enable_predictive_warm

        self._koka_pools: dict[str, KokaProcessPool] = {}
        self._python_stats = LatencyStats()
        self._koka_stats = LatencyStats()
        self._warm_started = False

        # Predictive pre-warming state
        self._operation_history: deque = deque(maxlen=50)
        self._predicted_binaries: set[str] = set()

        # Circuit breaker fallback state
        self._koka_healthy = True
        self._koka_failure_count = 0
        self._koka_failure_threshold = 3
        self._fallback_mode = False

        if warm_start:
            self._do_warm_start()

    def _do_warm_start(self) -> None:
        """Pre-initialize Koka processes for common binaries."""
        if self._warm_started:
            return

        # Start pools for commonly used binaries
        for binary in ["circuit", "resonance", "dream_cycle", "gan_ying", "hot_paths", "unified_runtime"]:
            pool = KokaProcessPool(binary, pool_size=self.pool_size)
            pool.start()
            self._koka_pools[binary] = pool

        self._warm_started = True

    def _predict_next_binaries(self, operation: str) -> list[str]:
        """Predict which binaries will likely be needed next based on operation patterns."""
        # Operation -> likely next binaries mapping
        prediction_map = {
            "prat_route": ["resonance"],
            "resonance_predecessor": ["resonance", "circuit"],
            "resonance_successor": ["resonance", "circuit"],
            "circuit_check": ["circuit", "dream_cycle"],
            "circuit_record": ["circuit"],
            "dream_phase": ["dream_cycle", "gan_ying"],
            "dream_run": ["dream_cycle", "gan_ying", "hot_paths"],
        }

        # Record operation for pattern analysis
        self._operation_history.append(operation)

        # Get predicted binaries
        predicted = prediction_map.get(operation, [])

        # Also analyze recent history for patterns
        if len(self._operation_history) >= 3:
            recent = list(self._operation_history)[-3:]
            # If we see circuit ops followed by dream ops, pre-warm unified_runtime
            if any("circuit" in op for op in recent) and any("dream" in op for op in recent):
                predicted.append("unified_runtime")

        return predicted

    def _pre_warm_binaries(self, binaries: list[str]) -> None:
        """Pre-warm predicted binaries if not already warm."""
        if not self.enable_predictive_warm:
            return

        for binary in binaries:
            if binary not in self._koka_pools:
                pool = KokaProcessPool(binary, pool_size=1)  # Single process for predicted
                pool.start()
                self._koka_pools[binary] = pool

    def _check_koka_health(self) -> bool:
        """Check if Koka processes are healthy, update fallback mode."""
        if self._fallback_mode:
            # Check if we can recover
            if self._koka_failure_count == 0:
                self._fallback_mode = False
                self._koka_healthy = True
                return True
            return False

        # Check pool health
        healthy_pools = 0
        total_pools = len(self._koka_pools)

        for pool in self._koka_pools.values():
            if pool._processes and all(p.is_healthy for p in pool._processes):
                healthy_pools += 1

        self._koka_healthy = healthy_pools > 0 or total_pools == 0
        return self._koka_healthy

    def _record_koka_failure(self) -> None:
        """Record Koka failure for circuit breaker."""
        self._koka_failure_count += 1
        if self._koka_failure_count >= self._koka_failure_threshold:
            self._fallback_mode = True
            self._koka_healthy = False

    def _record_koka_success(self) -> None:
        """Record Koka success for circuit breaker recovery."""
        if self._koka_failure_count > 0:
            self._koka_failure_count -= 1

    def _should_use_koka(self, operation: str) -> bool:
        """Decide whether to use Koka based on mode, complexity, and runtime perf."""
        # Check circuit breaker fallback
        if self._fallback_mode:
            # Only use Koka for critical operations in fallback mode
            profile = OPERATION_PROFILES.get(operation)
            if profile and profile.base_complexity > 0.9:
                # Critical operation, try Koka anyway but with fallback
                pass
            else:
                return False


        if self.mode == DispatchMode.SPEED:
            return False
        if self.mode == DispatchMode.SAFETY:
            return True

        # Adaptive: consider complexity and runtime latency
        profile = OPERATION_PROFILES.get(operation)
        if profile:
            # Check if Koka is performing well
            koka_avg = self._koka_stats.avg_us()
            if koka_avg > self.latency_threshold:
                # Koka is slow, prefer Python for non-critical ops
                return profile.complexity_score > 0.8
            return profile.complexity_score > 0.5
        return False

    def _get_pool(self, binary: str) -> KokaProcessPool:
        """Get or create process pool for binary."""
        if binary not in self._koka_pools:
            pool = KokaProcessPool(binary, pool_size=self.pool_size)
            pool.start()
            self._koka_pools[binary] = pool
        return self._koka_pools[binary]

    def _record_latency(self, is_koka: bool, latency_us: float, operation: str, success: bool = True) -> None:
        """Record latency for runtime adaptation."""
        if is_koka:
            self._koka_stats.record(latency_us)
            if operation in OPERATION_PROFILES:
                OPERATION_PROFILES[operation].latency_stats.record(latency_us)
            if success:
                self._record_koka_success()
            else:
                self._record_koka_failure()
        else:
            self._python_stats.record(latency_us)

        # Predictive pre-warming
        predicted = self._predict_next_binaries(operation)
        self._pre_warm_binaries(predicted)

    # ── PRAT Routing ─────────────────────────────────────────────────────────

    def prat_route(self, tool: str) -> str:
        """
        Perform the prat route operation.
        
        Args:
            tool: Parameter description.
        
        Returns:
            str
        """
        operation = "prat_route"
        start = time.perf_counter()

        try:
            prat_route_fn = getattr(rs, "prat_route", None)
            if prat_route_fn:
                result = str(prat_route_fn(tool))
            else:
                result = PythonFastPath.prat_route(tool)
        except Exception as e:
            logger.debug("Rust prat_route fallback: %s", e)
            result = PythonFastPath.prat_route(tool)

        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(False, latency, operation)
        return result

    def prat_route_batch(self, tools: list[str]) -> list[str]:
        """Route multiple tools in batch"""
        start = time.perf_counter()
        try:
            prat_route_batch_fn = getattr(rs, "prat_route_batch", None)
            if prat_route_batch_fn:
                results = cast(list[str], prat_route_batch_fn(tools))
            else:
                results = [PythonFastPath.prat_route(t) for t in tools]
        except Exception as e:
            logger.debug("Rust prat_route_batch fallback: %s", e)
            results = [PythonFastPath.prat_route(t) for t in tools]

        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(False, latency / max(1, len(tools)), "prat_route")
        return results

    # ── Resonance ───────────────────────────────────────────────────────────

    def get_predecessor(self, gana: str) -> str:
        """
        Get the predecessor.
        
        Args:
            gana: Parameter description.
        
        Returns:
            str
        """
        operation = "resonance_predecessor"
        start = time.perf_counter()
        try:
            resonance_predecessor_fn = getattr(rs, "resonance_predecessor", None)
            if resonance_predecessor_fn:
                result = str(resonance_predecessor_fn(gana))
            else:
                result = PythonFastPath.get_predecessor(gana)
        except Exception as e:
            logger.debug("Rust resonance_predecessor fallback: %s", e)
            result = PythonFastPath.get_predecessor(gana)

        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(False, latency, operation)
        return result

    def get_successor(self, gana: str) -> str:
        """
        Get the successor.
        
        Args:
            gana: Parameter description.
        
        Returns:
            str
        """
        operation = "resonance_successor"
        start = time.perf_counter()
        try:
            resonance_successor_fn = getattr(rs, "resonance_successor", None)
            if resonance_successor_fn:
                result = str(resonance_successor_fn(gana))
            else:
                result = PythonFastPath.get_successor(gana)
        except Exception as e:
            logger.debug("Rust resonance_successor fallback: %s", e)
            result = PythonFastPath.get_successor(gana)

        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(False, latency, operation)
        return result

    # ── Circuit Breaker ─────────────────────────────────────────────────────

    def circuit_check(self) -> str:
        """
        Perform the circuit check operation.
        
        Returns:
            str
        """
        operation = "circuit_check"
        use_koka = self._should_use_koka(operation)

        start = time.perf_counter()
        if use_koka:
            result_dict = self._get_pool("circuit").call({"op": "check"})
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(True, latency, operation)
            return cast(str, result_dict.get("state", "closed"))
        else:
            result_str = PythonFastPath.circuit_check()
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(False, latency, operation)
            return result_str

    def circuit_record_failure(self) -> str:
        """
        Perform the circuit record failure operation.
        
        Returns:
            str
        """
        operation = "circuit_record"
        use_koka = self._should_use_koka(operation)

        start = time.perf_counter()
        if use_koka:
            result_dict = self._get_pool("circuit").call({"op": "failure"})
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(True, latency, operation)
            return cast(str, result_dict.get("result", "ok"))
        else:
            result_str = PythonFastPath.circuit_record_failure()
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(False, latency, operation)
            return result_str

    def circuit_record_success(self) -> str:
        """
        Perform the circuit record success operation.
        
        Returns:
            str
        """
        operation = "circuit_record"
        use_koka = self._should_use_koka(operation)

        start = time.perf_counter()
        if use_koka:
            res = self._get_pool("circuit").call({"op": "success"})
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(True, latency, operation)
            return str(res.get("result", "ok"))
        else:
            res_str = PythonFastPath.circuit_record_success()
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(False, latency, operation)
            return res_str

    # ── Dream Cycle ─────────────────────────────────────────────────────────

    def dream_run(self) -> dict:
        """Run dream cycle (always Koka for effect handling)."""
        start = time.perf_counter()
        result = self._get_pool("dream_cycle").call({"op": "run"})
        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(True, latency, "dream_run")
        return result

    def dream_status(self) -> dict:
        """
        Perform the dream status operation.
        
        Returns:
            dict
        """
        start = time.perf_counter()
        result = self._get_pool("dream_cycle").call({"op": "status"})
        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(True, latency, "dream_phase")
        return result

    # ── Batch Operations ─────────────────────────────────────────────────────

    def batch_circuit_ops(self, operations: list[dict]) -> list[dict]:
        """Execute multiple circuit operations in batch.

        operations: [{"op": "check"}, {"op": "failure"}, {"op": "success"}, ...]
        """
        start = time.perf_counter()
        results = self._get_pool("circuit").call_parallel(operations)
        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(True, latency / len(operations), "circuit_check")
        return results

    def batch_resonance(self, ganas: list[str]) -> list[dict]:
        """Get predecessor/successor for multiple ganas in batch."""
        requests = []
        for gana in ganas:
            requests.append({"op": "predecessor", "gana": gana})
            requests.append({"op": "successor", "gana": gana})

        start = time.perf_counter()
        results = self._get_pool("resonance").call_parallel(requests)
        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(True, latency / len(ganas), "resonance_predecessor")

        # Pair up results
        paired = []
        for i in range(0, len(results), 2):
            paired.append({
                "gana": ganas[i // 2],
                "predecessor": results[i].get("predecessor", "gana_horn"),
                "successor": results[i + 1].get("successor", "gana_horn"),
            })
        return paired

    # ── Lifecycle ────────────────────────────────────────────────────────────

    @contextmanager
    def session(self) -> Generator["HybridDispatcherV2", None, None]:
        """Context manager for session with cleanup."""
        try:
            yield self
        finally:
            self.close()

    def close(self) -> None:
        """Close all Koka process pools."""
        for pool in self._koka_pools.values():
            pool.stop()
        self._koka_pools.clear()

    def stats(self) -> dict:
        """Get comprehensive statistics."""
        return {
            "python": {
                "total_calls": self._python_stats.total_calls,
                "avg_us": self._python_stats.avg_us(),
                "p95_us": self._python_stats.p95_us(),
            },
            "koka": {
                "total_calls": self._koka_stats.total_calls,
                "avg_us": self._koka_stats.avg_us(),
                "p95_us": self._koka_stats.p95_us(),
                "healthy": self._koka_healthy,
                "failure_count": self._koka_failure_count,
                "fallback_mode": self._fallback_mode,
            },
            "pools": {name: pool.stats() for name, pool in self._koka_pools.items()},
            "mode": self.mode.value,
            "warm_started": self._warm_started,
            "predictive_warm": self.enable_predictive_warm,
            "predicted_binaries": list(self._predicted_binaries),
        }

    # Unified Fast Brain Hook
    def check_unified_fast_brain(self) -> dict:
        """Poll the Unified Fast Brain for its status via Elixir or direct Koka check."""
        try:
            from whitemagic.core.acceleration.koka_native_bridge import get_koka_bridge
            b = get_koka_bridge()
            if "unified_fast_brain" in b._binaries:
                return {"active": True, "shm_ring": True}
        except (ImportError, ModuleNotFoundError):
            pass
        return {"active": False}

    def health_check(self) -> dict:
        """Check health of all Koka processes."""
        healthy = True
        details = {}

        for name, pool in self._koka_pools.items():
            pool_healthy = all(p.is_healthy for p in pool._processes)
            details[name] = {
                "healthy": pool_healthy,
                "processes": len(pool._processes),
            }
            if not pool_healthy:
                healthy = False

        return {
            "overall_healthy": healthy,
            "pools": details,
            "python_available": True,
            "fast_brain": self.check_unified_fast_brain()
        }


# ── Global Instance ────────────────────────────────────────────────────────

_dispatcher: HybridDispatcherV2 | None = None


def get_dispatcher(
    mode: DispatchMode = DispatchMode.ADAPTIVE,
    pool_size: int = 2,
    warm_start: bool = True,
) -> HybridDispatcherV2:
    """Get or create the global dispatcher."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = HybridDispatcherV2(mode, pool_size, warm_start)
    return _dispatcher


def set_mode(mode: DispatchMode) -> None:
    """Set the dispatch mode."""
    global _dispatcher
    if _dispatcher:
        _dispatcher.mode = mode
    else:
        _dispatcher = HybridDispatcherV2(mode)


def reset_dispatcher() -> None:
    """Reset the global dispatcher."""
    global _dispatcher
    if _dispatcher:
        _dispatcher.close()
    _dispatcher = None
