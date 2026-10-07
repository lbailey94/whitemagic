#!/usr/bin/env python3
"""wm_client.py — stdlib-only client for the WhiteMagic ``wm-node`` daemon.

The daemon (Phase 2 of the Agentic Consensus Network) listens on a Unix domain
socket and speaks newline-delimited JSON-RPC 2.0: one JSON object per line, one
response line per request. This module is both a CLI and a tiny importable
class.

Command line
------------
Socket resolution: ``--socket`` wins, else ``WM_NODE_SOCKET``.

    # Node status
    python3 scripts/wm_client.py --socket /tmp/wm-node.sock call node.status

    # Deposit a generic tuple (ttl 60s)
    python3 scripts/wm_client.py call tuple.put \
        '{"kind":"Generic","tag":"greet","payload":"hello","ttl_ms":60000}'

    # Read (non-destructive) then take (destructive) by pattern
    python3 scripts/wm_client.py call tuple.get  '{"kind":"Generic","tag":"greet"}'
    python3 scripts/wm_client.py call tuple.take '{"kind":"Generic","tag":"greet"}'

    # Emit a decaying pheromone signal and sense the field
    python3 scripts/wm_client.py call signal.emit \
        '{"path":"src/lib.rs","scope":["fn:main"],"intensity":0.8,
          "half_life":30000,"issuer":"opencode"}'
    python3 scripts/wm_client.py call signal.read '{"path":"src/lib.rs"}'

    # Proposal scaffold: put, vote, inspect
    python3 scripts/wm_client.py call proposal.put \
        '{"target":"src/x.rs","required_votes":2,"skeleton":{"target_file":"src/x.rs"}}'
    python3 scripts/wm_client.py call proposal.vote \
        '{"proposal_id":"<uuid>","validator_id":"validator-a",
          "decision":"approve","causal_lift":0.4}'
    python3 scripts/wm_client.py call proposal.get '{"proposal_id":"<uuid>"}'

Importable
----------
    from wm_client import Client, RpcError, TransportError

    with Client("/tmp/wm-node.sock", timeout=5.0) as node:
        status = node.call("node.status")
        print(status["version"])
        node.call("tuple.put", {"kind": "Generic", "tag": "t", "payload": "v"})

``Client.call`` returns the JSON-RPC ``result`` and raises :class:`RpcError`
for protocol-level errors or :class:`TransportError` for socket-level failures.

Exit codes (CLI): 0 = result, 1 = JSON-RPC error response, 2 = transport or
usage error. The full response envelope is printed as pretty JSON (use
``--compact`` for one line).
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from typing import Any

__all__ = ["Client", "WMNodeError", "TransportError", "RpcError", "main"]

DEFAULT_TIMEOUT = 10.0
MAX_FRAME_BYTES = 8 * 1024 * 1024
VERSION = "wm-client/1"


class WMNodeError(Exception):
    """Base class for wm-node client failures."""


class TransportError(WMNodeError):
    """The socket could not be reached, or the reply was not a valid frame."""


class RpcError(WMNodeError):
    """The node returned a JSON-RPC error object."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(f"JSON-RPC error {code}: {message}")
        self.code = code
        self.message = message
        self.data = data


