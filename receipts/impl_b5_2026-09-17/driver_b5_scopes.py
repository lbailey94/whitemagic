#!/usr/bin/env python3
"""B5 acceptance — galaxies/compartments, Gen3 compile/link side (spec W1_B5 §3/§5).

Asserted (Gen3 side):
  1. Labels are views over ONE store: 30 distinct labels (over Gen2's dynamic cap of 20) create
     no per-name resources — the store file set stays {data.mdb, lock.mdb}; labels are derived
     from record provenance (`corpus:<label>:<tags>`), not a registry.
  2. A label view is reconstructible from the evidence surface: filtering hits by provenance
     chain prefix yields exactly that label's records (wrapper-side view, no new API).
  3. No registry/compartment/capability surfaces exist in inspect (key scan).
Declared (link side, per spec §1.2/§1.3/§1.4): isolation classes + cross-class transfer (no class
markers in Gen3); compartments / membership-vs-authz / effective grants (no `_meta.compartment`;
authorization needs an authenticated channel — out of scope, disclosure is the contract);
capability typos (no capability parameter); fail-open-on-governance-error (no governance path;
Gen3's fail-closed is budgets/floors); cap bypass (no dynamic registry exists — closed by absence);
47-galaxy narrative (errata A#6; no Gen3 metric cites it).

Usage: python3 driver_b5_scopes.py <harness-binary> <bundle-dir>
"""
import json
import os
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
STORE = os.path.join(BASE, "b5_store")
JOURNAL = os.path.join(BASE, "b5.journal.jsonl")
RESP = os.path.join(BASE, "b5.responses.jsonl")
LABELS = [f"label{i:02d}" for i in range(30)]
SHARED = "scope view shared token for the label boundary check"


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    if os.path.exists(JOURNAL):
        os.unlink(JOURNAL)
    items = [{"content": f"{SHARED} in {label}", "galaxy": label, "tags": ["b5"]} for label in LABELS]
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": items}),
        call(3, "memory.episodic_search", {
            "query": SHARED, "limit": 30, "candidate_limit": 100,
            "include_historical": False, "min_score": 0.0, "min_coverage": 0.0}),
        call(4, "inspect", {"scope": "all"}),
    ]
    payload = "".join(json.dumps(r) + "\n" for r in reqs)
    env = dict(os.environ, WM_GEN3_JOURNAL=JOURNAL)
    proc = subprocess.run([BIN, "serve", "--store", STORE], input=payload,
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-400:]
    open(RESP, "w").write(proc.stdout)
    r = {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}
    payload_of = lambda i: json.loads(r[i]["result"]["content"][0]["text"])

    batch, hits, insp = payload_of(2), payload_of(3), payload_of(4)
    assert batch["status"] == "success" and batch["count"] == 30, batch
    assert hits["count"] == 30, hits

    # 1. one store, no per-name resources
    files = sorted(os.listdir(STORE))
    assert files == ["data.mdb", "lock.mdb"], files
    assert insp["inspect"]["tiers"]["tier3_adaptive"]["records"] == 30, insp

    # 2. label views reconstructible from provenance chains
    events = [json.loads(l) for l in open(JOURNAL) if l.strip()]
    chains = {e["result_id"]: e["chain"][0] for e in events if e["type"] == "provenance.chain"}
    labels_seen = {chains[h["id"]].split(":")[1] for h in hits["results"]}
    assert labels_seen == set(LABELS), (len(labels_seen), sorted(set(LABELS) - labels_seen)[:5])
    label0 = [h for h in hits["results"] if chains[h["id"]].startswith("corpus:label00:")]
    assert len(label0) == 1 and label0[0]["content"].endswith("label00"), label0

    # 3. no registry/compartment/capability surfaces in inspect
    forbidden = {"galaxy", "galaxies", "label", "labels", "registry", "compartment",
                 "compartments", "capability", "capabilities", "tier_grant", "authz"}
    found = []

    def scan(obj, path="inspect"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower() in forbidden:
                    found.append(f"{path}.{k}")
                scan(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                scan(v, f"{path}[{i}]")

    scan(insp["inspect"])
    assert found == [], found

    print("B5 SCOPES ACCEPTANCE PASS (Gen3 compile/link side)")
    print("labels as views: 30 labels (over Gen2's cap of 20) -> store files", files,
          "; records", insp["inspect"]["tiers"]["tier3_adaptive"]["records"])
    print("view filter    : provenance-chain prefix yields exactly one label00 record;",
          len(labels_seen), "distinct labels observed in one recall")
    print("no registry    : inspect exposes no galaxy/label/registry/compartment/capability surface")
    print("declared (link): isolation classes + transfer; compartments/membership!=authz/grants; "
          "capability typos; fail-open-governance; cap bypass closed by absence; 47-galaxy narrative guard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
