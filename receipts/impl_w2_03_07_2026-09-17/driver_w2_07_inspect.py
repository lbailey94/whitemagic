#!/usr/bin/env python3
"""W2_07 acceptance — inspect contract / one-universe (spec §5 items 1/2/4/5, §3 cases 5/7).

  inspect answers per state: tier map (tier1 constitution authority, tier2 statutes,
  tier3 adaptive), journal disclosure, arbitration mode; no certification language.
  One-universe: no calibration/conformal/self-model/forecast/claims keys — the four
  universes are not conflated; the unfed self-model series does not exist here (absent,
  disclosed by absence, and the only metric surface — projection stats — is null when off).
  Read-only: a separate inspect-only process leaves `data.mdb` and the journal byte-identical.

Usage: python3 driver_w2_07_inspect.py <harness-binary> <bundle-dir>
"""
import hashlib
import json
import os
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
STORE = os.path.join(BASE, "w207_store")
JOURNAL = os.path.join(BASE, "w207.journal.jsonl")
RESP = os.path.join(BASE, "w207.responses.jsonl")
INSPECT_JOURNAL = os.path.join(BASE, "w207_inspect_only.journal.jsonl")
ITEMS = [
    {"content": "the north bay is the current loading area", "galaxy": "codex", "tags": ["w207"]},
    {"content": "the west gate is locked at night", "galaxy": "codex", "tags": ["w207"]},
]
FORBIDDEN_KEYS = {"calibration", "calibration_store", "conformal", "forecast", "self_model",
                  "claims", "verdict", "certified", "approved", "action", "actions", "alert",
                  "alerts", "intervene", "advise", "correct", "target", "targets", "optimizer",
                  "winner", "winners"}


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def run(reqs, journal):
    payload = "".join(json.dumps(r) + "\n" for r in reqs)
    env = dict(os.environ, WM_GEN3_JOURNAL=journal)
    proc = subprocess.run([BIN, "serve", "--store", STORE], input=payload,
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-400:]
    return proc, {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}


def payload_of(reply):
    return json.loads(reply["result"]["content"][0]["text"])


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_keys(obj, hits, path="inspect"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in FORBIDDEN_KEYS:
                hits.append(f"{path}.{k}")
            scan_keys(v, hits, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan_keys(v, hits, f"{path}[{i}]")


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    for p in (JOURNAL, INSPECT_JOURNAL):
        if os.path.exists(p):
            os.unlink(p)

    proc, replies = run([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": ITEMS}),
        call(3, "inspect", {"scope": "all"}),
    ], JOURNAL)
    open(RESP, "w").write(proc.stdout)
    insp = payload_of(replies[3])["inspect"]

    tiers = insp["tiers"]
    assert tiers["tier1_constitution"]["writers"] == "external admin only", tiers
    assert tiers["tier1_constitution"]["readers"] and tiers["tier1_constitution"]["invariants"], tiers
    assert tiers["tier2_statutes"]["budget_writes_per_min"] and "policy" in tiers["tier2_statutes"], tiers
    assert tiers["tier3_adaptive"]["records"] == 2 and "relations" in tiers["tier3_adaptive"], tiers
    assert insp["arbitration"] and insp["journal"]["configured"] is True, insp
    assert insp["journal"]["ok"] is True and insp["journal"]["violations"] == 0, insp
    assert insp["projection"]["stats"] is None and insp["projection"]["enabled"] is False, insp

    hits = []
    scan_keys(insp, hits)
    assert hits == [], hits

    data_before, journal_before = sha256(os.path.join(STORE, "data.mdb")), sha256(JOURNAL)
    proc, replies = run([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "inspect", {"scope": "all"}),
        call(3, "inspect", {"scope": "tiers"}),
    ], INSPECT_JOURNAL)
    insp2 = payload_of(replies[2])["inspect"]
    assert "tiers" in insp2 and "relations" in insp2, insp2
    data_after, journal_after = sha256(os.path.join(STORE, "data.mdb")), sha256(JOURNAL)
    assert data_before == data_after, (data_before, data_after)
    assert journal_before == journal_after, (journal_before, journal_after)

    print("W2_07 INSPECT CONTRACT PASS")
    print("tiers          : tier1 authority (writers/readers/invariants), tier2 statutes (budget+policy), "
          "tier3 adaptive (records/relations); arbitration + journal disclosed")
    print("one universe   : no calibration/conformal/self_model/forecast/claims keys; "
          "projection stats null when off (unfed surface absent, not claimed)")
    print("read-only      : data.mdb and journal sha256 unchanged across a separate inspect process")
    return 0


if __name__ == "__main__":
    sys.exit(main())
