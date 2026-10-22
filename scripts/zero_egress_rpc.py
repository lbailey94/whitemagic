#!/usr/bin/env python3
"""Bounded JSON-RPC create/recall journey for an isolated WM Gen3 full server."""
from __future__ import annotations

import json
import errno
import os
import queue
import socket
import subprocess
import sys
import threading
import time
from typing import Any

RPC_TIMEOUT_SECONDS = 20.0
SERVER_STOP_SECONDS = 5.0
EXPECTED_PROFILE = "full"
MARKER = "WM_ZERO_EGRESS_20261022_COPPER_RIVER_9182"


class HarnessError(RuntimeError):
    pass


class HostPolicyBlock(HarnessError):
    pass


def classify_egress_error(error_number: int | None) -> str:
    """Separate namespace routing evidence from host-policy denial."""
    if error_number in (errno.ENETUNREACH, errno.EHOSTUNREACH):
        return "namespace-route-block"
    if error_number in (errno.EPERM, errno.EACCES):
        return "host-policy-block"
    return "unexpected-connect-error"


def check_egress_blocked(socket_factory=socket.socket) -> None:
    probe = None
    try:
        probe = socket_factory(socket.AF_INET, socket.SOCK_STREAM)
        probe.settimeout(2.0)
        probe.connect(("1.1.1.1", 443))
    except OSError as exc:
        classification = classify_egress_error(exc.errno)
        if classification == "namespace-route-block":
            print(f"[negative-control] PASS: external TCP connect blocked by namespace routing ({errno.errorcode.get(exc.errno, exc.errno)})")
            return
        if classification == "host-policy-block":
            raise HostPolicyBlock(
                f"socket/connect denied by host policy ({errno.errorcode.get(exc.errno, exc.errno)}); not namespace proof"
            ) from exc
        raise HarnessError(
            f"negative control got unexpected connect error {errno.errorcode.get(exc.errno, exc.errno)}: {exc}"
        ) from exc
    else:
        raise HarnessError("negative control unexpectedly connected to external TCP endpoint")
    finally:
        if probe is not None:
            probe.close()


def decode_tool_payload(response: dict[str, Any], expected_id: int) -> dict[str, Any]:
    """Reject wrong IDs, JSON-RPC errors, missing content, and malformed tool JSON."""
    if response.get("id") != expected_id:
        raise HarnessError(f"RPC id mismatch: expected {expected_id}, got {response.get('id')!r}")
    if "error" in response:
        raise HarnessError(f"JSON-RPC error for id {expected_id}: {response['error']!r}")
    result = response.get("result")
    if not isinstance(result, dict) or result.get("isError") is True:
        raise HarnessError(f"tool call id {expected_id} returned an error result: {result!r}")
    content = result.get("content")
    if not isinstance(content, list) or not content or not isinstance(content[0], dict):
        raise HarnessError(f"tool call id {expected_id} returned no text content")
    text = content[0].get("text")
    if not isinstance(text, str):
        raise HarnessError(f"tool call id {expected_id} returned non-text content")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HarnessError(f"tool call id {expected_id} returned malformed JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise HarnessError(f"tool call id {expected_id} payload was not an object")
    return payload


class RpcClient:
    def __init__(self, binary: str, store: str) -> None:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ["HOME"],
            "XDG_DATA_HOME": os.environ["XDG_DATA_HOME"],
            "XDG_CONFIG_HOME": os.environ["XDG_CONFIG_HOME"],
            "WM_HOMEOSTASIS_FROZEN": "1",
        }
        self.proc = subprocess.Popen(
            [binary, "serve", "--profile", EXPECTED_PROFILE, "--store", store,
             "--transport", "stdio", "--no-sweep", "--no-noise"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.stderr_tail: list[str] = []
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self) -> None:
        assert self.proc.stdout
        try:
            for line in self.proc.stdout:
                self.lines.put(line)
        finally:
            self.lines.put(None)

    def _read_stderr(self) -> None:
        assert self.proc.stderr
        for line in self.proc.stderr:
            self.stderr_tail.append(line.rstrip()[:500])
            if len(self.stderr_tail) > 12:
                del self.stderr_tail[:-12]

    def send_notification(self, method: str, params: dict[str, Any]) -> None:
        assert self.proc.stdin
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params}) + "\n")
        self.proc.stdin.flush()

    def rpc(self, request_id: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request_id, int) or request_id <= 0:
            raise HarnessError("RPC IDs must be positive integers")
        assert self.proc.stdin
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id,
                                          "method": method, "params": params}) + "\n")
        self.proc.stdin.flush()
        deadline = time.monotonic() + RPC_TIMEOUT_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise HarnessError(f"deadline exceeded for RPC id {request_id} ({method})")
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty as exc:
                raise HarnessError(f"deadline exceeded for RPC id {request_id} ({method})") from exc
            if line is None:
                code = self.proc.poll()
                tail = " | ".join(self.stderr_tail)
                raise HarnessError(f"server stdout closed before RPC id {request_id} response (exit={code}); stderr={tail}")
            try:
                response = json.loads(line)
            except json.JSONDecodeError as exc:
                raise HarnessError(f"malformed JSON-RPC line while awaiting id {request_id}: {line[:300]!r}") from exc
            if not isinstance(response, dict):
                raise HarnessError(f"non-object JSON-RPC response while awaiting id {request_id}")
            if response.get("id") != request_id:
                raise HarnessError(f"unexpected response id while awaiting {request_id}: {response.get('id')!r}")
            return response

    def close(self) -> None:
        if self.proc.stdin:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=SERVER_STOP_SECONDS)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=SERVER_STOP_SECONDS)
        for stream in (self.proc.stdout, self.proc.stderr):
            if stream:
                stream.close()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessError(message)


