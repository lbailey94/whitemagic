#!/usr/bin/env python3
"""A1 fixtures — scope law (§5.3) + context non-collapse + no global dedup + bare-bytes check.

Store A: identical bytes under two galaxies (scope labels) -> two distinct records;
re-ingest within a scope -> `duplicate_exact`; recall ordering unchanged by the refusals
(negative assertion); a separate process re-sends both -> refusals only, `data.mdb`
byte-identical (spec §5 item 6). Store B (fresh): the same bytes are admitted (no
global/cross-store dedup). Scope is realized as the caller's declared provenance
(`corpus:<galaxy>:<tags>`), which the gate identity keys on.

Usage: python3 driver_scope.py <harness-binary> <bundle-dir>
"""
import hashlib
import json
import os
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
STORE_A = os.path.join(BASE, "scope_store_a")
STORE_B = os.path.join(BASE, "scope_store_b")
JOURNAL_A = os.path.join(BASE, "scope_a.journal.jsonl")
JOURNAL_B = os.path.join(BASE, "scope_b.journal.jsonl")
JOURNAL_REFUSAL = os.path.join(BASE, "scope_refusal.journal.jsonl")
RESP_A = os.path.join(BASE, "scope_a.responses.jsonl")
RESP_B = os.path.join(BASE, "scope_b.responses.jsonl")
RESP_REFUSAL = os.path.join(BASE, "scope_refusal.responses.jsonl")

CONTENT = "scope law identical bytes marker"
ALPHA = [{"content": CONTENT, "galaxy": "alpha", "tags": ["scope-demo"]}]
BETA = [{"content": CONTENT, "galaxy": "beta", "tags": ["scope-demo"]}]


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def run(store, reqs, journal):
    payload = "".join(json.dumps(r) + "\n" for r in reqs)
    env = dict(os.environ, WM_GEN3_JOURNAL=journal)
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


def data_hash(store):
    h = hashlib.sha256()
    with open(os.path.join(store, "data.mdb"), "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    for path in (JOURNAL_A, JOURNAL_B, JOURNAL_REFUSAL):
        if os.path.exists(path):
            os.unlink(path)

    # --- store A: per-scope admission, per-scope dedup, ordering negative --
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": ALPHA}),
        call(3, "memory.batch_create", {"items": BETA}),
        call(4, "memory.episodic_search", {
            "query": CONTENT, "limit": 10, "candidate_limit": 100,
            "include_historical": False, "min_score": 0.0, "min_coverage": 0.0}),
        call(5, "memory.batch_create", {"items": ALPHA}),
        call(6, "memory.batch_create", {"items": BETA}),
        call(7, "memory.episodic_search", {
            "query": CONTENT, "limit": 10, "candidate_limit": 100,
            "include_historical": False, "min_score": 0.0, "min_coverage": 0.0}),
        call(8, "inspect", {"scope": "all"}),
    ]
    proc = run(STORE_A, reqs, JOURNAL_A)
    open(RESP_A, "w").write(proc.stdout)
    r = replies_of(proc)
    a, b, before, a2, b2, after, insp = (payload_of(r[i]) for i in (2, 3, 4, 5, 6, 7, 8))

    assert a["status"] == "success" and a["count"] == 1, a
    assert b["status"] == "success" and b["count"] == 1, b
    assert a2["status"] == "error" and a2["errors"] == ["duplicate_exact"], a2
    assert b2["status"] == "error" and b2["errors"] == ["duplicate_exact"], b2
    assert insp["inspect"]["tiers"]["tier3_adaptive"]["records"] == 2, insp
    assert before["count"] == 2 and after["count"] == 2, (before, after)
    order_before = [(h["id"], h["rank"], h["superseded_by"]) for h in before["results"]]
    order_after = [(h["id"], h["rank"], h["superseded_by"]) for h in after["results"]]
    assert order_before == order_after, (order_before, order_after)

    ev = events(JOURNAL_A)
    batches = [e for e in ev if e["type"] == "ingest.batch"]
    assert [x["written"] for x in batches] == [1, 1, 0, 0], batches
    refusals = [e for e in ev if e["type"] == "remember.refusal"]
    assert len(refusals) == 2 and all(e["reason"] == "duplicate_exact" for e in refusals), refusals
    assert {e["source"] for e in refusals} == {"corpus:alpha:scope-demo", "corpus:beta:scope-demo"}, refusals
    chains = [e for e in ev if e["type"] == "provenance.chain"]
    recall_chains = {tuple(e["chain"]) for e in chains if e.get("result_id") in (0, 1)}
    assert recall_chains == {("corpus:alpha:scope-demo",), ("corpus:beta:scope-demo",)}, chains

    # --- bare bytes: a separate refused re-ingest process leaves data.mdb identical
    hash_before = data_hash(STORE_A)
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": ALPHA}),
        call(3, "memory.batch_create", {"items": BETA}),
    ]
    proc = run(STORE_A, reqs, JOURNAL_REFUSAL)
    open(RESP_REFUSAL, "w").write(proc.stdout)
    r = replies_of(proc)
    r2, r3 = payload_of(r[2]), payload_of(r[3])
    assert r2["errors"] == ["duplicate_exact"] and r3["errors"] == ["duplicate_exact"], (r2, r3)
    hash_after = data_hash(STORE_A)
    assert hash_before == hash_after, (hash_before, hash_after)

    # --- store B (fresh): no global dedup ----------------------------------
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": ALPHA}),
        call(3, "inspect", {"scope": "all"}),
    ]
    proc = run(STORE_B, reqs, JOURNAL_B)
    open(RESP_B, "w").write(proc.stdout)
    r = replies_of(proc)
    fresh, insp_b = payload_of(r[2]), payload_of(r[3])
    assert fresh["status"] == "success" and fresh["count"] == 1, fresh
    assert insp_b["inspect"]["tiers"]["tier3_adaptive"]["records"] == 1, insp_b
    ev_b = events(JOURNAL_B)
    assert not any(e["type"] == "remember.refusal" for e in ev_b), ev_b

    print("A1 SCOPE FIXTURE PASS")
    print("store A ingest :", json.dumps({"alpha": a["status"], "beta": b["status"],
                                          "alpha_again": a2["errors"], "beta_again": b2["errors"]}))
    print("store A records:", insp["inspect"]["tiers"]["tier3_adaptive"]["records"],
          "; recall hits:", before["count"], "->", after["count"],
          "; scope sources:", sorted({e["source"] for e in refusals}))
    print("store A order  : unchanged by refusals ->", order_before)
    print("store A batches:", json.dumps([x["written"] for x in batches]))
    print("bare bytes     : data.mdb sha256 identical after separate refused re-ingest ->",
          hash_before[:16], "==", hash_after[:16])
    print("store B fresh  :", json.dumps({"status": fresh["status"], "records":
                                          insp_b["inspect"]["tiers"]["tier3_adaptive"]["records"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
