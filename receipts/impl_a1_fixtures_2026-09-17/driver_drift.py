#!/usr/bin/env python3
"""A1 fixtures — crash-drift (§5.4).

Kill -9 a writer mid-batch, then:
  probe  : the killed store reopens (LMDB recovery); recall over samples is coherent
           (0/1 hits, exact content, never >1); if the store is non-empty the first item is
           recallable (no silent zero); record count == the replay's duplicate-refusal count.
  replay : re-sending the batch converges to exactly N records; refusals are `duplicate_exact`
           (store-hydrated identity), admissions are recallable.
  third  : a third full re-send refuses all N -> exactly N identity keys, no doubles, no losses.

Usage: python3 driver_drift.py <harness-binary> <bundle-dir>
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

BIN, BASE = sys.argv[1], sys.argv[2]
N = 3000
SAMPLES = [0, 500, 1500, 2500, N - 1]
SLEEPS = [0.5, 0.2, 0.1]


def content(i):
    return f"drift item {i:05d} uniquetoken{i:05d} payload padding text"


ITEMS = [{"content": content(i), "galaxy": "codex", "tags": ["drift-demo"]} for i in range(N)]


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def recall(id_, query):
    return call(id_, "memory.episodic_search", {
        "query": query, "limit": 10, "candidate_limit": 100,
        "include_historical": False, "min_score": 0.0, "min_coverage": 0.0})


def payload(reqs):
    return "".join(json.dumps(r) + "\n" for r in reqs)


def env_of(journal, extra=None):
    return dict(os.environ, WM_GEN3_JOURNAL=journal, WM_GEN3_SWEEP="0", **(extra or {}))


def run(store, reqs, journal, extra=None, timeout=600):
    payload_s = payload(reqs)
    proc = subprocess.run([BIN, "serve", "--store", store], input=payload_s,
                          capture_output=True, text=True, env=env_of(journal, extra), timeout=timeout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"harness exit {proc.returncode}")
    return proc


def replies_of(proc):
    return {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}


def payload_of(reply):
    return json.loads(reply["result"]["content"][0]["text"])


def events(path):
    if not os.path.exists(path):
        return None
    return [json.loads(l) for l in open(path) if l.strip()]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def killed_run(store, journal, sleep):
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "sandbox.set_limits", {"max_writes_per_minute": 1000000}),
        call(3, "memory.batch_create", {"items": ITEMS}),
    ]
    payload_s = payload(reqs)
    proc = subprocess.Popen([BIN, "serve", "--store", store], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            env=env_of(journal))
    try:
        proc.stdin.write(payload_s)
        proc.stdin.flush()
    except BrokenPipeError:
        proc.wait()
        return proc.returncode, "", ""
    time.sleep(sleep)
    proc.kill()
    out, err = proc.communicate()
    return proc.returncode, out, err


def probe_reqs():
    reqs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            call(2, "inspect", {"scope": "all"})]
    for k, i in enumerate(SAMPLES):
        reqs.append(recall(10 + k, f"uniquetoken{i:05d}"))
    return reqs


def replay_reqs():
    reqs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            call(2, "sandbox.set_limits", {"max_writes_per_minute": 1000000}),
            call(3, "memory.batch_create", {"items": ITEMS}),
            call(4, "inspect", {"scope": "all"})]
    for k, i in enumerate(SAMPLES):
        reqs.append(recall(10 + k, f"uniquetoken{i:05d}"))
    return reqs


def third_reqs():
    return [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        call(2, "sandbox.set_limits", {"max_writes_per_minute": 1000000}),
        call(3, "memory.batch_create", {"items": ITEMS}),
    ]


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    accepted = None
    attempt_log = []
    for k, sleep in enumerate(SLEEPS):
        store = os.path.join(BASE, f"drift_store_{k}")
        j_killed = os.path.join(BASE, f"drift_killed_{k}.journal.jsonl")
        j_probe = os.path.join(BASE, f"drift_probe_{k}.journal.jsonl")
        j_replay = os.path.join(BASE, f"drift_replay_{k}.journal.jsonl")
        j_third = os.path.join(BASE, f"drift_third_{k}.journal.jsonl")
        for p in (j_killed, j_probe, j_replay, j_third):
            if os.path.exists(p):
                os.unlink(p)

        rc, _, err = killed_run(store, j_killed, sleep)
        if rc != -9:
            attempt_log.append({"attempt": k, "sleep": sleep, "killed": False,
                                "exit": rc, "stderr_tail": err[-300:]})
            continue

        # probe: coherence of the killed store (no writes)
        proc = run(store, probe_reqs(), j_probe)
        open(os.path.join(BASE, f"drift_probe_{k}.responses.jsonl"), "w").write(proc.stdout)
        r = replies_of(proc)
        insp = payload_of(r[2])
        r_killed = insp["inspect"]["tiers"]["tier3_adaptive"]["records"]
        sample_hits = {}
        for kk, i in enumerate(SAMPLES):
            p = payload_of(r[10 + kk])
            assert p["count"] <= 1, (i, p)
            if p["count"] == 1:
                assert p["results"][0]["content"] == content(i), (i, p["results"][0])
            sample_hits[i] = p["count"]
        if r_killed > 0:
            assert sample_hits[0] == 1, ("non-empty store but first item not recallable", r_killed)

        # replay: convergence
        proc = run(store, replay_reqs(), j_replay,
                   extra={"WM_GEN3_JOURNAL_HASH_OUT": os.path.join(BASE, f"drift_replay_{k}.journal.sha256")})
        open(os.path.join(BASE, f"drift_replay_{k}.responses.jsonl"), "w").write(proc.stdout)
        r = replies_of(proc)
        replay = payload_of(r[3])
        insp = payload_of(r[4])
        refused = replay.get("failed", 0) or 0
        admitted = len(replay["ids"])
        assert replay["status"] == "error" or refused == 0, replay
        assert refused + admitted == N, (refused, admitted)
        assert set(replay.get("errors", [])) <= {"duplicate_exact"}, replay
        assert refused == r_killed, ("killed record count != replay duplicate refusals", refused, r_killed)
        assert insp["inspect"]["tiers"]["tier3_adaptive"]["records"] == N, insp
        for kk, i in enumerate(SAMPLES):
            p = payload_of(r[10 + kk])
            assert p["count"] == 1 and p["results"][0]["content"] == content(i), (i, p)

        # third: exactly N identities
        proc = run(store, third_reqs(), j_third,
                   extra={"WM_GEN3_JOURNAL_HASH_OUT": os.path.join(BASE, f"drift_third_{k}.journal.sha256")})
        open(os.path.join(BASE, f"drift_third_{k}.responses.jsonl"), "w").write(proc.stdout)
        r = replies_of(proc)
        third = payload_of(r[3])
        assert third["failed"] == N and third["ids"] == [], third
        assert set(third["errors"]) == {"duplicate_exact"}, third

        # journals + hash-outs
        ev_replay = events(j_replay)
        assert [b["written"] for b in ev_replay if b["type"] == "ingest.batch"] == [admitted], ev_replay
        refusals = [e for e in ev_replay if e["type"] == "remember.refusal"]
        assert len(refusals) == refused and all(e["reason"] == "duplicate_exact" and e.get("existing_id") is not None
                                                for e in refusals), refusals
        ev_third = events(j_third)
        assert [b["written"] for b in ev_third if b["type"] == "ingest.batch"] == [0], ev_third
        assert len([e for e in ev_third if e["type"] == "remember.refusal"]) == N, ev_third
        for tag, jpath in (("replay", j_replay), ("third", j_third)):
            hout = os.path.join(BASE, f"drift_{tag}_{k}.journal.sha256")
            assert open(hout).read().strip() == sha256(jpath), (tag, hout)
        ev_killed = events(j_killed)
        attempt_log.append({
            "attempt": k, "sleep": sleep, "killed": True, "killed_records": r_killed,
            "killed_journal_events": None if ev_killed is None else len(ev_killed),
            "refused": refused, "admitted": admitted,
        })
        if 0 < refused < N:
            accepted = k
            break

    if accepted is None:
        print("A1 DRIFT FIXTURE FAIL: no attempt landed mid-batch")
        print(json.dumps(attempt_log, indent=1))
        return 1

    print("A1 DRIFT FIXTURE PASS")
    for row in attempt_log:
        print("attempt        :", json.dumps(row))
    print(f"kill window    : {SLEEPS[accepted]}s -> {attempt_log[-1]['killed_records']} committed / {N}")
    print("coherence      : killed record count == replay duplicate refusals; samples 0/1 exact; first item present")
    print("convergence    : replay admitted", attempt_log[-1]["admitted"], "+ refused", attempt_log[-1]["refused"],
          "=", N, "; third pass refused all", N, "(exactly N identities)")
    print("hash-outs      : replay + third journal sha256 verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
