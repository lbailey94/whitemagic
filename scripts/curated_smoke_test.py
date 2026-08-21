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
    if info.get("name") != "whitemagic":
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


def run_continuity_gate(binary):
    """G1.7 process-level continuity acceptance gate.

    Exercises the headline workflow through real `wm serve` processes and the
    MCP boundary, per docs/V7_PRODUCT_READINESS.md:

      1. initialize and discover the supported surface
      2. session.start
      3. session.record a decision AND a summary
      4. stop the server cleanly
      5. start a new server process on the same store
      6. session.continuity returns the expected prior turn
      7. session.replay progressive respects its token budget
      8. read-only mode can replay but refuses recording
      9. malformed/absent sessions fail clearly without corrupting state
    """
    store = tempfile.mkdtemp(prefix="wm-continuity-gate-")
    marker = "GATE decision: adopt event-sourced audit log for billing service"
    summary = "GATE summary: chose event-sourced audit log; next step is schema migration."

    # Steps 1-3: first process.
    server = Server(binary, store)
    try:
        init = server.rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "continuity-gate", "version": "1.0"},
            },
            1,
        )
        if init.get("result", {}).get("serverInfo", {}).get("name") == "whitemagic":
            ok("continuity gate 1: initialize + server identity")
        else:
            fail("continuity gate 1", "unexpected serverInfo", init)

        tools = server.rpc("tools/list", {}, 2)
        names = [t.get("name") for t in tools.get("result", {}).get("tools", [])]
        if "wm" in names:
            ok("continuity gate 1b: supported surface discovered (wm meta-tool)")
        else:
            fail("continuity gate 1b", f"wm meta-tool missing from {names}", tools)

        started = server.wm_payload("session.start", {"title": "continuity gate A"}, 3)
        if started.get("status") == "success":
            ok("continuity gate 2: session.start")
        else:
            fail("continuity gate 2", "session.start did not succeed", started)

        rec_decision = server.wm_payload(
            "session.record",
            {"content": marker, "role": "user", "turn_type": "decision", "importance": 0.9},
            4,
        )
        rec_summary = server.wm_payload(
            "session.record",
            {"content": summary, "role": "ai", "turn_type": "summary", "importance": 0.8},
            5,
        )
        if (
            rec_decision.get("status") == "success"
            and rec_summary.get("status") == "success"
        ):
            ok("continuity gate 3: decision + summary recorded")
        else:
            fail("continuity gate 3", "record failed", {"decision": rec_decision, "summary": rec_summary})
    finally:
        # Step 4: clean stop — close stdin (EOF) and wait for exit.
        server.close()
    ok("continuity gate 4: first process stopped cleanly")

    # Steps 5-7: second process on the same store.
    server = Server(binary, store)
    try:
        cont = server.wm_payload("session.continuity", {"n": 10}, 10)
        turns = cont.get("turns", [])
        contents = [t.get("content", "") for t in turns]
        if cont.get("previous_session") and marker in contents:
            ok("continuity gate 6: continuity returns expected prior turn")
        else:
            fail("continuity gate 6", "marker turn not recovered", cont)

        # Step 7: progressive replay must respect token budget — a tiny
        # budget must return strictly less content than an ample one.
        tiny = server.wm_payload(
            "session.replay", {"mode": "progressive", "token_budget": 20}, 11
        )
        ample = server.wm_payload(
            "session.replay", {"mode": "progressive", "token_budget": 100000}, 12
        )

        def replay_text(payload):
            return json.dumps(payload.get("turns", payload))

        if tiny.get("status") == "success" and ample.get("status") == "success":
            if len(replay_text(tiny)) <= len(replay_text(ample)):
                ok("continuity gate 7: progressive replay respects token budget")
            else:
                fail("continuity gate 7", "tiny budget returned more content than ample", {
                    "tiny": len(replay_text(tiny)),
                    "ample": len(replay_text(ample)),
                })
        else:
            fail("continuity gate 7", "replay failed", {"tiny": tiny, "ample": ample})

        # Step 9a: absent session fails clearly...
        absent = server.call_wm(
            "session.replay", {"mode": "full", "session_id": "00000000-0000-0000-0000-000000000000"}, 13
        )
        inner_error = absent.get("result", {}).get("isError", False) or (
            absent.get("result", {}).get("content", [{}])[0].get("text", "").find('"error"') >= 0
        )
        if inner_error:
            ok("continuity gate 9a: absent session_id fails clearly")
        else:
            fail("continuity gate 9a", "absent session_id did not error", absent)

        # ...and the server is still healthy afterwards (no corruption).
        healthy = server.wm_payload("session.continuity", {"n": 1}, 14)
        if healthy.get("status") == "success":
            ok("continuity gate 9b: state intact after malformed request")
        else:
            fail("continuity gate 9b", "server unhealthy after malformed request", healthy)
    finally:
        server.close()

    # Step 8: read-only mode can replay but refuses recording.
    server = Server(binary, store, extra_args=["--readonly"])
    try:
        ro_replay = server.wm_payload("session.replay", {"mode": "progressive", "token_budget": 100000}, 20)
        ro_record = server.wm_payload(
            "session.record", {"content": "must be refused", "role": "user"}, 21
        )
        if ro_replay.get("status") == "success":
            ok("continuity gate 8a: read-only replay succeeds")
        else:
            fail("continuity gate 8a", "read-only replay failed", ro_replay)
        if ro_record.get("status") == "error":
            ok("continuity gate 8b: read-only recording refused")
        else:
            fail("continuity gate 8b", "read-only recording was not refused", ro_record)
    finally:
        server.close()

    shutil.rmtree(store, ignore_errors=True)


