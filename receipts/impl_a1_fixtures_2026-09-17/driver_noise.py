#!/usr/bin/env python3
"""A1 fixtures — noise acceptance (spec W1_A1 rev 2 §5.7), ablation (§4), ordering-unchanged.

Run 1 (default, table on): baseline store -> 5 declared noise classes + 2 controls in one
batch; expects 5 `noise_class` refusals with the class named, 2 controls admitted, record
count unchanged, zero purges, and recall ordering over the pre-existing store unchanged.
Run 2 (fresh store, WM_GEN3_NOISE=0): the same noise items are admitted and recallable.

Usage: python3 driver_noise.py <harness-binary> <bundle-dir>
"""
import json
import os
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
STORE = os.path.join(BASE, "noise_store")
STORE_OFF = os.path.join(BASE, "noise_store_ablation")
JOURNAL = os.path.join(BASE, "noise.journal.jsonl")
JOURNAL_OFF = os.path.join(BASE, "noise_ablation.journal.jsonl")
RESP = os.path.join(BASE, "noise.responses.jsonl")
RESP_OFF = os.path.join(BASE, "noise_ablation.responses.jsonl")

BASELINE = [
    {"content": "baseline record one alpha", "galaxy": "codex", "tags": ["noise-demo"]},
    {"content": "baseline record two alpha", "galaxy": "codex", "tags": ["noise-demo"]},
    {"content": "baseline record three alpha", "galaxy": "codex", "tags": ["noise-demo"]},
]
NOISE = [
    {
        "content": "Traceback (most recent call last):\n  File \"x.py\", line 1\nError: boom",
        "galaxy": "codex",
        "tags": ["noise-demo"],
    },
    {"content": "first line is fine\nError: something failed", "galaxy": "codex", "tags": ["noise-demo"]},
    {"content": "{\"json\": {\"a\": 1}}", "galaxy": "codex", "tags": ["noise-demo"]},
    {"content": "<function foo at 0x7f00>", "galaxy": "codex", "tags": ["noise-demo"]},
    {"content": "tiny", "galaxy": "codex", "tags": ["noise-demo"]},
]
CONTROLS = [
    {"content": "a perfectly ordinary memory record", "galaxy": "codex", "tags": ["noise-demo"]},
    {"content": "the Error: prefix convention is documented", "galaxy": "codex", "tags": ["noise-demo"]},
]
CLASSES = ["traceback", "error_line", "json_blob", "function_repr", "too_short"]


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def recall(id_, query):
    return call(id_, "memory.episodic_search", {
        "query": query, "limit": 10, "candidate_limit": 100,
        "include_historical": False, "min_score": 0.0, "min_coverage": 0.0})


def run(store, reqs, journal, env_extra=None):
    payload = "".join(json.dumps(r) + "\n" for r in reqs)
    env = dict(os.environ, WM_GEN3_JOURNAL=journal, **(env_extra or {}))
    proc = subprocess.run([BIN, "serve", "--store", store], input=payload,
                          capture_output=True, text=True, env=env, timeout=300)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"harness exit {proc.returncode}")
    return proc


def replies_of(proc):
    out = {}
    for line in proc.stdout.splitlines():
        obj = json.loads(line)
        out[obj["id"]] = obj
    return out


def payload_of(reply):
    return json.loads(reply["result"]["content"][0]["text"])


def events(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def order(results):
    return [(r["id"], r["rank"], r.get("stratum"), r.get("superseded_by")) for r in results]


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    for path in (JOURNAL, JOURNAL_OFF):
        if os.path.exists(path):
            os.unlink(path)

    # --- run 1: table on ---------------------------------------------------
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": BASELINE}),
        recall(3, "baseline"),
        call(4, "memory.batch_create", {"items": NOISE + CONTROLS}),
        call(5, "inspect", {"scope": "all"}),
        recall(6, "baseline"),
        recall(7, "traceback"),
        recall(8, "ordinary"),
    ]
    proc = run(STORE, reqs, JOURNAL)
    open(RESP, "w").write(proc.stdout)
    r = replies_of(proc)
    first, before, refused, insp, after = (payload_of(r[i]) for i in (2, 3, 4, 5, 6))
    no_hit, control = payload_of(r[7]), payload_of(r[8])

    assert first["status"] == "success" and first["count"] == 3, first
    assert refused["status"] == "error", refused
    assert refused["failed"] == 5 and refused["errors"] == ["noise_class"] * 5, refused
    assert len(refused["ids"]) == 2, refused
    assert insp["inspect"]["tiers"]["tier3_adaptive"]["records"] == 5, insp
    assert order(before["results"]) == order(after["results"]), (before, after)
    assert no_hit["count"] == 0, no_hit
    assert control["count"] == 1, control

    ev = events(JOURNAL)
    refusals = [e for e in ev if e["type"] == "remember.refusal"]
    noise = [e for e in refusals if e.get("reason") == "noise_class"]
    assert len(refusals) == 5 and len(noise) == 5, refusals
    assert sorted(e["class"] for e in noise) == sorted(CLASSES), noise
    for e in noise:
        assert e.get("content_sha256") and e.get("source"), e
    assert not any(e.get("reason") == "duplicate_exact" for e in refusals), refusals
    batches = [e for e in ev if e["type"] == "ingest.batch"]
    assert [b["written"] for b in batches] == [3, 2], batches
    assert not any(e["type"] == "closure.violation" for e in ev), "violations present"

    # --- run 2: ablation (WM_GEN3_NOISE=0) ---------------------------------
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "memory.batch_create", {"items": NOISE}),
        recall(3, "traceback"),
        call(4, "inspect", {"scope": "all"}),
    ]
    proc = run(STORE_OFF, reqs, JOURNAL_OFF, env_extra={"WM_GEN3_NOISE": "0"})
    open(RESP_OFF, "w").write(proc.stdout)
    r = replies_of(proc)
    admitted, hit, insp_off = (payload_of(r[i]) for i in (2, 3, 4))
    assert admitted["status"] == "success" and admitted["count"] == 5, admitted
    assert hit["count"] == 1, hit
    assert insp_off["inspect"]["tiers"]["tier3_adaptive"]["records"] == 5, insp_off
    ev_off = events(JOURNAL_OFF)
    assert not any(e["type"] == "remember.refusal" for e in ev_off), ev_off
    batches_off = [e for e in ev_off if e["type"] == "ingest.batch"]
    assert [b["written"] for b in batches_off] == [5], batches_off

    print("A1 NOISE FIXTURE PASS")
    print("run1 refused   :", json.dumps({"failed": refused["failed"], "errors": sorted(set(refused["errors"])),
                                          "admitted_ids": refused["ids"]}))
    print("run1 classes   :", json.dumps(sorted(e["class"] for e in noise)))
    print("run1 records   :", insp["inspect"]["tiers"]["tier3_adaptive"]["records"],
          "(3 baseline + 2 controls; 5 noise items refused, none stored)")
    print("run1 ordering  : before == after ->", order(before["results"]))
    print("run1 no-store  : recall 'traceback' ->", no_hit["count"], "hits; control ->", control["count"], "hit")
    print("run1 batches   :", json.dumps([b["written"] for b in batches]))
    print("run2 ablation  : admitted", admitted["count"], "records; recall 'traceback' ->", hit["count"], "hit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
