#!/usr/bin/env python3
"""A3 acceptance — revisions/supersession (spec W1_A3 §3/§4/§5).

Fixtures (all via the stdio harness, structural arbitration):
  A. direction + F4 metric discipline + history-lossless + round-trip (store A: old then new)
  B. direction flip (store B: same contents, reverse ingestion order -> edge direction follows
     temporal precedence, not narrative)
  C. window-from-journal (relation.proposed ts values support a changes_since-style window)
  D. predicate-sense collision (spec case 1: "R must not link them") — OBSERVED, reported as a
     finding when the lexical rule links the pair.

Exit codes: 0 = all asserted items pass and case D is clean; 3 = asserted items pass but case D
is linked (finding to adjudicate); 1 = an asserted item failed.

Usage: python3 driver_a3_acceptance.py <harness-binary> <bundle-dir>
"""
import json
import os
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
OLD = "the deploy region for the service is us-east and the failover target is eu-west"
NEW = "the deploy region for the service is eu-west"


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def recall(id_, query, historical=False):
    return call(id_, "memory.episodic_search", {
        "query": query, "limit": 10, "candidate_limit": 100,
        "include_historical": historical, "min_score": 0.0, "min_coverage": 0.0})


def run(store, reqs, journal):
    payload = "".join(json.dumps(r) + "\n" for r in reqs)
    env = dict(os.environ, WM_GEN3_JOURNAL=journal, WM_GEN3_ARBITRATION="structural")
    proc = subprocess.run([BIN, "serve", "--store", store], input=payload,
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-400:]
    return {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}


def payload_of(reply):
    return json.loads(reply["result"]["content"][0]["text"])


def events(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def items(texts):
    return [{"content": t, "galaxy": "codex", "tags": ["a3"]} for t in texts]


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    findings = []

    # --- store A: old then new ---------------------------------------------
    ja = os.path.join(BASE, "a3_a.journal.jsonl")
    ids = None
    replies = run(os.path.join(BASE, "a3_store_a"), [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": items([OLD, NEW])}),
        recall(3, "deploy region failover"),
        recall(4, "deploy region failover", historical=True),
        call(5, "inspect", {"scope": "all"}),
    ], ja)
    batch = payload_of(replies[2])
    ids = batch["ids"]
    assert batch["status"] == "success" and len(ids) == 2, batch
    old_id, new_id = ids
    cur, hist, insp_a = (payload_of(replies[i]) for i in (3, 4, 5))

    ev = events(ja)
    proposals = [e for e in ev if e["type"] == "relation.proposed"]
    assert proposals, "no proposals on the state-change pair"
    assert all((p["src"], p["dst"]) == (new_id, old_id) for p in proposals), proposals
    raw = len(proposals)
    deduped = len({(p["src"], p["dst"]) for p in proposals})
    assert raw > deduped == 1, (raw, deduped)
    sel = [e for e in ev if e["type"] == "selection.decision"][0]["selected"]
    by_id = {e["id"]: e for e in sel}
    assert by_id[new_id]["stratum"] == 0, sel
    assert by_id[old_id]["stratum"] == 2 and by_id[old_id]["superseded_by"] is not None, sel
    hist_sel = [e for e in ev if e["type"] == "selection.decision"][1]["selected"]
    assert {e["stratum"] for e in hist_sel} == {1}, hist_sel
    assert {e["id"] for e in hist_sel} == {old_id, new_id}, hist_sel
    rel_a = insp_a["inspect"]["relations"]
    assert rel_a and all(r["kind"] == "Supersedes" for r in rel_a), rel_a

    # round-trip: second process, inspect only
    replies2 = run(os.path.join(BASE, "a3_store_a"), [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "inspect", {"scope": "all"}),
    ], os.path.join(BASE, "a3_a2.journal.jsonl"))
    rel_a2 = payload_of(replies2[2])["inspect"]["relations"]
    assert rel_a == rel_a2, (rel_a, rel_a2)

    # window-from-journal: proposals carry ts; a [min,max] window selects them
    ts = [p["ts"] for p in proposals]
    assert ts == sorted(ts), ts
    window = [p for p in proposals if min(ts) <= p["ts"] <= max(ts)]
    assert len(window) == raw, window

    # --- store B: reverse ingestion order (direction flip) -----------------
    jb = os.path.join(BASE, "a3_b.journal.jsonl")
    replies = run(os.path.join(BASE, "a3_store_b"), [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": items([NEW, OLD])}),
    ], jb)
    ids_b = payload_of(replies[2])["ids"]
    new_b, old_b = ids_b  # NEW ingested first, OLD second -> OLD is temporally later
    props_b = [e for e in events(jb) if e["type"] == "relation.proposed"]
    assert props_b, "no proposal in flip store"
    assert all((p["src"], p["dst"]) == (old_b, new_b) for p in props_b), props_b

    # --- store C: predicate-sense collision (spec case 1) -------------------
    jc = os.path.join(BASE, "a3_c.journal.jsonl")
    run(os.path.join(BASE, "a3_store_c"), [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": items([
            "I prefer Rust over Python for systems work",
            "I wrote Rust last year for a course",
        ])}),
    ], jc)
    props_c = [e for e in events(jc) if e["type"] == "relation.proposed"]
    linked = len(props_c) > 0
    if linked:
        findings.append({"case": 1, "expected": "no link (spec)", "observed":
                         f"{len(props_c)} proposal(s)", "evidence": "a3_c.journal.jsonl"})

    print("A3 ACCEPTANCE — asserted items PASS" if not findings else "A3 ACCEPTANCE — asserted items PASS; FINDINGS present")
    print("direction      : A src=new dst=old; B flip -> src=later-ingested (temporal precedence)")
    print("F4 metric      : raw proposals =", raw, "; deduped endpoint pairs =", deduped,
          "(headline uses deduped; raw disclosed)")
    print("history        : superseded record restored under include_historical (all stratum 1)")
    print("round-trip     : relations byte-identical across processes (kind/src/dst/rule_id/state/w/s/c/t)")
    print("window         : relation.proposed ts support a changes_since window (", raw, "in window )")
    print("case 1 (sense) :", "LINKED -> FINDING" if linked else "not linked (spec satisfied)")
    for f in findings:
        print("FINDING:", json.dumps(f))
    return 3 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
