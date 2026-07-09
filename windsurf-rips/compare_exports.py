#!/usr/bin/env python3
"""
Compare Windsurf API exports across dates to find new and changed sessions.

Compares by:
  - Cascade ID (session identity)
  - Transcript length (char count) — detects grew/truncated
  - Step count — detects new turns added
  - Content hash (SHA-256 of transcript) — detects content changes

Outputs:
  - New sessions (not in any previous export)
  - Changed sessions (same ID, different length/steps/hash)
  - Unchanged sessions
  - Sessions in old export but missing from new export

USAGE:
  python3 compare_exports.py [--new-dir DIR] [--old-dir DIR] [--report-only]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


def load_export_index(export_dir: Path) -> dict[str, dict[str, Any]]:
    """Load INDEX.json from an export directory, return map of cascadeId -> metadata."""
    index_file = export_dir / "INDEX.json"
    if not index_file.exists():
        return {}
    data = json.loads(index_file.read_text(encoding="utf-8"))
    sessions = {}
    for s in data.get("sessions", []):
        cid = s.get("cascadeId", "")
        if cid:
            sessions[cid] = s
    return sessions


def hash_transcript(export_dir: Path, cascade_id: str, sessions: dict) -> str | None:
    """Compute SHA-256 of the transcript .md file for a session."""
    # Find the .md file for this cascade ID
    for md_file in export_dir.glob("*.md"):
        if cascade_id[:8] in md_file.name:
            content = md_file.read_bytes()
            return hashlib.sha256(content).hexdigest()[:16]
    return None


def compare_exports(new_dir: Path, old_dirs: list[Path]) -> dict[str, Any]:
    """Compare new export with all old exports."""
    new_sessions = load_export_index(new_dir)

    # Load the most recent old export as the primary comparison baseline
    # But also track all previous exports to know if a session was ever seen
    all_old_ids: set[str] = set()
    best_old: dict[str, dict] = {}  # cascadeId -> best (most chars) old metadata
    old_by_dir: dict[str, dict[str, dict]] = {}

    for old_dir in old_dirs:
        old_sessions = load_export_index(old_dir)
        old_by_dir[str(old_dir)] = old_sessions
        for cid, meta in old_sessions.items():
            all_old_ids.add(cid)
            old_chars = meta.get("transcriptLength", 0)
            best_chars = best_old.get(cid, {}).get("transcriptLength", 0)
            if old_chars > best_chars:
                best_old[cid] = meta

    new_ids = set(new_sessions.keys())

    # Categorize
    brand_new = sorted(new_ids - all_old_ids)
    potentially_changed = sorted(new_ids & all_old_ids)
    missing = sorted(all_old_ids - new_ids)

    # For potentially changed, compare char count, step count, and hash
    changed = []
    unchanged = []

    for cid in potentially_changed:
        new_meta = new_sessions[cid]
        old_meta = best_old.get(cid, {})

        new_chars = new_meta.get("transcriptLength", 0)
        old_chars = old_meta.get("transcriptLength", 0)
        new_steps = new_meta.get("stepCount", 0)
        old_steps = old_meta.get("stepCount", 0)
        new_total_steps = new_meta.get("numTotalSteps", 0)
        old_total_steps = old_meta.get("numTotalSteps", 0)

        # Content hash comparison
        new_hash = hash_transcript(new_dir, cid, new_sessions)
        old_hash = None
        for old_dir in old_dirs:
            old_hash = hash_transcript(old_dir, cid, old_by_dir.get(str(old_dir), {}))
            if old_hash:
                break

        is_changed = (
            new_chars != old_chars or
            new_steps != old_steps or
            new_total_steps != old_total_steps or
            (new_hash and old_hash and new_hash != old_hash)
        )

        if is_changed:
            changed.append({
                "cascadeId": cid,
                "title": new_meta.get("title", "?"),
                "old_chars": old_chars,
                "new_chars": new_chars,
                "char_delta": new_chars - old_chars,
                "old_steps": old_steps,
                "new_steps": new_steps,
                "step_delta": new_steps - old_steps,
                "old_total_steps": old_total_steps,
                "new_total_steps": new_total_steps,
                "old_hash": old_hash,
                "new_hash": new_hash,
            })
        else:
            unchanged.append({
                "cascadeId": cid,
                "title": new_meta.get("title", "?"),
                "chars": new_chars,
                "steps": new_steps,
            })

    return {
        "new_export_dir": str(new_dir),
        "old_export_dirs": [str(d) for d in old_dirs],
        "summary": {
            "total_new_export": len(new_sessions),
            "total_old_unique": len(all_old_ids),
            "brand_new": len(brand_new),
            "changed": len(changed),
            "unchanged": len(unchanged),
            "missing_from_new": len(missing),
        },
        "brand_new": [
            {
                "cascadeId": cid,
                "title": new_sessions[cid].get("title", "?"),
                "chars": new_sessions[cid].get("transcriptLength", 0),
                "steps": new_sessions[cid].get("stepCount", 0),
                "total_steps": new_sessions[cid].get("numTotalSteps", 0),
            }
            for cid in brand_new
        ],
        "changed": sorted(changed, key=lambda x: x["char_delta"], reverse=True),
        "unchanged": unchanged,
        "missing_from_new": [
            {
                "cascadeId": cid,
                "title": best_old[cid].get("title", "?"),
                "chars": best_old[cid].get("transcriptLength", 0),
            }
            for cid in missing
        ],
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compare Windsurf API exports")
    parser.add_argument("--new-dir", type=str, default=None,
                        help="New export directory (default: most recent)")
    parser.add_argument("--old-dir", type=str, nargs="*", default=None,
                        help="Old export directories to compare against (default: all others)")
    parser.add_argument("--report-only", action="store_true",
                        help="Just print report, don't save JSON")
    args = parser.parse_args()

    script_dir = Path(__file__).parent

    # Find new export dir
    if args.new_dir:
        new_dir = Path(args.new_dir)
    else:
        export_dirs = sorted(script_dir.glob("api_export_*"))
        if not export_dirs:
            print("ERROR: No export directories found")
            sys.exit(1)
        new_dir = export_dirs[-1]

    # Find old export dirs (all except the new one)
    if args.old_dir:
        old_dirs = [Path(d) for d in args.old_dir]
    else:
        old_dirs = [d for d in sorted(script_dir.glob("api_export_*")) if d != new_dir]

    print(f"=== Export Comparison ===")
    print(f"New: {new_dir} ({new_dir.name})")
    print(f"Old: {len(old_dirs)} directories")
    for d in old_dirs:
        print(f"  - {d.name}")
    print()

    result = compare_exports(new_dir, old_dirs)

    s = result["summary"]
    print(f"--- Summary ---")
    print(f"  Total in new export:   {s['total_new_export']}")
    print(f"  Total in old exports:  {s['total_old_unique']}")
    print(f"  Brand new sessions:    {s['brand_new']}")
    print(f"  Changed sessions:      {s['changed']}")
    print(f"  Unchanged sessions:    {s['unchanged']}")
    print(f"  Missing from new:      {s['missing_from_new']}")
    print()

    if result["brand_new"]:
        print("--- Brand New Sessions ---")
        for sess in result["brand_new"]:
            print(f"  {sess['cascadeId'][:8]}  {sess['title'][:55]:57s}  {sess['chars']:>8,} chars  {sess['steps']:>5} steps")
        print()

    if result["changed"]:
        print("--- Changed Sessions (sorted by char delta) ---")
        for sess in result["changed"]:
            delta_str = f"+{sess['char_delta']:,}" if sess["char_delta"] > 0 else f"{sess['char_delta']:,}"
            step_delta_str = f"+{sess['step_delta']}" if sess["step_delta"] > 0 else f"{sess['step_delta']}"
            print(f"  {sess['cascadeId'][:8]}  {sess['title'][:50]:52s}  {sess['old_chars']:>8,} -> {sess['new_chars']:>8,} chars ({delta_str})  steps: {sess['old_steps']} -> {sess['new_steps']} ({step_delta_str})")
        print()

    if result["missing_from_new"]:
        print("--- Missing from New Export ---")
        for sess in result["missing_from_new"]:
            print(f"  {sess['cascadeId'][:8]}  {sess['title'][:55]:57s}  {sess['chars']:>8,} chars")
        print()

    if not args.report_only:
        report_file = new_dir / "comparison_report.json"
        report_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Report saved: {report_file}")

    # Also save a combined "needs ingestion" list
    needs_ingestion = {
        "brand_new": [s["cascadeId"] for s in result["brand_new"]],
        "changed": [s["cascadeId"] for s in result["changed"]],
        "all": [s["cascadeId"] for s in result["brand_new"]] + [s["cascadeId"] for s in result["changed"]],
    }
    if not args.report_only:
        ingest_file = new_dir / "needs_ingestion.json"
        ingest_file.write_text(json.dumps(needs_ingestion, indent=2), encoding="utf-8")
        print(f"Ingestion list: {ingest_file}")


if __name__ == "__main__":
    main()
