#!/usr/bin/env python3
"""Collect NLU shadow-mode data for the embedding-router promotion decision.

Starts `wm serve` with WM_EMBEDDER_ENDPOINT (HTTP llama-server embedding),
drives a corpus of natural-language thoughts through the `wm` meta-tool,
then reports shadow-mode stats and triggers graceful shutdown so the
server persists `mutable_shadow_stats.json` to the store.

Usage:
    python3 scripts/collect_shadow_data.py [--store PATH] [--binary PATH] [--endpoint URL]
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

QUERIES = [
    # memory
    "remember that Paris is the capital of France",
    "save this thought: the meeting is on Thursday",
    "note that the deploy failed at 3pm",
    "store this idea for later",
    "memorize the API key format",
    "remember the password rule from yesterday",
    "record that the server restarted",
    "keep this note in memory",
    "save the fact that the moon has no atmosphere",
    "remember to check the logs at midnight",
    "what do I know about the wm project",
    "find memories about rust",
    "search my memories for LMDB",
    "recall what I said about the deploy",
    "show me my recent memories",
    "list memories in the codex galaxy",
    "count my memories",
    "what tags do I have",
    "get memory by id",
    "read this memory",
    # galaxy
    "show the galaxies",
    "what galaxies exist",
    "create a new galaxy called research",
    "how many memories are in sandbox",
    "stats for the codex galaxy",
    "list all galaxies",
    "where do memories live",
    "tell me about the memory galaxies",
    "check galaxy health",
    "show galaxy info",
    # search / research
    "search the web for rust benchmarks",
    "look up information about lithium batteries",
    "research the topic of memory consolidation",
    "research a github repo about MCP",
    "fetch this webpage",
    "search for news about AI safety",
    "do a deep search on quantum computing",
    "research rabbit hole on agent memory",
    "fetch the url and summarize",
    "find information about the EU AI act",
    # session
    "start a session",
    "begin a new session",
    "end the session",
    "checkpoint the session",
    "what sessions do I have",
    "record this session turn",
    "replay the session",
    "show session history",
    "recall the session context",
    "hand off the session",
    # karma
    "log an error in friction",
    "log friction",
    "review the friction log",
    "auto log friction",
    "show my karma",
    "karma ledger status",
    "check the karma chain",
    "record karma",
    "resolve friction",
    "show improvement proposals",
    "what proposals are active",
    # claims
    "add a claim to the ledger",
    "resolve a claim",
    "list claims",
    "claims status",
    "what claims are pending",
    # transaction
    "begin a transaction",
    "commit the transaction",
    "rollback the transaction",
    # system
    "show system stats",
    "what is the brain wave state",
    "show resource usage",
    "list all tools",
    "what tools do you have",
    "list tools",
    "doctor check",
    "run a health check",
    "show the daemon status",
    "display the consciousness dashboard",
    # nlu
    "nlu shadow report",
    "show shadow mode stats",
    "nlu classification test",
    # imagination
    "imagine a scenario",
    "predict what happens next",
    "reflect on this scenario",
    "run a simulation",
    "forecast this outcome",
    # selfplay
    "run selfplay",
    "selfplay status",
    "export training data",
    # misc
    "what is your gana",
    "show the gana taxonomy",
    "polyglot status",
    "show julia status",
    "what languages are supported",
    # duplicate-ish variations (routing stress)
    "remember that water boils at 100 degrees",
    "remember that the sky appears blue",
    "remember that cats have nine lives",
    "remember the wifi password",
    "remember that e=mc2",
    "search for LMDB performance",
    "search my memory for LMDB",
    "search for tantivy",
    "search the web for LMDB",
    "find memory about search",
    "show me memories tagged rust",
    "list memories tagged important",
    "how many memories in total",
    "galaxy list",
    "galaxy stats",
    "session list",
    "karma status",
    "claims list",
    "system stats please",
    "tools list",
]

def rpc(server, method, params=None, req_id=1):
    req = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        req["params"] = params
    server.stdin.write((json.dumps(req) + "\n").encode())
    server.stdin.flush()
    line = b""
    while True:
        ch = server.stdout.read(1)
        if ch == b"\n" or ch == b"":
            break
        line += ch
    if not line.strip():
        return None
    try:
        return json.loads(line.decode())
    except json.JSONDecodeError:
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="/tmp/wm-shadow-collect")
    parser.add_argument("--binary", default=str(Path(__file__).resolve().parent.parent / "target/debug/wm"))
    parser.add_argument("--endpoint", default="http://127.0.0.1:8081")
    args = parser.parse_args()

    store = Path(args.store)
    if store.exists():
        shutil.rmtree(store)
    store.mkdir(parents=True)

    env = os.environ.copy()
    env["WM_EMBEDDER_ENDPOINT"] = args.endpoint
    env["WM_EMBEDDER_DIM"] = "768"
    env["WM_EMBEDDER_MODEL"] = "local"
    env["WM_EMBEDDER_TIMEOUT_MS"] = "120000"
    env["RUST_LOG"] = "info"

    print(f"Starting {args.binary} serve --store {store} (embedder: {args.endpoint})")
    err_log = Path("/tmp/opencode/shadow-srv-stderr.log")
    err_fh = open(err_log, "wb")
    proc = subprocess.Popen(
        [args.binary, "serve", "--store", str(store)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err_fh,
        env=env,
    )

    try:
        resp = rpc(proc, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "shadow-collect", "version": "1.0"},
        }, req_id=1)
        if resp is None or "error" in resp:
            print("initialize failed:", resp)
            sys.exit(1)
        print("Server initialized.")

        results = []
        t0 = time.perf_counter()
        for i, q in enumerate(QUERIES):
            # Dispatch pipeline per-tool limit: 60 RPM + 10 burst = 70 calls/min
            # for `wm`. Batch in 60-slot windows with a cooldown between.
            if i > 0 and i % 60 == 0:
                print(f"  ...cooldown at query {i} (dispatch rate window)")
                time.sleep(62)
            resp = rpc(proc, "tools/call", {
                "name": "wm",
                "arguments": {"thought": q},
            }, req_id=100 + i)
            tool = "?"
            conf = 0.0
            status = "?"
            if resp and "result" in resp:
                content = resp["result"].get("content", [])
                if content:
                    try:
                        data = json.loads(content[0].get("text", "{}"))
                        route = data.get("_wm_route", {})
                        tool = route.get("tool", "?")
                        conf = route.get("confidence", 0)
                        status = data.get("status", "?")
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass
            results.append((q, tool, conf, status))
            time.sleep(0.25)  # stay under the 600/min rate limit
        elapsed = time.perf_counter() - t0
        print(f"Driven {len(QUERIES)} queries in {elapsed:.1f}s ({elapsed/len(QUERIES)*1000:.0f} ms/query)")
        print("\n=== per-query dispatch ===")
        for q, tool, conf, status in results:
            print(f"  {q[:50]:<50} -> {tool} ({conf:.2f}) [{status}]")

        for attempt in range(5):
            resp = rpc(proc, "tools/call", {
                "name": "wm",
                "arguments": {"route": "nlu.shadow_report"},
            }, req_id=9999)
            if resp and "result" in resp:
                break
            time.sleep(16)  # rate-limit retry-after
        print("\n=== nlu.shadow_report ===")
        if resp and "result" in resp:
            content = resp["result"].get("content", [])
            if content:
                print(json.dumps(json.loads(content[0].get("text", "{}")), indent=2))
        else:
            print("no report:", resp)

        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
        print(f"\nServer exited (code {proc.returncode}).")
    finally:
        err_fh.close()
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    err = err_log.read_bytes() if err_log.exists() else b""
    lines = [l for l in err.decode(errors="replace").splitlines() if "embedder" in l or "router" in l]
    print("\n=== embedder/router stderr lines ===")
    for l in lines[:15]:
        print(l[:200])
    if not lines:
        print("(none matched)")
    if b"panic" in err:
        print("\n=== PANIC in stderr ===")
        idx = err.find(b"panic")
        print(err[max(0, idx-200):idx+1500].decode(errors="replace"))

    stats_path = store / "lmdb" / "mutable_shadow_stats.json"
    if stats_path.exists():
        print(f"\n=== persisted {stats_path} ===")
        print(stats_path.read_text())
    else:
        print("\nNo mutable_shadow_stats.json persisted.")

if __name__ == "__main__":
    main()
