"""MCP JSON-RPC conformance helpers.

Works around an upstream MCP Python SDK behavior (observed in mcp 1.28.1,
the latest release as of 2026-07-19) where a request with an *unknown
method* is rejected at the session-validation layer with ``-32602``
(Invalid params) instead of the JSON-RPC-correct ``-32601`` (Method not
found).

Root cause: ``mcp/shared/session.py`` ``BaseSession._receive_loop``
validates the whole incoming request against the ``ClientRequest`` pydantic
union. An unknown method fails union validation and the broad
``except Exception`` handler maps it to ``INVALID_PARAMS``.

These helpers intercept unknown-method *requests* at the transport edge
(the stdio reader loop and an HTTP ASGI middleware) and answer ``-32601``
before the session layer sees them. Traffic with known methods is
untouched. Notifications (no ``id``) are never answered, per JSON-RPC.

Removal condition: delete this module and its two wiring points when the
upstream python-sdk maps unknown methods to ``METHOD_NOT_FOUND`` itself
(verify with ``mcp-conform`` against both stdio and HTTP transports).
"""

from __future__ import annotations

import json
import typing
from functools import lru_cache
from typing import Any

import mcp.types as types
from mcp.shared.message import SessionMessage

# Conservative fallback used only if the SDK union structure changes and
# derivation finds implausibly few methods. Keep in sync with the SDK's
# ClientRequest union (mcp 1.28.1 has 17 members).
_FALLBACK_METHODS = frozenset(
    {
        "completion/complete",
        "initialize",
        "logging/setLevel",
        "ping",
        "prompts/get",
        "prompts/list",
        "resources/list",
        "resources/read",
        "resources/subscribe",
        "resources/templates/list",
        "resources/unsubscribe",
        "tasks/cancel",
        "tasks/get",
        "tasks/list",
        "tasks/result",
        "tools/call",
        "tools/list",
    }
)


@lru_cache(maxsize=1)
def known_client_methods() -> frozenset[str]:
    """Derive the set of known client→server method names from the SDK's
    own ``ClientRequest`` union, so the answer tracks the installed SDK
    version rather than a hand-maintained list.
    """
    try:
        root_ann = types.ClientRequest.model_fields["root"].annotation
        members = typing.get_args(root_ann)
        methods: set[str] = set()
        for member in members:
            field = getattr(member, "model_fields", {}).get("method")
            if field is None:
                continue
            for arg in typing.get_args(field.annotation):
                if isinstance(arg, str):
                    methods.add(arg)
        # The SDK defines ~17 methods; anything under 10 means the union
        # structure changed and derivation failed — use the fallback.
        if len(methods) >= 10:
            return frozenset(methods)
    except Exception:  # noqa: BLE001 — defensive: never break server startup
        pass
    return _FALLBACK_METHODS


def is_known_client_method(method: str) -> bool:
    """True if ``method`` is a known client→server MCP method."""
    return method in known_client_methods()


def unknown_request_method(payload: Any) -> str | None:
    """Return the method name if ``payload`` is a JSON-RPC *request* (has
    ``method`` and ``id``) with an unknown method, else ``None``.

    Notifications (no ``id``) return ``None`` because JSON-RPC forbids
    answering them. Malformed envelopes return ``None`` so the SDK's own
    validation handles them.
    """
    if not isinstance(payload, dict):
        return None
    if payload.get("jsonrpc") != "2.0":
        return None
    method = payload.get("method")
    if not isinstance(method, str):
        return None
    if "id" not in payload:  # notification — must not be answered
        return None
    return None if is_known_client_method(method) else method


def method_not_found_payload(request_id: Any, method: str) -> dict[str, Any]:
    """Build a JSON-RPC ``-32601 Method not found`` error payload."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": types.METHOD_NOT_FOUND,
            "message": f"Method not found: {method}",
        },
    }


def check_session_message(message: SessionMessage) -> SessionMessage | None:
    """stdio-path guard: if ``message`` is a request with an unknown method,
    return the ``-32601`` response to send back to the client; otherwise
    return ``None`` (forward the message to the session normally).
    """
    root = message.message.root
    if isinstance(root, types.JSONRPCRequest) and not is_known_client_method(root.method):
        error = types.JSONRPCError(
            jsonrpc="2.0",
            id=root.id,
            error=types.ErrorData(
                code=types.METHOD_NOT_FOUND,
                message=f"Method not found: {root.method}",
            ),
        )
        return SessionMessage(types.JSONRPCMessage(error))
    return None


class UnknownMethodASGIMiddleware:
    """Pure-ASGI middleware that short-circuits unknown-method JSON-RPC
    POSTs with ``-32601`` before they reach the MCP session layer.

    Only intercepts HTTP POST requests whose JSON body is a single
    JSON-RPC request (dict) with an unknown method. Everything else —
    GET/SSE, DELETE, notifications, batches, malformed JSON — is passed
    through untouched.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        body = b""
        disconnected = False
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                disconnected = True
                break
            if event["type"] == "http.request":
                body += event.get("body", b"")
                if not event.get("more_body", False):
                    break
        if disconnected:
            return

        payload: Any = None
        if body:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = None

        unknown = unknown_request_method(payload)
        if unknown is not None:
            response = json.dumps(
                method_not_found_payload(payload.get("id"), unknown)
            ).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": response})
            return

        # Pass-through: replay the buffered body to the downstream app.
        replayed = False

        async def replay_receive() -> dict[str, Any]:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)
