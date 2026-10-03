#!/usr/bin/env python3
"""Ops fold-in — bundle↔journal parity check (fold-in #13; A2 spec §1.4 link boundary).

Verifies the Gen3 journal side can reconstruct the fields A2 requires for every returned result
(route, score, basis/chain, currentness, galaxy), and that no Gen2-bundle-only surface is silently
claimed on the journal side (those stay link-side; the never-neither rule).

Usage: python3 driver_parity.py <harness-binary> <bundle-dir>
"""
import json
import os
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
STORE = os.path.join(BASE, "parity_store")
JOURNAL = os.path.join(BASE, "parity.journal.jsonl")
RESP = os.path.join(BASE, "parity.responses.jsonl")

ITEMS = [
    {"content": "the deploy region for the service is us-east", "galaxy": "codex", "tags": ["parity"]},
    {"content": "the deploy region for the service is eu-west", "galaxy": "codex", "tags": ["parity"]},
    {"content": "unrelated note about the northern corridor", "galaxy": "codex", "tags": ["parity"]},
]
# Gen2 bundle v0 surfaces that must NOT be claimed by the Gen3 journal (link-side, never neither).
LINK_SIDE_KEYS = ["bundle", "visibility", "integrity", "conflicts", "cold", "private",
                  "model_exclude", "representation", "truncated", "exact_read_available",
                  "revision_count", "chain_valid", "event_time", "via", "matched_terms"]


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    if os.path.exists(JOURNAL):
        os.unlink(JOURNAL)
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": ITEMS}),
        call(3, "memory.episodic_search", {
            "query": "deploy region failover", "limit": 10, "candidate_limit": 100,
            "include_historical": False, "min_score": 0.0, "min_coverage": 0.0}),
        call(4, "inspect", {"scope": "all"}),
    ]
    payload = "".join(json.dumps(r) + "\n" for r in reqs)
    env = dict(os.environ, WM_GEN3_JOURNAL=JOURNAL)
    proc = subprocess.run([BIN, "serve", "--store", STORE], input=payload,
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-400:]
    open(RESP, "w").write(proc.stdout)
    replies = {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}
    found = json.loads(replies[3]["result"]["content"][0]["text"])
    assert found["count"] == 2, found

    events = [json.loads(l) for l in open(JOURNAL) if l.strip()]
    decisions = [e for e in events if e["type"] == "selection.decision"]
    assert len(decisions) == 1, decisions
    sel = decisions[0]
    chains = {e["result_id"]: e for e in events if e["type"] == "provenance.chain"}

    # required reconstruction fields present
    for k in ("projection_ran", "projection_error", "semantic_candidates", "arbitration"):
        assert k in sel, (k, sel)
    for e in sel["selected"]:
        assert e["id"] in chains, (e, chains)
        chain = chains[e["id"]]
        assert chain["complete"] is True and chain["chain"], chain
        assert isinstance(e["score"], float) and isinstance(e["rank_key"], float), e
        assert e["stratum"] in (0, 1, 2), e
        assert (e["superseded_by"] is not None) == (e["stratum"] == 2), e
        src = chain["chain"][0]
        assert src.startswith("corpus:"), src
        galaxy = src.split(":")[1]
        assert galaxy == "codex", src

    # link-side surfaces must not be claimed by the journal
    claimed = []
    for e in events:
        for k in LINK_SIDE_KEYS:
            if k in e or k in e.get("type", ""):
                claimed.append((e["type"], k))
    assert claimed == [], claimed

    route = "substrate/lexical" + ("+semantic" if sel["projection_ran"] else "")
    print("OPS PARITY CHECK PASS")
    print("reconstruction : route=%s score/rank_key, basis=chain, currentness=stratum/superseded_by, "
          "galaxy=source" % route)
    print("results        :", json.dumps([{k: e[k] for k in ("id", "rank", "score", "stratum", "superseded_by")}
                                          for e in sel["selected"]]))
    print("link-side      : no Gen2 bundle-only keys claimed by the journal (%d scanned)" % len(LINK_SIDE_KEYS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
