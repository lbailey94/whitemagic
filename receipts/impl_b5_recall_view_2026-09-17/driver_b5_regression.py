#!/usr/bin/env python3
"""B5 recall-view acceptance — fresh 0-diff regression (registration §3.1).

Stage B of the B1 recipe only (stage A, reference-vs-recorded on the raw corpus, is B1's chain:
the pre-change reference here already carries the A1 exact-hash gate, so raw corpora would
legitimately refuse `duplicate_exact` inputs and the raw comparison is not the right test).

Compared: candidate (implementation-freeze build) vs reference (source-frozen rebuild of the
pre-change tip `9b1a61c`) on the GATE-NEUTRALIZED corpus (deduped by the A1 gate identity,
scripted + hash-recorded; `transform_id gate-neutralize.v1.2026-09-17`), both configs C00 (all
off) and C01 (defaults), with NO scope argument anywhere: ordered (id, rank) list, score bits,
candidate_count, recall@1/5, mrr, first_match_rank -> per-query 0 diffs, scores <= 1 f32 ULP.
Candidate journals must show no ingest refusals, no violations, written == items.

Usage: python3 driver_b5_regression.py <candidate-bin> <reference-bin> <bundle-dir>
"""
import hashlib
import json
import os
import struct
import subprocess
import sys

CAND, REF, BASE = sys.argv[1], sys.argv[2], sys.argv[3]
ROOT = "/home/lucas/Desktop/WMgen3"
CORPUS = os.path.join(ROOT, "experiments/semantic_projection/holdout")
HARNESS = "/home/lucas/Desktop/WHITEMAGIC/WMv9/scripts/memorastrict_bench.py"
OUT = os.path.join(BASE, "regression")
DEDUP = os.path.join(OUT, "corpus_dedup")
SEEDS = ["6", "7", "8", "9", "10"]
CATS = ["T8", "T1", "T6", "T2"]
CONFIGS = {"C00": {"WM_GEN3_SWEEP": "0"}, "C01": {}}


def verify_manifest():
    man = json.load(open(os.path.join(CORPUS, "MANIFEST.json")))
    for name, want in man["files"].items():
        got = hashlib.sha256(open(os.path.join(CORPUS, name), "rb").read()).hexdigest()
        assert got == want, (name, got, want)
    return len(man["files"])


def dedupe_corpus():
    os.makedirs(DEDUP, exist_ok=True)
    hashes = {}
    for seed in SEEDS:
        name = f"bench_seed{seed}.json"
        data = json.load(open(os.path.join(CORPUS, name)))
        for q in data:
            ids = q.get("haystack_session_ids") or []
            sessions = q.get("haystack_sessions") or []
            seen, kept_sessions = set(), []
            for sid, session in zip(ids, sessions):
                kept = []
                for turn in session:
                    key = (sid, turn.get("role", "user"), bool(turn.get("has_answer")),
                           turn.get("content", ""))
                    if key in seen:
                        continue
                    seen.add(key)
                    kept.append(turn)
                kept_sessions.append(kept)
            q["haystack_sessions"] = kept_sessions
        out = os.path.join(DEDUP, name)
        with open(out, "w") as fh:
            json.dump(data, fh)
        hashes[name] = hashlib.sha256(open(out, "rb").read()).hexdigest()
    with open(os.path.join(OUT, "corpus_dedup.sha256"), "w") as fh:
        for name in sorted(hashes):
            fh.write(f"{hashes[name]}  {name}\n")
    return hashes


def run(binary, seed, tag, data_dir, journal, env_extra):
    out_path = os.path.join(OUT, f"{tag}_s{seed}.json")
    cmd = ["python3", HARNESS, "--binary", binary, "--data", data_dir, "--seeds", seed,
           "--categories", *CATS, "--limit", "10", "--candidate-limit", "100",
           "--min-score", "0", "--min-coverage", "0", "--per-case", "--output", out_path]
    env = dict(os.environ, WM_GEN3_JOURNAL=journal,
               WM_GEN3_JOURNAL_HASH_OUT=journal + ".sha256", **env_extra)
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
    actual = out_path.replace(".json", f"_seed{seed}.json")
    assert proc.returncode == 0, (proc.returncode, proc.stderr[-400:], actual)
    return json.load(open(actual))


