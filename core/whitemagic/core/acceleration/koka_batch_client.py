# ruff: noqa: BLE001
"""Koka Batch IPC Client — Multi-command batching for 10x latency reduction (VC-01)
=============================================================================

Implements batch IPC protocol to reduce per-command overhead.
Instead of N round-trips for N commands, we use 1 write + N reads.

Phase 5: Migrated to ProcessSupervisor for bounded, observable, supervised I/O.
Uses acquire_lease for process access, supervisor's readline for timeout safety.

Usage:
    from whitemagic.core.acceleration.koka_batch_client import (
        KokaBatchClient, BatchCommand, BatchMode
    )

    client = KokaBatchClient()
    result = client.execute("emit", {"type": "memory_created"})
    batch = [BatchCommand("emit", {"type": "memory_created"})]
    results = client.execute_batch(batch)
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast

from whitemagic.core.acceleration.process_supervisor import (
    ProcessSupervisor,
    register,
)
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)
_DEFAULT_BATCH_READ_TIMEOUT_S = 5.0


class BatchMode(Enum):
    """BatchMode: batch mode."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@dataclass
class BatchCommand:
    """A single command in a batch."""
    op: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "op": self.op, "payload": _json_dumps(self.payload)}


@dataclass
class BatchResult:
    """Result of a single command execution."""
    id: int
    status: str
    result: dict[str, Any]
    latency_ms: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BatchResult:
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
    def from_dict(cls, data: dict[str, Any]) -> BatchResponse:
        return cls(
            request_id=data.get("request_id", ""),
            results=[BatchResult.from_dict(r) for r in data.get("results", [])],
            total_latency_ms=data.get("total_latency_ms", 0.0),
            commands_processed=data.get("commands_processed", 0),
        )


