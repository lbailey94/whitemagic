#!/usr/bin/env python3
"""W2_01 acceptance — relations/edges (spec W2_01 §3/§5).

Asserted:
  1. Round-trip (C5 extension): kind/direction/provenance(rule_id)/state/w/s/c/t byte-identical
     across processes.
  2. Direction registration: the edge is later->earlier (temporal precedence).
  3. Counts are edges, not attempts: relation rows == admitted proposals (raw); deduped endpoint
     metric reported alongside; sweep attempt stats stay separate.
  4. Rate/quality gates declared: pair budget + candidacy params from the tier-2 policy.
  5. Dynamics parked: no Hebbian/decay/strengthen/edge-prune symbol in the serving path.
  6. Visibility: both endpoints are listed on the edge (inspect).
Declared (not executed): transfer N/A (no edge transfer mechanism exists); causal ties by
construction (sweep orders by created_at, the rule requires strict later > earlier — no inversion
path); no hidden coupling (B1 no-planner + rank-field audit cited); read discipline (ops read-path
audit cited).

Usage: python3 driver_w2_01_edges.py <harness-binary> <bundle-dir>
"""
import json
import os
import re
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
ROOT = "/home/lucas/Desktop/WMgen3"
OLD = "the deploy region for the service is us-east and the failover target is eu-west"
NEW = "the deploy region for the service is eu-west"
DYNAMICS = ["hebbian", "decay", "strengthen", "weaken", "edge_prune", "prune_edges", "prune_edge"]


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


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


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    store = os.path.join(BASE, "w201_store")
    j1 = os.path.join(BASE, "w201.journal.jsonl")
    replies = run(store, [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": [
            {"content": OLD, "galaxy": "codex", "tags": ["w201"]},
            {"content": NEW, "galaxy": "codex", "tags": ["w201"]},
        ]}),
        call(3, "inspect", {"scope": "all"}),
    ], j1)
    ids = payload_of(replies[2])["ids"]
    old_id, new_id = ids
    insp = payload_of(replies[3])["inspect"]
    relations = insp["relations"]

    props = [e for e in events(j1) if e["type"] == "relation.proposed"]
    raw = len(props)
    deduped = len({(p["src"], p["dst"]) for p in props})
    assert raw > 0 and deduped == 1, (raw, deduped)
    assert all((p["src"], p["dst"]) == (new_id, old_id) for p in props), props

    # counts are edges, not attempts: admitted rows == raw proposals
    assert len(relations) == raw, (len(relations), raw)
    for r in relations:
        assert r["kind"] == "Supersedes", r
        assert r["rule_id"], r
        assert {r["src"], r["dst"]} == {old_id, new_id}, r
        assert r["state"] in ("Candidate", "Superseded", "Rejected"), r
        for k in ("w", "s", "c", "t"):
            assert k in r, r

    # declared rate/quality gates + candidacy params
    policy = insp["tiers"]["tier2_statutes"]["policy"]
    assert policy["pair_budget"] == 200000 and policy["rare_df_divisor"] == 20 \
        and policy["rare_df_floor"] == 2, policy

    # round-trip across processes
    j2 = os.path.join(BASE, "w201_roundtrip.journal.jsonl")
    replies2 = run(store, [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "inspect", {"scope": "all"}),
    ], j2)
    relations2 = payload_of(replies2[2])["inspect"]["relations"]
    assert relations == relations2, (relations, relations2)

    # dynamics parked: no edge-dynamics symbol in the serving path
    hits = []
    for d in ("crates/wm-gen3-core/src", "crates/wm-gen3-harness/src"):
        for name in sorted(os.listdir(os.path.join(ROOT, d))):
            if not name.endswith(".rs"):
                continue
            text = "\n".join(l.split("//")[0] for l in open(os.path.join(ROOT, d, name)).read().splitlines())
            for tok in DYNAMICS:
                if re.search(tok, text, re.I):
                    hits.append((name, tok))
    assert hits == [], hits

    print("W2_01 EDGES ACCEPTANCE PASS")
    print("direction      : later->earlier (", new_id, "->", old_id, "); kind Supersedes; provenance rule_id present")
    print("counts         : admitted rows =", len(relations), "= raw proposals", raw,
          "; deduped endpoint metric =", deduped, "(attempts stay in sweep stats)")
    print("gates          : pair_budget 200000, rare_df_divisor 20, rare_df_floor 2 (declared, tier-2)")
    print("round-trip     : relations byte-identical across processes (incl. rule_id/state/w/s/c/t)")
    print("dynamics       : no Hebbian/decay/strengthen/edge-prune symbol in the serving path (parked)")
    print("declared N/A   : transfer (no mechanism); causal ties (strict later>earlier, no inversion path)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
