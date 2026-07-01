# ruff: noqa: BLE001
"""Chrome DevTools Protocol (CDP) Connection.

WebSocket-based communication with Chrome/Chromium for browser automation.
Based on the insight: "CDP opens WebSocket to browser"

Usage:
    async with CDPConnection("ws://localhost:9222/devtools/page/...") as cdp:
        result = await cdp.send("Page.navigate", {"url": "https://example.com"})
"""

from __future__ import annotations

import asyncio
import logging
import urllib.parse
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

# Optional websockets import
WebSocketClientProtocol = Any
try:
    import websockets

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

# Optional httpx import for discovery
try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


def _validate_url(url: str) -> None:
    """Validate URL to prevent dangerous schemes like file://."""
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        raise ValueError(f"URL must include scheme: {url}")
    allowed_schemes = {"http", "https"}
    if parsed.scheme not in allowed_schemes:
        raise ValueError(
            f"URL scheme '{parsed.scheme}' not allowed. Only {allowed_schemes} are permitted."
        )


def _validate_javascript(expression: str) -> None:
    """Basic validation for JavaScript expression to prevent obviously dangerous code."""
    if not expression or not expression.strip():
        raise ValueError("JavaScript expression cannot be empty")
    # Limit length to prevent massive payloads
    if len(expression) > 100000:
        raise ValueError("JavaScript expression too long (max 100000 characters)")
    # Basic check for obviously dangerous patterns (not exhaustive, just defense-in-depth)
    dangerous_patterns = [
        "eval(",
        "execScript(",
        "document.cookie",
        "localStorage.",
        "sessionStorage.",
    ]
    for pattern in dangerous_patterns:
        if pattern in expression:
            raise ValueError(
                f"JavaScript expression contains potentially dangerous pattern: {pattern}"
            )


@dataclass
class CDPResponse:
    """Response from a CDP command."""

    id: int
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    @property
    def success(self) -> bool:
        """
        Perform the success operation.

        Returns:
            bool
        """
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "id": self.id,
            "result": self.result,
            "error": self.error,
            "success": self.success,
        }


@dataclass
class CDPEvent:
    """Event received from CDP."""

    method: str
    params: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "method": self.method,
            "params": self.params,
            "timestamp": self.timestamp,
        }


