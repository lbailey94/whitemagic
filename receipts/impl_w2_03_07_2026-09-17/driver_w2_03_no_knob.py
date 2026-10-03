#!/usr/bin/env python3
"""W2_03 acceptance — no-knob strata test (spec §3 cases 1/2/4/5, §5 items 1/2/4/5).

Scrubbed-environment runs (only the declared `WM_GEN3_*` switches present) on the frozen
canary fixtures: strata still derive and enforce at request time.
  run 1 (defaults):   source stratum 0, target stratum 2 (effective = last relation, F4),
                      ordering [src, dst]; mode named in the journal.
  run 2 (`WM_GEN3_SWEEP=0`): flat strata 1, zero proposals, ordering [dst, src].
Mechanical no-knob check: the binary and the source contain no `WM_VALIDITY` symbol.

Usage: python3 driver_w2_03_no_knob.py <harness-binary> <bundle-dir>
"""
import json
import os
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
ROOT = "/home/lucas/Desktop/WMgen3"
FIX = os.path.dirname(os.path.abspath(__file__))


def run(store, fixture, journal, switches):
    env = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "")}
    env.update(switches)
    env["WM_GEN3_JOURNAL"] = journal
    env["WM_GEN3_JOURNAL_HASH_OUT"] = journal + ".sha256"
    with open(os.path.join(FIX, fixture)) as fh:
        payload = fh.read()
    proc = subprocess.run([BIN, "serve", "--store", store], input=payload,
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-400:]
    replies = {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}
    return replies, proc.stdout


def payload_of(reply):
    return json.loads(reply["result"]["content"][0]["text"])


def events(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def last_selection(path):
    return [e for e in events(path) if e["type"] == "selection.decision"][-1]


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    # mechanical no-knob check: no WM_VALIDITY symbol in binary or source
    binary = open(BIN, "rb").read()
    assert b"WM_VALIDITY" not in binary, "binary carries a WM_VALIDITY knob"
    for d in ("crates/wm-gen3-core/src", "crates/wm-gen3-harness/src"):
        for name in os.listdir(os.path.join(ROOT, d)):
            if name.endswith(".rs"):
                text = open(os.path.join(ROOT, d, name)).read()
                assert "WM_VALIDITY" not in text, (name, "source carries a WM_VALIDITY knob")

    # --- run 1: scrubbed env, declared switches only ------------------------
    store1 = os.path.join(BASE, "w203_store_default")
    j1 = os.path.join(BASE, "w203_default.journal.jsonl")
    replies, stdout = run(store1, "A_full.jsonl", j1, {"WM_GEN3_ARBITRATION": "structural"})
    open(os.path.join(BASE, "w203_default.responses.jsonl"), "w").write(stdout)
    found = payload_of(replies[3])
    assert found["count"] == 2, found
    assert [h["id"] for h in found["results"]] == [1, 0], found
    sel = last_selection(j1)
    assert sel["arbitration"] == "Structural", sel
    entries = sel["selected"]
    assert [e["stratum"] for e in entries] == [0, 2], sel
    proposals = [e for e in events(j1) if e["type"] == "relation.proposed"]
    assert len(proposals) == 5, proposals
    last_rel = max(e["relation_id"] for e in proposals)
    assert entries[1]["superseded_by"] == last_rel, (entries, last_rel)

    # --- run 2: WM_GEN3_SWEEP=0 (declared switch) ---------------------------
    store2 = os.path.join(BASE, "w203_store_sweepoff")
    j2 = os.path.join(BASE, "w203_sweepoff.journal.jsonl")
    replies, stdout = run(store2, "A_full.jsonl", j2,
                          {"WM_GEN3_ARBITRATION": "structural", "WM_GEN3_SWEEP": "0"})
    open(os.path.join(BASE, "w203_sweepoff.responses.jsonl"), "w").write(stdout)
    found = payload_of(replies[3])
    assert [h["id"] for h in found["results"]] == [0, 1], found
    sel = last_selection(j2)
    assert [e["stratum"] for e in sel["selected"]] == [1, 1], sel
    assert not any(e["type"] == "relation.proposed" for e in events(j2)), "proposals with sweep off"

    print("W2_03 NO-KNOB STRATA PASS")
    print("no-knob scan   : no WM_VALIDITY symbol in binary or source")
    print("defaults       : order [1,0]; strata [0,2]; superseded_by = last relation",
          last_rel, "; mode Structural")
    print("sweep off      : order [0,1]; strata [1,1]; zero proposals (declared switch only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
