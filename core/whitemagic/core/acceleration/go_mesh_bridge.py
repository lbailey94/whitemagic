# ruff: noqa: BLE001
"""Go Mesh Bridge - Python to Go via Redis/gRPC.
==============================================
Bridges to Go mesh modules for distributed memory sync and agent
coordination. The Go mesh node runs as a separate process communicating
via Redis pub/sub and gRPC.

Go modules:
- gossip.go - Gossipsub memory sync (vector clocks, anti-entropy, distributed locks)
- agent_stream.go - Agent registry with load-aware task distribution

Falls back to pure Python when Go mesh is not available.

Usage:
    from whitemagic.core.acceleration.go_mesh_bridge import (
        mesh_sync_memory, mesh_agent_status, go_mesh_status
    )
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

_redis_client: Any | None = None
_redis_lock = threading.RLock()
_HAS_GO_MESH = False
_MESH_CHANNEL = "whitemagic_mesh"


def _get_redis() -> Any:
    """Lazy-load Redis client for Go mesh bridge."""
    global _redis_client, _HAS_GO_MESH
    if _redis_client is not None:
        return _redis_client
    with _redis_lock:
        if _redis_client is not None:
            return _redis_client
        try:
            import redis

            url = os.environ.get("REDIS_URL", "redis://localhost:6379")
            client = redis.from_url(url, decode_responses=True)
            client.ping()
            _redis_client = client
            _HAS_GO_MESH = True
            logger.info("Go mesh bridge connected via Redis: %s", url)
            return client
        except Exception as e:
            logger.debug("Go mesh bridge unavailable: %s", e)
            return None


def _send_mesh_command(command: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Send a command to the Go mesh node via Redis."""
    client = _get_redis()
    if client is None:
        return None

    request_id = f"mesh_{command}_{time.time_ns()}"
    message = {
        "command": command,
        "payload": payload,
        "request_id": request_id,
        "_origin": "python_bridge",
    }

    try:
        response_channel = f"{_MESH_CHANNEL}:response:{request_id}"
        pubsub = client.pubsub()
        pubsub.subscribe(response_channel)
        client.publish(f"{_MESH_CHANNEL}:commands", _json_dumps(message))

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            msg = pubsub.get_message(timeout=0.5)
            if msg and msg["type"] == "message":
                pubsub.unsubscribe(response_channel)
                parsed = _json_loads(msg["data"])
                if isinstance(parsed, dict):
                    return parsed

        pubsub.unsubscribe(response_channel)
        logger.debug("Go mesh %s timed out", command)
    except Exception as e:
        logger.debug("Go mesh command %s failed: %s", command, e)

    return None


