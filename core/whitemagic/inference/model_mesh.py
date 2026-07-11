# ruff: noqa: BLE001
"""Model Mesh — IceOryx2 shared-memory model serving.

Replaces HTTP localhost calls to llama-server with zero-copy shared memory
IPC via IceOryx2. Model processes (llama-server, bitmamba.cpp) publish
inference results to shared memory channels, and the WhiteMagic MCP server
subscribes to receive results without HTTP overhead.

Architecture:
    ┌──────────────────────────────────────────────────────────┐
    │  Model Process (llama-server / bitmamba.cpp)             │
    │  ┌──────────┐    ┌──────────────┐    ┌───────────────┐   │
    │  │ Inference│───▶│ ModelMesh    │───▶│ IceOryx2      │   │
    │  │ Engine   │    │ Publisher    │    │ Shared Memory │   │
    │  └──────────┘    └──────────────┘    └───────┬───────┘   │
    └──────────────────────────────────────────────┼───────────┘
                                                    │ zero-copy
    ┌──────────────────────────────────────────────┼───────────┐
    │  WhiteMagic MCP Server                       ▼           │
    │  ┌──────────┐    ┌──────────────┐    ┌───────────────┐   │
    │  │ ModelMesh│───▶│ IceOryx2     │───▶│ Inference     │   │
    │  │ Subscriber│   │ Subscriber   │    │ Router        │   │
    │  └──────────┘    └──────────────┘    └───────────────┘   │
    └──────────────────────────────────────────────────────────┘

Channels:
    wm/model/llama        — llama-server inference results
    wm/model/bitmamba     — BitMamba autonomic layer output
    wm/model/requests     — Inference requests (client → model process)
    wm/model/status       — Model health/availability broadcasts

Protocol:
    Request:  {id, model, prompt, max_tokens, temperature, ...}
    Response: {id, text, tokens, latency_ms, status}

The Rust FFI (ipc_bridge.rs) provides the low-level IceOryx2 transport.
This Python module provides the model-mesh protocol layer on top.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Channel names ────────────────────────────────────────────────────────

CHANNEL_MODEL_LLAMA = "wm/model/llama"
CHANNEL_MODEL_BITMAMBA = "wm/model/bitmamba"
CHANNEL_MODEL_REQUESTS = "wm/model/requests"
CHANNEL_MODEL_STATUS = "wm/model/status"

# ── Configuration ────────────────────────────────────────────────────────

_MESH_ENABLED = os.environ.get("WM_MODEL_MESH", "0") == "1"
_RESPONSE_TIMEOUT_S = float(os.environ.get("WM_MESH_TIMEOUT", "30.0"))
_STATUS_INTERVAL_S = float(os.environ.get("WM_MESH_STATUS_INTERVAL", "10.0"))


# ── Data structures ──────────────────────────────────────────────────────


@dataclass
class InferenceRequest:
    """A model inference request for the mesh."""

    id: str
    model: str  # "llama", "bitmamba", etc.
    prompt: str
    max_tokens: int = 128
    temperature: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_bytes(self) -> bytes:
        return json.dumps({
            "id": self.id,
            "model": self.model,
            "prompt": self.prompt[:2000],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "metadata": self.metadata,
        }).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> InferenceRequest | None:
        try:
            d = json.loads(data)
            return cls(
                id=d["id"],
                model=d["model"],
                prompt=d.get("prompt", ""),
                max_tokens=d.get("max_tokens", 128),
                temperature=d.get("temperature", 0.7),
                metadata=d.get("metadata", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return None


@dataclass
class InferenceResponse:
    """A model inference response from the mesh."""

    id: str
    text: str
    tokens: list[int] = field(default_factory=list)
    latency_ms: float = 0.0
    status: str = "ok"  # "ok", "error", "timeout"
    model: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_bytes(self) -> bytes:
        return json.dumps({
            "id": self.id,
            "text": self.text,
            "tokens": self.tokens[:200],  # Truncate for IPC
            "latency_ms": self.latency_ms,
            "status": self.status,
            "model": self.model,
            "metadata": self.metadata,
        }).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> InferenceResponse | None:
        try:
            d = json.loads(data)
            return cls(
                id=d["id"],
                text=d.get("text", ""),
                tokens=d.get("tokens", []),
                latency_ms=d.get("latency_ms", 0.0),
                status=d.get("status", "ok"),
                model=d.get("model", ""),
                metadata=d.get("metadata", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return None


@dataclass
class ModelStatus:
    """Health status broadcast from a model process."""

    model: str
    status: str  # "ready", "loading", "error", "busy"
    ram_mb: float = 0.0
    tokens_per_sec: float = 0.0
    queue_depth: int = 0
    timestamp: float = 0.0

    def to_bytes(self) -> bytes:
        return json.dumps({
            "model": self.model,
            "status": self.status,
            "ram_mb": self.ram_mb,
            "tokens_per_sec": self.tokens_per_sec,
            "queue_depth": self.queue_depth,
            "timestamp": self.timestamp,
        }).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> ModelStatus | None:
        try:
            d = json.loads(data)
            return cls(
                model=d.get("model", ""),
                status=d.get("status", "unknown"),
                ram_mb=d.get("ram_mb", 0.0),
                tokens_per_sec=d.get("tokens_per_sec", 0.0),
                queue_depth=d.get("queue_depth", 0),
                timestamp=d.get("timestamp", 0.0),
            )
        except json.JSONDecodeError:
            return None


@dataclass
class MeshStats:
    """Running statistics for the model mesh."""

    requests_sent: int = 0
    responses_received: int = 0
    timeouts: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    models_available: dict[str, ModelStatus] = field(default_factory=dict)

    @property
    def avg_latency_ms(self) -> float:
        if self.responses_received == 0:
            return 0.0
        return self.total_latency_ms / self.responses_received

    def to_dict(self) -> dict[str, Any]:
        return {
            "requests_sent": self.requests_sent,
            "responses_received": self.responses_received,
            "timeouts": self.timeouts,
            "errors": self.errors,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "models_available": {
                k: {"status": v.status, "ram_mb": v.ram_mb, "tok/s": v.tokens_per_sec}
                for k, v in self.models_available.items()
            },
        }


# ── Model Mesh Client ────────────────────────────────────────────────────


class ModelMeshClient:
    """Client for sending inference requests via the model mesh.

    Uses IceOryx2 shared memory (via Rust FFI) for zero-copy communication
    with model processes. Falls back to HTTP if IceOryx2 is not available.
    """

    def __init__(self) -> None:
        self._stats = MeshStats()
        self._lock = threading.RLock()
        self._pending: dict[str, threading.Event] = {}
        self._responses: dict[str, InferenceResponse] = {}
        self._poll_thread: threading.Thread | None = None
        self._running = False
        self._stop_event = threading.Event()
        self._ipc_available = self._check_ipc()

    def _check_ipc(self) -> bool:
        """Check if IceOryx2 IPC is available."""
        try:
            import whitemagic_rs
            if hasattr(whitemagic_rs, "ipc_status"):
                status = whitemagic_rs.ipc_status()
                return status.get("iceoryx2_compiled") == "true"
        except ImportError:
            pass
        return False

    @property
    def is_available(self) -> bool:
        """Check if the model mesh is available."""
        return self._ipc_available and _MESH_ENABLED

    @property
    def stats(self) -> MeshStats:
        return self._stats

    def request(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 128,
        temperature: float = 0.7,
        timeout: float | None = None,
    ) -> InferenceResponse | None:
        """Send an inference request via the mesh and wait for response.

        Args:
            model: Model name ("llama", "bitmamba", etc.)
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            timeout: Response timeout in seconds (default: _RESPONSE_TIMEOUT_S)

        Returns:
            InferenceResponse or None if timeout/error
        """
        if not self.is_available:
            return None

        timeout = timeout or _RESPONSE_TIMEOUT_S
        req_id = str(uuid.uuid4())
        request = InferenceRequest(
            id=req_id,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Register pending request
        event = threading.Event()
        with self._lock:
            self._pending[req_id] = event
            self._stats.requests_sent += 1

        # Publish request via IceOryx2
        try:
            import whitemagic_rs
            whitemagic_rs.ipc_publish(CHANNEL_MODEL_REQUESTS, request.to_bytes())
        except ImportError:
            logger.debug("Rust bindings not available for mesh publish")
            with self._lock:
                self._pending.pop(req_id, None)
                self._stats.errors += 1
            return None
        except Exception as e:
            logger.debug("Mesh publish failed: %s", e)
            with self._lock:
                self._pending.pop(req_id, None)
                self._stats.errors += 1
            return None

        # Start polling if not already running
        self._ensure_polling()

        # Wait for response
        if event.wait(timeout=timeout):
            with self._lock:
                response = self._responses.pop(req_id, None)
                self._pending.pop(req_id, None)
            if response:
                with self._lock:
                    self._stats.responses_received += 1
                    self._stats.total_latency_ms += response.latency_ms
                return response
        else:
            logger.debug("Mesh request %s timed out", req_id)
            with self._lock:
                self._pending.pop(req_id, None)
                self._stats.timeouts += 1
            return None

        return None

    def request_async(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 128,
        temperature: float = 0.7,
    ) -> str:
        """Send an inference request without waiting for response.

        Returns the request ID for later retrieval.
        """
        req_id = str(uuid.uuid4())
        request = InferenceRequest(
            id=req_id,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        with self._lock:
            self._stats.requests_sent += 1

        try:
            import whitemagic_rs
            whitemagic_rs.ipc_publish(CHANNEL_MODEL_REQUESTS, request.to_bytes())
        except ImportError:
            logger.debug("Rust bindings not available for mesh async")
            with self._lock:
                self._stats.errors += 1
        except Exception as e:
            logger.debug("Mesh async publish failed: %s", e)
            with self._lock:
                self._stats.errors += 1

        return req_id

    def get_response(self, req_id: str, timeout: float | None = None) -> InferenceResponse | None:
        """Get a response for a previously sent async request."""
        timeout = timeout or _RESPONSE_TIMEOUT_S
        deadline = time.time() + timeout

        while time.time() < deadline:
            with self._lock:
                if req_id in self._responses:
                    return self._responses.pop(req_id)
            time.sleep(0.05)

        return None

    def get_status(self) -> dict[str, Any]:
        """Get mesh status and statistics."""
        with self._lock:
            return self._stats.to_dict()

    def get_model_status(self, model: str) -> ModelStatus | None:
        """Get status for a specific model."""
        with self._lock:
            return self._stats.models_available.get(model)

    def start(self) -> bool:
        """Start the response polling thread."""
        if not self.is_available:
            return False
        self._ensure_polling()
        return True

    def stop(self) -> None:
        """Stop the polling thread."""
        self._running = False
        self._stop_event.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2.0)

    def _ensure_polling(self) -> None:
        """Ensure the polling thread is running."""
        if self._poll_thread and self._poll_thread.is_alive():
            return
        self._running = True
        self._stop_event.clear()
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="model-mesh-poll"
        )
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        """Poll for responses and status updates from model processes."""
        while self._running and not self._stop_event.is_set():
            try:
                self._poll_responses()
                self._poll_status()
            except Exception as e:
                logger.debug("Mesh poll error: %s", e)

            self._stop_event.wait(timeout=0.1)

    def _poll_responses(self) -> None:
        """Poll response channels for pending responses."""
        try:
            import whitemagic_rs
            # Poll llama response channel
            for channel in (CHANNEL_MODEL_LLAMA, CHANNEL_MODEL_BITMAMBA):
                samples = whitemagic_rs.ipc_try_receive(channel, 16)
                for sample in samples:
                    response = InferenceResponse.from_bytes(sample)
                    if response:
                        with self._lock:
                            self._responses[response.id] = response
                            event = self._pending.get(response.id)
                        if event:
                            event.set()
        except ImportError:
            pass
        except Exception:
            pass

    def _poll_status(self) -> None:
        """Poll status channel for model health updates."""
        try:
            import whitemagic_rs
            samples = whitemagic_rs.ipc_try_receive(CHANNEL_MODEL_STATUS, 8)
            for sample in samples:
                status = ModelStatus.from_bytes(sample)
                if status:
                    with self._lock:
                        self._stats.models_available[status.model] = status
        except ImportError:
            pass
        except Exception:
            pass


# ── Model Mesh Publisher (for model processes) ──────────────────────────


class ModelMeshPublisher:
    """Publisher for model processes to broadcast results via the mesh.

    Used by llama-server wrapper or bitmamba.cpp wrapper to publish
    inference results to shared memory instead of HTTP responses.
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._ipc_available = self._check_ipc()
        self._status_thread: threading.Thread | None = None
        self._running = False
        self._stop_event = threading.Event()
        self._tokens_per_sec: float = 0.0
        self._ram_mb: float = 0.0
        self._queue_depth: int = 0

    def _check_ipc(self) -> bool:
        try:
            import whitemagic_rs
            if hasattr(whitemagic_rs, "ipc_status"):
                status = whitemagic_rs.ipc_status()
                return status.get("iceoryx2_compiled") == "true"
        except ImportError:
            pass
        return False

    @property
    def is_available(self) -> bool:
        return self._ipc_available and _MESH_ENABLED

    def publish_response(self, response: InferenceResponse) -> bool:
        """Publish an inference response to the mesh."""
        if not self.is_available:
            return False
        response.model = self._model_name
        channel = (
            CHANNEL_MODEL_LLAMA if self._model_name == "llama"
            else CHANNEL_MODEL_BITMAMBA if self._model_name == "bitmamba"
            else CHANNEL_MODEL_LLAMA
        )
        try:
            import whitemagic_rs
            whitemagic_rs.ipc_publish(channel, response.to_bytes())
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.debug("Mesh publish response failed: %s", e)
            return False

    def publish_status(
        self,
        status: str = "ready",
        ram_mb: float = 0.0,
        tokens_per_sec: float = 0.0,
        queue_depth: int = 0,
    ) -> bool:
        """Publish model health status."""
        if not self.is_available:
            return False
        status_msg = ModelStatus(
            model=self._model_name,
            status=status,
            ram_mb=ram_mb,
            tokens_per_sec=tokens_per_sec,
            queue_depth=queue_depth,
            timestamp=time.time(),
        )
        try:
            import whitemagic_rs
            whitemagic_rs.ipc_publish(CHANNEL_MODEL_STATUS, status_msg.to_bytes())
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.debug("Mesh publish status failed: %s", e)
            return False

    def start_status_broadcast(
        self,
        status_fn: Any = None,
        interval: float = _STATUS_INTERVAL_S,
    ) -> None:
        """Start periodic status broadcasting."""
        if not self.is_available:
            return
        self._running = True
        self._stop_event.clear()
        self._status_fn = status_fn
        self._status_thread = threading.Thread(
            target=self._status_loop, daemon=True, name=f"mesh-status-{self._model_name}"
        )
        self._status_thread.start()

    def stop_status_broadcast(self) -> None:
        """Stop status broadcasting."""
        self._running = False
        self._stop_event.set()
        if self._status_thread and self._status_thread.is_alive():
            self._status_thread.join(timeout=2.0)

    def _status_loop(self) -> None:
        while self._running and not self._stop_event.is_set():
            try:
                if self._status_fn:
                    status_data = self._status_fn()
                    self.publish_status(**status_data)
                else:
                    self.publish_status(
                        status="ready",
                        ram_mb=self._ram_mb,
                        tokens_per_sec=self._tokens_per_sec,
                        queue_depth=self._queue_depth,
                    )
            except Exception as e:
                logger.debug("Status broadcast error: %s", e)
            self._stop_event.wait(timeout=_STATUS_INTERVAL_S)


# ── Singletons ───────────────────────────────────────────────────────────

_mesh_client: ModelMeshClient | None = None
_mesh_lock = threading.Lock()


def get_mesh_client() -> ModelMeshClient:
    """Get or create the global model mesh client singleton."""
    global _mesh_client
    if _mesh_client is None:
        with _mesh_lock:
            if _mesh_client is None:
                _mesh_client = ModelMeshClient()
    return _mesh_client


def is_mesh_available() -> bool:
    """Check if the model mesh is available and enabled."""
    if not _MESH_ENABLED:
        return False
    return get_mesh_client().is_available
