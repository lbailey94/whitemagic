#!/usr/bin/env python3
"""A2 starvation-vs-refusal + route disclosure driver (spec W1_A2 cases 7, 9).

Runs the frozen implementation (commit e3c6c6d) through the stdio harness:
  1. budget 1: second write refused with a typed budget refusal; reads stay open;
     an empty read discloses insufficiency (a token distinct from the refusal);
  2. projection on (model cache present): selection.decision discloses
     projection_ran=true / projection_error=false.

Usage: python3 driver_starve_route.py <harness-binary> <workdir>
"""
import json
import os
import subprocess
import sys

BIN = sys.argv[1]
BASE = sys.argv[2]
CACHE = os.environ.get(
    "WM_GEN3_EMBED_CACHE", "/home/lucas/Desktop/WHITEMAGIC/WMv9/.fastembed_cache"
)


def req(i, route, args):
    return json.dumps({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                       "params": {"name": "wm", "arguments": {"route": route, "args": args}}})


def run(store, journal, extra_env, requests):
    if os.path.exists(journal):
        os.unlink(journal)
    out = subprocess.run(
        [BIN, "serve", "--store", store],
        input="".join(r + "\n" for r in requests), capture_output=True, text=True,
        env=dict(os.environ, WM_GEN3_JOURNAL=journal, **extra_env), timeout=180,
    )
    replies = {}
    for line in out.stdout.splitlines():
        obj = json.loads(line)
        replies[obj["id"]] = json.loads(obj["result"]["content"][0]["text"])
    events = [json.loads(l) for l in open(journal)]
    return replies, events


def main() -> int:
    os.makedirs(BASE, exist_ok=True)

    store = os.path.join(BASE, "store_starve")
    journal = os.path.join(BASE, "starve.jsonl")
    replies, events = run(store, journal, {}, [
        req(2, "sandbox.set_limits", {"max_writes_per_minute": 1}),
        req(3, "memory.batch_create", {"items": [
            {"content": "alpha beta gamma", "galaxy": "codex", "tags": ["a2-s"]},
            {"content": "delta epsilon zeta", "galaxy": "codex", "tags": ["a2-s"]}]}),
        req(4, "memory.episodic_search", {"query": "alpha"}),
        req(5, "memory.episodic_search", {"query": "zulu"}),
    ])
    assert replies[3]["status"] == "error", replies[3]
    assert replies[3]["errors"] == ["write budget exceeded"], replies[3]
    assert replies[4]["status"] == "success" and replies[4]["count"] == 1, replies[4]
    assert replies[5]["status"] == "success" and replies[5]["count"] == 0, replies[5]
    refusals = [e for e in events if e["type"] == "remember.refusal"]
    abst = [e for e in events if e["type"] == "selection.decision" and e.get("abstained")]
    assert len(refusals) == 1 and "write budget exceeded" in refusals[0]["reason"], refusals
    assert len(abst) == 1 and abst[0]["reason"] == "insufficient_evidence", abst
    assert refusals[0]["reason"] != abst[0]["reason"]
    assert abst[0]["projection_ran"] is False and abst[0]["projection_error"] is False, abst[0]

    if not os.path.isdir(CACHE):
        print("A2-STARVE DEMO PASS (route-on skipped: no model cache)")
        return 0

    store2 = os.path.join(BASE, "store_route")
    journal2 = os.path.join(BASE, "route.jsonl")
    replies2, events2 = run(store2, journal2,
                            {"WM_GEN3_PROJECTION": "1", "WM_GEN3_EMBED_CACHE": CACHE}, [
        req(2, "memory.batch_create", {"items": [
            {"content": "alpha beta gamma", "galaxy": "codex", "tags": ["a2-r"]}]}),
        req(3, "memory.episodic_search", {"query": "alpha"}),
    ])
    assert replies2[3]["status"] == "success" and replies2[3]["count"] == 1, replies2[3]
    decision = [e for e in events2 if e["type"] == "selection.decision"][-1]
    assert decision["projection_ran"] is True and decision["projection_error"] is False, decision

    print("A2-STARVE+ROUTE DEMO PASS")
    print("budget refusal :", json.dumps({"status": replies[3]["status"], "errors": replies[3]["errors"]}))
    print("reads open     :", json.dumps({"alpha": replies[4]["count"], "zulu": replies[5]["count"]}))
    print("tokens distinct:", json.dumps({"refusal": refusals[0]["reason"], "abstention": abst[0]["reason"]}))
    print("route (on)     :", json.dumps({k: decision[k] for k in ("projection_ran", "projection_error", "semantic_candidates")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
