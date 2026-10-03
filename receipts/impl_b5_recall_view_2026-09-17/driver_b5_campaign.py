#!/usr/bin/env python3
"""B5 recall-view acceptance — fresh fixture campaign (registration §3.2–§3.8).

Cases asserted (candidate = implementation-freeze build):
  2. View correctness: >20 labels (24); scoped recall returns exactly that label's records;
     a shared-token cross-label pair does not bleed.
  3. Filter-not-scorer: unscoped order restricted to a label equals that label's scoped order.
  4. Cross-scope crowd-out: in-view record survives higher-support out-of-scope records with
     candidate_limit=1 (filter-before-selection demonstrated).
  5. Unknown/empty label: empty results + pinned disclosure (abstained, insufficient_evidence,
     cause no_candidates_in_scope, scope present).
  6. Malformed selector: scope="" and any selector containing ':' -> typed caller error, no
     selection.decision event, no silent widening.
  7. Explicit-only: source scan — no env/config path can set a scope.
  8. Bare bytes: data.mdb sha256 unchanged across scoped reads; store file set invariant.
Plus: label-less/malformed provenance records are never selected by any view.

Usage: python3 driver_b5_campaign.py <binary> <bundle-dir>
"""
import hashlib
import json
import os
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
STORE = os.path.join(BASE, "campaign_store")
JOURNAL_A = os.path.join(BASE, "campaign_ingest.journal.jsonl")
JOURNAL_B = os.path.join(BASE, "campaign.journal.jsonl")
RESP = os.path.join(BASE, "campaign.responses.jsonl")
ROOT = "/home/lucas/Desktop/WMgen3"

