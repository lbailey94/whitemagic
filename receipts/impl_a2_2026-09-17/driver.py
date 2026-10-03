#!/usr/bin/env python3
"""A2 acceptance driver (spec W1_A2): explicit insufficiency disclosure.

Runs the frozen implementation (commit a588ae1) through the stdio harness:
  1. ingest one record
  2. query below declared floors        -> expect zero results + insufficient_evidence (no_results_above_floors)
  3. query with no candidates at all    -> expect zero results + insufficient_evidence (no_candidates)
  4. control query (floors 0)           -> expect one result (disclosure only when needed)

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
        {"content": "alpha beta gamma", "galaxy": "codex", "tags": ["a2-demo"]}]}),
    call(3, "memory.episodic_search", {"query": "alpha zulu", "min_score": 0.9}),
    call(4, "memory.episodic_search", {"query": "zulu"}),
    call(5, "memory.episodic_search", {"query": "alpha"}),
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
    below_floor = replies[3]
    no_candidates = replies[4]
    control = replies[5]
    assert below_floor["count"] == 0 and below_floor["results"] == [], below_floor
    assert no_candidates["count"] == 0 and no_candidates["results"] == [], no_candidates
    assert control["count"] == 1 and control["results"][0]["content"] == "alpha beta gamma", control

    journal = [json.loads(l) for l in open(JOURNAL)]
    abst = [e for e in journal if e["type"] == "selection.decision" and e.get("abstained")]
    causes = sorted(e["cause"] for e in abst)
    assert causes == ["no_candidates", "no_results_above_floors"], abst
    assert all(e["reason"] == "insufficient_evidence" for e in abst), abst
    assert journal[-1]["type"] == "run.end", journal[-1]
    assert all(e.get("reason") != "no_candidates" for e in journal), "legacy token must be gone"

    print("A2 DEMO PASS")
    print("below-floor  :", json.dumps({"count": below_floor["count"]}))
    print("no-candidates:", json.dumps({"count": no_candidates["count"]}))
    print("control      :", json.dumps({"count": control["count"], "id": control["results"][0]["id"]}))
    print("abstentions  :", json.dumps(abst))
    return 0


if __name__ == "__main__":
    sys.exit(main())
