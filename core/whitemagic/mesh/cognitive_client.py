# ruff: noqa: BLE001
"""WhiteMagic Cognitive gRPC Client — connects to the Go gateway daemon.

This client provides a Python interface to the CognitiveService gRPC server
running in the Go gateway (wm_gateway). It supports:
- Tool dispatch (streaming)
- Citta stream subscription
- Session management (create, resume)
- Dream event subscription
- Telemetry subscription
- Daemon status and shutdown

Usage::

    from whitemagic.mesh.cognitive_client import CognitiveClient

    client = CognitiveClient()
    client.connect()
    status = client.daemon_status()
    for moment in client.citta_stream():
        print(moment)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Generator

logger = logging.getLogger(__name__)

# Proto imports — generated stubs
try:
    from whitemagic.mesh.proto import mesh_pb2, mesh_pb2_grpc
    import grpc
    HAS_GRPC = True
except ImportError:
    HAS_GRPC = False
    mesh_pb2 = None  # type: ignore[assignment]
    mesh_pb2_grpc = None  # type: ignore[assignment]
    grpc = None  # type: ignore[assignment]

SOCKET_PATH = "/tmp/whitemagic/wm.sock"
TCP_ADDR = "localhost:4730"


class CognitiveClient:
    """gRPC client for the WhiteMagic cognitive gateway."""

    def __init__(
        self,
        socket_path: str | None = None,
        tcp_addr: str | None = None,
    ) -> None:
        self._socket_path = socket_path or os.environ.get("WM_SOCKET_PATH", SOCKET_PATH)
        self._tcp_addr = tcp_addr or os.environ.get("WM_TCP_ADDR", TCP_ADDR)
        self._channel: Any = None
        self._stub: Any = None

    def connect(self) -> bool:
        """Connect to the gateway. Returns True on success."""
        if not HAS_GRPC:
            logger.warning("grpcio not installed — client unavailable")
            return False

        # Try Unix socket first, then TCP
        if os.path.exists(self._socket_path):
            self._channel = grpc.insecure_channel(f"unix://{self._socket_path}")
        else:
            self._channel = grpc.insecure_channel(self._tcp_addr)

        try:
            grpc.channel_ready_future(self._channel).result(timeout=5.0)
            self._stub = mesh_pb2_grpc.CognitiveServiceStub(self._channel)
            logger.info("Connected to cognitive gateway")
            return True
        except Exception as e:
            logger.warning("Failed to connect to gateway: %s", e)
            return False

    def close(self) -> None:
        """Close the connection."""
        if self._channel:
            self._channel.close()
            self._channel = None
            self._stub = None

    @property
    def is_connected(self) -> bool:
        return self._stub is not None

    def call_tool(
        self,
        gana: str,
        tool: str,
        operation: str = "",
        args: dict[str, str] | None = None,
        session_id: str = "",
    ) -> dict[str, Any]:
        """Call a tool via the gateway. Returns the result dict."""
        if not self._stub:
            return {"status": "error", "error": "not connected"}

        request = mesh_pb2.ToolRequest(
            gana=gana,
            tool=tool,
            operation=operation,
            args=args or {},
            session_id=session_id,
        )

        results = []
        for event in self._stub.CallTool(request):
            results.append({
                "status": event.status,
                "request_id": event.request_id,
                "payload": json.loads(event.payload) if event.payload else {},
                "citta": {
                    "timestamp": event.citta.timestamp,
                    "gana": event.citta.gana,
                    "depth_layer": event.citta.depth_layer,
                } if event.canta else None,
            })

        return results[-1] if results else {"status": "error", "error": "no response"}

    def citta_stream(
        self,
        session_id: str = "",
        include_history: bool = False,
        history_count: int = 0,
    ) -> Generator[dict[str, Any], None, None]:
        """Subscribe to the citta stream. Yields citta moments."""
        if not self._stub:
            return

        request = mesh_pb2.CittaSubscribe(
            session_id=session_id,
            include_history=include_history,
            history_count=history_count,
        )

        for moment in self._stub.CittaStream(request):
            yield {
                "timestamp": moment.timestamp,
                "gana": moment.gana,
                "operation": moment.operation,
                "depth_layer": moment.depth_layer,
                "emotional_tone": moment.emotional_tone,
                "coherence": moment.coherence,
                "output_preview": moment.output_preview,
                "cycle_number": moment.cycle_number,
                "neuro_signals": dict(moment.neuro_signals),
            }

    def create_session(
        self,
        agent_id: str = "python-client",
        agent_type: str = "ai",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a new session. Returns session info."""
        if not self._stub:
            return {"status": "error", "error": "not connected"}

        request = mesh_pb2.SessionRequest(
            agent_id=agent_id,
            agent_type=agent_type,
            metadata=metadata or {},
        )

        response = self._stub.CreateSession(request)
        return {
            "session_id": response.session_id,
            "created_at": response.created_at,
            "continuity_context": response.continuity_context,
        }

    def resume_session(
        self,
        session_id: str,
        last_cycle: int = 0,
    ) -> Generator[dict[str, Any], None, None]:
        """Resume a session and stream citta moments."""
        if not self._stub:
            return

        request = mesh_pb2.SessionResume(
            session_id=session_id,
            last_cycle=last_cycle,
        )

        for moment in self._stub.ResumeSession(request):
            yield {
                "timestamp": moment.timestamp,
                "gana": moment.gana,
                "operation": moment.operation,
                "depth_layer": moment.depth_layer,
                "coherence": moment.coherence,
                "cycle_number": moment.cycle_number,
            }

    def dream_stream(
        self,
        session_id: str = "",
        include_artifacts: bool = False,
    ) -> Generator[dict[str, Any], None, None]:
        """Subscribe to dream events."""
        if not self._stub:
            return

        request = mesh_pb2.DreamSubscribe(
            session_id=session_id,
            include_artifacts=include_artifacts,
        )

        for event in self._stub.DreamEvents(request):
            yield {
                "timestamp": event.timestamp,
                "phase": event.phase,
                "description": event.description,
                "resonance": event.resonance,
            }

    def telemetry_stream(
        self,
        interval_ms: int = 1000,
    ) -> Generator[dict[str, Any], None, None]:
        """Subscribe to telemetry snapshots."""
        if not self._stub:
            return

        request = mesh_pb2.TelemetryRequest(interval_ms=interval_ms)

        for snap in self._stub.Telemetry(request):
            yield {
                "timestamp": snap.timestamp,
                "connected_clients": snap.connected_clients,
                "privacy_status": snap.privacy_status,
                "bytes_egress": snap.bytes_egress,
            }

    def daemon_status(self) -> dict[str, Any]:
        """Get daemon status."""
        if not self._stub:
            return {"status": "error", "error": "not connected"}

        response = self._stub.DaemonStatus(mesh_pb2.StatusRequest())
        return {
            "running": response.running,
            "uptime_seconds": response.uptime_seconds,
            "version": response.version,
            "connected_clients": response.connected_clients,
            "privacy_status": response.privacy_status,
            "active_loops": list(response.active_loops),
        }

    def daemon_shutdown(self, force: bool = False) -> dict[str, Any]:
        """Request daemon shutdown."""
        if not self._stub:
            return {"status": "error", "error": "not connected"}

        request = mesh_pb2.ShutdownRequest(force=force)
        response = self._stub.DaemonShutdown(request)
        return {
            "running": response.running,
            "version": response.version,
        }


_client: CognitiveClient | None = None


def get_cognitive_client() -> CognitiveClient:
    """Get the global CognitiveClient singleton."""
    global _client
    if _client is None:
        _client = CognitiveClient()
    return _client
