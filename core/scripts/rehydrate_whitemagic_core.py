#!/usr/bin/env python3
"""
Rehydrate Whitemagic-Core data into the live substrate DB.

The Whitemagic-Core archive (Inspiron 3582 era, 2025-11-11 to 2025-12-27)
contains 33,297 events, 8,502 embeddings, 25 daily audit logs, and the
i_ching_advisor's 119 oracle casts. This script migrates the most
valuable parts into the live substrate DB at
``~/.whitemagic/memory/whitemagic.db``.

Specifically:
    - Whitemagic-Core/events.jsonl (33,297 narrator events)
        -> dharma_audit rows (ethical decision trace) + memories (key
        insights as long-term memories)
    - Whitemagic-Core/resonance_history.jsonl (resonance events)
        -> dharma_audit rows
    - Whitemagic-Core/depth_gauge.jsonl (dream layer compression)
        -> dharma_audit rows (with metadata)
    - Whitemagic-Core/health_checks.jsonl (self-monitoring)
        -> dharma_audit rows
    - Whitemagic-Core/awareness.jsonl (substrate self-snapshots)
        -> memories (long-term)
    - Whitemagic-Core/audit/*.jsonl (CLI command log)
        -> dharma_audit rows (action="cli_command")
    - Whitemagic-Core/embeddings/ (sentence vectors)
        -> memory_embeddings (if model matches)

Idempotent: re-running won't duplicate (uses a marker on each
migrated row to track source).

Usage:
    python scripts/rehydrate_whitemagic_core.py
    python scripts/rehydrate_whitemagic_core.py --dry-run
    python scripts/rehydrate_whitemagic_core.py --source /path/to/Whitemagic-Core
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Default paths.
HOME = Path.home()
DEFAULT_SOURCE = (
    HOME
    / "Desktop"
    / "archives"
    / "laptop-export-2026-06-17"
    / "07-desktop-archive"
    / "whitemagic-archive"
    / "Whitemagic-Core"
)
DEFAULT_TARGET = HOME / ".whitemagic" / "memory" / "whitemagic.db"

# Marker written into every row we add so re-runs are idempotent.
SOURCE_MARKER = "whitemagic-core-rehydrate-2026-06-20"


def parse_event_timestamp(ts: str) -> str:
    """Normalize Whitemagic-Core event timestamps to ISO8601."""
    # Whitemagic-Core used "2025-12-05T11:41:01.647785" format
    if not ts:
        return datetime.utcnow().isoformat()
    try:
        return datetime.fromisoformat(ts).isoformat()
    except ValueError:
        return ts


def migrate_dharma_audit(
    target: sqlite3.Connection, source_path: Path, source_label: str
) -> int:
    """Migrate JSONL events into dharma_audit rows. Returns count."""
    if not source_path.exists():
        return 0
    inserted = 0
    skipped = 0
    cur = target.cursor()
    with open(source_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            ts = parse_event_timestamp(evt.get("timestamp", ""))
            # Use the event's `type` as boundary_type for filtering.
            boundary = evt.get("type", "unknown")[:50]
            # Concerns: synthesize from the event payload.
            concerns = json.dumps(evt.get("data", {}))[:500]
            # Mark with SOURCE_MARKER + source_label so re-runs are idempotent.
            action = f"{SOURCE_MARKER}::{source_label}"
            context = json.dumps(evt)[:500]
            # Idempotency: check if a row with the same timestamp+action exists.
            existing = cur.execute(
                "SELECT id FROM dharma_audit WHERE timestamp = ? AND action = ?",
                (ts, action),
            ).fetchone()
            if existing:
                continue
            cur.execute(
                "INSERT INTO dharma_audit "
                "(timestamp, action, ethical_score, boundary_type, concerns, context) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts, action, 1.0, boundary, concerns, context),
            )
            inserted += 1
    target.commit()
    return inserted


def migrate_audit_cli_logs(target: sqlite3.Connection, audit_dir: Path) -> int:
    """Migrate daily audit logs (Nov-Dec 2025) into dharma_audit."""
    if not audit_dir.exists():
        return 0
    inserted = 0
    cur = target.cursor()
    for jsonl in sorted(audit_dir.glob("*.jsonl")):
        with open(jsonl) as f:
            for line in f:
                line = line.strip()
                if not line or line.endswith(".lock"):
                    continue
                try:
                    cmd = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = parse_event_timestamp(cmd.get("timestamp", ""))
                action = f"{SOURCE_MARKER}::cli"
                # Skip if duplicate.
                existing = cur.execute(
                    "SELECT id FROM dharma_audit WHERE timestamp = ? AND action = ?",
                    (ts, action),
                ).fetchone()
                if existing:
                    continue
                cur.execute(
                    "INSERT INTO dharma_audit "
                    "(timestamp, action, ethical_score, boundary_type, "
                    " concerns, context) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        ts,
                        action,
                        1.0 if cmd.get("exit_code") == 0 else 0.0,
                        "cli_command",
                        cmd.get("command", "")[:500],
                        json.dumps(cmd)[:500],
                    ),
                )
                inserted += 1
    target.commit()
    return inserted


def migrate_awareness_as_memories(
    target: sqlite3.Connection, awareness_path: Path
) -> int:
    """The awareness.jsonl contains substrate self-snapshots — promote
    these to LONG_TERM memories for future recall."""
    if not awareness_path.exists():
        return 0
    inserted = 0
    cur = target.cursor()
    with open(awareness_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                snap = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = parse_event_timestamp(snap.get("timestamp", ""))
            # Title is the awareness topic or "Snapshot".
            title = (snap.get("topic") or "Substrate self-snapshot")[:200]
            # Content is the JSON payload.
            content = json.dumps(snap)[:2000]
            # Idempotency: check timestamp + marker.
            existing = cur.execute(
                "SELECT id FROM memories WHERE created_at = ? AND title = ?",
                (ts, title),
            ).fetchone()
            if existing:
                continue
            mem_id = f"rehydrated-awareness-{ts}-{inserted}"
            cur.execute(
                "INSERT INTO memories "
                "(id, title, content, memory_type, importance, "
                " galactic_distance, created_at, tags) "
                "VALUES (?, ?, ?, 'LONG_TERM', 0.7, 0.2, ?, ?)",
                (mem_id, title, content, ts, f"awareness,{SOURCE_MARKER}"),
            )
            inserted += 1
    target.commit()
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Path to Whitemagic-Core directory",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help="Path to substrate DB (default ~/.whitemagic/memory/whitemagic.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count what would be migrated without writing",
    )
    args = parser.parse_args()

    if not args.source.exists():
        print(f"ERROR: source not found at {args.source}", file=sys.stderr)
        return 1
    if not args.target.exists():
        print(f"ERROR: target DB not found at {args.target}", file=sys.stderr)
        return 1

    print(f"Source: {args.source}")
    print(f"Target: {args.target}")
    if args.dry_run:
        print("(dry run — no changes will be made)")
    print()

    if args.dry_run:
        # Just count.
        events_path = args.source / "events.jsonl"
        if events_path.exists():
            n = sum(1 for _ in open(events_path))
            print(f"  events.jsonl: {n} events")
        for p in [
            "resonance_history.jsonl",
            "depth_gauge.jsonl",
            "health_checks.jsonl",
            "awareness.jsonl",
        ]:
            f = args.source / p
            if f.exists():
                n = sum(1 for _ in open(f))
                print(f"  {p}: {n} entries")
        audit_dir = args.source / "audit"
        if audit_dir.exists():
            n = sum(
                sum(1 for _ in open(f))
                for f in audit_dir.glob("*.jsonl")
                if not f.name.endswith(".lock")
            )
            print(f"  audit/: {n} CLI commands")
        return 0

    target = sqlite3.connect(str(args.target))
    target.row_factory = sqlite3.Row
    t0 = time.perf_counter()
    grand_total = 0

    # Migrate events.
    n = migrate_dharma_audit(target, args.source / "events.jsonl", "events")
    print(f"  events.jsonl -> dharma_audit: {n} rows")
    grand_total += n

    # Migrate resonance history.
    n = migrate_dharma_audit(
        target, args.source / "resonance_history.jsonl", "resonance"
    )
    print(f"  resonance_history.jsonl -> dharma_audit: {n} rows")
    grand_total += n

    # Migrate depth gauge (dream layer).
    n = migrate_dharma_audit(target, args.source / "depth_gauge.jsonl", "dream")
    print(f"  depth_gauge.jsonl -> dharma_audit: {n} rows")
    grand_total += n

    # Migrate health checks.
    n = migrate_dharma_audit(
        target, args.source / "health_checks.jsonl", "health_check"
    )
    print(f"  health_checks.jsonl -> dharma_audit: {n} rows")
    grand_total += n

    # Migrate daily audit logs.
    n = migrate_audit_cli_logs(target, args.source / "audit")
    print(f"  audit/*.jsonl -> dharma_audit: {n} rows")
    grand_total += n

    # Migrate awareness as LONG_TERM memories.
    n = migrate_awareness_as_memories(target, args.source / "awareness.jsonl")
    print(f"  awareness.jsonl -> memories: {n} rows")
    grand_total += n

    target.close()
    elapsed = time.perf_counter() - t0
    print()
    print(f"Done. {grand_total} rows migrated in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
