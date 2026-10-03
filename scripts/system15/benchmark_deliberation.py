#!/usr/bin/env python3
"""Frontier 1 System 1.5 Local Deliberator Benchmark.

Evaluates the System 0.5 + System 1.5 Deliberator Cascade against the
80-intent benchmark set. Compares standalone System 0.5 static retrieval
against the grammar-constrained local SLM cascade.
"""

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import subprocess
import sys
import time

INTENTS_PATH = "/tmp/opencode/route_eval/route-eval/intents.jsonl"
BASELINE_CATALOG = "/home/lucas/SharedWorkspace/uploads/miranda-macbook/v9_curated_routes.json"
ENRICHED_CATALOG = "/home/lucas/Desktop/WHITEMAGIC/WMv9/catalogs/routes_v9_enriched.json"
WM_BIN_DEBUG = "/home/lucas/Desktop/WHITEMAGIC/WMv9/target/debug/wm"
WM_BIN_RELEASE = "/home/lucas/Desktop/WHITEMAGIC/WMv9/target/release/wm"

GOLD_MAP = {
    "remember": "memory.create",
    "recall": "memory.search",
    "session_checkpoint": "session.checkpoint",
    "session_continuity": "session.continuity",
    "session_record": "session.record",
    "status": "gnosis.status",
    "inspect": "gnosis.explain",
    "ingest": "memory.ingest",
}

def resolve_wm_bin():
    if "WM_BIN" in os.environ:
        return os.environ["WM_BIN"]
    if os.path.exists(WM_BIN_RELEASE):
        check = subprocess.run([WM_BIN_RELEASE, "shortlist", "--help"], capture_output=True)
        if check.returncode == 0:
            return WM_BIN_RELEASE
    return WM_BIN_DEBUG

