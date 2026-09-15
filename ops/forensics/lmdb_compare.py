#!/usr/bin/env python3
"""Read-only LMDB key-set comparator for WhiteMagic stores and backups.

Compares a live store (or any LMDB) against a snapshot/archive by listing each
named DBI and diffing key sets: overlap, unique-to-snapshot, unique-to-live.
Used for the 2026-09-14 card/TB overlap analyses. Never writes; never opens
writable (`readonly=True, lock=False`), so it is safe against served stores
and read-only media.

Accepts, for either argument:
  - a store dir containing `lmdb/` (as `wm` lays it out)
  - an `lmdb` dir directly
  - a `data.mdb` file path

Usage:
  python3 lmdb_compare.py LIVE SNAPSHOT [--skip-dbi NAME]... [--json OUT]

Dependencies: python-lmdb (`python3 -m venv venv && venv/bin/pip install lmdb`).

Note: derived DBIs (embeddings, caches, term indexes) are skipped by default —
they are recomputable and expensive to iterate. Content-level change signal
comes from `idx_content_hash` and the galaxy DBIs, not from those.
"""

import argparse
import json
import os
import sys

try:
    import lmdb
except ImportError:  # pragma: no cover
    sys.exit("python-lmdb is required: python3 -m venv venv && venv/bin/pip install lmdb")

DEFAULT_SKIP = {"embeddings", "embedding_cache", "episodic_terms", "episodic_terms_v2"}


def open_path(path):
    if os.path.isdir(os.path.join(path, "lmdb")):
        return lmdb.open(os.path.join(path, "lmdb"), readonly=True, lock=False,
                         subdir=True, max_dbs=256, readahead=False)
    if os.path.isdir(path):
        return lmdb.open(path, readonly=True, lock=False,
                         subdir=True, max_dbs=256, readahead=False)
    if os.path.isfile(path):
        return lmdb.open(path, readonly=True, lock=False,
                         subdir=False, max_dbs=256, readahead=False)
    raise SystemExit(f"not a store path: {path}")


def dbi_names(env):
    main = env.open_db(None)
    names = []
    with env.begin() as txn:
        for k, _v in txn.cursor(main):
            names.append(k.decode("utf-8", "replace"))
    return names


def key_set(env, name):
    keys = set()
    dbi = env.open_db(name.encode())
    with env.begin() as txn:
        for k, _v in txn.cursor(dbi):
            keys.add(k)
    return keys


def main():
    ap = argparse.ArgumentParser(description="Read-only LMDB key-set comparator")
    ap.add_argument("live", help="live store dir, lmdb dir, or data.mdb")
    ap.add_argument("snapshot", help="snapshot store dir, lmdb dir, or data.mdb")
    ap.add_argument("--skip-dbi", action="append", default=[],
                    help="extra DBI names to skip (repeatable)")
    ap.add_argument("--json", dest="json_out", help="write full JSON report here")
    args = ap.parse_args()

    skip = DEFAULT_SKIP | set(args.skip_dbi)
    live = open_path(args.live)
    snap = open_path(args.snapshot)
    live_names = set(dbi_names(live))
    snap_names = set(dbi_names(snap))

    print(f"{'dbi':24s} {'snap':>8s} {'live':>8s} {'overlap':>8s} {'uniq_snap':>9s} {'uniq_live':>9s}")
    report = {}
    for name in sorted(live_names | snap_names):
        if name in skip:
            continue
        lks = key_set(live, name) if name in live_names else set()
        sks = key_set(snap, name) if name in snap_names else set()
        row = {
            "snap": len(sks), "live": len(lks),
            "overlap": len(sks & lks),
            "unique_snap": len(sks - lks),
            "unique_live": len(lks - sks),
        }
        report[name] = row
        if not (row["snap"] or row["live"]):
            continue
        print(f"{name:24s} {row['snap']:>8d} {row['live']:>8d} {row['overlap']:>8d} "
              f"{row['unique_snap']:>9d} {row['unique_live']:>9d}")

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump({"live": args.live, "snapshot": args.snapshot, "dbis": report},
                      fh, indent=1)
        print(f"\nJSON written: {args.json_out}")


if __name__ == "__main__":
    main()
