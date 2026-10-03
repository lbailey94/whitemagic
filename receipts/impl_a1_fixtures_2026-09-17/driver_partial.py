#!/usr/bin/env python3
"""A1 fixtures — atomic-vs-partial (§5.5).

Run A: a large item (~0.47 MB) plus two ordinary items in one batch -> success; the large
item is recalled byte-exactly (single outcome, no success-reported-while-absent).
Run B: a batch larger than the statutory write budget (default 120) -> explicit partial
disclosure: N admitted, M refused `write budget exceeded (fail-closed)`, every admitted id
recallable, the refused item absent, journal `ingest.batch` written < items.

Usage: python3 driver_partial.py <harness-binary> <bundle-dir>
"""
import json
import os
import re
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
STORE_LARGE = os.path.join(BASE, "partial_store_large")
STORE_BUDGET = os.path.join(BASE, "partial_store_budget")
JOURNAL_LARGE = os.path.join(BASE, "partial_large.journal.jsonl")
JOURNAL_BUDGET = os.path.join(BASE, "partial_budget.journal.jsonl")
RESP_LARGE = os.path.join(BASE, "partial_large.responses.jsonl")
RESP_BUDGET = os.path.join(BASE, "partial_budget.responses.jsonl")

LARGE = "largepayloadmarker " + ("lorem ipsum dolor sit amet consectetur " * 12000)
ORDINARY_ONE = "ordinary partial record ordinalone uniquetext"
ORDINARY_TWO = "ordinary partial record ordinaltwo uniquetext"


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def recall(id_, query):
    return call(id_, "memory.episodic_search", {
        "query": query, "limit": 10, "candidate_limit": 100,
        "include_historical": False, "min_score": 0.0, "min_coverage": 0.0})


def run(store, reqs, journal):
    payload = "".join(json.dumps(r) + "\n" for r in reqs)
    env = dict(os.environ, WM_GEN3_JOURNAL=journal, WM_GEN3_SWEEP="0")
    proc = subprocess.run([BIN, "serve", "--store", store], input=payload,
                          capture_output=True, text=True, env=env, timeout=300)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"harness exit {proc.returncode}")
    return proc


def replies_of(proc):
    return {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}


def payload_of(reply):
    return json.loads(reply["result"]["content"][0]["text"])


def events(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def budget_of(proc):
    m = re.search(r"budget=(\d+)", proc.stderr)
    assert m, proc.stderr
    return int(m.group(1))


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    for path in (JOURNAL_LARGE, JOURNAL_BUDGET):
        if os.path.exists(path):
            os.unlink(path)

    # --- run A: large item --------------------------------------------------
    items = [
        {"content": LARGE, "galaxy": "codex", "tags": ["partial-demo"]},
        {"content": ORDINARY_ONE, "galaxy": "codex", "tags": ["partial-demo"]},
        {"content": ORDINARY_TWO, "galaxy": "codex", "tags": ["partial-demo"]},
    ]
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": items}),
        recall(3, "largepayloadmarker"),
        recall(4, "ordinalone"),
        call(5, "inspect", {"scope": "all"}),
    ]
    proc = run(STORE_LARGE, reqs, JOURNAL_LARGE)
    open(RESP_LARGE, "w").write(proc.stdout)
    r = replies_of(proc)
    batch, large, ordinary, insp = (payload_of(r[i]) for i in (2, 3, 4, 5))
    assert batch["status"] == "success" and batch["count"] == 3, batch
    assert large["count"] == 1 and large["results"][0]["content"] == LARGE, \
        {"count": large["count"], "len": len(large["results"][0]["content"]) if large["count"] else None}
    assert ordinary["count"] == 1, ordinary
    records_large = insp["inspect"]["tiers"]["tier3_adaptive"]["records"]
    assert records_large == 3, insp
    ev = events(JOURNAL_LARGE)
    assert [b["written"] for b in ev if b["type"] == "ingest.batch"] == [3], ev
    assert not any(e["type"] == "remember.refusal" for e in ev), ev

    # --- run B: budget-forced partial --------------------------------------
    reqs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}]
    n = 121
    items = [
        {"content": f"budget record {i:04d} uniquebudgettoken{i:04d}",
         "galaxy": "codex", "tags": ["partial-demo"]}
        for i in range(n)
    ]
    reqs.append(call(2, "memory.batch_create", {"items": items}))
    reqs.append(call(3, "inspect", {"scope": "all"}))
    for i in range(n):
        reqs.append(recall(100 + i, f"uniquebudgettoken{i:04d}"))
    proc = run(STORE_BUDGET, reqs, JOURNAL_BUDGET)
    open(RESP_BUDGET, "w").write(proc.stdout)
    r = replies_of(proc)
    budget = budget_of(proc)
    assert budget < n, {"budget": budget, "n": n}
    batch, insp = payload_of(r[2]), payload_of(r[3])
    assert batch["status"] == "error", batch
    assert batch["failed"] == n - budget, batch
    assert batch["errors"] == ["write budget exceeded"] * (n - budget), batch
    assert len(batch["ids"]) == budget, batch
    assert insp["inspect"]["tiers"]["tier3_adaptive"]["records"] == budget, insp

    recalled = {i: payload_of(r[100 + i])["count"] for i in range(n)}
    assert all(recalled[i] == 1 for i in range(budget)), \
        {i: c for i, c in recalled.items() if c != 1}
    assert all(recalled[i] == 0 for i in range(budget, n)), \
        {i: c for i, c in recalled.items() if i >= budget and c != 0}

    ev = events(JOURNAL_BUDGET)
    batches = [b for b in ev if b["type"] == "ingest.batch"]
    assert len(batches) == 1 and batches[0]["items"] == n and batches[0]["written"] == budget, batches
    refusals = [e for e in ev if e["type"] == "remember.refusal"]
    assert len(refusals) == n - budget, refusals
    assert all(e["reason"] == "write budget exceeded (fail-closed)" for e in refusals), refusals

    print("A1 PARTIAL FIXTURE PASS")
    print("large item     :", json.dumps({"bytes": len(LARGE), "recalled_exact": True,
                                          "records": records_large}))
    print("budget partial :", json.dumps({"items": n, "budget": budget, "admitted": len(batch["ids"]),
                                          "failed": batch["failed"], "errors": sorted(set(batch["errors"])),
                                          "refusals_journaled": len(refusals)}))
    print("recall admitted:", sum(1 for i in range(budget) if recalled[i] == 1), "/", budget,
          "| refused absent:", sum(1 for i in range(budget, n) if recalled[i] == 0), "/", n - budget)
    return 0


if __name__ == "__main__":
    sys.exit(main())
