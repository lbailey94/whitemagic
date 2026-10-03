#!/usr/bin/env python3
"""Ops fold-in — read-path discipline audit (fold-in #2; 9.1.8 snapshot-read class).

Source level: `recall`/`inspect` bodies contain no durable store mutation; `inspect` is `&self`
(immutable — it cannot journal or mutate by construction).
Runtime: ingest -> hash; recall-only process -> store bytes unchanged, journal carries only
disclosure events; inspect-only process -> store bytes unchanged, journal carries no events
(run.end only). Recall's journal appends are declared disclosure (A2), not store mutation.

Usage: python3 driver_readpath_audit.py <harness-binary> <bundle-dir>
"""
import hashlib
import json
import os
import re
import subprocess
import sys

BIN, BASE = sys.argv[1], sys.argv[2]
ROOT = "/home/lucas/Desktop/WMgen3"
STORE = os.path.join(BASE, "readpath_store")
J_INGEST = os.path.join(BASE, "readpath_ingest.journal.jsonl")
J_RECALL = os.path.join(BASE, "readpath_recall.journal.jsonl")
J_INSPECT = os.path.join(BASE, "readpath_inspect.journal.jsonl")
MUTATION_TOKENS = ["put_record_and_postings", "put_vector", "put_relation", "put_embedding",
                   "delete", "bump_counter", "alloc_relation_id", "create_db", "begin_rw_txn",
                   "commit(", ".put_"]
DISCLOSURE_EVENTS = {"selection.decision", "provenance.chain", "run.end"}


def call(id_, route, args):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call",
            "params": {"name": "wm", "arguments": {"route": route, "args": args}}}


def run(reqs, journal):
    payload = "".join(json.dumps(r) + "\n" for r in reqs)
    env = dict(os.environ, WM_GEN3_JOURNAL=journal)
    proc = subprocess.run([BIN, "serve", "--store", STORE], input=payload,
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-400:]
    return {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}


def body_of(source, start_marker):
    rest = source[source.index(start_marker):]
    end_impl = rest.find("\n}")
    nxt = re.search(r"\n    pub fn ", rest)
    cut = min(x for x in (end_impl if end_impl != -1 else len(rest),
                          nxt.start() if nxt else len(rest)))
    body = rest[:cut]
    return "\n".join(line.split("//")[0] for line in body.splitlines())


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    for p in (J_INGEST, J_RECALL, J_INSPECT):
        if os.path.exists(p):
            os.unlink(p)

    # --- source level -------------------------------------------------------
    source = open(os.path.join(ROOT, "crates/wm-gen3-core/src/ops.rs")).read()
    recall_body = body_of(source, "pub fn recall(&mut self")
    inspect_body = body_of(source, "pub fn inspect(&self")
    for name, body in (("recall", recall_body), ("inspect", inspect_body)):
        hits = [t for t in MUTATION_TOKENS if t in body]
        assert hits == [], (name, hits)
    assert "pub fn inspect(&self" in source, "inspect must be immutable (&self)"
    usage_only = re.findall(r"self\.usage\.(?:insert|entry)", recall_body)
    assert usage_only, "recall's in-process usage counter expected (declared)"

    # --- runtime ------------------------------------------------------------
    run([{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
         call(2, "memory.batch_create", {"items": [
             {"content": "the north bay is the current loading area", "galaxy": "codex", "tags": ["audit"]},
             {"content": "the west gate is locked at night", "galaxy": "codex", "tags": ["audit"]},
         ]})], J_INGEST)
    h0 = sha256(os.path.join(STORE, "data.mdb"))

    run([{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
         call(2, "memory.episodic_search", {
             "query": "north bay loading", "limit": 10, "candidate_limit": 100,
             "include_historical": False, "min_score": 0.0, "min_coverage": 0.0})], J_RECALL)
    h1 = sha256(os.path.join(STORE, "data.mdb"))
    assert h0 == h1, ("recall mutated the store", h0, h1)
    recall_events = {json.loads(l)["type"] for l in open(J_RECALL) if l.strip()}
    assert recall_events <= DISCLOSURE_EVENTS, recall_events

    run([{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
         call(2, "inspect", {"scope": "all"})], J_INSPECT)
    h2 = sha256(os.path.join(STORE, "data.mdb"))
    assert h0 == h2, ("inspect mutated the store", h0, h2)
    inspect_events = {json.loads(l)["type"] for l in open(J_INSPECT) if l.strip()}
    assert inspect_events <= {"run.end"}, inspect_events

    print("OPS READ-PATH AUDIT PASS")
    print("source         : recall/inspect bodies contain no durable mutation; inspect is &self "
          "(cannot mutate/journal); recall's only mutable touches are declared (journal disclosure + "
          "in-process usage counter)")
    print("runtime        : data.mdb sha256 unchanged after recall-only and inspect-only processes "
          "(%s)" % h0[:16])
    print("journals       : recall-only ->", sorted(recall_events),
          "| inspect-only ->", sorted(inspect_events) or ["(none)"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
