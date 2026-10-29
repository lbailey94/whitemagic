#!/usr/bin/env python3
"""External stdio + Streamable HTTP compatibility fixture and latency probe.

Runs against an exact `wm` binary and a fresh temporary store. It emits raw
round-trip timings and p50/p95/p99 summaries; it does not invoke a real MCP
provider or write memory records.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import select
import socket
import statistics
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

VERSION = "2026-07-28"
CAPS = {
    "io.modelcontextprotocol/protocolVersion": VERSION,
    "io.modelcontextprotocol/clientCapabilities": {},
}


def modern(method: str, params: dict[str, Any] | None = None, ident: int = 1) -> dict[str, Any]:
    args = dict(params or {})
    args["_meta"] = dict(CAPS)
    return {"jsonrpc": "2.0", "id": ident, "method": method, "params": args}


def assert_rpc(response: dict[str, Any], ident: int, *, error: int | None = None) -> None:
    assert response.get("jsonrpc") == "2.0", response
    assert response.get("id") == ident, response
    if error is None:
        assert "result" in response and "error" not in response, response
    else:
        assert response.get("error", {}).get("code") == error, response


class StdioServer:
    def __init__(self, binary: Path, store: Path, profile: str):
        self.proc = subprocess.Popen(
            [str(binary), "--store", str(store), "serve", "--profile", profile,
             "--no-sweep", "--no-noise", "--transport", "stdio"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1,
        )

    def call(self, request: dict[str, Any], timeout: float = 15.0) -> tuple[dict[str, Any], float]:
        assert self.proc.stdin and self.proc.stdout
        start = time.perf_counter_ns()
        self.proc.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.proc.stdin.flush()
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            raise TimeoutError("stdio MCP response timed out")
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(f"stdio MCP process exited with {self.proc.poll()}")
        return json.loads(line), (time.perf_counter_ns() - start) / 1_000_000

    def notification_then_ping(self, notification: dict[str, Any], ping: dict[str, Any]) -> dict[str, Any]:
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(json.dumps(notification, separators=(",", ":")) + "\n")
        self.proc.stdin.write(json.dumps(ping, separators=(",", ":")) + "\n")
        self.proc.stdin.flush()
        ready, _, _ = select.select([self.proc.stdout], [], [], 15.0)
        if not ready:
            raise TimeoutError("stdio response after notification timed out")
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("stdio server exited after notification")
        response = json.loads(line)
        assert response.get("id") == ping["id"], response
        return response

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            self.proc.wait(timeout=5)


class HttpServer:
    def __init__(self, binary: Path, store: Path, profile: str):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.proc = subprocess.Popen(
            [str(binary), "--store", str(store), "serve", "--profile", profile,
             "--no-sweep", "--no-noise", "--transport", "http",
             "--bind", f"127.0.0.1:{self.port}"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.wait_ready()

    def wait_ready(self) -> None:
        for _ in range(100):
            if self.proc.poll() is not None:
                raise RuntimeError(f"HTTP MCP process exited with {self.proc.returncode}")
            try:
                status, _, _ = self.request("GET", "/health", b"")
                if status == 200:
                    return
            except OSError:
                pass
            time.sleep(0.05)
        raise TimeoutError("HTTP MCP server did not become ready")

    def request(self, method: str, path: str, body: bytes,
                headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        conn.request(method, path, body=body if method != "GET" else None, headers=headers or {})
        response = conn.getresponse()
        payload = response.read()
        if payload and response.getheader("Content-Type", "").startswith("application/json"):
            payload = json.loads(payload)
        result = response.status, {key.lower(): value for key, value in response.getheaders()}, payload
        conn.close()
        return result

    def rpc(self, request: dict[str, Any], *, name: str | None = None,
            version: str = VERSION, method_header: str | None = None) -> tuple[int, dict[str, str], dict[str, Any] | None, float]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": version,
            "Mcp-Method": method_header if method_header is not None else request.get("method", ""),
        }
        if name is not None:
            headers["Mcp-Name"] = name
        start = time.perf_counter_ns()
        status, response_headers, payload = self.request(
            "POST", "/mcp", json.dumps(request, separators=(",", ":")).encode(), headers
        )
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        value = payload if isinstance(payload, dict) else json.loads(payload) if payload else None
        return status, response_headers, value, elapsed

    def close(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)


def quantile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((percentile / 100) * (len(ordered) - 1))))
    return ordered[index]


def summarize(samples: list[float]) -> dict[str, float]:
    return {
        "p50_ms": quantile(samples, 50),
        "p95_ms": quantile(samples, 95),
        "p99_ms": quantile(samples, 99),
        "mean_ms": statistics.fmean(samples),
    }


def probe_stdio(binary: Path, store: Path, profile: str, warmup: int, count: int) -> dict[str, Any]:
    server = StdioServer(binary, store, profile)
    try:
        legacy_init, _ = server.call({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "mcp-compat-probe", "version": "1"}}})
        assert_rpc(legacy_init, 1)
        assert legacy_init["result"]["protocolVersion"] == "2024-11-05", legacy_init
        legacy_list, _ = server.call({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert_rpc(legacy_list, 2)
        assert "resultType" not in legacy_list["result"], legacy_list

        discover, _ = server.call(modern("server/discover", ident=3))
        assert_rpc(discover, 3)
        assert VERSION in discover["result"]["supportedVersions"], discover
        no_caps = modern("ping", ident=4)
        del no_caps["params"]["_meta"]["io.modelcontextprotocol/clientCapabilities"]
        malformed, _ = server.call(no_caps)
        assert_rpc(malformed, 4, error=-32602)
        bad_version = modern("tools/list", ident=5)
        bad_version["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] = "2099-01-01"
        unsupported, _ = server.call(bad_version)
        assert_rpc(unsupported, 5, error=-32022)
        invalid_id = modern("tools/call", {"name": "memory.count", "arguments": {}}, ident={"bad": True})
        bad_id_response, _ = server.call(invalid_id)
        assert bad_id_response.get("id") is None and bad_id_response.get("error", {}).get("code") == -32600, bad_id_response
        modern_batch = [modern("tools/list", ident=40), modern("tools/list", ident=41)]
        batch_response, _ = server.call(modern_batch)
        assert batch_response.get("id") is None and batch_response.get("error", {}).get("code") == -32600, batch_response

        # Cancellation is a notification with no response. The next response
        # must belong to the ping request, proving the stream remains aligned.
        cancel = {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 999}}
        aligned = server.notification_then_ping(cancel, modern("tools/list", ident=6))
        assert_rpc(aligned, 6)

        samples: dict[str, list[float]] = {"legacy": [], "modern": []}
        for _ in range(warmup):
            server.call({"jsonrpc": "2.0", "id": 7, "method": "tools/list"})
            server.call(modern("tools/list", ident=8))
        for index in range(count):
            # Alternate order to reduce monotonic thermal/order bias.
            order = ("legacy", "modern") if index % 2 == 0 else ("modern", "legacy")
            for era in order:
                request = {"jsonrpc": "2.0", "id": 9, "method": "tools/list"} if era == "legacy" else modern("tools/list", ident=10)
                response, elapsed = server.call(request)
                assert_rpc(response, request["id"])
                samples[era].append(elapsed)
        return {era: {"raw_ms": values, **summarize(values)} for era, values in samples.items()}
    finally:
        server.close()


def probe_http(binary: Path, store: Path, profile: str, warmup: int, count: int) -> dict[str, Any]:
    server = HttpServer(binary, store, profile)
    try:
        legacy = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        status, _, response = server.request("POST", "/mcp", json.dumps(legacy).encode(), {
            "Content-Type": "application/json", "MCP-Protocol-Version": "2024-11-05",
        })
        assert status == 200 and response["id"] == 1, (status, response)
        assert "resultType" not in response["result"], response
        legacy_init = {"jsonrpc": "2.0", "id": 12, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "mcp-compat-probe", "version": "1"},
        }}
        status, _, response = server.request("POST", "/mcp", json.dumps(legacy_init).encode(), {
            "Content-Type": "application/json", "MCP-Protocol-Version": "2025-11-25",
        })
        assert status == 200 and response["result"]["protocolVersion"] == "2024-11-05", (status, response)

        modern_list = modern("tools/list", ident=2)
        status, _, response, _ = server.rpc(modern_list)
        assert status == 200 and response["id"] == 2, (status, response)
        assert response["result"]["resultType"] == "complete", response
        call = modern("tools/call", {"name": "memory_stats", "arguments": {}}, 3)
        status, _, response, _ = server.rpc(call, name="=?base64?bWVtb3J5X3N0YXRz?=")
        assert status == 200 and response["result"]["resultType"] == "complete", (status, response)

        mismatched = modern("tools/list", ident=4)
        status, _, response, _ = server.rpc(mismatched, method_header="tools/call")
        assert status == 400 and response["error"]["code"] == -32020, (status, response)
        missing_version_headers = {
            "Content-Type": "application/json", "Mcp-Method": "tools/list",
        }
        status, _, payload = server.request("POST", "/mcp", json.dumps(modern("tools/list", ident=13)).encode(), missing_version_headers)
        assert status == 400 and payload["error"]["code"] == -32020, (status, payload)
        missing_method_header = {
            "Content-Type": "application/json", "MCP-Protocol-Version": VERSION,
        }
        status, _, payload = server.request("POST", "/mcp", json.dumps(modern("tools/list", ident=14)).encode(), missing_method_header)
        assert status == 400 and payload["error"]["code"] == -32020, (status, payload)
        batch = [modern("tools/list", ident=15), modern("tools/list", ident=16)]
        status, _, payload = server.request("POST", "/mcp", json.dumps(batch).encode(), {"Content-Type": "application/json"})
        assert status == 400 and payload["error"]["code"] == -32600, (status, payload)
        missing_name = modern("tools/call", {"name": "memory.count", "arguments": {}}, 5)
        status, _, response, _ = server.rpc(missing_name)
        assert status == 400 and response["error"]["code"] == -32020, (status, response)
        unsupported = modern("tools/list", ident=6)
        status, _, response, _ = server.rpc(unsupported, version="2099-01-01")
        assert status == 400 and response["error"]["code"] == -32020, (status, response)
        unsupported["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] = "2099-01-01"
        status, _, response, _ = server.rpc(unsupported, version="2099-01-01")
        assert status == 400 and response["error"]["code"] == -32022, (status, response)
        notification = modern("notifications/cancelled", {"requestId": 123})
        notification.pop("id")
        status, _, response = server.request("POST", "/mcp", json.dumps(notification).encode(), {
            "Content-Type": "application/json", "MCP-Protocol-Version": VERSION,
            "Mcp-Method": "notifications/cancelled",
        })
        assert status == 400 and response["error"]["code"] == -32600, (status, response)
        bad_origin = server.request("POST", "/mcp", json.dumps(modern("tools/list", ident=7)).encode(), {
            "Content-Type": "application/json", "MCP-Protocol-Version": VERSION,
            "Mcp-Method": "tools/list", "Origin": "https://attacker.example",
        })
        assert bad_origin[0] == 403, bad_origin

        samples: dict[str, list[float]] = {"legacy": [], "modern": []}
        for _ in range(warmup):
            server.request("POST", "/mcp", json.dumps({"jsonrpc": "2.0", "id": 8, "method": "tools/list"}).encode(), {
                "Content-Type": "application/json", "MCP-Protocol-Version": "2024-11-05",
            })
            server.rpc(modern("tools/list", ident=9))
        for index in range(count):
            order = ("legacy", "modern") if index % 2 == 0 else ("modern", "legacy")
            for era in order:
                if era == "legacy":
                    request = {"jsonrpc": "2.0", "id": 10, "method": "tools/list"}
                    start = time.perf_counter_ns()
                    status, _, response = server.request("POST", "/mcp", json.dumps(request).encode(), {
                        "Content-Type": "application/json", "MCP-Protocol-Version": "2024-11-05",
                    })
                    elapsed = (time.perf_counter_ns() - start) / 1_000_000
                else:
                    status, _, response, elapsed = server.rpc(modern("tools/list", ident=11))
                assert status == 200 and response["id"] in (10, 11), (status, response)
                samples[era].append(elapsed)
        return {era: {"raw_ms": values, **summarize(values)} for era, values in samples.items()}
    finally:
        server.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True, help="exact wm executable to probe")
    parser.add_argument("--profile", choices=("cyberbrain", "full"), default="cyberbrain")
    parser.add_argument("--store-root", type=Path, required=True, help="existing parent for isolated temporary stores")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--samples", type=int, default=50)
    parser.add_argument("--out", type=Path, required=True, help="private JSON report path")
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    store_root = args.store_root.resolve(strict=True)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error("--binary must name an executable file")
    if not store_root.is_dir() or args.warmup < 0 or args.samples < 1:
        parser.error("store root must exist; warmup must be >= 0 and samples >= 1")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "binary": str(binary), "profile": args.profile, "protocol_version": VERSION,
        "warmup": args.warmup, "sample_count_per_era_transport": args.samples,
        "fixture": "custom JSON-RPC contract fixture; not an official SDK",
        "transports": {},
    }
    with tempfile.TemporaryDirectory(prefix="mcp-compat-", dir=store_root) as isolated:
        root = Path(isolated)
        report["transports"]["stdio"] = probe_stdio(binary, root / "stdio-store", args.profile, args.warmup, args.samples)
        report["transports"]["streamable_http"] = probe_http(binary, root / "http-store", args.profile, args.warmup, args.samples)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"out": str(args.out.resolve()), "transports": {
        name: {era: summarize(data["raw_ms"]) for era, data in modes.items()}
        for name, modes in report["transports"].items()
    }}, indent=2))


if __name__ == "__main__":
    main()
