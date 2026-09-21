#!/usr/bin/env python3
"""Generate `release-manifest.json` for a tagged WhiteMagic release.

The manifest is the canonical machine-readable description of a release
(GitHub Releases are the canonical source; crates.io/npm/Docker/MCP registry
are mirrors that may lag). It is signed separately in CI — the signature over
*this file* is the trust anchor, not the per-binary checksums.

It is also the release **facts** authority for downstream surfaces (the
website, README, llms.txt, package metadata): version, release date,
platforms, artifact sizes, install-gated targets, crate count, and optional
test/benchmark snapshots live here and are consumed, never re-typed.

Usage:
    release_manifest.py --version 9.1.4 --channel "open alpha"
                        [--artifacts-dir artifacts]
                        [--notes-file NOTES.md]
                        [--minimum-store-schema 7]
                        [--tests-json tests.json]
                        [--benchmarks-file benchmark_results.txt]
                        [--install-gated linux-x86_64]

`--channel` is required: it is an evidence-tied label
(`docs/RELEASE_CADENCE.md` §Channel labels), recorded in the signed manifest.
It has no default on purpose — a silent `stable` would contradict the
current channel.

Additive fields keep `schema: 1`; the updater's `ReleaseManifest` uses
`#[serde(default)]` and ignores unknown fields, so older clients are safe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# artifact filename -> target key in the manifest
TARGETS = {
    "wm-linux-x86_64-musl": "linux-x86_64-musl",
    "wm-linux-x86_64": "linux-x86_64",
    "wm-linux-aarch64-musl": "linux-aarch64-musl",
    "wm-linux-aarch64": "linux-aarch64",
    "wm-macos-x86_64": "macos-x86_64",
    "wm-macos-aarch64": "macos-aarch64",
    "wm-windows-x86_64.exe": "windows-x86_64",
}

# Targets whose install path is gated (README §Install path: Linux x86-64 and
# arm64 since 9.2.3 ships arm64 with native CI smoke; macOS/Windows binaries
# are published but not yet install-gated).
DEFAULT_INSTALL_GATED = ["linux-x86_64", "linux-aarch64"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def workspace_crate_count(root: Path) -> int | None:
    """Count workspace members from Cargo.lock (entries with no `source`)."""
    lock = root / "Cargo.lock"
    if not lock.is_file():
        return None
    count = sum(
        1
        for block in lock.read_text(encoding="utf-8").split("[[package]]")[1:]
        if "source =" not in block and re.search(r'^name = "', block, re.M)
    )
    return count or None


def load_tests(path: Path | None) -> dict | None:
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "passed": data.get("passed"),
        "ignored": data.get("ignored"),
        "failed": data.get("failed"),
        "source": data.get("source"),
    }


def load_benchmarks(path: Path | None) -> dict | None:
    if path is None:
        return None
    text = path.read_text(encoding="utf-8").strip()
    return {"source": path.name, "raw": text}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", required=True)
    ap.add_argument(
        "--channel",
        required=True,
        help="evidence-tied release channel label (e.g. 'open alpha'); recorded "
        "in the signed manifest — see docs/RELEASE_CADENCE.md §Channel labels",
    )
    ap.add_argument("--repo", default="lbailey94/whitemagic")
    ap.add_argument("--artifacts-dir", default="artifacts")
    ap.add_argument("--out", default=None)
    ap.add_argument("--notes-file", default=None)
    ap.add_argument("--minimum-store-schema", type=int, default=7)
    ap.add_argument(
        "--install-gated",
        default=",".join(DEFAULT_INSTALL_GATED),
        help="comma-separated target keys whose install path is gated",
    )
    ap.add_argument("--tests-json", default=None, help="CI test counts JSON")
    ap.add_argument(
        "--benchmarks-file", default=None, help="benchmark_results.txt snapshot"
    )
    args = ap.parse_args()

    artifacts = Path(args.artifacts_dir)
    if not artifacts.is_dir():
        print(f"artifacts dir not found: {artifacts}", file=sys.stderr)
        return 2

    gated = {key.strip() for key in args.install_gated.split(",") if key.strip()}
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
            "size": binary.stat().st_size,
            "install_gated": key in gated,
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
        "supported_profile": "curated",
        "notes": notes,
        "targets": targets,
    }

    root = Path(__file__).resolve().parents[1]
    crates = workspace_crate_count(root)
    if crates is not None:
        manifest["crates"] = crates
    tests = load_tests(Path(args.tests_json)) if args.tests_json else None
    if tests is not None:
        manifest["tests"] = tests
    benchmarks = (
        load_benchmarks(Path(args.benchmarks_file)) if args.benchmarks_file else None
    )
    if benchmarks is not None:
        manifest["benchmarks"] = benchmarks

    out = Path(args.out) if args.out else artifacts / "release-manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"manifest: {out} ({len(targets)} targets)")
    for key, t in sorted(targets.items()):
        gate = "gated" if t["install_gated"] else "published"
        print(
            f"  {key:<20} sha256={t['sha256'][:12]}… size={t['size']}"
            f" sig={'yes' if t['signature'] else 'no'} {gate}"
        )
    if crates is not None:
        print(f"  crates={crates}")
    return 0



if __name__ == "__main__":
    sys.exit(main())
