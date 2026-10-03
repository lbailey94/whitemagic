#!/usr/bin/env python3
"""A2 floor-bounds acceptance driver (spec W1_A2 adversarial case 1).

Runs the frozen implementation (commit 41532c6) through the stdio harness:
  1. ingest one record
  2. min_score 1.5      -> expect a structured caller error (fail-closed), not silence
  3. min_score -0.1     -> same
  4. min_coverage 2.0   -> same, field named
  5. control query      -> success, one result, and exactly one selection.decision total
     (caller errors precede selection and emit no journal events)

Usage: python3 driver.py <harness-binary> <workdir>
"""
import json
import os
import subprocess
import sys

BIN = sys.argv[1]
BASE = sys.argv[2]
STORE = os.path.join(BASE, "store")
JOURNAL = os.path.join(BASE, "journal.jsonl")
RESP = os.path.join(BASE, "responses.jsonl")


def call(i, route, args):
    return {"jsonrpc": "2.0", "id": i, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


REQS = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    call(2, "memory.batch_create", {"items": [
        {"content": "alpha beta gamma", "galaxy": "codex", "tags": ["a2-bounds"]}]}),
    call(3, "memory.episodic_search", {"query": "alpha", "min_score": 1.5}),
    call(4, "memory.episodic_search", {"query": "alpha", "min_score": -0.1}),
    call(5, "memory.episodic_search", {"query": "alpha", "min_coverage": 2.0}),
    call(6, "memory.episodic_search", {"query": "alpha"}),
]


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    if os.path.exists(JOURNAL):
        os.unlink(JOURNAL)
    payload = "".join(json.dumps(r) + "\n" for r in REQS)
    env = dict(os.environ, WM_GEN3_JOURNAL=JOURNAL)
    proc = subprocess.run(
        [BIN, "serve", "--store", STORE],
        input=payload, capture_output=True, text=True, env=env, timeout=120,
    )
    with open(RESP, "w") as fh:
        fh.write(proc.stdout)
    sys.stderr.write(proc.stderr)

    replies = {}
    for line in proc.stdout.splitlines():
        obj = json.loads(line)
        replies[obj["id"]] = json.loads(obj["result"]["content"][0]["text"])
    over = replies[3]
    neg = replies[4]
    cover = replies[5]
    control = replies[6]
    for reply, token in ((over, "min_score=1.5"), (neg, "min_score=-0.1")):
        assert reply["status"] == "error", reply
        assert "invalid floor" in reply["error"] and "min_score" in reply["error"], reply
    assert cover["status"] == "error", cover
    assert "min_coverage=2" in cover["error"], cover
    assert control["status"] == "success" and control["count"] == 1, control

    journal = [json.loads(l) for l in open(JOURNAL)]
    decisions = [e for e in journal if e["type"] == "selection.decision"]
    assert len(decisions) == 1, decisions
    assert decisions[0]["abstained"] is False, decisions[0]

    print("A2-FLOORS DEMO PASS")
    print("over-range   :", json.dumps({"status": over["status"], "error": over["error"]}))
    print("negative     :", json.dumps({"status": neg["status"], "error": neg["error"]}))
    print("coverage     :", json.dumps({"status": cover["status"], "error": cover["error"]}))
    print("control      :", json.dumps({"status": control["status"], "count": control["count"]}))
    print("decisions    :", len(decisions), "(invalid calls journaled none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
