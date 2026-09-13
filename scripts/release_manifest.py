#!/usr/bin/env python3
"""Generate `release-manifest.json` for a tagged WhiteMagic release.

The manifest is the canonical machine-readable description of a release
(GitHub Releases are the canonical source; crates.io/npm/Docker/MCP registry
are mirrors that may lag). It is signed separately in CI — the signature over
*this file* is the trust anchor, not the per-binary checksums.

Usage:
    release_manifest.py --version 9.1.4 [--channel stable]
                        [--artifacts-dir artifacts]
                        [--notes-file NOTES.md]
                        [--minimum-store-schema 7]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# artifact filename -> target key in the manifest
TARGETS = {
    "wm-linux-x86_64-musl": "linux-x86_64-musl",
    "wm-linux-x86_64": "linux-x86_64",
    "wm-macos-x86_64": "macos-x86_64",
    "wm-macos-aarch64": "macos-aarch64",
    "wm-windows-x86_64.exe": "windows-x86_64",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", required=True)
    ap.add_argument("--channel", default="stable")
    ap.add_argument("--repo", default="lbailey94/whitemagic")
    ap.add_argument("--artifacts-dir", default="artifacts")
    ap.add_argument("--out", default=None)
    ap.add_argument("--notes-file", default=None)
    ap.add_argument("--minimum-store-schema", type=int, default=7)
    args = ap.parse_args()

    artifacts = Path(args.artifacts_dir)
    if not artifacts.is_dir():
        print(f"artifacts dir not found: {artifacts}", file=sys.stderr)
        return 2

    targets = {}
    for filename, key in TARGETS.items():
        binary = artifacts / filename
        if not binary.is_file():
            continue
        checksum_file = artifacts / f"{filename}.sha256"
        if checksum_file.is_file():
            sha = checksum_file.read_text(encoding="utf-8").split()[0].strip()
        else:
            sha = sha256_file(binary)
        bundle = artifacts / f"{filename}.bundle"
        targets[key] = {
            "url": f"https://github.com/{args.repo}/releases/download/v{args.version}/{filename}",
            "sha256": sha,
            "signature": bundle.name if bundle.is_file() else None,
        }

    if not targets:
        print("no known release artifacts found", file=sys.stderr)
        return 2

    notes = None
    if args.notes_file:
        notes = Path(args.notes_file).read_text(encoding="utf-8")

    manifest = {
        "schema": 1,
        "channel": args.channel,
        "version": args.version,
        "published": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "minimum_store_schema": args.minimum_store_schema,
        "notes": notes,
        "targets": targets,
    }

    out = Path(args.out) if args.out else artifacts / "release-manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"manifest: {out} ({len(targets)} targets)")
    for key, t in sorted(targets.items()):
        print(f"  {key:<20} sha256={t['sha256'][:12]}… sig={'yes' if t['signature'] else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
