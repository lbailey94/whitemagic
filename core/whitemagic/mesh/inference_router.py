# ruff: noqa: BLE001
"""Mesh Inference Router — Route inference requests across mesh nodes.

Routes inference requests to the best available node based on:
- Model availability (which models each node has loaded)
- Current load (queue depth, tokens/sec)
- Network latency (RTT to peer)
- Reputation (karma-weighted trust score)

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │  InferenceRouter                                    │
    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │
    │  │ Node     │  │ Load     │  │ Routing      │       │
    │  │ Registry │→ │ Tracker  │→ │ Strategy     │       │
    │  └──────────┘  └──────────┘  └──────┬───────┘       │
    │                                     │               │
    │  ┌──────────┐  ┌──────────┐  ┌──────▼───────┐       │
    │  │ Local    │  │ Mesh     │  │ Fallback     │       │
    │  │ Fallback │← │ Dispatch │← │ Selector     │       │
    │  └──────────┘  └──────────┘  └──────────────┘       │
    └─────────────────────────────────────────────────────┘

Routing strategies:
    - fastest: Select node with lowest estimated latency
    - round_robin: Distribute evenly across available nodes
    - capacity: Select node with most available capacity
    - reputation: Weight by node reputation score
    - local_first: Try local model first, then mesh

The router integrates with the existing ModelMeshClient for
shared-memory IPC and falls back to HTTP when mesh is unavailable.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

_DEFAULT_STRATEGY = os.environ.get("WM_MESH_ROUTING_STRATEGY", "fastest")
_DEFAULT_TIMEOUT = float(os.environ.get("WM_MESH_ROUTING_TIMEOUT", "30.0"))
_HEALTH_CHECK_INTERVAL = float(os.environ.get("WM_MESH_HEALTH_INTERVAL", "60.0"))
_MAX_HISTORY = int(os.environ.get("WM_MESH_ROUTING_HISTORY", "100"))


class RoutingStrategy(Enum):
    """Inference routing strategies."""

    FASTEST = "fastest"
    ROUND_ROBIN = "round_robin"
    CAPACITY = "capacity"
    REPUTATION = "reputation"
    LOCAL_FIRST = "local_first"


# ── Data structures ───────────────────────────────────────────────────────


@dataclass
class NodeInfo:
    """Information about a mesh inference node."""

    node_id: str
    address: str = ""
    models: list[str] = field(default_factory=list)
    status: str = "unknown"  # ready, busy, loading, error, offline
    queue_depth: int = 0
    tokens_per_sec: float = 0.0
    ram_mb: float = 0.0
    reputation: float = 0.5  # 0.0-1.0
    last_heartbeat: float = 0.0
    last_rtt_ms: float = 0.0
    is_local: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "address": self.address,
            "models": self.models,
            "status": self.status,
            "queue_depth": self.queue_depth,
            "tokens_per_sec": self.tokens_per_sec,
            "ram_mb": self.ram_mb,
            "reputation": self.reputation,
            "last_heartbeat": self.last_heartbeat,
            "last_rtt_ms": round(self.last_rtt_ms, 2),
            "is_local": self.is_local,
        }

    @property
    def is_available(self) -> bool:
        """Check if node is available for routing."""
        return self.status in ("ready", "busy") and (
            time.time() - self.last_heartbeat < _HEALTH_CHECK_INTERVAL * 3
            or self.is_local
        )

    @property
    def estimated_latency_ms(self) -> float:
        """Estimate total latency for a request."""
        # RTT + queue wait time
        queue_wait = self.queue_depth * (1000.0 / max(self.tokens_per_sec, 1.0))
        return self.last_rtt_ms + queue_wait

    @property
    def available_capacity(self) -> float:
        """Available capacity (0.0-1.0). Higher = more available."""
        if self.tokens_per_sec <= 0:
            return 0.0
        load_factor = 1.0 / (1.0 + self.queue_depth * 0.1)
        return load_factor * self.reputation


@dataclass
class RoutingDecision:
    """Result of a routing decision."""

    node_id: str
    strategy: str
    estimated_latency_ms: float
    model: str
    fallback: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "strategy": self.strategy,
            "estimated_latency_ms": round(self.estimated_latency_ms, 2),
            "model": self.model,
            "fallback": self.fallback,
            "reason": self.reason,
        }


# ── Inference Router ─────────────────────────────────────────────────────


class InferenceRouter:
    """Routes inference requests across mesh nodes.

    Tracks node health, model availability, and routes requests
    to the best available node using the configured strategy.
    """

    _instance: InferenceRouter | None = None
    _lock = threading.Lock()

    def __init__(self, strategy: str = _DEFAULT_STRATEGY) -> None:
        self._strategy = RoutingStrategy(strategy)
        self._nodes: dict[str, NodeInfo] = {}
        self._round_robin_idx = 0
        self._data_lock = threading.Lock()
        self._request_history: deque[dict[str, Any]] = deque(maxlen=_MAX_HISTORY)
        self._stats = {
            "total_requests": 0,
            "local_requests": 0,
            "mesh_requests": 0,
            "fallbacks": 0,
            "errors": 0,
        }
        self._local_node_id = f"local_{os.getpid()}"
        self._init_local_node()

    @classmethod
    def get_instance(cls) -> InferenceRouter:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _init_local_node(self) -> None:
        """Register the local node."""
        local = NodeInfo(
            node_id=self._local_node_id,
            status="ready",
            is_local=True,
            last_heartbeat=time.time(),
            tokens_per_sec=20.0,  # Conservative default
            reputation=1.0,
        )
        self._nodes[self._local_node_id] = local

    def register_node(
        self,
        node_id: str,
        address: str = "",
        models: list[str] | None = None,
        reputation: float = 0.5,
    ) -> dict[str, Any]:
        """Register a mesh inference node."""
        with self._data_lock:
            self._nodes[node_id] = NodeInfo(
                node_id=node_id,
                address=address,
                models=models or [],
                status="ready",
                reputation=reputation,
                last_heartbeat=time.time(),
            )
        logger.info("Inference router: registered node '%s' (%d models)", node_id, len(models or []))
        return {"status": "success", "node_id": node_id}

    def unregister_node(self, node_id: str) -> dict[str, Any]:
        """Unregister a mesh node."""
        with self._data_lock:
            if node_id in self._nodes and not self._nodes[node_id].is_local:
                self._nodes[node_id].status = "offline"
        return {"status": "success", "unregistered": node_id}

    def update_node_health(
        self,
        node_id: str,
        status: str = "ready",
        queue_depth: int = 0,
        tokens_per_sec: float = 0.0,
        ram_mb: float = 0.0,
        rtt_ms: float = 0.0,
    ) -> None:
        """Update node health metrics (called by heartbeat/mesh status)."""
        with self._data_lock:
            node = self._nodes.get(node_id)
            if node:
                node.status = status
                node.queue_depth = queue_depth
                node.tokens_per_sec = tokens_per_sec or node.tokens_per_sec
                node.ram_mb = ram_mb or node.ram_mb
                node.last_rtt_ms = rtt_ms or node.last_rtt_ms
                node.last_heartbeat = time.time()

    def update_node_models(self, node_id: str, models: list[str]) -> None:
        """Update the list of models available on a node."""
        with self._data_lock:
            node = self._nodes.get(node_id)
            if node:
                node.models = models

    def route(
        self,
        model: str,
        prompt: str = "",
        max_tokens: int = 128,
        temperature: float = 0.7,
        strategy: str | None = None,
    ) -> RoutingDecision:
        """Route an inference request to the best available node.

        Args:
            model: Model name to route to
            prompt: Input prompt (for logging)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            strategy: Override routing strategy

        Returns:
            RoutingDecision with selected node and metadata
        """
        strat = RoutingStrategy(strategy) if strategy else self._strategy
        self._stats["total_requests"] += 1

        # Find nodes that have this model
        with self._data_lock:
            candidates = [
                n for n in self._nodes.values()
                if n.is_available and model in n.models
            ]

        if not candidates:
            # Fallback to local
            self._stats["fallbacks"] += 1
            local = self._nodes.get(self._local_node_id)
            if local:
                return RoutingDecision(
                    node_id=self._local_node_id,
                    strategy=strat.value,
                    estimated_latency_ms=local.estimated_latency_ms,
                    model=model,
                    fallback=True,
                    reason="No mesh nodes with model, using local",
                )
            self._stats["errors"] += 1
            return RoutingDecision(
                node_id="",
                strategy=strat.value,
                estimated_latency_ms=999.0,
                model=model,
                fallback=True,
                reason="No available nodes",
            )

        # Select node based on strategy
        selected = self._select_node(candidates, strat, model)

        if selected.is_local:
            self._stats["local_requests"] += 1
        else:
            self._stats["mesh_requests"] += 1

        decision = RoutingDecision(
            node_id=selected.node_id,
            strategy=strat.value,
            estimated_latency_ms=selected.estimated_latency_ms,
            model=model,
            reason=f"Selected by {strat.value} strategy",
        )

        # Record in history
        self._request_history.append({
            "timestamp": time.time(),
            "model": model,
            "node_id": selected.node_id,
            "strategy": strat.value,
            "estimated_latency_ms": selected.estimated_latency_ms,
        })

        return decision

    def _select_node(
        self,
        candidates: list[NodeInfo],
        strategy: RoutingStrategy,
        model: str,
    ) -> NodeInfo:
        """Select the best node using the configured strategy."""

        if strategy == RoutingStrategy.FASTEST:
            return min(candidates, key=lambda n: n.estimated_latency_ms)

        elif strategy == RoutingStrategy.ROUND_ROBIN:
            with self._data_lock:
                self._round_robin_idx = (self._round_robin_idx + 1) % len(candidates)
                return candidates[self._round_robin_idx]

        elif strategy == RoutingStrategy.CAPACITY:
            return max(candidates, key=lambda n: n.available_capacity)

        elif strategy == RoutingStrategy.REPUTATION:
            return max(candidates, key=lambda n: n.reputation)

        elif strategy == RoutingStrategy.LOCAL_FIRST:
            for n in candidates:
                if n.is_local:
                    return n
            return min(candidates, key=lambda n: n.estimated_latency_ms)

        # Default: fastest
        return min(candidates, key=lambda n: n.estimated_latency_ms)

    def get_nodes(self) -> list[dict[str, Any]]:
        """Get all registered nodes."""
        with self._data_lock:
            return [n.to_dict() for n in self._nodes.values()]

    def get_available_nodes(self, model: str | None = None) -> list[dict[str, Any]]:
        """Get available nodes, optionally filtered by model."""
        with self._data_lock:
            nodes = [n for n in self._nodes.values() if n.is_available]
            if model:
                nodes = [n for n in nodes if model in n.models]
            return [n.to_dict() for n in nodes]

    def get_status(self) -> dict[str, Any]:
        """Get router status."""
        with self._data_lock:
            active = [n for n in self._nodes.values() if n.is_available]
            models_available: set[str] = set()
            for n in active:
                models_available.update(n.models)

            return {
                "strategy": self._strategy.value,
                "total_nodes": len(self._nodes),
                "active_nodes": len(active),
                "models_available": sorted(models_available),
                "stats": dict(self._stats),
                "recent_requests": list(self._request_history)[-10:],
                "nodes": [n.to_dict() for n in active],
            }

    def set_strategy(self, strategy: str) -> dict[str, Any]:
        """Change the routing strategy."""
        try:
            self._strategy = RoutingStrategy(strategy)
            return {"status": "success", "strategy": strategy}
        except ValueError:
            return {"status": "error", "error": f"Unknown strategy: {strategy}"}


# ── Singleton ────────────────────────────────────────────────────────────

def get_inference_router() -> InferenceRouter:
    """Get the global InferenceRouter singleton."""
    return InferenceRouter.get_instance()
