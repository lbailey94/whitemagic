#!/usr/bin/env python3
"""Aggregate System 0.5 decision outcomes into an action report.

Joins <store>/receipts/outcomes.jsonl with the subject receipts
(shortlist-*.json / decision-*.json) and reports:
  - outcome totals and verification health
  - success rate per top-1 route (and per task class)
  - correction pairs (top-1 -> corrected route)
  - margin calibration (success rate by margin bucket, for gate tuning)
  - catalog-edit suggestions for routes that keep getting corrected

Usage:
  python3 s05_outcomes.py [--store PATH] [--json] [--out FILE] [--min-corrections N]
"""
import argparse
import glob
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone


def load_outcomes(journal):
    """Latest outcome per subject receipt (by recorded_at_ms).

    Parses the journal as a stream of concatenated JSON values so that both
    compact JSONL lines and any legacy pretty-printed records are recovered.
    """
    latest = {}
    malformed = 0
    text = open(journal).read()
    decoder = json.JSONDecoder()
    index = 0
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            break
        try:
            record, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            malformed += 1
            newline = text.find("\n", index)
            if newline == -1:
                break
            index = newline + 1
            continue
        index = end
        if not isinstance(record, dict):
            malformed += 1
            continue
        subject = record.get("subject_receipt")
        if not subject:
            malformed += 1
            continue
        previous = latest.get(subject)
        if previous is None or record.get("recorded_at_ms", 0) >= previous.get(
            "recorded_at_ms", 0
        ):
            latest[subject] = record
    return latest, malformed


def find_subject(store, uuid):
    hits = sorted(glob.glob(os.path.join(store, "receipts", f"*-{uuid}.json")))
    return hits[0] if hits else None


def load_subject(path):
    if not path:
        return {}
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def margin_bucket(margin):
    if margin is None:
        return "unknown"
    if margin < 0.02:
        return "<0.02"
    if margin < 0.05:
        return "0.02-0.05"
    if margin < 0.10:
        return "0.05-0.10"
    return ">=0.10"


def build_rows(store):
    journal = os.path.join(store, "receipts", "outcomes.jsonl")
    if not os.path.exists(journal):
        return None, 0, 0
    latest, malformed = load_outcomes(journal)
    rows = []
    missing_subject = 0
    for subject, record in latest.items():
        path = find_subject(store, subject)
        if path is None:
            missing_subject += 1
        receipt = load_subject(path)
        rows.append(
            {
                "subject": subject,
                "outcome": record.get("outcome", "unknown"),
                "corrected_route": record.get("corrected_route"),
                "subject_verified": bool(record.get("subject_verified")),
                "top1": receipt.get("top1") or receipt.get("chosen_route"),
                "task_class": receipt.get("task_class"),
                "gate": receipt.get("gate") or ("deliberation" if (receipt.get("spec") or "").endswith("#deliberation") else None),
                "margin": receipt.get("margin") if receipt.get("margin") is not None else receipt.get("margin_prior"),
                "model": receipt.get("model_id") or ("qwen2.5-0.5b" if (receipt.get("spec") or "").endswith("#deliberation") else None),
                "spec": receipt.get("spec"),
                "recorded_at_ms": record.get("recorded_at_ms", 0),
            }
        )
    return rows, malformed, missing_subject


