"""Hybrid Adaptive Dispatcher - Switches between Python in-memory and Koka IPC.

Strategy:
- Simple lookups (routing, predecessor): Python in-memory (sub-µs)
- Complex state (circuit breaker, dream cycle): Koka IPC (type-safe, effect-handled)
- Chained operations: Koka persistent process (shared state across calls)

Mode selection:
- "speed": Always use Python in-memory
- "safety": Always use Koka IPC
- "adaptive": Choose based on operation complexity (default)
"""

import queue
import subprocess
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
import logging
logger = logging.getLogger(__name__)

KOKA_DIR = Path(__file__).parent.parent / "whitemagic-koka"
_DEFAULT_HYBRID_PROCESS_TIMEOUT_S = 5.0


class DispatchMode(Enum):
    SPEED = "speed"      # Python in-memory only
    SAFETY = "safety"    # Koka IPC only
    ADAPTIVE = "adaptive"  # Choose based on complexity


@dataclass
class OperationProfile:
    """Profile for operation complexity."""
    name: str
    has_state: bool          # Maintains state across calls
    has_effects: bool       # Uses effect handlers
    chain_benefit: bool     # Benefits from persistent process
    complexity_score: float # 0.0-1.0, higher = use Koka


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

    # PRAT routing table
    TOOL_TO_GANA = {
        "search_memories": "gana_winnowing_basket",
        "gnosis": "gana_ghost",
        "health_report": "gana_horn",
        "create_memory": "gana_heart",
        "cluster_stats": "gana_dipper",
        "consolidate": "gana_abundance",
        "synthesize": "gana_three_stars",
    }

    # Gana order for predecessor/successor
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

    # Circuit breaker state
    circuit_state: dict[str, Any] = {
        "state": "closed",
        "failures": 0,
        "successes": 0,
        "threshold": 5,
        "timeout_ms": 30000,
    }

    # Dream cycle state
    dream_state: dict[str, Any] = {
        "phase": "dormant",
        "cycles": 0,
        "memories": 0,
        "insights": 0,
    }

    @classmethod
    def prat_route(cls, tool: str) -> str:
        """Route tool to Gana (sub-µs)."""
        res = cls.TOOL_TO_GANA.get(tool, "gana_ghost")
        return str(res)

    @classmethod
    def get_predecessor(cls, gana: str) -> str:
        """Get predecessor Gana (sub-µs)."""
        idx = cls.GANA_INDEX.get(gana, 0)
        _ = idx  # Prevent unused warning in benchmark
        res = cls.GANA_ORDER[(idx - 1) % 28]
        return str(res)

    @classmethod
    def get_successor(cls, gana: str) -> str:
        """Get successor Gana (sub-µs)."""
        idx = cls.GANA_INDEX.get(gana, 0)
        res = cls.GANA_ORDER[(idx + 1) % 28]
        return str(res)

    @classmethod
    def circuit_check(cls) -> str:
        """Check circuit state (in-memory)."""
        res = cls.circuit_state["state"]
        return str(res)

    @classmethod
    def circuit_record_success(cls) -> str:
        """Record success in circuit."""
        successes = int(cls.circuit_state["successes"]) + 1
        cls.circuit_state["successes"] = successes
        if cls.circuit_state["state"] == "half-open":
            if successes >= 3:
                cls.circuit_state["state"] = "closed"
                cls.circuit_state["failures"] = 0
        return "ok"

    @classmethod
    def circuit_record_failure(cls) -> str:
        """Record failure in circuit."""
        failures = int(cls.circuit_state["failures"]) + 1
        cls.circuit_state["failures"] = failures
        if cls.circuit_state["state"] == "closed":
            threshold = int(cls.circuit_state["threshold"])
            if failures >= threshold:
                cls.circuit_state["state"] = "open"
        elif cls.circuit_state["state"] == "half-open":
            cls.circuit_state["state"] = "open"
        return "ok"