LABELS = [f"view{i:02d}" for i in range(24)]
TOKEN = "campaign shared token"


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def recall(id_, query, scope=None, limit=100, candidate_limit=100):
    args = {"query": query, "limit": limit, "candidate_limit": candidate_limit,
            "include_historical": False, "min_score": 0.0, "min_coverage": 0.0}
    if scope is not None:
        args["scope"] = scope
    return call(id_, "memory.episodic_search", args)


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def run_payload(payload, journal):
    env = dict(os.environ, WM_GEN3_JOURNAL=journal)
    proc = subprocess.run([BIN, "serve", "--store", STORE], input=payload,
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-400:]
    return {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    for f in (JOURNAL_A, JOURNAL_B, RESP):
        if os.path.exists(f):
            os.unlink(f)

    items = [{"content": f"{TOKEN} numbered {label}", "galaxy": label, "tags": ["campaign"]}
             for label in LABELS]
    items += [
        {"content": f"{TOKEN} cross pair alpha", "galaxy": "crossA", "tags": ["campaign"]},
        {"content": f"{TOKEN} cross pair beta", "galaxy": "crossB", "tags": ["campaign"]},
        {"content": "crowdquery alpha zephyr", "galaxy": "crowdL", "tags": ["campaign"]},
        {"content": "crowdquery alpha beta gamma", "galaxy": "crowdO1", "tags": ["campaign"]},
        {"content": "crowdquery alpha beta gamma", "galaxy": "crowdO2", "tags": ["campaign"]},
        {"content": "crowdquery alpha beta gamma", "galaxy": "crowdO3", "tags": ["campaign"]},
        {"content": f"{TOKEN} multi one", "galaxy": "multi", "tags": ["campaign"]},
        {"content": f"{TOKEN} multi two extra", "galaxy": "multi", "tags": ["campaign"]},
        {"content": f"{TOKEN} multi three extra words", "galaxy": "multi", "tags": ["campaign"]},
        {"content": f"{TOKEN} label-less record", "galaxy": "", "tags": ["campaign"]},
    ]
    expected_unscoped = sum(1 for item in items if TOKEN in item["content"])

    # phase 1: ingest only (fresh store)
    ingest = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
              call(2, "memory.batch_create", {"items": items})]
    r1 = run_payload("".join(json.dumps(x) + "\n" for x in ingest), JOURNAL_A)
    payload_of = lambda r, i: json.loads(r[i]["result"]["content"][0]["text"])
    batch = payload_of(r1, 2)
    assert batch["status"] == "success", batch
    ids = batch["ids"]
    assert len(ids) == len(items), (len(ids), len(items))
    by_source = {}
    for item, rid in zip(items, ids):
        by_source.setdefault(f"corpus:{item['galaxy']}:{item['tags']}", []).append(rid)

    before = sha256(os.path.join(STORE, "data.mdb"))
    files_before = sorted(os.listdir(STORE))

    # phase 2: read-only campaign (no ingest; fresh process)
    reqs = [
        recall(1, TOKEN),                        # unscoped
        recall(2, TOKEN, scope="view07"),        # one label
        recall(3, TOKEN, scope="crossA"),        # shared-token pair, no bleed
        recall(4, "crowdquery alpha beta gamma", scope="crowdL", candidate_limit=1),
        recall(5, TOKEN, scope="multi"),         # order test label
        recall(6, TOKEN, scope="ghost_view"),    # empty view
        recall(7, TOKEN, scope=""),              # malformed: empty
        recall(8, TOKEN, scope="a:b"),           # malformed: colon
        call(9, "inspect", {"scope": "all"}),
    ]
    out = run_payload("".join(json.dumps(x) + "\n" for x in reqs), JOURNAL_B)
    open(RESP, "w").write(json.dumps({"phase1_ids": ids,
                                      "phase2": {k: v for k, v in sorted(out.items())}},
                                     indent=1))

    # 8. bare bytes across scoped reads; store file set invariant
    assert files_before == ["data.mdb", "lock.mdb"], files_before
    assert sorted(os.listdir(STORE)) == ["data.mdb", "lock.mdb"], os.listdir(STORE)
    assert sha256(os.path.join(STORE, "data.mdb")) == before, "data.mdb changed across reads"

    # 2. view correctness
    unscoped = payload_of(out, 1)
    assert unscoped["status"] == "success", unscoped
    assert unscoped["count"] == expected_unscoped, (unscoped["count"], expected_unscoped)
    v07 = payload_of(out, 2)
    assert v07["count"] == 1 and v07["results"][0]["id"] == by_source["corpus:view07:['campaign']"][0], v07
    crossA = payload_of(out, 3)
    assert crossA["count"] == 1 and crossA["results"][0]["id"] == by_source["corpus:crossA:['campaign']"][0], crossA

    # 4. crowd-out: in-view record survives with candidate_limit=1
    crowd = payload_of(out, 4)
    assert crowd["count"] == 1 and crowd["results"][0]["id"] == by_source["corpus:crowdL:['campaign']"][0], crowd

    # 3. filter-not-scorer: unscoped order restricted to the label == scoped order
    multi_ids = set(by_source["corpus:multi:['campaign']"])
    restricted = [h["id"] for h in unscoped["results"] if h["id"] in multi_ids]
    scoped_multi = payload_of(out, 5)
    assert scoped_multi["count"] == 3, scoped_multi
    assert [h["id"] for h in scoped_multi["results"]] == restricted, (restricted, scoped_multi["results"])

    # 5. empty view: pinned disclosure
    ghost = payload_of(out, 6)
    assert ghost["status"] == "success" and ghost["count"] == 0 and ghost["results"] == [], ghost

    # 6. malformed selector: typed caller error, no result
    for idx, sel in ((7, ""), (8, "a:b")):
        bad = payload_of(out, idx)
        assert bad["status"] == "error", (sel, bad)
        assert "invalid scope selector" in bad["error"], (sel, bad)

    # 7. explicit-only: static scan — no env/config path can set a scope
    scan_hits = []
    for root, _dirs, names in os.walk(os.path.join(ROOT, "crates")):
        if "target" in root:
            continue
        for n in names:
            if not n.endswith(".rs"):
                continue
            text = open(os.path.join(root, n), encoding="utf-8", errors="replace").read()
            for line in text.splitlines():
                if "env::var" in line and "SCOPE" in line.upper():
                    scan_hits.append((n, line.strip()))
                if "WM_GEN3_SCOPE" in line:
                    scan_hits.append((n, line.strip()))
    assert scan_hits == [], scan_hits

    # journal analysis (ingest + campaign journals)
    events = []
    for j in (JOURNAL_A, JOURNAL_B):
        events += [json.loads(l) for l in open(j) if l.strip()]
    chains = {e["result_id"]: e["chain"][0] for e in events if e["type"] == "provenance.chain"}
    labels_seen = {chains[h["id"]].split(":")[1] for h in unscoped["results"]
                   if chains[h["id"]].startswith("corpus:")}
    assert {l for l in LABELS if l in labels_seen} == set(LABELS), len(labels_seen)
    # label-less record (empty galaxy) is unscoped-visible but not in any view
    empty_label = [h for h in unscoped["results"] if chains[h["id"]].startswith("corpus::")]
    assert len(empty_label) == 1, empty_label
    decisions = [e for e in events if e["type"] == "selection.decision"]
    ghost_events = [e for e in decisions if e.get("scope") == "ghost_view"]
    assert len(ghost_events) == 1, ghost_events
    assert ghost_events[0]["abstained"] is True
    assert ghost_events[0]["reason"] == "insufficient_evidence"
    assert ghost_events[0]["cause"] == "no_candidates_in_scope"
    assert ghost_events[0]["scope_considered"] == 0
    assert not [e for e in decisions if e.get("scope") in ("", "a:b")], "malformed selector journaled"
    scoped_events = [e for e in decisions if e.get("scope") in
                     ("view07", "crossA", "crowdL", "multi")]
    assert len(scoped_events) == 4, scoped_events
    assert all(e.get("scope_considered") is not None for e in scoped_events), scoped_events

    insp = payload_of(out, 9)
    records = insp["inspect"]["tiers"]["tier3_adaptive"]["records"]
    assert records == len(items), (records, len(items))

    print("B5 RECALL-VIEW CAMPAIGN PASS")
    print(f"view correctness : {len(LABELS)} labels (> Gen2 cap 20); scoped recall exact; "
          f"shared-token pair no bleed; label-less record visible unscoped only")
    print("crowd-out        : candidate_limit=1 with 3 higher-support out-of-scope records -> "
          "in-view record still returned (filter-before-selection)")
    print("filter-not-scorer: unscoped order restricted to label == scoped order")
    print("empty view       : results [] + abstained/insufficient_evidence/no_candidates_in_scope, "
          "scope_considered 0")
    print("malformed select : scope=\"\" and scope=\"a:b\" -> typed caller error, no journal entry")
    print("explicit-only    : source scan clean (no env/config scope path)")
    print("bare bytes       : data.mdb sha256 unchanged across scoped reads; store = {data.mdb, lock.mdb}")
    print("inspect          : record count invariant; no registry surface")
    return 0


if __name__ == "__main__":
    sys.exit(main())