def summarize(rows, min_corrections):
    outcomes = Counter(row["outcome"] for row in rows)
    verified = sum(1 for row in rows if row["subject_verified"])
    unverified = len(rows) - verified

    per_route = defaultdict(lambda: Counter())
    for row in rows:
        key = row["top1"] or "(unknown)"
        per_route[key]["n"] += 1
        per_route[key][row["outcome"]] += 1

    corrections = Counter(
        (row["top1"] or "(unknown)", row["corrected_route"])
        for row in rows
        if row["outcome"] == "corrected" and row["corrected_route"]
    )

    margin_stats = defaultdict(lambda: Counter())
    gate_stats = defaultdict(lambda: Counter())
    for row in rows:
        margin_stats[margin_bucket(row["margin"])]["n"] += 1
        margin_stats[margin_bucket(row["margin"])][row["outcome"]] += 1
        gate_stats[row["gate"] or "(unknown)"]["n"] += 1
        gate_stats[row["gate"] or "(unknown)"][row["outcome"]] += 1

    suggestions = []
    stolen_by = Counter(target for _, target in corrections)
    for (top1, target), count in corrections.most_common():
        if count >= min_corrections:
            suggestions.append(
                f"{top1}: corrected to '{target}' {count}x — add distinguishing "
                f"utterances to {top1}, or route the ambiguous cases to {target}"
            )
    for target, count in stolen_by.most_common(3):
        if count >= min_corrections and not any(target in s for s in suggestions):
            suggestions.append(
                f"'{target}' attracts {count} corrections — verify its catalog "
                f"utterances are not over-broad"
            )

    def rates(counter):
        total = counter.get("n", 0)
        success = counter.get("success", 0)
        return {
            "n": total,
            "success": success,
            "corrected": counter.get("corrected", 0),
            "failure": counter.get("failure", 0),
            "unknown": counter.get("unknown", 0),
            "success_rate": (success / total) if total else None,
        }

    return {
        "receipts_with_outcomes": len(rows),
        "outcomes": dict(outcomes),
        "subject_verified": verified,
        "subject_unverified": unverified,
        "per_route": {route: rates(counter) for route, counter in sorted(per_route.items())},
        "corrections": [
            {"top1": top1, "corrected_route": target, "count": count}
            for (top1, target), count in corrections.most_common()
        ],
        "margin_buckets": {
            bucket: rates(counter) for bucket, counter in sorted(margin_stats.items())
        },
        "gate": {gate: rates(counter) for gate, counter in sorted(gate_stats.items())},
        "suggestions": suggestions,
    }


def print_report(report, malformed, missing_subject):
    print("=" * 62)
    print("      WhiteMagic System 0.5 — Outcome Report")
    print("=" * 62)
    print(f"receipts with outcomes: {report['receipts_with_outcomes']} "
          f"(verified {report['subject_verified']}, unverified {report['subject_unverified']})")
    print(f"outcomes: {report['outcomes']}")
    if malformed or missing_subject:
        print(f"malformed lines: {malformed} | missing subject receipts: {missing_subject}")

    print("\nper top-1 route:")
    for route, stats in report["per_route"].items():
        rate = f"{stats['success_rate']:.2f}" if stats["success_rate"] is not None else "-"
        print(f"  {route:34s} n={stats['n']:3d} success={stats['success']:3d} "
              f"corrected={stats['corrected']:3d} failure={stats['failure']:3d} rate={rate}")

    print("\ncorrections (top-1 -> corrected):")
    if not report["corrections"]:
        print("  none")
    for entry in report["corrections"]:
        print(f"  {entry['top1']:30s} -> {entry['corrected_route']:30s} {entry['count']}x")

    print("\nmargin calibration:")
    for bucket, stats in report["margin_buckets"].items():
        rate = f"{stats['success_rate']:.2f}" if stats["success_rate"] is not None else "-"
        print(f"  margin {bucket:12s} n={stats['n']:3d} success_rate={rate}")

    print("\ngate:")
    for gate, stats in report["gate"].items():
        rate = f"{stats['success_rate']:.2f}" if stats["success_rate"] is not None else "-"
        print(f"  {gate:12s} n={stats['n']:3d} success_rate={rate}")

    print("\nsuggestions:")
    if not report["suggestions"]:
        print("  none yet (need >= min-corrections per pair)")
    for suggestion in report["suggestions"]:
        print(f"  - {suggestion}")
    print("=" * 62)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--store",
        default=os.path.expanduser("~/.local/share/whitemagic/gen3"),
        help="Gen3 store directory",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    parser.add_argument("--out", help="Write the JSON report to this path")
    parser.add_argument("--min-corrections", type=int, default=2)
    args = parser.parse_args()

    rows, malformed, missing_subject = build_rows(args.store)
    if rows is None:
        print(f"no outcomes journal at {os.path.join(args.store, 'receipts', 'outcomes.jsonl')}")
        return 1

    report = summarize(rows, args.min_corrections)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "store": args.store,
        **report,
    }
    if args.out:
        with open(args.out, "w") as handle:
            json.dump(payload, handle, indent=2)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print_report(report, malformed, missing_subject)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
