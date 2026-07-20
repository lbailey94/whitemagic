"""Tests for MCP JSON-RPC conformance helpers (whitemagic.mcp.conformance).

Regression context: the MCP Python SDK (1.28.1) maps unknown-method
requests to -32602 (Invalid params) at the session layer. JSON-RPC/MCP
conformance expects -32601 (Method not found). These tests pin the
transport-edge workaround.
"""
from __future__ import annotations

import json

import mcp.types as types
import pytest
from mcp.shared.message import SessionMessage

from whitemagic.mcp.conformance import (
    UnknownMethodASGIMiddleware,
    check_session_message,
    is_known_client_method,
    known_client_methods,
    method_not_found_payload,
    unknown_request_method,
)


class TestKnownMethods:
    def test_derives_sdk_methods(self):
        methods = known_client_methods()
        # Core methods every MCP client may legitimately send
        assert "initialize" in methods
        assert "ping" in methods
        assert "tools/list" in methods
        assert "tools/call" in methods
        assert "resources/read" in methods
        # SDK 1.28.1 defines 17; require a plausible floor
        assert len(methods) >= 15

    def test_known_and_unknown(self):
        assert is_known_client_method("tools/call")
        assert not is_known_client_method("totally/unknown_method")
        assert not is_known_client_method("")

    def test_fallback_used_when_derivation_fails(self, monkeypatch):
        # Force derivation to see an implausible union and confirm fallback
        import whitemagic.mcp.conformance as conf

        class _FakeFields:
            annotation = int  # not a union of request types

        class _FakeModel:
            model_fields = {"root": _FakeFields()}

        monkeypatch.setattr(conf.types, "ClientRequest", _FakeModel)
        conf.known_client_methods.cache_clear()
        try:
            methods = conf.known_client_methods()
            assert "tools/call" in methods  # fallback list
        finally:
            conf.known_client_methods.cache_clear()


class TestUnknownRequestMethod:
    def test_unknown_request_detected(self):
        payload = {"jsonrpc": "2.0", "id": 1, "method": "foo/bar", "params": {}}
        assert unknown_request_method(payload) == "foo/bar"

    def test_known_request_passes(self):
        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        assert unknown_request_method(payload) is None

    def test_notification_never_answered(self):
        # Unknown method but no id → notification → must not be answered
        payload = {"jsonrpc": "2.0", "method": "foo/bar"}
        assert unknown_request_method(payload) is None

    def test_malformed_envelope_passes_to_sdk(self):
        assert unknown_request_method({"id": 1, "method": "foo/bar"}) is None
        assert unknown_request_method({"jsonrpc": "2.0", "id": 1}) is None
        assert unknown_request_method("not a dict") is None
        assert unknown_request_method(None) is None
        assert unknown_request_method([{"jsonrpc": "2.0", "id": 1, "method": "x/y"}]) is None


class TestMethodNotFoundPayload:
    def test_shape_and_code(self):
        payload = method_not_found_payload(7, "foo/bar")
        assert payload["jsonrpc"] == "2.0"
        assert payload["id"] == 7
        assert payload["error"]["code"] == -32601
        assert "foo/bar" in payload["error"]["message"]

    def test_code_matches_sdk_constant(self):
        payload = method_not_found_payload(1, "x")
        assert payload["error"]["code"] == types.METHOD_NOT_FOUND


