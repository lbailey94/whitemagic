#!/usr/bin/env python3
"""Build the nightly trust manifest (extracted from wm-nightly-backup.sh, 2026-09-12).

Commits store anchor-log and seal-snapshot digests, plus the site prescience
ledger state, into one JSON file. The nightly run then stamps it with BOTH
OpenTimestamps (Bitcoin) and RFC-3161 (freetsa) — a manifest digest stamped by
two independent authorities is what makes the evidence chain independently
verifiable.

The prescience block binds the ledger's *attested* state, not just its bytes:
sha256 + merkle_root + signed_at + key_id + cohort counts. A swapped or edited
ledger changes the digest; counts/root make the coverage legible in receipts.

Usage:
    build_trust_manifest.py --anchors DIR --seals DIR --out FILE
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
from datetime import datetime, timezone

PRESCIENCE = os.path.expanduser(
    "~/Desktop/WHITEMAGIC/whitemagic-site/public/api/prescience.json"
)
KARMA_ANCHORS = os.path.expanduser(
    "~/Desktop/WHITEMAGIC/WMv9/anchors/karma_anchors.jsonl"
)
EMPTY_MERKLE = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tail_record(path: str) -> dict:
    try:
        with open(path, "rb") as f:
            last = f.read().strip().split(b"\n")[-1].decode()
        r = json.loads(last)
        return {k: r.get(k) for k in ("root", "prev_hash", "leaf_count", "valid", "stale", "invalid")}
    except Exception as e:
        return {"error": str(e)}


def prescience_block() -> dict:
    """Bind the attested prescience ledger state (never fakes on failure)."""
    blk: dict = {"path": "~" + PRESCIENCE[len(os.path.expanduser("~")):]}
    try:
        with open(PRESCIENCE, "rb") as f:
            raw = f.read()
        d = json.loads(raw)
        s = d["summary"]
        att = s.get("ledger_attestation", {})
        blk.update({
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "mtime_utc": datetime.fromtimestamp(
                os.path.getmtime(PRESCIENCE), timezone.utc
            ).isoformat().replace("+00:00", "Z"),
            "merkle_root": att.get("merkle_root"),
            "signed_at": att.get("signed_at"),
            "key_id": att.get("key_id"),
            "total_attested_rows": att.get("total_attested_rows"),
            "total": s.get("total"),
            "validated": s.get("validated"),
            "pending": s.get("pending"),
            "expired": s.get("expired"),
            "falsified": s.get("falsified"),
            "scoring_primary": s.get("scoring_primary"),
            "total_points_v21": s.get("total_points_v21"),
            "total_points_v1": s.get("total_points_v1"),
        })
    except Exception as e:
        blk["error"] = str(e)
    return blk


def karma_block() -> dict:
    """Digest + chain-integrity check of the versioned karma anchor log."""
    blk: dict = {"path": "~" + KARMA_ANCHORS[len(os.path.expanduser("~")):]}
    try:
        lines = [l for l in open(KARMA_ANCHORS).read().strip().split("\n") if l]
        intact = True
        for i, line in enumerate(lines):
            r = json.loads(line)
            expected = "genesis" if i == 0 else hashlib.sha256(lines[i - 1].encode()).hexdigest()
            if r.get("prev_hash") != expected:
                intact = False
        last = json.loads(lines[-1])
        blk.update({
            "sha256": sha256_file(KARMA_ANCHORS),
            "records": len(lines),
            "chain_intact": intact,
            "latest": {
                "chain_head": last.get("chain_head"),
                "root": last.get("root"),
                "entry_count": last.get("entry_count"),
                "timestamp": last.get("timestamp"),
            },
        })
    except Exception as e:
        blk["error"] = str(e)
    return blk


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anchors", required=True, help="anchors dir (per-store anchors.jsonl)")
    ap.add_argument("--seals", required=True, help="seals dir (per-store dated snapshots)")
    ap.add_argument("--out", required=True, help="manifest output path")
    args = ap.parse_args()

    day = os.path.basename(args.out).removeprefix("trust-").removesuffix(".json")
    manifest = {
        "type": "wm-nightly-trust-manifest",
        "v": 1,
        "utc_date": day,
        "stores": {},
        "site": {"prescience_ledger": prescience_block()},
        "ledgers": {"karma_anchors": karma_block()},
    }

    for log_path in sorted(glob.glob(os.path.join(args.anchors, "*", "anchors.jsonl"))):
        store = os.path.basename(os.path.dirname(log_path))
        rec = tail_record(log_path)
        n_lines = sum(1 for _ in open(log_path, "rb"))
        manifest["stores"][store] = {
            "anchors_log_sha256": sha256_file(log_path),
            "anchors_records": n_lines,
            "anchor_tail": rec,
            "coverage": f"{rec.get('valid', 0)} valid attestations"
            if isinstance(rec.get("valid"), int) else "unknown",
        }

    for store_dir in sorted(glob.glob(os.path.join(args.seals, "*"))):
        store = os.path.basename(store_dir)
        days = sorted(os.listdir(store_dir))
        if not days:
            continue
        newest = os.path.join(store_dir, days[-1])
        entry = {"snapshot_day": days[-1]}
        for fname in sorted(os.listdir(newest)):
            entry[f"{fname}_sha256"] = sha256_file(os.path.join(newest, fname))
        manifest["stores"].setdefault(store, {})["seal_snapshot"] = entry

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    p = manifest["site"]["prescience_ledger"]
    if "error" in p:
        print(f"manifest: {len(manifest['stores'])} stores; prescience block ERROR: {p['error']}")
        return 1
    root = (p.get("merkle_root") or "")
    print(
        f"manifest: {len(manifest['stores'])} stores; prescience "
        f"{p.get('validated')}v/{p.get('pending')}p/{p.get('expired')}e/{p.get('falsified')}f, "
        f"merkle {root[:16]}…, digest {p.get('sha256', '')[:16]}…"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