def run(binary: str, store: str) -> None:
    client = RpcClient(binary, store)
    try:
        init = client.rpc(1, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "wm-no-network-qualification", "version": "1"},
        })
        info = init.get("result", {}).get("serverInfo", {})
        expected_version = os.environ.get("WM_VERSION")
        require(bool(expected_version), "WM_VERSION not supplied by binary identity check")
        require(info.get("version") == expected_version,
                f"binary --version and initialize serverInfo differ: expected {expected_version}, got {info!r}")
        require(info.get("profile") == EXPECTED_PROFILE, f"expected profile {EXPECTED_PROFILE}, got {info!r}")
        require(info.get("name") == "whitemagic-gen3", f"unexpected server identity: {info!r}")
        client.send_notification("notifications/initialized", {})

        listed = client.rpc(2, "tools/list", {})
        tools = listed.get("result", {}).get("tools")
        require(isinstance(tools, list), "tools/list did not return a tools array")
        names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
        require({"memory.create", "memory.search"} <= names,
                f"full profile missing create/search tools: {sorted({'memory.create', 'memory.search'} - names)}")
        print(f"[rpc] initialize OK; tools/list OK ({len(tools)} tools; create+search present)")

        created_response = client.rpc(3, "tools/call", {
            "name": "memory.create",
            "arguments": {"content": MARKER, "galaxy": "codex", "tags": ["no-network-qualification"]},
        })
        created = decode_tool_payload(created_response, 3)
        require(created.get("status") == "success", f"memory.create did not succeed: {created!r}")
        memory_id = created.get("id") or created.get("uuid")
        require(isinstance(memory_id, str) and memory_id, f"memory.create omitted a persistent ID: {created!r}")
        print(f"[rpc] memory.create OK (id {memory_id})")

        searched_response = client.rpc(4, "tools/call", {
            "name": "memory.search",
            "arguments": {"query": MARKER, "galaxy": "codex", "limit": 5},
        })
        searched = decode_tool_payload(searched_response, 4)
        results = searched.get("results")
        require(searched.get("status") == "success" and isinstance(results, list),
                f"memory.search failed or returned malformed results: {searched!r}")
        matches = [item for item in results if isinstance(item, dict) and
                   (item.get("id") == memory_id or item.get("uuid") == memory_id) and
                   MARKER in item.get("content", "")]
        require(bool(matches), f"search did not return the exact created item {memory_id}: {searched!r}")
        print("[rpc] memory.search returned the exact created marker and ID")
        print(f"[product] PASS: Gen3 {expected_version} full-profile memory create+recall completed over stdio")
    finally:
        client.close()


if __name__ == "__main__":
    if sys.argv[1:] == ["--check-egress"]:
        try:
            check_egress_blocked()
        except HostPolicyBlock as exc:
            print(f"[negative-control] HOST-POLICY-BLOCK: {exc}", file=sys.stderr)
            raise SystemExit(42)
        except HarnessError as exc:
            print(f"[negative-control] FAIL: {exc}", file=sys.stderr)
            raise SystemExit(1)
        raise SystemExit(0)
    try:
        binary = os.environ["WM_BINARY"]
        store = os.environ["STORE"]
        run(binary, store)
    except (KeyError, HarnessError, OSError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
