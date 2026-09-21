#!/usr/bin/env python3
"""Local token/savings ledger report — backfill + current state.

Reads, read-only and entirely locally:

  - each project store's ``mutable_tool_stats.json`` (local WM ops by family)
  - each project store's ``savings_ledger.jsonl`` (state-over-transcript rows,
    token-ledger v0; absent on stores that predate it)
  - optionally the opencode session DB (token / cache / cost aggregates)

Nothing is transmitted. Byte/token figures only; dollar figures stay out of
public copy (see docs/TOKEN_LEDGER.md for the binding attribution rules:
provider/harness prompt caching is *context*, not a WhiteMagic saving).

Usage:
    python3 scripts/token_ledger_report.py
    python3 scripts/token_ledger_report.py --json
    python3 scripts/token_ledger_report.py --stores '~/Desktop/WHITEMAGIC/data/WMdata/projects/*/lmdb'
    python3 scripts/token_ledger_report.py --no-opencode
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
from collections import defaultdict

DEFAULT_STORES_GLOB = os.path.expanduser(
    "~/Desktop/WHITEMAGIC/data/WMdata/projects/*/lmdb"
)
DEFAULT_OPENCODE_DB = os.path.expanduser("~/.local/share/opencode/opencode.db")
# Disclosed estimate divisor; recalibrate against a real tokenizer before any
# external publication (docs/TOKEN_LEDGER.md).
BYTES_PER_TOKEN = 4


def family_of(tool: str) -> str:
    if tool.startswith("memory."):
        return "memory"
    if tool.startswith("session."):
        return "session"
    if tool == "gnosis":
        return "gnosis"
    return "other"


def read_store(lmdb_dir: str) -> dict:
    """Aggregate one store: dispatch counters + savings-ledger rows."""
    out = {
        "path": lmdb_dir,
        "ops_total": 0,
        "ops_by_family": defaultdict(int),
        "top_tools": [],
        "ledger_present": False,
        "ledger_rows": 0,
        "ledger_malformed": 0,
        "record_calls": 0,
        "record_bytes_stored": 0,
        "continuity_calls": 0,
        "bytes_available": 0,
        "bytes_injected": 0,
        "turns_available": 0,
        "turns_returned": 0,
        "turns_omitted": 0,
    }

    stats_path = os.path.join(lmdb_dir, "mutable_tool_stats.json")
    if os.path.isfile(stats_path):
        try:
            with open(stats_path, encoding="utf-8") as fh:
                stats = json.load(fh)
            tools = defaultdict(int)
            for name, entry in stats.items():
                calls = int(entry.get("call_count", 0)) if isinstance(entry, dict) else 0
                if calls <= 0:
                    continue
                out["ops_total"] += calls
                out["ops_by_family"][family_of(name)] += calls
                tools[name] += calls
            out["top_tools"] = sorted(
                ({"tool": n, "calls": c} for n, c in tools.items()),
                key=lambda t: (-t["calls"], t["tool"]),
            )[:5]
        except (OSError, ValueError, AttributeError):
            pass

    ledger_path = os.path.join(lmdb_dir, "savings_ledger.jsonl")
    if os.path.isfile(ledger_path):
        out["ledger_present"] = True
        try:
            with open(ledger_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        out["ledger_malformed"] += 1
                        continue
                    out["ledger_rows"] += 1
                    op = row.get("op")
                    num = lambda k: int(row.get(k, 0) or 0)  # noqa: E731
                    if op == "record":
                        out["record_calls"] += 1
                        out["record_bytes_stored"] += num("bytes_stored")
                    elif op == "continuity":
                        out["continuity_calls"] += 1
                        out["bytes_available"] += num("bytes_available")
                        out["bytes_injected"] += num("bytes_injected")
                        out["turns_available"] += num("turns_available")
                        out["turns_returned"] += num("turns_returned")
                        out["turns_omitted"] += num("turns_omitted")
        except OSError:
            pass

    out["ops_by_family"] = dict(out["ops_by_family"])
    return out


def opencode_totals(db_path: str) -> dict | None:
    """Session-table aggregates (read-only). None when unavailable."""
    if not os.path.isfile(db_path):
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        row = conn.execute(
            "SELECT COUNT(*), SUM(tokens_input), SUM(tokens_cache_read), "
            "SUM(tokens_cache_write), SUM(tokens_output), SUM(tokens_reasoning), "
            "SUM(cost), MIN(time_created), MAX(time_updated) FROM session"
        ).fetchone()
        by_month = conn.execute(
            "SELECT strftime('%Y-%m', time_updated/1000,'unixepoch') AS m, COUNT(*), "
            "SUM(tokens_input), SUM(tokens_cache_read), SUM(tokens_output), SUM(cost) "
            "FROM session GROUP BY m ORDER BY m"
        ).fetchall()
    except sqlite3.Error:
        conn.close()
        return None
    conn.close()

    sessions, fresh, cache_read, cache_write, output, reasoning, cost, t_min, t_max = row
    sessions = sessions or 0
    fresh = fresh or 0
    cache_read = cache_read or 0
    cache_write = cache_write or 0
    denom = fresh + cache_read + cache_write
    return {
        "db": db_path,
        "sessions": sessions,
        "tokens_input": fresh,
        "tokens_cache_read": cache_read,
        "tokens_cache_write": cache_write,
        "tokens_output": output or 0,
        "tokens_reasoning": reasoning or 0,
        "cost_usd": round(cost or 0.0, 2),
        "cache_served_share_pct": round(100.0 * cache_read / denom, 2) if denom else None,
        "first_session": t_min,
        "last_session": t_max,
        "by_month": [
            {
                "month": m,
                "sessions": n,
                "tokens_input": i or 0,
                "tokens_cache_read": cr or 0,
                "tokens_output": o or 0,
                "cost_usd": round(c or 0.0, 2),
                "cache_served_share_pct": round(
                    100.0 * (cr or 0) / ((i or 0) + (cr or 0)), 2
                )
                if (i or 0) + (cr or 0)
                else None,
            }
            for (m, n, i, cr, o, c) in by_month
        ],
    }


def build_report(stores_glob: str, opencode_db: str, with_opencode: bool) -> dict:
    stores = [read_store(p) for p in sorted(glob.glob(os.path.expanduser(stores_glob)))]
    totals = {
        "ops_total": sum(s["ops_total"] for s in stores),
        "ops_by_family": defaultdict(int),
        "ledger_present_stores": sum(1 for s in stores if s["ledger_present"]),
        "record_calls": sum(s["record_calls"] for s in stores),
        "record_bytes_stored": sum(s["record_bytes_stored"] for s in stores),
        "continuity_calls": sum(s["continuity_calls"] for s in stores),
        "bytes_available": sum(s["bytes_available"] for s in stores),
        "bytes_injected": sum(s["bytes_injected"] for s in stores),
        "turns_available": sum(s["turns_available"] for s in stores),
        "turns_returned": sum(s["turns_returned"] for s in stores),
        "turns_omitted": sum(s["turns_omitted"] for s in stores),
    }
    for s in stores:
        for fam, n in s["ops_by_family"].items():
            totals["ops_by_family"][fam] += n
    totals["ops_by_family"] = dict(totals["ops_by_family"])
    saved = max(0, totals["bytes_available"] - totals["bytes_injected"])
    totals["state_to_context_ratio"] = (
        round(totals["bytes_available"] / totals["bytes_injected"], 2)
        if totals["bytes_injected"]
        else None
    )
    totals["token_equivalent_saved_estimate"] = saved // BYTES_PER_TOKEN

    return {
        "generated_by": "scripts/token_ledger_report.py",
        "stores_glob": stores_glob,
        "stores": stores,
        "totals": totals,
        "opencode": opencode_totals(opencode_db) if with_opencode else None,
        "attribution": (
            "State-over-transcript is WhiteMagic-attributable; provider/harness "
            "prompt caching is context, not a WhiteMagic saving. Token-equivalent "
            f"is an estimate (bytes/{BYTES_PER_TOKEN}). See docs/TOKEN_LEDGER.md."
        ),
    }


def print_report(report: dict) -> None:
    t = report["totals"]
    print("=== Local token/savings ledger report ===")
    print(f"Stores: {len(report['stores'])} scanned · ledger present in {t['ledger_present_stores']}")
    print(f"Local WM ops (100% local compute): {t['ops_total']:,}")
    fams = " · ".join(f"{k}={v:,}" for k, v in sorted(t["ops_by_family"].items()))
    print(f"  by family: {fams}")
    print(
        f"Ledger: {t['record_calls']:,} record calls ({t['record_bytes_stored']:,} B stored) · "
        f"{t['continuity_calls']:,} continuity calls"
    )
    if t["bytes_injected"]:
        print(
            f"  state-over-transcript: {t['bytes_available']:,} B available → "
            f"{t['bytes_injected']:,} B injected (ratio {t['state_to_context_ratio']}) · "
            f"token-equivalent saved ~{t['token_equivalent_saved_estimate']:,}"
        )
    else:
        print("  state-over-transcript: no ledger rows yet (fills as sessions record and resume)")

    oc = report["opencode"]
    if oc:
        print("--- opencode session accounting (context, not attribution) ---")
        print(
            f"{oc['sessions']:,} sessions · fresh input {oc['tokens_input']:,} · "
            f"cache-read {oc['tokens_cache_read']:,} · output {oc['tokens_output']:,} · "
            f"cache-served share {oc['cache_served_share_pct']}%"
        )
        for m in oc["by_month"]:
            print(
                f"  {m['month']}: {m['sessions']:>4} sessions · "
                f"fresh {m['tokens_input']:>12,} · cache {m['tokens_cache_read']:>14,} · "
                f"cache share {m['cache_served_share_pct']}%"
            )
    print(report["attribution"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stores", default=DEFAULT_STORES_GLOB, help="store lmdb glob")
    parser.add_argument("--opencode-db", default=DEFAULT_OPENCODE_DB)
    parser.add_argument("--no-opencode", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(args.stores, args.opencode_db, not args.no_opencode)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