def ulp_diff(x, y):
    """ULP distance at f32 (the core's scoring precision); None on sign mismatch."""
    a = struct.unpack(">I", struct.pack(">f", x))[0]
    b = struct.unpack(">I", struct.pack(">f", y))[0]
    if (a >> 31) != (b >> 31):
        return None
    return abs(a - b)


def fields(q):
    return {
        "retrieved": [(r["id"], r["rank"]) for r in q["retrieved_results"]],
        "candidate_count": q["candidate_count"],
        "recall_at_1": q["recall_at_1"],
        "recall_at_5": q["recall_at_5"],
        "mrr": q["mrr"],
        "first_match_rank": q["first_match_rank"],
    }


def diff(a, b, label, stats):
    diffs = []
    assert len(a["per_query"]) == len(b["per_query"]), (label, len(a["per_query"]), len(b["per_query"]))
    for qa, qb in zip(a["per_query"], b["per_query"]):
        assert qa["question_id"] == qb["question_id"], (label, qa["question_id"], qb["question_id"])
        fa, fb = fields(qa), fields(qb)
        for k in fa:
            if fa[k] != fb[k]:
                diffs.append({"qid": qa["question_id"], "field": k, "a": fa[k], "b": fb[k]})
        sa = [r["score"] for r in qa["retrieved_results"]]
        sb = [r["score"] for r in qb["retrieved_results"]]
        assert len(sa) == len(sb), (label, qa["question_id"])
        for x, y in zip(sa, sb):
            u = ulp_diff(x, y)
            assert u is not None, (label, qa["question_id"], x, y)
            stats["ulp_max"] = max(stats["ulp_max"], u)
            stats["scores"] += 1
            if u == 0:
                stats["exact"] += 1
            else:
                stats["nonzero"] += 1
    return diffs


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    files_verified = verify_manifest()
    dedup_hashes = dedupe_corpus()
    report = {}

    for cfg, env_extra in CONFIGS.items():
        # --- stage B: candidate vs reference (gate-neutralized corpus) ---
        b_diffs, b_queries = [], 0
        b_stats = {"ulp_max": 0, "scores": 0, "exact": 0, "nonzero": 0}
        for seed in SEEDS:
            ref_json = run(REF, seed, f"ref_dedup_{cfg}", DEDUP,
                           os.path.join(OUT, f"ref_dedup_{cfg}_s{seed}.journal.jsonl"), env_extra)
            cand_journal = os.path.join(OUT, f"cand_dedup_{cfg}_s{seed}.journal.jsonl")
            cand_json = run(CAND, seed, f"cand_dedup_{cfg}", DEDUP, cand_journal, env_extra)
            b_diffs += [dict(d, seed=seed) for d in diff(ref_json, cand_json, f"cand/ref/{cfg}/seed{seed}", b_stats)]
            b_queries += len(cand_json["per_query"])
            events = [json.loads(l) for l in open(cand_journal) if l.strip()]
            assert not any(e["type"] == "remember.refusal" for e in events), (cfg, seed, "refusals")
            assert not any(e["type"] == "closure.violation" for e in events), (cfg, seed, "violations")
            assert not any(e["type"] == "ingest.batch" and e.get("written") != e.get("items")
                           for e in events), (cfg, seed, "partial ingest")
            assert not any("scope" in json.dumps(e) for e in events if e["type"] == "selection.decision"), \
                (cfg, seed, "scope field on the default path")
        assert b_diffs == [], json.dumps(b_diffs[:5], indent=1)
        assert b_stats["ulp_max"] <= 1, b_stats
        report[cfg] = {"b_queries": b_queries, "b": b_stats}

    print("B5 REGRESSION FIXTURE PASS (fresh 0-diff, stage B: candidate vs pre-change reference)")
    print(f"raw corpus     : {files_verified} files MANIFEST-verified (holdout seeds {','.join(SEEDS)})")
    print(f"gate-neutral   : deduped corpus sha256 recorded (corpus_dedup.sha256, {len(dedup_hashes)} files)")
    for cfg, r in report.items():
        label = "all switches off" if cfg == "C00" else "defaults (sweep on)"
        print(f"stage B {cfg}    : candidate vs reference (deduped, no scope) ({label}) -> "
              f"{r['b_queries']} queries, ordering/metrics 0 diffs; scores exact "
              f"{r['b']['exact']}/{r['b']['scores']}, max f32 ULP {r['b']['ulp_max']}")
    print("candidate int. : no ingest refusals, no violations, written == items; no scope field on the default path")
    return 0


if __name__ == "__main__":
    sys.exit(main())