def load_intents(sample_per_class=None):
    by_class = defaultdict(list)
    with open(INTENTS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            gold_class = item.get("gold")
            gold_mapped = GOLD_MAP.get(gold_class)
            if gold_mapped:
                item["gold_mapped"] = gold_mapped
                item["gold_class"] = gold_class
                by_class[gold_class].append(item)
    
    if sample_per_class is not None and sample_per_class > 0:
        selected = []
        for cls in sorted(by_class.keys()):
            selected.extend(by_class[cls][:sample_per_class])
        return selected
    
    all_intents = []
    for cls in sorted(by_class.keys()):
        all_intents.extend(by_class[cls])
    return all_intents

def run_shortlist_cascade(wm_bin, intent_text, catalog_path, k=5, tau=0.08):
    cmd = [
        wm_bin,
        "shortlist",
        "--routes", catalog_path,
        "--k", str(k),
        "--margin-threshold", str(tau),
        "--cascade",
        "--json"
    ]
    start = time.time()
    res = subprocess.run(
        cmd,
        input=intent_text,
        capture_output=True,
        text=True
    )
    wall_ms = (time.time() - start) * 1000.0
    if res.returncode != 0:
        return {"error": res.stderr}
    try:
        out = json.loads(res.stdout)
        out["wall_ms"] = wall_ms
        return out
    except Exception as e:
        return {"error": f"JSON parse error: {e}, stdout: {res.stdout}"}

def verify_receipt(wm_bin, receipt_path):
    cmd = [wm_bin, "verify-receipt", receipt_path, "--json"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return False
    try:
        data = json.loads(res.stdout)
        return data.get("valid", False)
    except Exception:
        return False

def record_outcome(wm_bin, receipt_path, is_success, corrected_route=None, note=""):
    outcome_str = "success" if is_success else "corrected"
    cmd = [
        wm_bin,
        "outcome",
        receipt_path,
        "--outcome", outcome_str,
        "--json"
    ]
    if not is_success and corrected_route:
        cmd.extend(["--corrected-route", corrected_route])
    if note:
        cmd.extend(["--note", note])
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0

def run_benchmark(catalog_path, catalog_name, intents, tau=0.08, k=5, record_outcomes_flag=False):
    wm_bin = resolve_wm_bin()
    n = len(intents)
    print(f"\n==================================================")
    print(f" Running Benchmark on {catalog_name} ({n} intents)")
    print(f" Binary: {wm_bin} (tau={tau}, k={k})")
    print(f" Record Outcomes: {record_outcomes_flag}")
    print(f"==================================================")

    s05_correct = 0
    cascade_correct = 0
    shortlist_contains_gold = 0
    ambiguous_count = 0
    total_retrieval_ms = 0.0
    total_deliberation_ms = 0.0
    receipts_verified = 0
    receipts_checked = 0
    outcomes_recorded = 0

    per_class_stats = defaultdict(lambda: {"total": 0, "s05_ok": 0, "cascade_ok": 0, "shortlist_ok": 0})

    for i, item in enumerate(intents):
        intent = item.get("intent", item.get("text", ""))
        gold = item["gold_mapped"]
        gold_class = item["gold_class"]
        per_class_stats[gold_class]["total"] += 1

        res = run_shortlist_cascade(wm_bin, intent, catalog_path, k=k, tau=tau)
        if "error" in res:
            print(f"[{i+1}/{n}] ERROR: {res['error']}")
            continue

        ranked = res.get("ranked", [])
        top1_s05 = ranked[0].get("route") if ranked else None
        top_k_routes = [r.get("route") for r in ranked]
        
        in_shortlist = gold in top_k_routes
        if in_shortlist:
            shortlist_contains_gold += 1
            per_class_stats[gold_class]["shortlist_ok"] += 1

        is_s05_correct = (top1_s05 == gold)
        if is_s05_correct:
            s05_correct += 1
            per_class_stats[gold_class]["s05_ok"] += 1

        gate = res.get("gate", "dispatch")
        is_ambiguous = (gate == "ambiguous")
        if is_ambiguous:
            ambiguous_count += 1

        delib = res.get("deliberation")
        dispatched_receipt_path = None
        if delib:
            chosen = delib.get("chosen_route")
            delib_lat = delib.get("latency_ms", 0.0)
            total_deliberation_ms += delib_lat
            receipt_id = delib.get("receipt_id")
            if receipt_id:
                receipt_path = os.path.expanduser(f"~/.local/share/whitemagic/gen3/receipts/deliberation-{receipt_id}.json")
                if os.path.exists(receipt_path):
                    dispatched_receipt_path = receipt_path
                    receipts_checked += 1
                    if verify_receipt(wm_bin, receipt_path):
                        receipts_verified += 1
        else:
            chosen = top1_s05
            shortlist_receipt_path = res.get("receipt_path")
            if shortlist_receipt_path and os.path.exists(shortlist_receipt_path):
                dispatched_receipt_path = shortlist_receipt_path
                receipts_checked += 1
                if verify_receipt(wm_bin, shortlist_receipt_path):
                    receipts_verified += 1

        is_cascade_correct = (chosen == gold)
        if is_cascade_correct:
            cascade_correct += 1
            per_class_stats[gold_class]["cascade_ok"] += 1

        if record_outcomes_flag and dispatched_receipt_path:
            ok = record_outcome(
                wm_bin,
                dispatched_receipt_path,
                is_success=is_cascade_correct,
                corrected_route=gold if not is_cascade_correct else None,
                note=f"intent={intent[:60]}"
            )
            if ok:
                outcomes_recorded += 1

        retrieval_ms = res.get("latency_ms", 0.0)
        total_retrieval_ms += retrieval_ms

        mark_s05 = "✓" if is_s05_correct else "✗"
        mark_casc = "✓" if is_cascade_correct else "✗"
        gate_flag = "[AMB->SLM]" if is_ambiguous else "[DIRECT]  "
        
        print(f"[{i+1:2d}/{n}] {gate_flag} S0.5:{mark_s05} Casc:{mark_casc} | Gold: {gold:20s} S0.5: {str(top1_s05):20s} Final: {str(chosen):20s}")

    s05_acc = s05_correct / n if n > 0 else 0.0
    casc_acc = cascade_correct / n if n > 0 else 0.0
    r_at_k = shortlist_contains_gold / n if n > 0 else 0.0
    cond_acc = cascade_correct / shortlist_contains_gold if shortlist_contains_gold > 0 else 0.0
    avg_retrieval_ms = total_retrieval_ms / n if n > 0 else 0.0
    avg_delib_ms = total_deliberation_ms / ambiguous_count if ambiguous_count > 0 else 0.0

    print("\n---------------- RESULTS SUMMARY ----------------")
    print(f"Catalog:                   {catalog_name}")
    print(f"Total Intents:             {n}")
    print(f"System 0.5 Top-1 Accuracy: {s05_acc:.3f} ({s05_correct}/{n})")
    print(f"Shortlist Recall@{k}:        {r_at_k:.3f} ({shortlist_contains_gold}/{n})")
    print(f"System 1.5 Cascade Top-1:  {casc_acc:.3f} ({cascade_correct}/{n})")
    print(f"Conditioned Accuracy:      {cond_acc:.3f}")
    print(f"Ambiguity Trigger Rate:    {ambiguous_count/n*100:.1f}% ({ambiguous_count}/{n})")
    print(f"Avg Retrieval Latency:     {avg_retrieval_ms:.2f} ms")
    if ambiguous_count > 0:
        print(f"Avg Deliberation Latency:  {avg_delib_ms:.1f} ms")
    print(f"Receipt Attestation Rate:  {receipts_verified}/{receipts_checked} ({100.0 if receipts_checked == receipts_verified else 0.0}%)")
    if record_outcomes_flag:
        print(f"Outcomes Journaled:        {outcomes_recorded}/{n}")
    print("-------------------------------------------------\n")

    return {
        "catalog": catalog_name,
        "n": n,
        "s05_accuracy": s05_acc,
        "recall_at_k": r_at_k,
        "cascade_accuracy": casc_acc,
        "conditioned_accuracy": cond_acc,
        "ambiguity_rate": ambiguous_count / n if n > 0 else 0.0,
        "avg_retrieval_ms": avg_retrieval_ms,
        "avg_deliberation_ms": avg_delib_ms,
        "receipts_verified": receipts_verified,
        "receipts_checked": receipts_checked,
        "outcomes_recorded": outcomes_recorded,
        "per_class": dict(per_class_stats),
    }

def main():
    parser = argparse.ArgumentParser(description="System 1.5 Deliberator Benchmark")
    parser.add_argument("--catalog", choices=["baseline", "enriched", "both"], default="enriched",
                        help="Which catalog to benchmark (default: enriched)")
    parser.add_argument("--sample-per-class", type=int, default=None,
                        help="Sample N intents per class (e.g. 3 for stratified 24 intents, None for all 80)")
    parser.add_argument("--tau", type=float, default=0.08,
                        help="Conformal margin threshold tau (default 0.08)")
    parser.add_argument("--k", type=int, default=5,
                        help="Shortlist size k (default 5)")
    parser.add_argument("--record-outcomes", action="store_true",
                        help="Automatically journal outcomes to outcomes.jsonl")
    parser.add_argument("--out", type=str, default="receipts/system15_deliberation_benchmark_2026-10-03.json",
                        help="Path to save benchmark JSON report")
    args = parser.parse_args()

    intents = load_intents(sample_per_class=args.sample_per_class)
    print(f"Loaded {len(intents)} intents across 8 classes.")

    results = {}
    if args.catalog in ("baseline", "both"):
        results["baseline"] = run_benchmark(
            BASELINE_CATALOG,
            "Baseline Catalog (68 routes)",
            intents,
            tau=args.tau,
            k=args.k,
            record_outcomes_flag=args.record_outcomes
        )
    if args.catalog in ("enriched", "both"):
        results["enriched"] = run_benchmark(
            ENRICHED_CATALOG,
            "Enriched Catalog (68 routes)",
            intents,
            tau=args.tau,
            k=args.k,
            record_outcomes_flag=args.record_outcomes
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Full benchmark report written to {out_path.resolve()}")

if __name__ == "__main__":
    main()