class KokaProcess:
    """Manages a persistent Koka IPC process."""

    def __init__(self, binary_name: str):
        self.binary_name = binary_name
        self.binary_path = KOKA_DIR / binary_name
        self._proc: subprocess.Popen | None = None

    def start(self) -> None:
        """Start the persistent process."""
        if self._proc is None and self.binary_path.exists():
            self._proc = subprocess.Popen(
                [str(self.binary_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

    def _readline_with_timeout(self, timeout: float = _DEFAULT_HYBRID_PROCESS_TIMEOUT_S) -> str | None:
        if self._proc is None or self._proc.stdout is None:
            return None

        result_queue: queue.Queue[str | None] = queue.Queue(maxsize=1)

        def _reader() -> None:
            try:
                # Use a local reference to avoid None-check issues in thread
                proc = self._proc
                if proc and proc.stdout:
                    result_queue.put(proc.stdout.readline())
                else:
                    result_queue.put(None)
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                result_queue.put(None)

        thread = threading.Thread(target=_reader, name=f"hybrid-{self.binary_name}", daemon=True)
        thread.start()

        try:
            return result_queue.get(timeout=timeout)
        except (OSError, FileNotFoundError, PermissionError):
            return None

    def _reset_process(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=1.0)
            except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
                try:
                    self._proc.kill()
                except (ProcessLookupError, OSError):
                    pass
        self._proc = None

    def call(self, request: dict) -> dict[Any, Any]:
        """Send request and get response."""
        if self._proc is None:
            self.start()

        if self._proc is None or self._proc.stdin is None:
            return {"error": "Process not available"}

        import json
        try:
            self._proc.stdin.write(json.dumps(request) + '\n')
            self._proc.stdin.flush()
        except (AttributeError, BrokenPipeError, OSError):
            self._reset_process()
            return {"error": "Write failed"}

        response = self._readline_with_timeout()
        if not response:
            self._reset_process()
            return {"error": "no response"}
        res = json.loads(response)
        return dict(res)

    def stop(self) -> None:
        """Stop the process."""
        if self._proc:
            self._reset_process()


class HybridDispatcher:
    """Adaptive dispatcher that chooses optimal execution path."""

    def __init__(self, mode: DispatchMode = DispatchMode.ADAPTIVE):
        self.mode = mode
        self._koka_processes: dict[str, KokaProcess] = {}
        self._stats = {
            "python_calls": 0,
            "koka_calls": 0,
            "python_time_us": 0.0,
            "koka_time_us": 0.0,
        }

    def _should_use_koka(self, operation: str) -> bool:
        """Decide whether to use Koka based on mode and operation."""
        if self.mode == DispatchMode.SPEED:
            return False
        if self.mode == DispatchMode.SAFETY:
            return True

        # Adaptive: use Koka for complex operations
        profile = OPERATION_PROFILES.get(operation)
        if profile:
            return profile.complexity_score > 0.5
        return False

    def _get_koka(self, binary: str) -> KokaProcess:
        """Get or create Koka process."""
        if binary not in self._koka_processes:
            self._koka_processes[binary] = KokaProcess(binary)
        return self._koka_processes[binary]

    # PRAT routing
    def prat_route(self, tool: str) -> str:
        """Route tool to Gana."""
        if self._should_use_koka("prat_route"):
            start = time.perf_counter()
            result = self._get_koka("prat").call({"op": "check", "tool": tool})
            self._stats["koka_calls"] += 1
            self._stats["koka_time_us"] += (time.perf_counter() - start) * 1_000_000
            gana = result.get("gana")
            return str(gana) if gana else "gana_ghost"
        else:
            start = time.perf_counter()
            res = PythonFastPath.prat_route(tool)
            self._stats["python_calls"] += 1
            self._stats["python_time_us"] += (time.perf_counter() - start) * 1_000_000
            return str(res)

    # Resonance
    def get_predecessor(self, gana: str) -> str:
        """Get predecessor Gana."""
        if self._should_use_koka("resonance_predecessor"):
            start = time.perf_counter()
            result = self._get_koka("resonance").call({"op": "predecessor", "gana": gana})
            self._stats["koka_calls"] += 1
            self._stats["koka_time_us"] += (time.perf_counter() - start) * 1_000_000
            pred = result.get("predecessor")
            return str(pred) if pred else "gana_horn"
        else:
            start = time.perf_counter()
            res = PythonFastPath.get_predecessor(gana)
            self._stats["python_calls"] += 1
            self._stats["python_time_us"] += (time.perf_counter() - start) * 1_000_000
            return str(res)

    # Circuit breaker
    def circuit_check(self) -> str:
        """Check circuit state."""
        if self._should_use_koka("circuit_check"):
            start = time.perf_counter()
            result = self._get_koka("circuit").call({"op": "check"})
            self._stats["koka_calls"] += 1
            self._stats["koka_time_us"] += (time.perf_counter() - start) * 1_000_000
            state = result.get("state")
            return str(state) if state is not None else "closed"
        else:
            start = time.perf_counter()
            res = PythonFastPath.circuit_check()
            self._stats["python_calls"] += 1
            self._stats["python_time_us"] += (time.perf_counter() - start) * 1_000_000
            return str(res)

    def circuit_record_failure(self) -> str:
        """Record circuit failure."""
        if self._should_use_koka("circuit_record"):
            start = time.perf_counter()
            result = self._get_koka("circuit").call({"op": "failure"})
            self._stats["koka_calls"] += 1
            self._stats["koka_time_us"] += (time.perf_counter() - start) * 1_000_000
            res = result.get("result")
            return str(res) if res is not None else "ok"
        else:
            start = time.perf_counter()
            result_python = PythonFastPath.circuit_record_failure()
            assert isinstance(result_python, str)
            self._stats["python_calls"] += 1
            self._stats["python_time_us"] += (time.perf_counter() - start) * 1_000_000
            return result_python

    # Dream cycle (always Koka - complex state machine)
    def dream_run(self) -> dict[str, Any]:
        """Run dream cycle (always Koka for effect handling)."""
        start = time.perf_counter()
        result = self._get_koka("dream_cycle").call({"op": "run"})
        assert isinstance(result, dict)
        self._stats["koka_calls"] += 1
        self._stats["koka_time_us"] += (time.perf_counter() - start) * 1_000_000
        return dict(result)

    @contextmanager
    def session(self) -> Generator["HybridDispatcher", None, None]:
        """Context manager for session with cleanup."""
        try:
            yield self
        finally:
            self.close()

    def close(self) -> None:
        """Close all Koka processes."""
        for proc in self._koka_processes.values():
            proc.stop()
        self._koka_processes.clear()

    def stats(self) -> dict[str, Any]:
        """Get dispatch statistics."""
        return {
            **self._stats,
            "avg_python_us": float(self._stats["python_time_us"]) / max(1, int(self._stats["python_calls"])),
            "avg_koka_us": float(self._stats["koka_time_us"]) / max(1, int(self._stats["koka_calls"])),
        }


# Convenience functions
_dispatcher: HybridDispatcher | None = None

def get_dispatcher(mode: DispatchMode = DispatchMode.ADAPTIVE) -> HybridDispatcher:
    """Get or create the global dispatcher."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = HybridDispatcher(mode)
    return _dispatcher


def set_mode(mode: DispatchMode) -> None:
    """Set the dispatch mode."""
    global _dispatcher
    if _dispatcher:
        _dispatcher.mode = mode
    else:
        _dispatcher = HybridDispatcher(mode)
