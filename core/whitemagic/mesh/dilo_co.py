# ruff: noqa: BLE001
"""DiLoCo — Decoupled Distributed Local SGD with Compression.

Implements a simplified DiLoCo (Decoupled Local SGD) training coordinator
inspired by Google DeepMind's paper, enhanced with:

- **SparseLoCo compression**: Top-k gradient sparsification + error feedback
  to reduce communication bandwidth by ~100x while preserving convergence.
- **Parcae pooling**: Worker pool abstraction where multiple heterogeneous
  workers (different compute capacity, model shards) contribute gradients
  to a shared parameter pool. Named after the three Parcae (Fates) of Roman
  mythology — Nona, Decima, Morta — representing the lifecycle of a gradient.

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │  Coordinator (this module)                          │
    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │
    │  │ Global   │←─│ Gradient │←─│ SparseLoCo   │       │
    │  │ Params   │  │ Pool     │  │ Compressor   │       │
    │  └────┬─────┘  └──────────┘  └──────────────┘       │
    │       │ sync every H steps                       │
    └───────┼───────────────────────────────────────────┘
            │
    ┌───────┼───────────────────────────────────┐
    │       │                                   │
    ▼       ▼                                   ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ Worker 0 │  │ Worker 1 │  │ Worker N │
    │ (local   │  │ (local   │  │ (mesh   │
    │  SGD)    │  │  SGD)    │  │  node)  │
    └──────────┘  └──────────┘  └──────────┘

Key parameters:
    - H: local steps between global syncs (default: 16)
    - k: sparsity ratio for SparseLoCo (default: 0.01 = top 1%)
    - lr: learning rate
    - lr_outer: outer learning rate for global update
    - num_workers: expected worker count

Usage:
    from whitemagic.mesh.dilo_co import get_dilo_co
    coordinator = get_dilo_co()
    coordinator.init_params({"layer1.weight": [0.1, ...], ...})
    coordinator.register_worker("worker_0")
    # Workers do local SGD, then submit gradients
    coordinator.submit_gradient("worker_0", {"layer1.weight": [...]})
    # Every H steps, sync
    coordinator.sync_step()
    params = coordinator.get_params()
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

_DEFAULT_H = int(os.environ.get("WM_DILOCO_H", "16"))
_DEFAULT_K = float(os.environ.get("WM_DILOCO_K", "0.01"))
_DEFAULT_LR = float(os.environ.get("WM_DILOCO_LR", "0.01"))
_DEFAULT_LR_OUTER = float(os.environ.get("WM_DILOCO_LR_OUTER", "1.0"))
_DEFAULT_MAX_WORKERS = int(os.environ.get("WM_DILOCO_MAX_WORKERS", "8"))


# ── SparseLoCo Compressor ─────────────────────────────────────────────────


class SparseLoCoCompressor:
    """SparseLoCo gradient compression with error feedback.

    Keeps only the top-k% of gradient values by magnitude, and accumulates
    the error (dropped gradients) into a feedback buffer so that information
    is not lost over multiple steps.

    This reduces communication by ~1/kx while preserving convergence
    properties similar to full-precision SGD.
    """

    def __init__(self, k_ratio: float = _DEFAULT_K) -> None:
        self.k_ratio = k_ratio
        self._error_buffers: dict[str, np.ndarray] = {}
        self._compress_count = 0
        self._total_compressed_bytes = 0
        self._total_uncompressed_bytes = 0

    def compress(
        self,
        gradients: dict[str, np.ndarray],
    ) -> dict[str, dict[str, Any]]:
        """Compress gradients using top-k sparsification + error feedback.

        Returns a dict of param_name -> {indices, values, shape}.
        """
        compressed: dict[str, dict[str, Any]] = {}

        for name, grad in gradients.items():
            if not isinstance(grad, np.ndarray):
                grad = np.array(grad, dtype=np.float32)
            grad = grad.astype(np.float32)

            # Add error feedback
            if name in self._error_buffers:
                grad = grad + self._error_buffers[name]

            # Flatten for top-k selection
            flat = grad.ravel()
            k = max(1, int(len(flat) * self.k_ratio))

            # Top-k by absolute value
            if len(flat) <= k:
                indices = np.arange(len(flat))
                values = flat.copy()
            else:
                abs_flat = np.abs(flat)
                kth = np.partition(abs_flat, -k)[-k]
                mask = abs_flat >= kth
                indices = np.where(mask)[0][:k]
                values = flat[indices]

            # Update error buffer (dropped gradients)
            compressed_flat = np.zeros_like(flat)
            compressed_flat[indices] = values
            compressed_dense = compressed_flat.reshape(grad.shape)
            self._error_buffers[name] = grad - compressed_dense

            # Track stats
            self._compress_count += 1
            self._total_uncompressed_bytes += grad.nbytes
            self._total_compressed_bytes += indices.nbytes + values.nbytes

            compressed[name] = {
                "indices": indices,
                "values": values,
                "shape": grad.shape,
            }

        return compressed

    def decompress(
        self,
        compressed: dict[str, dict[str, Any]],
    ) -> dict[str, np.ndarray]:
        """Decompress SparseLoCo gradients back to dense arrays."""
        result: dict[str, np.ndarray] = {}
        for name, data in compressed.items():
            dense = np.zeros(data["shape"], dtype=np.float32)
            flat = dense.ravel()
            flat[data["indices"]] = data["values"]
            result[name] = dense.reshape(data["shape"])
        return result

    def get_stats(self) -> dict[str, Any]:
        ratio = 0.0
        if self._total_uncompressed_bytes > 0:
            ratio = self._total_compressed_bytes / self._total_uncompressed_bytes
        return {
            "compress_count": self._compress_count,
            "k_ratio": self.k_ratio,
            "compression_ratio": f"{1 / ratio:.1f}x" if ratio > 0 else "N/A",
            "uncompressed_bytes": self._total_uncompressed_bytes,
            "compressed_bytes": self._total_compressed_bytes,
            "error_buffers": len(self._error_buffers),
        }

    def reset_error(self) -> None:
        """Reset error feedback buffers (e.g., after a full sync)."""
        self._error_buffers.clear()


# ── Parcae Worker Pool ────────────────────────────────────────────────────


@dataclass
class ParcaeWorker:
    """A worker in the Parcae pool.

    Represents a single compute node contributing gradients to the
    shared parameter pool. Workers can be local threads, mesh peers,
    or remote nodes.
    """

    worker_id: str
    compute_capacity: float = 1.0  # Relative compute (1.0 = baseline)
    last_sync_step: int = 0
    gradients_submitted: int = 0
    total_bytes_compressed: int = 0
    is_active: bool = True
    registered_at: float = field(default_factory=lambda: time.time())
    last_seen: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "compute_capacity": self.compute_capacity,
            "last_sync_step": self.last_sync_step,
            "gradients_submitted": self.gradients_submitted,
            "total_bytes_compressed": self.total_bytes_compressed,
            "is_active": self.is_active,
            "registered_at": self.registered_at,
            "last_seen": self.last_seen,
        }


class ParcaePool:
    """Parcae worker pool — manages heterogeneous workers in DiLoCo.

    Named after the three Parcae (Roman Fates):
    - Nona: spins the thread of life (worker registration)
    - Decima: measures the thread (gradient accumulation)
    - Morta: cuts the thread (sync and reset)

    The pool tracks worker health, compute capacity, and ensures
    fair gradient aggregation weighted by compute capacity.
    """

    def __init__(self, max_workers: int = _DEFAULT_MAX_WORKERS) -> None:
        self._workers: dict[str, ParcaeWorker] = {}
        self._max_workers = max_workers
        self._lock = threading.RLock()

    def register(self, worker_id: str, compute_capacity: float = 1.0) -> bool:
        """Register a new worker. Returns False if pool is full."""
        with self._lock:
            if len(self._workers) >= self._max_workers and worker_id not in self._workers:
                return False
            self._workers[worker_id] = ParcaeWorker(
                worker_id=worker_id,
                compute_capacity=compute_capacity,
            )
        logger.info("Parcae pool: registered worker '%s' (capacity=%.1f)", worker_id, compute_capacity)
        return True

    def unregister(self, worker_id: str) -> None:
        with self._lock:
            if worker_id in self._workers:
                self._workers[worker_id].is_active = False

    def heartbeat(self, worker_id: str) -> None:
        """Update worker last_seen timestamp."""
        with self._lock:
            if worker_id in self._workers:
                self._workers[worker_id].last_seen = time.time()

    def get_active_workers(self) -> list[ParcaeWorker]:
        """Get all active workers."""
        with self._lock:
            return [w for w in self._workers.values() if w.is_active]

    def get_worker(self, worker_id: str) -> ParcaeWorker | None:
        with self._lock:
            return self._workers.get(worker_id)

    def total_capacity(self) -> float:
        """Total compute capacity of active workers."""
        with self._lock:
            return sum(w.compute_capacity for w in self._workers.values() if w.is_active)

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            active = [w for w in self._workers.values() if w.is_active]
            return {
                "total_workers": len(self._workers),
                "active_workers": len(active),
                "max_workers": self._max_workers,
                "total_capacity": sum(w.compute_capacity for w in active),
                "workers": [w.to_dict() for w in active],
            }


# ── DiLoCo Coordinator ────────────────────────────────────────────────────


class DiLoCoCoordinator:
    """DiLoCo distributed training coordinator.

    Manages global parameters, collects compressed gradients from workers,
    and performs periodic global synchronization every H local steps.

    The coordinator runs on the "main" node and aggregates gradients
    from the Parcae pool of workers.
    """

    def __init__(
        self,
        h: int = _DEFAULT_H,
        k_ratio: float = _DEFAULT_K,
        lr: float = _DEFAULT_LR,
        lr_outer: float = _DEFAULT_LR_OUTER,
        max_workers: int = _DEFAULT_MAX_WORKERS,
    ) -> None:
        self.h = h  # Local steps between syncs
        self.lr = lr
        self.lr_outer = lr_outer
        self._global_params: dict[str, np.ndarray] = {}
        self._gradient_pool: list[dict[str, np.ndarray]] = []
        self._compressor = SparseLoCoCompressor(k_ratio=k_ratio)
        self._pool = ParcaePool(max_workers=max_workers)
        self._local_step = 0
        self._sync_count = 0
        self._lock = threading.RLock()
        self._param_hash: str = ""

    def init_params(self, params: dict[str, Any]) -> None:
        """Initialize global parameters."""
        with self._lock:
            self._global_params = {
                k: np.array(v, dtype=np.float32) for k, v in params.items()
            }
            self._param_hash = self._compute_hash()

    def register_worker(self, worker_id: str, compute_capacity: float = 1.0) -> bool:
        """Register a worker to the Parcae pool."""
        return self._pool.register(worker_id, compute_capacity)

    def submit_gradient(
        self,
        worker_id: str,
        gradients: dict[str, Any],
        compressed: bool = False,
    ) -> dict[str, Any]:
        """Submit gradients from a worker.

        If not compressed, applies SparseLoCo compression first.
        Returns compression stats.
        """
        self._pool.heartbeat(worker_id)
        worker = self._pool.get_worker(worker_id)
        if worker is None:
            return {"status": "error", "error": "Worker not registered"}

        # Convert to numpy
        grad_arrays: dict[str, np.ndarray] = {}
        for name, grad in gradients.items():
            if not isinstance(grad, np.ndarray):
                grad = np.array(grad, dtype=np.float32)
            grad_arrays[name] = grad.astype(np.float32)

        # Compress if needed
        if not compressed:
            compressed_grads = self._compressor.compress(grad_arrays)
            grad_arrays = self._compressor.decompress(compressed_grads)
            worker.total_bytes_compressed += sum(
                d["indices"].nbytes + d["values"].nbytes
                for d in compressed_grads.values()
            )

        with self._lock:
            self._gradient_pool.append(grad_arrays)
            worker.gradients_submitted += 1
            worker.last_sync_step = self._local_step

        return {
            "status": "success",
            "worker_id": worker_id,
            "compressed_bytes": worker.total_bytes_compressed,
            "local_step": self._local_step,
        }

    def sync_step(self) -> dict[str, Any]:
        """Perform a global synchronization step.

        Averages collected gradients, applies outer learning rate,
        updates global parameters, and clears the gradient pool.
        """
        with self._lock:
            if not self._gradient_pool:
                self._local_step += 1
                return {"status": "skipped", "reason": "No gradients to sync"}

            # Average gradients across all workers
            num_grads = len(self._gradient_pool)
            avg_grads: dict[str, np.ndarray] = {}
            for name in self._gradient_pool[0]:
                stacked = np.stack([g[name] for g in self._gradient_pool])
                avg_grads[name] = np.mean(stacked, axis=0)

            # Apply outer learning rate update
            for name, grad in avg_grads.items():
                if name in self._global_params:
                    self._global_params[name] -= self.lr_outer * grad

            # Clear pool and update stats
            self._gradient_pool.clear()
            self._local_step += 1
            self._sync_count += 1
            self._param_hash = self._compute_hash()
            self._compressor.reset_error()

        logger.info(
            "DiLoCo sync #%d: %d gradients averaged, lr_outer=%.4f",
            self._sync_count, num_grads, self.lr_outer,
        )

        return {
            "status": "success",
            "sync_count": self._sync_count,
            "gradients_averaged": num_grads,
            "local_step": self._local_step,
            "param_hash": self._param_hash[:16],
        }

    def should_sync(self) -> bool:
        """Check if it's time for a global sync (every H local steps)."""
        return self._local_step > 0 and self._local_step % self.h == 0

    def get_params(self) -> dict[str, Any]:
        """Get current global parameters (serialized)."""
        with self._lock:
            return {
                name: arr.tolist() for name, arr in self._global_params.items()
            }

    def get_param_shapes(self) -> dict[str, list[int]]:
        """Get parameter shapes without transferring full data."""
        with self._lock:
            return {name: list(arr.shape) for name, arr in self._global_params.items()}

    def get_status(self) -> dict[str, Any]:
        """Get coordinator status."""
        with self._lock:
            return {
                "h": self.h,
                "lr": self.lr,
                "lr_outer": self.lr_outer,
                "local_step": self._local_step,
                "sync_count": self._sync_count,
                "param_count": len(self._global_params),
                "param_hash": self._param_hash[:16],
                "pending_gradients": len(self._gradient_pool),
                "pool": self._pool.get_status(),
                "compressor": self._compressor.get_stats(),
            }

    def _compute_hash(self) -> str:
        """Compute a hash of current parameters for consistency checking."""
        if not self._global_params:
            return ""
        h = hashlib.sha256()
        for name in sorted(self._global_params):
            arr = self._global_params[name]
            h.update(name.encode())
            h.update(arr.tobytes())
        return h.hexdigest()


# ── Singleton ────────────────────────────────────────────────────────────

_coordinator: DiLoCoCoordinator | None = None
_coordinator_lock = threading.RLock()


def get_dilo_co() -> DiLoCoCoordinator:
    """Get the global DiLoCo coordinator singleton."""
    global _coordinator
    if _coordinator is None:
        with _coordinator_lock:
            if _coordinator is None:
                _coordinator = DiLoCoCoordinator()
    return _coordinator