class TestCheckSessionMessage:
    def _wrap(self, payload: dict) -> SessionMessage:
        return SessionMessage(types.JSONRPCMessage(payload))

    def test_unknown_request_short_circuits(self):
        msg = self._wrap({"jsonrpc": "2.0", "id": 42, "method": "nope/nope"})
        resp = check_session_message(msg)
        assert resp is not None
        root = resp.message.root
        assert isinstance(root, types.JSONRPCError)
        assert root.id == 42
        assert root.error.code == -32601

    def test_known_request_forwarded(self):
        msg = self._wrap({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        assert check_session_message(msg) is None

    def test_notification_forwarded(self):
        msg = self._wrap({"jsonrpc": "2.0", "method": "notifications/initialized"})
        assert check_session_message(msg) is None


class TestASGIMiddleware:
    def _make_client(self, downstream_spy: dict):
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        async def echo(request):
            body = await request.body()
            downstream_spy["called"] = True
            downstream_spy["body"] = body
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = None
            return JSONResponse({"echo": parsed, "raw_len": len(body)})

        app = Starlette(routes=[Route("/mcp", echo, methods=["POST"])])
        wrapped = UnknownMethodASGIMiddleware(app)
        return TestClient(wrapped)

    def test_unknown_method_short_circuits(self):
        spy: dict = {}
        client = self._make_client(spy)
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 3, "method": "bogus/method"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"]["code"] == -32601
        assert data["id"] == 3
        assert not spy.get("called"), "downstream app must not be called"

    def test_known_method_passes_through(self):
        spy: dict = {}
        client = self._make_client(spy)
        payload = {"jsonrpc": "2.0", "id": 4, "method": "tools/list"}
        resp = client.post("/mcp", json=payload)
        assert resp.status_code == 200
        assert resp.json()["echo"] == payload
        assert spy.get("called")

    def test_notification_passes_through(self):
        spy: dict = {}
        client = self._make_client(spy)
        payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp = client.post("/mcp", json=payload)
        assert resp.status_code == 200
        assert spy.get("called")

    def test_malformed_json_passes_through(self):
        spy: dict = {}
        client = self._make_client(spy)
        resp = client.post(
            "/mcp",
            content=b"{not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert spy.get("called")
        assert spy.get("body") == b"{not json"

    def test_get_passes_through(self):
        async def ok(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        from starlette.testclient import TestClient

        client = TestClient(UnknownMethodASGIMiddleware(ok))
        assert client.get("/mcp").status_code == 200


    @pytest.mark.slow
    def test_sigterm_shutdown_with_idle_stdin(self, tmp_path):
        """SIGTERM must stop the server even when stdin is open and idle.

        Regression test for a flaky shutdown hang (2026-07-19): a plain
        signal.signal() handler calling asyncio.Event.set() did not wake a
        select()-parked event loop (no self-pipe write), and the
        thread-based stdin readline left a blocked executor thread that
        asyncio.run() waited on forever.
        """
        import os
        import signal
        import subprocess
        import sys
        from pathlib import Path

        core_dir = Path(__file__).resolve().parent.parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(core_dir)
        env["WM_STATE_ROOT"] = str(tmp_path / "state")
        env["WM_SKIP_POLYGLOT"] = "1"
        env["WM_SILENT_INIT"] = "1"

        proc = subprocess.Popen(
            [sys.executable, "-m", "whitemagic.run_mcp_lean"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            text=True,
        )
        try:
            assert proc.stdin and proc.stdout
            proc.stdin.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": "test", "version": "0.1"},
                        },
                    }
                )
                + "\n"
            )
            proc.stdin.flush()
            init = json.loads(proc.stdout.readline())
            assert "result" in init
            # stdin stays OPEN but idle — the hang scenario
            proc.send_signal(signal.SIGTERM)
            # Generous: graceful path joins worker threads (bounded ~15s),
            # watchdog hard-bounds at 25s.
            proc.wait(timeout=35)
            assert proc.returncode is not None
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)


class TestLiveStdioConformance:
    """End-to-end: the stdio server must answer -32601 for unknown methods."""

    @pytest.mark.slow
    def test_stdio_unknown_method_returns_32601(self, tmp_path):
        import os
        import subprocess
        import sys
        from pathlib import Path

        core_dir = Path(__file__).resolve().parent.parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(core_dir)
        env["WM_STATE_ROOT"] = str(tmp_path / "state")
        env["WM_SKIP_POLYGLOT"] = "1"
        env["WM_SILENT_INIT"] = "1"

        proc = subprocess.Popen(
            [sys.executable, "-m", "whitemagic.run_mcp_lean"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            text=True,
        )

        def send(msg: dict) -> dict:
            assert proc.stdin and proc.stdout
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()
            return json.loads(proc.stdout.readline())

        try:
            init = send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "0.1"},
                    },
                }
            )
            assert "result" in init
            assert proc.stdin
            proc.stdin.write(
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
            )
            proc.stdin.flush()
            resp = send({"jsonrpc": "2.0", "id": 2, "method": "totally/unknown"})
            assert resp["error"]["code"] == -32601
            # And the session must still be alive afterwards
            ping = send({"jsonrpc": "2.0", "id": 3, "method": "ping"})
            assert "result" in ping
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Server can linger on SIGTERM when stdin is idle (blocked
                # readline thread) — escalate to SIGKILL for test cleanup.
                proc.kill()
                proc.wait(timeout=5)
