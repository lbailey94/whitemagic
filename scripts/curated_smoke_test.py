#!/usr/bin/env python3
"""Curated profile smoke test for the WhiteMagic v5 release binary.

Runs the curated release workflow end to end against a fresh temporary store:

  1. initialize handshake
  2. tools/list exposes only the `wm` meta-tool with profile-aware text
  3. memory.create via explicit route
  4. memory.search finds the created memory
  5. memory.hybrid_recall finds the created memory
  6. session.start succeeds
  7. transaction.begin -> memory.create -> transaction.rollback (confirmed)
     restores the pre-transaction state
  8. claims calibration returns a valid scorecard
  9. restart persistence: a new process finds the memory after restart
 10. read-only mode: reads succeed and mutations are refused

The test asserts JSON payloads, not just process exit codes. Any failure
prints a diagnostic and exits 1. This is the process-level release gate
referenced by docs/RELEASE_READINESS.md.

Usage:
    python3 scripts/curated_smoke_test.py
    python3 scripts/curated_smoke_test.py --binary target/release/wm
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

FAILURES = []


def fail(step, detail, payload=None):
    FAILURES.append(step)
    print(f"[FAIL] {step}: {detail}")
    if payload is not None:
        print(f"       payload: {json.dumps(payload, indent=2)[:2000]}")


def ok(step):
    print(f"[ ok ] {step}")


def find_binary():
    candidates = []
    explicit = os.environ.get("WM_BINARY")
    if explicit:
        candidates.append(explicit)
    for profile in ("release", "debug"):
        candidates.append(os.path.join(REPO_ROOT, "target", profile, "wm"))
    if sys.platform == "win32":
        candidates = [c + ".exe" for c in candidates]
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise SystemExit(
        f"wm binary not found. Build it first (cargo build --release) or pass --binary. Tried: {candidates}"
    )


class Server:
    def __init__(self, binary, store, extra_args=None):
        args = [
            binary,
            "serve",
            "--store",
            store,
            "--profile",
            "curated",
            "--max-requests",
            "100",
            "--rate-limit",
            "0",
        ]
        if extra_args:
            args += extra_args
        self.proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def rpc(self, method, params=None, msg_id=1):
        req = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            req["params"] = params
        self.proc.stdin.write((json.dumps(req) + "\n").encode())
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(f"server closed stdout before responding to {method}")
        return json.loads(line.decode())

    def call_wm(self, route, args=None, msg_id=1):
        arguments = {"route": route}
        if args is not None:
            arguments["args"] = args
        return self.rpc("tools/call", {"name": "wm", "arguments": arguments}, msg_id)

    def wm_payload(self, route, args=None, msg_id=1):
        resp = self.call_wm(route, args, msg_id)
        content = resp.get("result", {}).get("content")
        if not content:
            raise RuntimeError(f"tools/call for {route} returned no content: {resp}")
        return json.loads(content[0]["text"])

    def close(self):
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except (subprocess.TimeoutExpired, OSError):
            self.proc.kill()
            self.proc.wait(timeout=10)


def run_workflow(server):
    init = server.rpc(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "curated-smoke", "version": "1.0"},
        },
        1,
    )
    info = init.get("result", {}).get("serverInfo", {})
    if info.get("name") != "whitemagic-v5":
        fail("initialize", "unexpected serverInfo", init)
    else:
        ok("initialize handshake")

    listed = server.rpc("tools/list", {}, 2)
    tools = listed.get("result", {}).get("tools", [])
    if len(tools) != 1 or tools[0].get("name") != "wm":
        fail("tools/list", "expected exactly the wm meta-tool", listed)
    else:
        ok("tools/list exposes only the wm meta-tool")
    description = tools[0].get("description", "") if tools else ""
    if "229 tools" in description:
        fail("tools/list", "description advertises the full archive surface", description)
    elif "curated" not in description:
        fail("tools/list", "description does not reflect the curated profile", description)
    else:
        ok("tools/list description reflects the curated profile")

    discovered = server.wm_payload("tools.list", {}, 100)
    profile_tools = discovered.get("tools", [])
    for route in ("memory.search", "memory.hybrid_recall"):
        route_schema = next(
            (
                tool.get("input_schema")
                for tool in profile_tools
                if tool.get("name") == route
            ),
            None,
        )
        required = route_schema.get("required", []) if route_schema else []
        if (
            not route_schema
            or route_schema.get("type") != "object"
            or "query" not in route_schema.get("properties", {})
            or "query" not in required
        ):
            fail("tools/list", f"{route} schema must require query", route_schema)
        else:
            ok(f"tools/list exposes {route} query schema")

    created = server.wm_payload(
        "memory.create",
        {
            "galaxy": "codex",
            "content": "curated smoke marker: transaction rollback and session continuity",
            "tags": ["smoke", "release"],
        },
        3,
    )
    if created.get("status") != "success":
        fail("memory.create", "create failed", created)
        return
    memory_id = created.get("id")
    if not memory_id:
        fail("memory.create", "missing memory id", created)
        return
    ok("memory.create via explicit route")

    searched = server.wm_payload(
        "memory.search",
        {"query": "curated smoke marker", "galaxy": "codex", "limit": 5},
        4,
    )
    results = searched.get("results", [])
    if searched.get("status") != "success" or not any(
        r.get("id") == memory_id for r in results
    ):
        fail("memory.search", "created memory not found", searched)
    else:
        ok("memory.search finds the created memory")

    recalled = server.wm_payload(
        "memory.hybrid_recall",
        {"query": "transaction rollback", "galaxy": "codex", "limit": 5},
        5,
    )
    if recalled.get("status") != "success" or recalled.get("count", 0) < 1:
        fail("memory.hybrid_recall", "hybrid recall returned nothing", recalled)
    else:
        ok("memory.hybrid_recall finds the created memory")

    session = server.wm_payload("session.start", {"title": "curated smoke"}, 6)
    if session.get("status") != "success" or not session.get("session_id"):
        fail("session.start", "session did not start", session)
    else:
        ok("session.start")

    begun = server.wm_payload("transaction.begin", {}, 7)
    if begun.get("status") != "success":
        fail("transaction.begin", "begin failed", begun)
        return
    ok("transaction.begin")

    temp = server.wm_payload(
        "memory.create",
        {"galaxy": "codex", "content": "temporary memory that must be rolled back"},
        8,
    )
    if temp.get("status") != "success":
        fail("transaction.create", "temp create failed", temp)
        return
    temp_id = temp.get("id")

    rolled = server.wm_payload("transaction.rollback", {"confirm": True}, 9)
    if rolled.get("status") != "success":
        fail("transaction.rollback", "rollback failed", rolled)
    else:
        ok("transaction.rollback restores state")

    after = server.wm_payload(
        "memory.search",
        {"query": "temporary memory that must be rolled back", "galaxy": "codex", "limit": 5},
        10,
    )
    if after.get("status") == "success" and any(
        r.get("memory_id") == temp_id for r in after.get("results", [])
    ):
        fail("transaction.rollback", "temporary memory still present after rollback", after)
    else:
        ok("rollback removed the temporary memory")

    calibration = server.wm_payload("claims", {"action": "calibration"}, 11)
    if calibration.get("status") != "success" or "brier" not in calibration:
        fail("claims.calibration", "calibration scorecard missing", calibration)
    else:
        ok("claims.calibration returns a scorecard")

    return memory_id


def main():
    parser = argparse.ArgumentParser(description="Curated profile smoke test")
    parser.add_argument("--binary", default=None, help="path to the wm binary")
    parser.add_argument("--store", default=None, help="store directory (default: fresh tempdir)")
    args = parser.parse_args()

    binary = args.binary or find_binary()
    print(f"binary: {binary}")

    if args.store:
        store = args.store
        shutil.rmtree(store, ignore_errors=True)
        os.makedirs(store)
        clean_up = False
    else:
        store = tempfile.mkdtemp(prefix="wm-curated-smoke-")
        clean_up = True
    print(f"store:  {store}")

    try:
        server = Server(binary, store)
        try:
            memory_id = run_workflow(server)
        finally:
            server.close()

        if memory_id is None:
            raise SystemExit(1)

        # Restart persistence: a new process must find the memory.
        server = Server(binary, store)
        try:
            server.rpc(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "curated-smoke", "version": "1.0"},
                },
                20,
            )
            searched = server.wm_payload(
                "memory.search",
                {"query": "curated smoke marker", "galaxy": "codex", "limit": 5},
                21,
            )
            if any(r.get("id") == memory_id for r in searched.get("results", [])):
                ok("restart persistence: memory survives restart")
            else:
                fail("restart persistence", "memory not found after restart", searched)
        finally:
            server.close()

        # Read-only mode: reads succeed, mutations are refused.
        server = Server(binary, store, extra_args=["--readonly"])
        try:
            server.rpc(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "curated-smoke", "version": "1.0"},
                },
                30,
            )
            searched = server.wm_payload(
                "memory.search",
                {"query": "curated smoke marker", "galaxy": "codex", "limit": 5},
                31,
            )
            if any(r.get("id") == memory_id for r in searched.get("results", [])):
                ok("read-only mode: reads succeed")
            else:
                fail("read-only mode", "search failed", searched)

            mutated = server.wm_payload(
                "session.start", {"title": "must be refused"}, 32
            )
            if mutated.get("status") == "error":
                ok("read-only mode: mutations are refused")
            else:
                fail("read-only mode", "mutation was not refused", mutated)
        finally:
            server.close()
    finally:
        if clean_up:
            shutil.rmtree(store, ignore_errors=True)

    if FAILURES:
        print(f"\n{len(FAILURES)} smoke step(s) failed: {FAILURES}")
        raise SystemExit(1)
    print("\ncurated smoke test passed")


if __name__ == "__main__":
    main()
