"""Koka Batch IPC Client — Multi-command batching for 10x latency reduction (VC-01)
=============================================================================

Implements batch IPC protocol to reduce per-command overhead.
Instead of N round-trips for N commands, we use 1 write + N reads.

Target: batch of 10 commands < 5x single command latency (ideally ~1.5x)

Usage:
    from whitemagic.core.acceleration.koka_batch_client import (
        KokaBatchClient, BatchCommand, BatchMode
    )

    client = KokaBatchClient()

    # Single command (backward compatible)
    result = client.execute("emit", {"type": "memory_created"})

    # Batch commands
    batch = [
        BatchCommand("emit", {"type": "memory_created"}),
        BatchCommand("emit", {"type": "memory_updated"}),
        BatchCommand("status", {}),
    ]
    results = client.execute_batch(batch)
"""
from __future__ import annotations

import logging
import queue
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast

from whitemagic.utils.fast_json import dumps_str as _json_dumps, loads as _json_loads

logger = logging.getLogger(__name__)
_DEFAULT_BATCH_READ_TIMEOUT_S = 5.0


class BatchMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@dataclass
class BatchCommand:
    """A single command in a batch."""
    op: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: int = 0  # Assigned by client

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "op": self.op,
            "payload": _json_dumps(self.payload),
        }


@dataclass
class BatchResult:
    """Result of a single command execution."""
    id: int
    status: str
    result: dict[str, Any]
    latency_ms: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchResult":
        return cls(
            id=data.get("id", 0),
            status=data.get("status", "unknown"),
            result=data.get("result", {}),
            latency_ms=data.get("latency_ms", 0.0),
        )


@dataclass
class BatchResponse:
    """Response from a batch execution."""
    request_id: str
    results: list[BatchResult]
    total_latency_ms: float
    commands_processed: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchResponse":
        return cls(
            request_id=data.get("request_id", ""),
            results=[BatchResult.from_dict(r) for r in data.get("results", [])],
            total_latency_ms=data.get("total_latency_ms", 0.0),
            commands_processed=data.get("commands_processed", 0),
        )