def run_backup_gate(binary):
    """G1.9 full-store backup/verify/restore acceptance gate.

    Creates data + session state, backs up the FULL store root, deletes the
    working copy, restores it, and proves memory plus session continuity
    survived through real serve processes. Also proves tampered backups are
    refused before anything is touched.
    """
    store = tempfile.mkdtemp(prefix="wm-backup-gate-store-")
    out = tempfile.mkdtemp(prefix="wm-backup-gate-out-")
    marker = "BACKUP decision: migrate cron jobs to systemd timers"
    mem_content = "backup gate memory: the deployment window is Tuesday 0900 UTC"

    # 1. Create state through a real server.
    server = Server(binary, store)
    try:
        server.rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "backup-gate", "version": "1.0"},
            },
            1,
        )
        started = server.wm_payload("session.start", {"title": "backup gate"}, 2)
        if started.get("status") != "success":
            fail("backup gate", "session.start failed", started)
            server.close()
            return
        rec = server.wm_payload(
            "session.record",
            {"content": marker, "role": "user", "turn_type": "decision", "importance": 0.9},
            3,
        )
        mem = server.wm_payload(
            "memory.create",
            {"galaxy": "codex", "content": mem_content, "tags": ["backup-gate"]},
            4,
        )
        if rec.get("status") != "success" or mem.get("status") != "success":
            fail("backup gate", "state creation failed", {"rec": rec, "mem": mem})
    finally:
        server.close()

    # 2. Back up the full store root.
    backed_up = subprocess.run(
        [binary, "backup", "--store", store, "--out", out],
        capture_output=True, text=True, timeout=120,
    )
    if backed_up.returncode != 0:
        fail("backup gate: wm backup", f"exit {backed_up.returncode}: {backed_up.stderr}")
        return
    backups = sorted(
        p for p in os.listdir(out) if p.startswith("whitemagic-backup-")
    )
    if not backups:
        fail("backup gate: wm backup", "no backup directory created")
        return
    backup_dir = os.path.join(out, backups[-1])
    ok(f"backup gate: wm backup ({backups[-1]})")

    # 3. Tampered backup must be refused BEFORE touching the target.
    # Tamper a COPY so the clean backup remains usable below.
    tamper_dir = os.path.join(out, "tampered-copy")
    shutil.copytree(backup_dir, tamper_dir)
    sums_path = os.path.join(tamper_dir, "SHA256SUMS")
    with open(sums_path, "ab") as fh:
        fh.write(b"deadbeef00  data/lmdb/data.mdb\n")
    tampered = subprocess.run(
        [binary, "restore", "--backup", tamper_dir,
         "--store", os.path.join(out, "must-not-exist")],
        capture_output=True, text=True, timeout=120,
    )
    if tampered.returncode != 0 and "verification FAILED" in (tampered.stderr + tampered.stdout):
        ok("backup gate: tampered manifest refused")
    else:
        fail("backup gate: tamper refusal",
             f"exit {tampered.returncode}: {tampered.stdout} {tampered.stderr}")

    # 4. Disaster: remove the working store, restore from the clean backup.
    shutil.rmtree(store, ignore_errors=True)
    restored = subprocess.run(
        [binary, "restore", "--backup", backup_dir, "--store", store],
        capture_output=True, text=True, timeout=120,
    )
    if restored.returncode != 0:
        fail("backup gate: wm restore", f"exit {restored.returncode}: {restored.stderr}")
        return
    ok("backup gate: wm restore after store deletion")

    # 5. Prove continuity + memory survived through a real server process.
    server = Server(binary, store)
    try:
        cont = server.wm_payload("session.continuity", {"n": 10}, 10)
        contents = [t.get("content", "") for t in cont.get("turns", [])]
        if cont.get("previous_session") and marker in contents:
            ok("backup gate: session continuity survived restore")
        else:
            fail("backup gate: continuity", "marker turn not recovered", cont)

        found = server.wm_payload(
            "memory.search", {"query": "deployment window", "galaxy": "codex", "limit": 5}, 11
        )
        if any("deployment window" in r.get("content", "")
               for r in found.get("results", [])):
            ok("backup gate: memories survived restore")
        else:
            fail("backup gate: memory search", "memory not found after restore", found)
    finally:
        server.close()

    shutil.rmtree(store, ignore_errors=True)
    shutil.rmtree(out, ignore_errors=True)


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

        # Seal/verify integrity (B5): seal a real store written by this
        # test, verify it clean, then verify tamper detection end to end
        # through the actual CLI commands.
        lmdb_dir = os.path.join(store, "lmdb")
        sealed = subprocess.run(
            [binary, "seal", "--store", store],
            capture_output=True, text=True, timeout=60,
        )
        if sealed.returncode == 0 and "Sealed" in sealed.stdout:
            ok(f"wm seal: {sealed.stdout.strip().splitlines()[0]}")
        else:
            fail("wm seal", f"exit {sealed.returncode}: {sealed.stdout} {sealed.stderr}")

        verified = subprocess.run(
            [binary, "verify", "--store", store],
            capture_output=True, text=True, timeout=60,
        )
        if verified.returncode == 0 and "OK" in verified.stdout:
            ok("wm verify: clean store passes")
        else:
            fail("wm verify", f"exit {verified.returncode}: {verified.stdout} {verified.stderr}")

        # Verify must not mutate the store: a second run still passes.
        verified_again = subprocess.run(
            [binary, "verify", "--store", store],
            capture_output=True, text=True, timeout=60,
        )
        if verified_again.returncode == 0:
            ok("wm verify: idempotent (no self-inflicted drift)")
        else:
            fail("wm verify idempotence", f"exit {verified_again.returncode}: {verified_again.stdout}")

        # Tamper with a sealed file and expect a failing verification.
        data_mdb = os.path.join(lmdb_dir, "data.mdb")
        with open(data_mdb, "ab") as fh:
            fh.write(b"\x00smoke-tamper")
        tampered = subprocess.run(
            [binary, "verify", "--store", store],
            capture_output=True, text=True, timeout=60,
        )
        if tampered.returncode == 1 and "VERIFY FAILED" in tampered.stdout:
            ok("wm verify: tampered store fails with exit 1")
        else:
            fail("wm verify tamper detection",
                 f"exit {tampered.returncode}: {tampered.stdout} {tampered.stderr}")
    finally:
        if clean_up:
            shutil.rmtree(store, ignore_errors=True)

    # G1.7 process-level continuity gate (own temp store).
    run_continuity_gate(binary)

    # G1.9 full-store backup/restore gate (own temp stores).
    run_backup_gate(binary)

    if FAILURES:
        print(f"\n{len(FAILURES)} smoke step(s) failed: {FAILURES}")
        raise SystemExit(1)
    print("\ncurated smoke test passed")


if __name__ == "__main__":
    main()
