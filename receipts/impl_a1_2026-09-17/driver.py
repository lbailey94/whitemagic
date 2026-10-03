#!/usr/bin/env python3
"""A1 acceptance driver (spec W1_A1): exact-hash gate demonstration.

Runs the frozen implementation (commit 8c5e32f) through the stdio harness:
  1. ingest two records
  2. re-ingest the same two records -> expect duplicate_exact refusals
  3. inspect -> record counts unchanged

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

ITEMS = [
    {"content": "the north bay is the current loading area", "galaxy": "codex", "tags": ["a1-demo"]},
    {"content": "the west gate is locked at night", "galaxy": "codex", "tags": ["a1-demo"]},
]

REQS = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
     "params": {"name": "wm", "arguments": {"route": "memory.batch_create", "args": {"items": ITEMS}}}},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
     "params": {"name": "wm", "arguments": {"route": "memory.batch_create", "args": {"items": ITEMS}}}},
    {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
     "params": {"name": "wm", "arguments": {"route": "inspect", "args": {}}}},
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
        replies[obj["id"]] = obj
    first = json.loads(replies[2]["result"]["content"][0]["text"])
    second = json.loads(replies[3]["result"]["content"][0]["text"])
    insp = json.loads(replies[4]["result"]["content"][0]["text"])

    assert first["status"] == "success" and first["count"] == 2, first
    assert second["status"] == "error", second
    assert second["errors"] == ["duplicate_exact", "duplicate_exact"], second
    assert second["ids"] == [], second

    journal = [json.loads(l) for l in open(JOURNAL)]
    refusals = [e for e in journal if e["type"] == "remember.refusal"
                and e.get("reason") == "duplicate_exact"]
    batches = [e for e in journal if e["type"] == "ingest.batch"]
    assert len(refusals) == 2, refusals
    assert [b["written"] for b in batches] == [2, 0], batches
    for r in refusals:
        assert r["content_sha256"] and r["source"] and "existing_id" in r, r

    print("A1 DEMO PASS")
    print("first  ingest :", json.dumps(first))
    print("second ingest :", json.dumps(second))
    print("ingest.batch  :", json.dumps([{k: b[k] for k in ("type", "items", "written")} for b in batches]))
    print("refusals      :", json.dumps([{k: r[k] for k in ("reason", "source", "existing_id")} for r in refusals]))
    print("inspect       :", json.dumps(insp)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