class KokaBatchClient:
    """High-performance batch IPC client for Koka binaries.

    Features:
    - Batch command execution (10x latency reduction target)
    - Connection pooling with lazy initialization
    - Automatic fallback to single-command mode
    - Health monitoring and auto-restart
    """

    def __init__(
        self,
        binary_path: Path | str | None = None,
        max_connections: int = 4,
        auto_start: bool = True,
    ):
        self._lock = threading.Lock()
        self._max_connections = max_connections
        self._processes: list[subprocess.Popen] = []
        self._available: list[subprocess.Popen] = []

        # Find binary
        if binary_path:
            self._binary_path = Path(binary_path)
        else:
            base = Path(__file__).resolve().parent.parent.parent.parent / "whitemagic-koka"
            self._binary_path = base / "batch_ipc"  # Compiled binary name

        self._started = False
        self._stats = {
            "total_commands": 0,
            "total_batches": 0,
            "total_latency_ms": 0.0,
            "errors": 0,
        }

        if auto_start:
            self._ensure_started()

    def _ensure_started(self) -> bool:
        """Ensure at least one process is running."""
        with self._lock:
            if self._started and self._available:
                return True

            if not self._binary_path.exists():
                logger.debug("Koka batch binary not found: %s", self._binary_path)
                return False

            try:
                proc = subprocess.Popen(
                    ["stdbuf", "-o0", "-i0", str(self._binary_path)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # Line buffered
                )

                # Read startup banner
                banner = self._readline_with_timeout(proc, timeout=2.0)
                if banner and ("started" in banner or "batch_ipc" in banner):
                    self._processes.append(proc)
                    self._available.append(proc)
                    self._started = True
                    logger.info("Koka batch client started: %s", self._binary_path)
                    return True
                else:
                    logger.warning("Unexpected startup from Koka: %s", (banner or "")[:100])
                    self._discard_process(proc)
                    return False

            except Exception as e:
                logger.error("Failed to start Koka batch process: %s", e)
                return False

    def _get_process(self) -> subprocess.Popen | None:
        """Get an available process from the pool."""
        with self._lock:
            if self._available:
                return self._available.pop()

            if len(self._processes) < self._max_connections:
                if self._ensure_started():
                    if self._available:
                        return self._available.pop()

            return None

    def _return_process(self, proc: subprocess.Popen) -> None:
        """Return a process to the pool."""
        with self._lock:
            if proc.poll() is None:  # Still running
                self._available.append(proc)

    def _discard_process(self, proc: subprocess.Popen) -> None:
        """Remove and terminate a timed-out or unhealthy process."""
        with self._lock:
            if proc in self._available:
                self._available.remove(proc)
            if proc in self._processes:
                self._processes.remove(proc)
        try:
            proc.terminate()
            proc.wait(timeout=1.0)
        except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
            try:
                proc.kill()
            except (ProcessLookupError, OSError):
                pass

    def _readline_with_timeout(self, proc: subprocess.Popen, timeout: float = _DEFAULT_BATCH_READ_TIMEOUT_S) -> str | None:
        if proc.stdout is None:
            return None

        result_queue: queue.Queue[str | None] = queue.Queue(maxsize=1)

        def _reader() -> None:
            try:
                stdout = proc.stdout
                if stdout is not None:
                    result_queue.put(stdout.readline())
                else:
                    result_queue.put(None)
            except Exception:
                result_queue.put(None)

        thread = threading.Thread(target=_reader, name='wm-koka-batch-readline', daemon=True)
        thread.start()

        try:
            return result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def execute(
        self,
        op: str,
        payload: dict[str, Any] | None = None,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """Execute a single command (backward compatible with non-batch IPC).

        Args:
            op: Operation name (e.g., "emit", "status", "count")
            payload: Command payload
            timeout: Maximum wait time in seconds

        Returns:
            Response dict with status and result
        """
        proc = self._get_process()
        if not proc:
            return {"error": "no_process_available", "status": "failed"}

        try:
            request = {
                "op": op,
                "payload": _json_dumps(payload or {}),
            }

            stdin = proc.stdin
            if stdin is None:
                return {"error": "stdin_unavailable", "status": "failed"}

            stdin.write(_json_dumps(request) + "\n")
            stdin.flush()

            response_line = self._readline_with_timeout(proc, timeout=timeout)

            if response_line:
                result = _json_loads(response_line)
                self._stats["total_commands"] += 1
                return cast(dict[str, Any], result)
            else:
                self._stats["errors"] += 1
                self._discard_process(proc)
                return {"error": "no_response", "status": "failed"}

        except Exception as e:
            self._stats["errors"] += 1
            self._discard_process(proc)
            logger.error("Koka execute error: %s", e)
            return {"error": str(e), "status": "failed"}
        finally:
            if proc.poll() is None:
                self._return_process(proc)

    def execute_batch(
        self,
        commands: list[BatchCommand],
        mode: BatchMode = BatchMode.SEQUENTIAL,
        timeout: float = 30.0,
    ) -> BatchResponse:
        """Execute multiple commands in a single batch.

        This is the key optimization: instead of N round-trips,
        we send all commands in one write and read all responses.

        Args:
            commands: List of BatchCommand objects
            mode: Execution mode (sequential or parallel)
            timeout: Maximum wait time for entire batch

        Returns:
            BatchResponse with results for each command
        """
        proc = self._get_process()
        if not proc:
            return BatchResponse(
                request_id="",
                results=[BatchResult(0, "failed", {"error": "no_process"}, 0.0)
                        for _ in commands],
                total_latency_ms=0.0,
                commands_processed=0,
            )

        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())[:8]

        # Assign IDs to commands
        for i, cmd in enumerate(commands):
            cmd.id = i

        try:
            # Build batch request
            request = {
                "mode": mode.value,
                "request_id": request_id,
                "commands": [cmd.to_dict() for cmd in commands],
            }

            # Single write for all commands
            stdin = proc.stdin
            if stdin is None:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return BatchResponse(
                    request_id=request_id,
                    results=[BatchResult(i, "failed", {"error": "stdin_unavailable"}, 0.0)
                            for i in range(len(commands))],
                    total_latency_ms=elapsed_ms,
                    commands_processed=0,
                )

            stdin.write(_json_dumps(request) + "\n")
            stdin.flush()

            # Read response (single read for all results)
            response_line = self._readline_with_timeout(proc, timeout=timeout)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            if response_line:
                data = _json_loads(response_line)
                response = BatchResponse.from_dict(data)

                # Update stats
                self._stats["total_commands"] += len(commands)
                self._stats["total_batches"] += 1
                self._stats["total_latency_ms"] += elapsed_ms

                return response
            else:
                self._stats["errors"] += 1
                self._discard_process(proc)
                return BatchResponse(
                    request_id=request_id,
                    results=[BatchResult(i, "failed", {"error": "no_response"}, 0.0)
                            for i in range(len(commands))],
                    total_latency_ms=elapsed_ms,
                    commands_processed=0,
                )

        except Exception as e:
            self._stats["errors"] += 1
            self._discard_process(proc)
            logger.error("Koka batch execute error: %s", e)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return BatchResponse(
                request_id=request_id,
                results=[BatchResult(i, "failed", {"error": str(e)}, 0.0)
                        for i in range(len(commands))],
                total_latency_ms=elapsed_ms,
                commands_processed=0,
            )
        finally:
            if proc.poll() is None:
                self._return_process(proc)

    def health_check(self) -> dict[str, Any]:
        """Check if the batch client is healthy."""
        result = self.execute("health", {})
        return {
            "healthy": "status" in result and result.get("status") != "failed",
            "batch_ipc": result.get("batch_ipc", False),
            "version": result.get("version", "unknown"),
            "stats": self._stats.copy(),
        }

    def stats(self) -> dict[str, Any]:
        """Get client statistics."""
        return {
            **self._stats,
            "avg_latency_ms": (
                self._stats["total_latency_ms"] / max(1, self._stats["total_commands"])
            ),
            "available_processes": len(self._available),
            "total_processes": len(self._processes),
        }

    def close(self) -> None:
        """Close all processes."""
        with self._lock:
            for proc in self._processes:
                try:
                    stdin = proc.stdin
                    if stdin is not None:
                        stdin.write(_json_dumps({"op": "quit"}) + "\n")
                        stdin.flush()
                    proc.wait(timeout=2.0)
                except (subprocess.TimeoutExpired, ProcessLookupError, OSError, BrokenPipeError):
                    proc.terminate()
                    try:
                        proc.wait(timeout=1.0)
                    except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
                        proc.kill()

            self._processes.clear()
            self._available.clear()
            self._started = False


# Global client instance
_client: KokaBatchClient | None = None
_client_lock = threading.Lock()


def get_batch_client() -> KokaBatchClient:
    """Get or create the global batch client."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = KokaBatchClient()
    return _client


def close_batch_client() -> None:
    """Close the global batch client."""
    global _client
    if _client:
        _client.close()
        _client = None


def benchmark_batch_vs_single(
    iterations: int = 100,
    batch_size: int = 10,
) -> dict[str, Any]:
    """Benchmark batch IPC vs single command IPC.

    Target: batch of 10 commands < 5x single command latency

    Returns:
        Dict with benchmark results
    """
    client = get_batch_client()

    if not client._started:
        return {"error": "Koka batch client not available"}

    results: dict[str, Any] = {
        "iterations": iterations,
        "batch_size": batch_size,
        "single_latencies_us": [],
        "batch_latencies_us": [],
    }

    # Warmup
    for _ in range(10):
        client.execute("ping", {})

    # Benchmark single commands
    for _ in range(iterations):
        start = time.perf_counter()
        client.execute("ping", {})
        elapsed_us = (time.perf_counter() - start) * 1_000_000
        results["single_latencies_us"].append(elapsed_us)

    # Benchmark batch commands
    batch = [BatchCommand("ping", {}) for _ in range(batch_size)]

    for _ in range(iterations):
        start = time.perf_counter()
        client.execute_batch(batch)
        elapsed_us = (time.perf_counter() - start) * 1_000_000
        results["batch_latencies_us"].append(elapsed_us)

    # Calculate stats
    single_avg = sum(results["single_latencies_us"]) / len(results["single_latencies_us"])
    batch_avg = sum(results["batch_latencies_us"]) / len(results["batch_latencies_us"])

    # Per-command comparison
    single_per_cmd = single_avg
    batch_per_cmd = batch_avg / batch_size

    results["single_avg_us"] = single_avg
    results["batch_avg_us"] = batch_avg
    results["batch_per_cmd_us"] = batch_per_cmd
    results["speedup_factor"] = single_per_cmd / batch_per_cmd if batch_per_cmd > 0 else 0
    results["target_met"] = results["speedup_factor"] >= 2.0  # 10 commands < 5x single

    return results
