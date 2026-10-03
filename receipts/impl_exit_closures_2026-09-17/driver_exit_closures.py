#!/usr/bin/env python3
"""Row-exit closures — A1 cases 3/7 (+10 declared N/A) and B1 case 2.

A1 case 3 (write-gate bounds): out-of-range `max_writes_per_minute` is refused fail-closed with a
typed error (no clamp); an in-range value still succeeds.
A1 case 7 (near-dup): paraphrases (no exact-hash collision) are both admitted and retrievable —
no implicit semantic dedup.
A1 case 10 (strict mode): declared N/A in the exit receipt — Gen3 has no strict-mode construct;
the readonly write-route refusal (`IMPL_A2_DISCIPLINE`) is the nearest typed-refusal evidence.
B1 case 2 (no implicit filtering): records sharing tags are never dropped (both admitted and
retrievable).

Usage: python3 driver_exit_closures.py <harness-binary> <bundle-dir>
"""
import json
import os
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
STORE = os.path.join(BASE, "closures_store")
JOURNAL = os.path.join(BASE, "closures.journal.jsonl")
RESP = os.path.join(BASE, "closures.responses.jsonl")

PARAPHRASES = [
    "the north bay handles the loading dock",
    "the north bay is where the loading dock sits",
]
TAG_SHARED = [
    {"content": "shared tag record about the west gate", "galaxy": "codex", "tags": ["shared-tag"]},
    {"content": "another shared tag record about the east gate", "galaxy": "codex", "tags": ["shared-tag"]},
]


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def recall(id_, query):
    return call(id_, "memory.episodic_search", {
        "query": query, "limit": 10, "candidate_limit": 100,
        "include_historical": False, "min_score": 0.0, "min_coverage": 0.0})


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    if os.path.exists(JOURNAL):
        os.unlink(JOURNAL)
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "sandbox.set_limits", {"max_writes_per_minute": 4294967296}),
        call(3, "sandbox.set_limits", {"max_writes_per_minute": 120}),
        call(4, "memory.batch_create", {"items": [{"content": t, "galaxy": "codex", "tags": ["para"]}
                                                   for t in PARAPHRASES]}),
        recall(5, "north bay loading dock"),
        call(6, "memory.batch_create", {"items": TAG_SHARED}),
        recall(7, "shared tag record gate"),
        call(8, "inspect", {"scope": "all"}),
    ]
    payload = "".join(json.dumps(r) + "\n" for r in reqs)
    env = dict(os.environ, WM_GEN3_JOURNAL=JOURNAL)
    proc = subprocess.run([BIN, "serve", "--store", STORE], input=payload,
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-400:]
    open(RESP, "w").write(proc.stdout)
    r = {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}
    payload_of = lambda i: json.loads(r[i]["result"]["content"][0]["text"])

    # A1 case 3: out-of-range refused fail-closed; in-range succeeds
    refused = payload_of(2)
    assert refused["status"] == "error" and refused["field"] == "max_writes_per_minute", refused
    assert "fail-closed" in refused["error"], refused
    ok = payload_of(3)
    assert ok["status"] == "success" and ok["limits"]["max_writes_per_minute"] == 120, ok

    # A1 case 7: paraphrases both admitted and retrievable
    para = payload_of(4)
    assert para["status"] == "success" and para["count"] == 2, para
    hits = payload_of(5)
    assert hits["count"] == 2, hits

    # B1 case 2: tag-sharing records never dropped
    shared = payload_of(6)
    assert shared["status"] == "success" and shared["count"] == 2, shared
    found = payload_of(7)
    assert found["count"] == 2, found
    insp = payload_of(8)
    assert insp["inspect"]["tiers"]["tier3_adaptive"]["records"] == 4, insp

    print("ROW-EXIT CLOSURES PASS")
    print("A1 case 3     : out-of-range refused fail-closed (field named, value 4294967296); "
          "in-range 120 accepted")
    print("A1 case 7     : paraphrases admitted (2) and retrievable (2) — no implicit semantic dedup")
    print("B1 case 2     : tag-sharing records admitted (2) and retrievable (2) — no tag filtering")
    print("A1 case 10    : N/A declared in the exit receipt (no strict-mode construct; readonly "
          "typed refusal cited)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
