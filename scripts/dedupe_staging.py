#!/usr/bin/env python3
"""Cross-source staging dedup for the App Retirement harvest (Phase 3).

Groups staged transcripts into clusters of identical/near-identical
conversations and keeps ONE canonical copy per cluster:

- Normalization: ordered (role, kind, stripped-collapsed text) turn
  sequence; header/provenance lines excluded from signatures.
- Exact twins: SHA-256 of the normalized sequence.
- Near-dups: MinHash over k=4 word shingles, estimated Jaccard >= 0.95,
  union-find clustering. Conservative by design: only merges sessions
  that are (near-)verbatim copies, never paraphrases.
- Canonical selection: JSONL with roles preferred, then larger content;
  twins are MOVED to <out>/duplicates/ and recorded with full provenance
  in dedup_report.json.

Usage:
  python3 scripts/dedupe_staging.py --staging <dir-with-*.jsonl> [--apply]

Without --apply it only writes the report (review gate).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from collections import defaultdict

WS = re.compile(r"\s+")
SHINGLE_K = 4
PERMS = 64
JACCARD_THRESHOLD = 0.95


def load_transcript(path):
    turns = []
    header = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") == "header":
                header = obj
                continue
            text = WS.sub(" ", (obj.get("content") or obj.get("text") or "").strip())
            if not text:
                continue
            role = obj.get("role") or obj.get("type") or "unknown"
            kind = obj.get("kind", "text")
            turns.append((role, kind, text))
    return header, turns


def exact_signature(turns):
    joined = "\n".join(f"{r}|{k}|{t}" for r, k, t in turns)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def shingles(turns):
    words = " ".join(t for _, _, t in turns).split()
    if len(words) < SHINGLE_K:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + SHINGLE_K]) for i in range(len(words) - SHINGLE_K + 1)}


def minhash(sig_set):
    if not sig_set:
        return []
    sketch = []
    for p in range(PERMS):
        m = min(hashlib.sha1(f"{p}:{s}".encode()).digest()[:8] for s in sig_set)
        sketch.append(m)
    return sketch


def jaccard_est(mh_a, mh_b):
    if not mh_a or not mh_b:
        return 0.0
    same = sum(1 for a, b in zip(mh_a, mh_b) if a == b)
    return same / PERMS


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--staging", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    paths = sorted(
        os.path.join(a.staging, f) for f in os.listdir(a.staging) if f.endswith(".jsonl")
    )
    docs = {}
    for p in paths:
        header, turns = load_transcript(p)
        docs[p] = {
            "header": header,
            "turns": turns,
            "sig": exact_signature(turns),
            "mh": minhash(shingles(turns)),
            "size": sum(len(t) for _, _, t in turns),
        }

    parent = {p: p for p in paths}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    by_sig = defaultdict(list)
    for p, d in docs.items():
        by_sig[d["sig"]].append(p)

    exact_pairs, near_pairs = 0, 0
    sig_groups = list(by_sig.values())
    for group in sig_groups:
        for other in group[1:]:
            union(group[0], other)
            exact_pairs += 1
    # near-dup pass across distinct exact-groups only
    reps = [g[0] for g in sig_groups]
    for i in range(len(reps)):
        for j in range(i + 1, len(reps)):
            pa, pb = reps[i], reps[j]
            est = jaccard_est(docs[pa]["mh"], docs[pb]["mh"])
            if est >= JACCARD_THRESHOLD:
                union(pa, pb)
                near_pairs += 1

    clusters = defaultdict(list)
    for p in paths:
        clusters[find(p)].append(p)

    report = {"clusters": [], "totals": {"files": len(paths), "clusters": 0,
                                         "exact_twin_pairs": exact_pairs,
                                         "near_twin_pairs": near_pairs,
                                         "twins_moved": 0}}
    moved = 0
    dup_dir = os.path.join(a.staging, "duplicates")
    for root, members in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        canon = max(members, key=lambda p: docs[p]["size"])
        entry = {
            "canonical": canon,
            "canonical_session_id": docs[canon]["header"].get("session_id"),
            "size_chars": docs[canon]["size"],
            "twins": [],
        }
        for p in sorted(m for m in members if m != canon):
            entry["twins"].append(
                {
                    "path": p,
                    "session_id": docs[p]["header"].get("session_id"),
                    "reason": "exact" if docs[p]["sig"] == docs[canon]["sig"] else "near",
                    "size_chars": docs[p]["size"],
                }
            )
        if entry["twins"]:
            report["clusters"].append(entry)
            report["totals"]["twins_moved"] += len(entry["twins"])
            if a.apply:
                os.makedirs(dup_dir, exist_ok=True)
                for t in entry["twins"]:
                    shutil.move(t["path"], os.path.join(dup_dir, os.path.basename(t["path"])))
                    moved += 1

    report["totals"]["clusters"] = len(clusters)
    out = os.path.join(os.path.dirname(a.staging.rstrip("/")), "dedup_report.json")
    with open(out, "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report["totals"], indent=2))
    print(f"report: {out}{' (twins moved: %d)' % moved if a.apply else ' (DRY — rerun with --apply)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
