#!/usr/bin/env python3
"""Nucleus-freeze canary fixtures: generate JSON-RPC request files for wm-gen3.

Ephemeral tooling (lives in /tmp; not part of the frozen tree).
"""
import json, os

base = "/tmp/opencode/nucleus/req"
os.makedirs(base, exist_ok=True)


def req(id_, method, params=None):
    r = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        r["params"] = params
    return json.dumps(r)


def wm(route, args=None):
    return {"name": "wm", "arguments": {"route": route, "args": args or {}}}


def write(name, lines):
    with open(os.path.join(base, name), "w") as f:
        for l in lines:
            f.write(l + "\n")


pair = [
    {"content": "the deploy region for the service is us-east and the failover target is eu-west", "galaxy": "codex", "tags": ["fixture"]},
    {"content": "the deploy region for the service is eu-west", "galaxy": "codex", "tags": ["fixture"]},
]
gate_items = [
    {"content": "zephyr quartz telemetry diagnostics", "galaxy": "codex", "tags": ["fixture"]},
    {"content": "zephyr lantern calibration baseline", "galaxy": "codex", "tags": ["fixture"]},
]


def q(text):
    return ("memory.episodic_search", {
        "query": text, "limit": 10, "candidate_limit": 100,
        "include_historical": False, "min_score": 0.0, "min_coverage": 0.0,
    })


# A — ingest the superseding pair, query, closure runtime canary, inspect.
seq = [req(1, "initialize"), req(2, "tools/call", wm("memory.batch_create", {"items": pair}))]
seq += [req(3, "tools/call", wm(*q("deploy region failover")))]
seq += [req(4, "tools/call", wm("gen3.canary")), req(5, "tools/call", wm("inspect", {"scope": "all"}))]
write("A_full.jsonl", seq)

# A' — second process on the same store: query + inspect only (round trip).
seq2 = [req(1, "tools/call", wm(*q("deploy region failover"))), req(2, "tools/call", wm("inspect", {"scope": "all"}))]
write("A_query_only.jsonl", seq2)

# B — gate candidate-count cases: 2 candidates / 1 candidate / 0 candidates.
seqb = [req(1, "initialize"), req(2, "tools/call", wm("memory.batch_create", {"items": gate_items}))]
seqb += [req(3, "tools/call", wm(*q("zephyr"))), req(4, "tools/call", wm(*q("lantern"))), req(5, "tools/call", wm(*q("quokka")))]
write("B_full.jsonl", seqb)

print("wrote:", sorted(os.listdir(base)))