class CDPConnection:
    """Chrome DevTools Protocol WebSocket connection.

    Provides async communication with Chrome/Chromium for:
    - Navigation
    - DOM inspection
    - JavaScript execution
    - Screenshot capture
    - Network monitoring
    """

    def __init__(self, ws_url: str):
        """Initialize CDP connection.

        Args:
            ws_url: WebSocket URL from Chrome DevTools (e.g., ws://localhost:9222/devtools/page/...)

        """
        if not HAS_WEBSOCKETS:
            raise ImportError("websockets required: pip install websockets")

        parsed = urllib.parse.urlparse(ws_url)
        if parsed.scheme not in {"ws", "wss"}:
            raise ValueError(
                f"WebSocket URL must use ws:// or wss:// scheme, got: {ws_url}"
            )
        if not parsed.hostname or parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError(
                f"WebSocket URL must connect to localhost for security, got: {ws_url}"
            )

        self.ws_url = ws_url
        self._ws: WebSocketClientProtocol | None = None
        self._message_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._event_handlers: dict[
            str, list[Callable[[CDPEvent], Awaitable[None]]]
        ] = {}
        self._receiver_task: asyncio.Task | None = None
        self._connected = False

    async def connect(self) -> None:
        """Establish WebSocket connection to Chrome."""
        self._ws = await websockets.connect(self.ws_url)
        self._connected = True
        self._receiver_task = asyncio.create_task(self._receive_messages())

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._connected = False
        if self._receiver_task:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                logger.debug("Swallowed exception", exc_info=True)
        if self._ws:
            await self._ws.close()

    async def __aenter__(self) -> CDPConnection:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.disconnect()

    async def send(
        self, method: str, params: dict[str, Any] | None = None
    ) -> CDPResponse:
        """Send a CDP command and wait for response.

        Args:
            method: CDP method (e.g., "Page.navigate", "DOM.getDocument")
            params: Method parameters

        Returns:
            CDPResponse with result or error

        """
        if not self._connected or not self._ws:
            raise RuntimeError("Not connected to Chrome")

        self._message_id += 1
        msg_id = self._message_id

        message = {
            "id": msg_id,
            "method": method,
            "params": params or {},
        }

        # Create future for response
        future: asyncio.Future[CDPResponse] = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = future

        # Send message
        await self._ws.send(_json_dumps(message))

        # Wait for response
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except TimeoutError:
            del self._pending[msg_id]
            return CDPResponse(
                id=msg_id, error={"message": "Timeout waiting for response"}
            )

    async def _receive_messages(self) -> None:
        """Background task to receive and route messages."""
        try:
            ws = self._ws
            if ws is None:
                return

            async for message in ws:
                data = _json_loads(message)

                if "id" in data:
                    msg_id = data["id"]
                    if msg_id in self._pending:
                        future = self._pending.pop(msg_id)
                        response = CDPResponse(
                            id=msg_id,
                            result=data.get("result"),
                            error=data.get("error"),
                        )
                        future.set_result(response)

                elif "method" in data:
                    event = CDPEvent(
                        method=data["method"],
                        params=data.get("params", {}),
                    )
                    await self._dispatch_event(event)

        except asyncio.CancelledError:
            pass  # Task cancellation is expected
        except Exception as e:
            logger.warning("CDP connection error: %s", e, exc_info=True)
            self._connected = False

    async def _dispatch_event(self, event: CDPEvent) -> None:
        """Dispatch event to registered handlers."""
        handlers = self._event_handlers.get(event.method, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                logger.debug(
                    "CDP event handler error, skipping handler"
                )  # Don't let handler errors break event loop

    def on(
        self, event_name: str, handler: Callable[[CDPEvent], Awaitable[None]]
    ) -> None:
        """Register an event handler.

        Args:
            event_name: CDP event name (e.g., "Page.loadEventFired")
            handler: Async function to call when event occurs

        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    def off(
        self, event_name: str, handler: Callable[[CDPEvent], Awaitable[None]]
    ) -> None:
        """Remove an event handler."""
        if event_name in self._event_handlers:
            try:
                self._event_handlers[event_name].remove(handler)
            except ValueError:
                logger.debug("Swallowed exception", exc_info=True)

    # Convenience methods for common operations

    async def enable_page(self) -> CDPResponse:
        """Enable Page domain events."""
        return await self.send("Page.enable")

    async def enable_dom(self) -> CDPResponse:
        """Enable DOM domain events."""
        return await self.send("DOM.enable")

    async def enable_network(self) -> CDPResponse:
        """Enable Network domain events."""
        return await self.send("Network.enable")

    async def navigate(self, url: str) -> CDPResponse:
        """Navigate to a URL."""
        _validate_url(url)
        return await self.send("Page.navigate", {"url": url})

    async def get_document(self) -> CDPResponse:
        """Get the root DOM node."""
        return await self.send("DOM.getDocument")

    async def query_selector(self, node_id: int, selector: str) -> CDPResponse:
        """Find element by CSS selector."""
        return await self.send(
            "DOM.querySelector",
            {
                "nodeId": node_id,
                "selector": selector,
            },
        )

    async def get_outer_html(self, node_id: int) -> CDPResponse:
        """Get outer HTML of a node."""
        return await self.send("DOM.getOuterHTML", {"nodeId": node_id})

    async def evaluate(self, expression: str) -> CDPResponse:
        """Evaluate JavaScript in the page context."""
        _validate_javascript(expression)
        return await self.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
            },
        )

    async def screenshot(self, format: str = "png", quality: int = 80) -> CDPResponse:
        """Capture page screenshot."""
        params: dict[str, Any] = {"format": format}
        if format == "jpeg":
            params["quality"] = quality
        return await self.send("Page.captureScreenshot", params)


async def discover_targets(
    host: str = "localhost", port: int = 9222
) -> list[dict[str, Any]]:
    """Discover available Chrome debugging targets.

    Args:
        host: Chrome host
        port: Chrome debugging port

    Returns:
        List of available targets with their WebSocket URLs

    """
    if not HAS_HTTPX:
        raise ImportError("httpx required: pip install httpx")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://{host}:{port}/json")
        payload = response.json()
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []


async def connect_to_chrome(
    host: str = "localhost",
    port: int = 9222,
    target_type: str = "page",
) -> CDPConnection:
    """Connect to Chrome, auto-discovering the WebSocket URL.

    Args:
        host: Chrome host
        port: Chrome debugging port
        target_type: Type of target to connect to ("page", "browser", etc.)

    Returns:
        Connected CDPConnection instance

    """
    targets = await discover_targets(host, port)

    # Find matching target
    for target in targets:
        if target.get("type") == target_type:
            ws_url = target.get("webSocketDebuggerUrl")
            if ws_url:
                connection = CDPConnection(ws_url)
                await connection.connect()
                return connection

    raise RuntimeError(
        f"No {target_type} target found. Is Chrome running with --remote-debugging-port={port}?"
    )