class Client:
    """Tiny newline-delimited JSON-RPC 2.0 client over a Unix socket.

    Args:
        socket_path: Path to ``wm-node.sock``. Falls back to ``WM_NODE_SOCKET``.
        timeout: Per-operation timeout in seconds for connect/send/recv.
    """

    def __init__(self, socket_path: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> None:
        resolved = socket_path or os.environ.get("WM_NODE_SOCKET") or ""
        if not resolved:
            raise ValueError(
                "no socket path: pass socket_path/--socket or set WM_NODE_SOCKET"
            )
        self.socket_path = resolved
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._buf = b""
        self._next_id = 1

    # -- lifecycle ---------------------------------------------------------

    def connect(self) -> "Client":
        """Connect to the node (idempotent). Raises :class:`TransportError`."""
        if self._sock is not None:
            return self
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(self.socket_path)
        except FileNotFoundError:
            sock.close()
            raise TransportError(
                f"wm-node socket not found: {self.socket_path} (is wm-node running?)"
            ) from None
        except ConnectionRefusedError:
            sock.close()
            raise TransportError(
                f"connection refused: {self.socket_path} exists but no listener "
                "(stale socket?)"
            ) from None
        except socket.timeout:
            sock.close()
            raise TransportError(f"timed out connecting to {self.socket_path}") from None
        except OSError as exc:
            sock.close()
            raise TransportError(f"cannot connect to {self.socket_path}: {exc}") from exc
        self._sock = sock
        self._buf = b""
        return self

    def close(self) -> None:
        """Close the connection if open."""
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None
                self._buf = b""

    def __enter__(self) -> "Client":
        return self.connect()

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- protocol ----------------------------------------------------------

    def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        req_id: int | None = None,
    ) -> dict[str, Any]:
        """Send one request and return the full JSON-RPC response envelope."""
        self.connect()
        if req_id is None:
            req_id = self._next_id
            self._next_id += 1
        frame = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            frame["params"] = params
        payload = json.dumps(frame, separators=(",", ":")).encode("utf-8") + b"\n"
        assert self._sock is not None
        try:
            self._sock.sendall(payload)
        except socket.timeout:
            raise TransportError(f"timed out sending to {self.socket_path}") from None
        except OSError as exc:
            raise TransportError(f"send failed: {exc}") from exc
        return self._recv_frame()

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a request and return its ``result``.

        Raises :class:`RpcError` when the node returns an error object.
        """
        response = self.request(method, params)
        if isinstance(response.get("error"), dict):
            err = response["error"]
            raise RpcError(
                int(err.get("code", 0)), str(err.get("message", "unknown error")), err.get("data")
            )
        if "result" not in response:
            raise TransportError(f"malformed response envelope: {response!r}")
        return response["result"]

    def _recv_frame(self) -> dict[str, Any]:
        assert self._sock is not None
        while b"\n" not in self._buf:
            try:
                chunk = self._sock.recv(65536)
            except socket.timeout:
                raise TransportError("timed out waiting for a response") from None
            except OSError as exc:
                raise TransportError(f"receive failed: {exc}") from exc
            if not chunk:
                raise TransportError("wm-node closed the connection")
            self._buf += chunk
            if len(self._buf) > MAX_FRAME_BYTES:
                raise TransportError("response frame exceeds maximum size")
        line, self._buf = self._buf.split(b"\n", 1)
        try:
            decoded = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TransportError(f"invalid JSON frame from node: {exc}") from exc
        if not isinstance(decoded, dict):
            raise TransportError(f"expected a JSON object frame, got: {decoded!r}")
        return decoded


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wm_client.py",
        description="call the WhiteMagic wm-node daemon over its Unix socket",
        epilog="socket resolution: --socket, then WM_NODE_SOCKET",
    )
    parser.add_argument(
        "--socket",
        default=os.environ.get("WM_NODE_SOCKET", ""),
        help="path to wm-node.sock (default: $WM_NODE_SOCKET)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"connect/send/recv timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    call = sub.add_parser("call", help="invoke a wm-node JSON-RPC method")
    call.add_argument("method", help="e.g. node.status, tuple.put, signal.read")
    call.add_argument(
        "params",
        nargs="?",
        default="{}",
        help="JSON object of parameters (default: {})",
    )
    call.add_argument(
        "--compact",
        action="store_true",
        help="print the response as a single compact JSON line",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.socket:
        parser.error("--socket is required (or set WM_NODE_SOCKET)")
    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as exc:
        print(f"wm_client: invalid params JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(params, dict):
        print("wm_client: params must be a JSON object", file=sys.stderr)
        return 2

    client = Client(args.socket, timeout=args.timeout)
    try:
        response = client.request(args.method, params)
    except TransportError as exc:
        print(f"wm_client: {exc}", file=sys.stderr)
        return 2
    finally:
        client.close()

    if args.compact:
        print(json.dumps(response, separators=(",", ":"), sort_keys=True))
    else:
        print(json.dumps(response, indent=2, sort_keys=True))
    return 1 if isinstance(response.get("error"), dict) else 0


if __name__ == "__main__":
    sys.exit(main())
