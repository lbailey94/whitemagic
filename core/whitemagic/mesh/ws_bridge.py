# ruff: noqa: BLE001
"""WebSocket bridge — connects PWA/browser clients to the cognitive gateway.

This module runs a lightweight WebSocket server that bridges browser-based
PWA clients to the Go gRPC cognitive gateway. It translates between
JSON-based WebSocket messages and gRPC calls.

Usage::

    from whitemagic.mesh.ws_bridge import WebSocketBridge

    bridge = WebSocketBridge(port=4731)
    bridge.start()  # runs in background thread
    # ... serves WebSocket connections at ws://localhost:4731
    bridge.stop()
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

try:
    import websockets
    from websockets.asyncio.server import serve
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    websockets = None  # type: ignore[assignment]
    serve = None  # type: ignore[assignment]


class WebSocketBridge:
    """WebSocket → gRPC bridge for PWA clients."""

    def __init__(
        self,
        port: int = 4731,
        grpc_socket: str = "/tmp/whitemagic/wm.sock",
    ) -> None:
        self._port = port
        self._grpc_socket = grpc_socket
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: Any = None
        self._running = False
        self._clients: set[Any] = set()

    def start(self) -> bool:
        """Start the WebSocket bridge in a background thread."""
        if not HAS_WEBSOCKETS:
            logger.warning("websockets not installed — bridge unavailable")
            return False

        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(target=self._run, name="wm_ws_bridge", daemon=True)
        self._thread.start()
        logger.info("WebSocket bridge started on port %d", self._port)
        return True

    def stop(self) -> None:
        """Stop the WebSocket bridge."""
        self._running = False
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    async def _shutdown(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def _run(self) -> None:
        """Run the WebSocket server in its own event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def handler(websocket: Any) -> None:
            """Handle a WebSocket connection."""
            self._clients.add(websocket)
            logger.info("WS client connected (total=%d)", len(self._clients))

            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        response = await self._handle_message(data)
                        await websocket.send(json.dumps(response))
                    except json.JSONDecodeError:
                        await websocket.send(json.dumps({"error": "invalid JSON"}))
                    except Exception as e:
                        await websocket.send(json.dumps({"error": str(e)}))
            except Exception:
                logger.debug("Ignored error in ws_bridge.py:103")
            finally:
                self._clients.discard(websocket)
                logger.info("WS client disconnected (total=%d)", len(self._clients))

        async def main() -> None:
            self._server = await serve(handler, "localhost", self._port)
            await asyncio.Future()  # run forever

        try:
            self._loop.run_until_complete(main())
        except Exception as e:
            logger.error("WebSocket bridge error: %s", e)

    async def _handle_message(self, data: dict[str, Any]) -> dict[str, Any]:
        """Route a WebSocket message to the appropriate handler."""
        msg_type = data.get("type", "")

        if msg_type == "status":
            return await self._handle_status()
        elif msg_type == "call_tool":
            return await self._handle_call_tool(data)
        elif msg_type == "create_session":
            return await self._handle_create_session(data)
        elif msg_type == "telemetry":
            return await self._handle_telemetry(data)
        else:
            return {"error": f"unknown message type: {msg_type}"}

    async def _handle_status(self) -> dict[str, Any]:
        """Get daemon status via gRPC."""
        try:
            from whitemagic.mesh.cognitive_client import get_cognitive_client
            client = get_cognitive_client()
            if not client.is_connected:
                client.connect()
            return client.daemon_status()
        except Exception as e:
            return {"error": str(e)}

    async def _handle_call_tool(self, data: dict[str, Any]) -> dict[str, Any]:
        """Call a tool via gRPC."""
        try:
            from whitemagic.mesh.cognitive_client import get_cognitive_client
            client = get_cognitive_client()
            if not client.is_connected:
                client.connect()
            return client.call_tool(
                gana=data.get("gana", ""),
                tool=data.get("tool", ""),
                operation=data.get("operation", ""),
                args=data.get("args", {}),
                session_id=data.get("session_id", ""),
            )
        except Exception as e:
            return {"error": str(e)}

    async def _handle_create_session(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a session via gRPC."""
        try:
            from whitemagic.mesh.cognitive_client import get_cognitive_client
            client = get_cognitive_client()
            if not client.is_connected:
                client.connect()
            return client.create_session(
                agent_id=data.get("agent_id", "pwa"),
                agent_type=data.get("agent_type", "pwa"),
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            return {"error": str(e)}

    async def _handle_telemetry(self, data: dict[str, Any]) -> dict[str, Any]:
        """Get a single telemetry snapshot (non-streaming for WS)."""
        try:
            from whitemagic.core.consciousness.consciousness_loop import get_daemon
            daemon = get_daemon()
            return daemon.status()
        except Exception as e:
            return {"error": str(e)}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def client_count(self) -> int:
        return len(self._clients)


_bridge: WebSocketBridge | None = None
_bridge_lock = threading.RLock()


def get_ws_bridge() -> WebSocketBridge:
    """Get the global WebSocketBridge singleton."""
    global _bridge
    if _bridge is None:
        with _bridge_lock:
            if _bridge is None:
                _bridge = WebSocketBridge()
    return _bridge
