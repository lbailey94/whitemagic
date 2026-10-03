#!/usr/bin/env python3
"""B1 acceptance — rank-field audit (spec W1_B1 §5.3): every selected hit carries the B1 rank
fields; the default ordering (PenaltyMultiplier: rank_key desc, id desc) is reconstructible
from the journal; every hit has a complete A2 provenance chain; rank_key >= score for
non-superseded records (recency factor >= 1).

Usage: python3 driver_rankfields.py <harness-binary> <bundle-dir>
"""
import json
import os
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
STORE = os.path.join(BASE, "rankfields_store")
JOURNAL = os.path.join(BASE, "rankfields.journal.jsonl")
RESP = os.path.join(BASE, "rankfields.responses.jsonl")

ITEMS = [
    {"content": "rank audit record alpha covers the northern corridor", "galaxy": "codex", "tags": ["rank-demo"]},
    {"content": "rank audit record beta covers the northern corridor and the eastern gate",
     "galaxy": "codex", "tags": ["rank-demo"]},
    {"content": "rank audit record gamma covers the eastern gate and the southern yard",
     "galaxy": "codex", "tags": ["rank-demo"]},
]
QUERY = "rank audit record northern corridor eastern gate"


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
            "query": QUERY, "limit": 10, "candidate_limit": 100,
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
    assert found["count"] >= 3, found

    events = [json.loads(l) for l in open(JOURNAL) if l.strip()]
    decisions = [e for e in events if e["type"] == "selection.decision"]
    assert len(decisions) == 1, decisions
    selected = decisions[0]["selected"]
    required = {"id", "rank", "rank_key", "score", "semantic_support", "stratum", "superseded_by"}
    for entry in selected:
        assert required <= set(entry), (entry, required - set(entry))
    ranks = [e["rank"] for e in selected]
    assert ranks == list(range(1, len(selected) + 1)), ranks

    reconstructed = sorted(selected, key=lambda e: (-e["rank_key"], -e["id"]))
    assert [e["id"] for e in reconstructed] == [e["id"] for e in selected], (reconstructed, selected)
    assert [e["id"] for e in found["results"]] == [e["id"] for e in selected], (found, selected)
    for e in selected:
        if e["superseded_by"] is None:
            assert e["rank_key"] >= e["score"], e

    chains = [e for e in events if e["type"] == "provenance.chain"]
    chained = {e["result_id"]: e["complete"] for e in chains}
    for e in selected:
        assert chained.get(e["id"]) is True, (e, chained)

    print("B1 RANK-FIELD AUDIT PASS")
    print("selected       :", json.dumps([
        {k: e[k] for k in ("id", "rank", "rank_key", "score", "semantic_support", "stratum", "superseded_by")}
        for e in selected]))
    print("reconstruction : rank_key desc, id desc -> matches reported order; ranks 1..n")
    print("provenance     : complete chains for all selected ids:", sorted(chained))
    return 0


if __name__ == "__main__":
    sys.exit(main())