def mesh_sync_memory(
    memory_id: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Announce a memory to the mesh for cross-node sync via gossipsub.

    Returns:
        Dict with sync status and peer acknowledgments, or None.

    """
    return _send_mesh_command(
        "sync_memory",
        {
            "memory_id": memory_id,
            "content": content,
            "metadata": metadata or {},
        },
    )


def mesh_request_memory(memory_id: str) -> dict[str, Any] | None:
    """Request a memory from the mesh network."""
    return _send_mesh_command("request_memory", {"memory_id": memory_id})


def mesh_acquire_lock(
    resource: str,
    ttl_seconds: int = 30,
) -> dict[str, Any] | None:
    """Acquire a distributed lock on a resource via Go mesh consensus.

    Returns:
        Dict with {acquired, lock_id, expires_at}, or None.

    """
    return _send_mesh_command(
        "acquire_lock",
        {
            "resource": resource,
            "ttl_seconds": ttl_seconds,
        },
    )


def mesh_release_lock(lock_id: str) -> dict[str, Any] | None:
    """Release a distributed lock."""
    return _send_mesh_command("release_lock", {"lock_id": lock_id})


def mesh_agent_status() -> dict[str, Any] | None:
    """Get all registered agents and their load from Go mesh."""
    return _send_mesh_command("agent_status", {})


def mesh_distribute_task(
    task: dict[str, Any],
    strategy: str = "least_loaded",
) -> dict[str, Any] | None:
    """Distribute a task to an agent via Go mesh load-aware routing.

    Args:
        task: Task definition dict.
        strategy: "least_loaded", "round_robin", or "random".

    Returns:
        Dict with {agent_id, accepted, queue_position}, or None.

    """
    return _send_mesh_command(
        "distribute_task",
        {
            "task": task,
            "strategy": strategy,
        },
    )


def mesh_peer_list() -> list[dict[str, Any]] | None:
    """Get list of mesh peers with their status."""
    result = _send_mesh_command("peer_list", {})
    if result and "peers" in result:
        peers = result.get("peers")
        if isinstance(peers, list):
            return [p for p in peers if isinstance(p, dict)]
    return None


def go_mesh_status() -> dict[str, Any]:
    """Get Go mesh bridge status."""
    _get_redis()
    return {
        "has_go_mesh": _HAS_GO_MESH,
        "redis_connected": _redis_client is not None,
        "channel": _MESH_CHANNEL,
        "modules": {
            "gossip": _HAS_GO_MESH,
            "agent_stream": _HAS_GO_MESH,
        },
        "backend": "go_mesh" if _HAS_GO_MESH else "python_fallback",
    }


_go_prefetch_bin: str | None = None
_go_prefetch_lock = threading.RLock()
_go_prefetch_checked = False


def _find_go_prefetch() -> str | None:
    """Locate the Go prefetch_service binary."""
    global _go_prefetch_bin, _go_prefetch_checked
    if _go_prefetch_checked:
        return _go_prefetch_bin
    with _go_prefetch_lock:
        if _go_prefetch_checked:
            return _go_prefetch_bin
        _go_prefetch_checked = True
        base = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            )
        )
        candidates = [
            os.path.join(base, "polyglot", "whitemagic-go", "prefetch_service"),
            os.environ.get("WM_GO_PREFETCH_BIN", ""),
        ]
        for path in candidates:
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                _go_prefetch_bin = path
                logger.info("Go prefetch service found: %s", path)
                return path
    return None


def go_concurrent_prefetch(
    tools: list[dict[str, Any]],
    max_workers: int = 0,
) -> dict[str, Any] | None:
    """Prefetch multiple tools concurrently using Go goroutines.

    Each tool gets its own goroutine, coordinated by a semaphore to limit
    concurrency to max_workers (defaults to NumCPU).

    Args:
        tools: List of dicts with "name", "gana", "probability" keys.
        max_workers: Max concurrent goroutines (0 = NumCPU).

    Returns:
        Dict with results, total_ms, workers, goroutines, or None if Go unavailable.
    """
    binary = _find_go_prefetch()
    if binary is None:
        return None

    import subprocess

    request = {
        "command": "prefetch",
        "tools": tools,
        "max_workers": max_workers,
    }

    try:
        proc = subprocess.run(
            [binary],
            input=_json_dumps(request),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            result = _json_loads(proc.stdout.strip())
            if isinstance(result, dict):
                return result
    except subprocess.TimeoutExpired:
        logger.warning("Go prefetch service timed out after 10s")
    except (OSError, ValueError, RuntimeError) as e:
        logger.debug("Go prefetch call failed: %s", e)

    return None


def go_prefetch_status() -> dict[str, Any]:
    """Get Go prefetch service status."""
    binary = _find_go_prefetch()
    if binary is None:
        return {
            "has_go_prefetch": False,
            "backend": "python_fallback",
        }

    import subprocess

    try:
        proc = subprocess.run(
            [binary],
            input=_json_dumps({"command": "status"}),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            result = _json_loads(proc.stdout.strip())
            if isinstance(result, dict):
                result["has_go_prefetch"] = True
                return result
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
        logger.debug("Go prefetch status failed: %s", e)

    return {
        "has_go_prefetch": True,
        "binary": binary,
        "backend": "go_goroutine",
    }