class KokaBatchClient:
    """High-performance batch IPC client for Koka binaries.

    Uses ProcessSupervisor for process lifecycle, leasing, and supervised I/O.
    """

    def __init__(
        self,
        binary_path: Path | str | None = None,
        max_connections: int = 4,
        auto_start: bool = True,
    ):
        self._max_connections = max_connections

        if binary_path:
            self._binary_path = Path(binary_path)
        else:
            base = (
                Path(__file__).resolve().parent.parent.parent.parent / "whitemagic-koka"
            )
            self._binary_path = base / "batch_ipc"

        self._supervisor: ProcessSupervisor | None = None
        self._stats = {
            "total_commands": 0,
            "total_batches": 0,
            "total_latency_ms": 0.0,
            "errors": 0,
        }

        if auto_start:
            self._ensure_started()

    def _get_supervisor(self) -> ProcessSupervisor:
        if self._supervisor is None:
            self._supervisor = ProcessSupervisor(
                name="koka-batch",
                cmd=["stdbuf", "-o0", "-i0", str(self._binary_path)],
                binary_path=str(self._binary_path),
                max_processes=self._max_connections,
                startup_timeout=2.0,
                call_timeout=30.0,
                skip_polyglot=True,
            )
            register(self._supervisor)
        return self._supervisor

    def _ensure_started(self) -> bool:
        """Ensure at least one process is running."""
        if not self._binary_path.exists():
            logger.debug("Koka batch binary not found: %s", self._binary_path)
            return False
        return self._get_supervisor().is_available()

    def execute(
        self,
        op: str,
        payload: dict[str, Any] | None = None,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """Execute a single command (backward compatible with non-batch IPC)."""
        sup = self._get_supervisor()
        request = {"op": op, "payload": _json_dumps(payload or {})}
        result = sup.call(request, timeout=timeout)
        if result.ok and result.data:
            self._stats["total_commands"] += 1
            return cast(dict[str, Any], result.data)
        self._stats["errors"] += 1
        return {"error": result.error or "unknown", "status": "failed"}

    def execute_batch(
        self,
        commands: list[BatchCommand],
        mode: BatchMode = BatchMode.SEQUENTIAL,
        timeout: float = 30.0,
    ) -> BatchResponse:
        """Execute multiple commands in a single batch.

        Uses acquire_lease to get exclusive process access, then does
        a single write + single read for all commands.
        """
        sup = self._get_supervisor()
        if not sup.is_available():
            return BatchResponse(
                request_id="",
                results=[
                    BatchResult(0, "failed", {"error": "no_process"}, 0.0)
                    for _ in commands
                ],
                total_latency_ms=0.0,
                commands_processed=0,
            )

        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())[:8]

        for i, cmd in enumerate(commands):
            cmd.id = i

        request = {
            "mode": mode.value,
            "request_id": request_id,
            "commands": [cmd.to_dict() for cmd in commands],
        }

        lease = sup.acquire_lease(timeout=1.0)
        if lease is None:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return BatchResponse(
                request_id=request_id,
                results=[
                    BatchResult(i, "failed", {"error": "pool_exhausted"}, 0.0)
                    for i in range(len(commands))
                ],
                total_latency_ms=elapsed_ms,
                commands_processed=0,
            )

        try:
            with lease as proc:
                if proc.stdin is None:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    return BatchResponse(
                        request_id=request_id,
                        results=[
                            BatchResult(i, "failed", {"error": "stdin_unavailable"}, 0.0)
                            for i in range(len(commands))
                        ],
                        total_latency_ms=elapsed_ms,
                        commands_processed=0,
                    )

                proc.stdin.write(_json_dumps(request) + "\n")
                proc.stdin.flush()

                response_line = sup._readline_with_timeout(proc, timeout=timeout)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                if response_line:
                    data = _json_loads(response_line)
                    response = BatchResponse.from_dict(data)
                    self._stats["total_commands"] += len(commands)
                    self._stats["total_batches"] += 1
                    self._stats["total_latency_ms"] += elapsed_ms
                    return response
                else:
                    self._stats["errors"] += 1
                    # Process will be discarded by lease release
                    return BatchResponse(
                        request_id=request_id,
                        results=[
                            BatchResult(i, "failed", {"error": "no_response"}, 0.0)
                            for i in range(len(commands))
                        ],
                        total_latency_ms=elapsed_ms,
                        commands_processed=0,
                    )
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("Koka batch execute error: %s", e)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return BatchResponse(
                request_id=request_id,
                results=[
                    BatchResult(i, "failed", {"error": str(e)}, 0.0)
                    for i in range(len(commands))
                ],
                total_latency_ms=elapsed_ms,
                commands_processed=0,
            )

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
        sup = self._supervisor
        return {
            **self._stats,
            "avg_latency_ms": (
                self._stats["total_latency_ms"] / max(1, self._stats["total_commands"])
            ),
            "available_processes": len(sup._available) if sup else 0,
            "total_processes": len(sup._processes) if sup else 0,
        }

    def close(self) -> None:
        """Close all processes."""
        if self._supervisor is not None:
            self._supervisor.close()
            self._supervisor = None


# Global client instance
_client: KokaBatchClient | None = None
_client_lock = __import__("threading").Lock()


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
    """Benchmark batch IPC vs single command IPC."""
    client = get_batch_client()

    if client._supervisor is None or not client._supervisor.is_available():
        return {"error": "Koka batch client not available"}

    results: dict[str, Any] = {
        "iterations": iterations,
        "batch_size": batch_size,
        "single_latencies_us": [],
        "batch_latencies_us": [],
    }

    for _ in range(10):
        client.execute("ping", {})

    for _ in range(iterations):
        start = time.perf_counter()
        client.execute("ping", {})
        elapsed_us = (time.perf_counter() - start) * 1_000_000
        results["single_latencies_us"].append(elapsed_us)

    batch = [BatchCommand("ping", {}) for _ in range(batch_size)]

    for _ in range(iterations):
        start = time.perf_counter()
        client.execute_batch(batch)
        elapsed_us = (time.perf_counter() - start) * 1_000_000
        results["batch_latencies_us"].append(elapsed_us)

    single_avg = sum(results["single_latencies_us"]) / len(
        results["single_latencies_us"]
    )
    batch_avg = sum(results["batch_latencies_us"]) / len(results["batch_latencies_us"])
    single_per_cmd = single_avg
    batch_per_cmd = batch_avg / batch_size

    results["single_avg_us"] = single_avg
    results["batch_avg_us"] = batch_avg
    results["batch_per_cmd_us"] = batch_per_cmd
    results["speedup_factor"] = (
        single_per_cmd / batch_per_cmd if batch_per_cmd > 0 else 0
    )
    results["target_met"] = results["speedup_factor"] >= 2.0

    return results
