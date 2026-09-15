#!/usr/bin/env python3
"""Read-only session-id overlap between two opencode-style SQLite DBs.

Prints total sessions per database and the set differences — used to prove the
TB cold-tier copies were strict subsets of the live opencode.db (2026-09-14).

Usage:
  python3 sqlite_session_overlap.py LIVE.db OTHER.db [--json OUT]

Opens both databases with `mode=ro` URI flags: read-only on the file system,
safe against served/live DBs. Works over read-only FUSE mounts.
"""

import argparse
import json
import sqlite3
import sys


def session_ids(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return {row[0] for row in con.execute("SELECT id FROM session")}
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser(description="Read-only SQLite session overlap")
    ap.add_argument("live")
    ap.add_argument("other")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    try:
        live = session_ids(args.live)
        other = session_ids(args.other)
    except sqlite3.Error as exc:
        sys.exit(f"sqlite error: {exc}")

    result = {
        "live": len(live), "other": len(other),
        "overlap": len(live & other),
        "unique_to_other": len(other - live),
        "unique_to_live": len(live - other),
    }
    for k, v in result.items():
        print(f"{k:16s} {v}")
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(result, fh, indent=1)
        print(f"\nJSON written: {args.json_out}")


if __name__ == "__main__":
    main()
