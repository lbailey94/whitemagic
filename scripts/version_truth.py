#!/usr/bin/env python3
"""Version-truth checker/updater for WhiteMagic release bumps.

The workspace version in `Cargo.toml` is canonical; every other surface that
hardcodes the product version must agree before a tag. Each release used to do
this by hand (the "version-truth pass"), and `scripts/release.sh` only bumped
three of the fifteen surfaces — leaving Docker labels, the MCPB manifest, the
hosted server card, CITATION, docs and install examples to drift.

CHANGELOG.md is deliberately excluded: its version strings are historical
records, not version truth.

Usage:
    version_truth.py --check [--version X]
    version_truth.py --set X [--dry-run]

    --check compares every surface with the workspace version (or --version X
    when the bump already happened but the tag has not).
    --set replaces every 9.x.y reference on the curated surfaces; run
    `cargo check` afterwards to refresh Cargo.lock.

Exit codes:
    0  every surface agrees (check) / rewrite completed (set)
    1  drift found (check)
    2  usage or missing-surface problems
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Surfaces that carry the product version. Keep in sync with reality:
# `rg -n '9\.[0-9]+\.[0-9]+' --glob '!target' --glob '!Cargo.lock'` should not
# find other non-historical files.
SURFACES = [
    "Cargo.toml",
    "npm/whitemagic-mcp/package.json",
    "npm/whitemagic-mcp/server.json",
    "npm/whitemagic-mcp/mcpb/manifest.json",
    "ops/hosted/server-card.json",
    "CITATION.cff",
    "Dockerfile",
    "docs/QUICKSTART.md",
    "docs/MCP_CONFIG_GUIDE.md",
    "docs/DOCKER_HUB_RUNBOOK.md",
    "skill.md",
    "README.md",
    "scripts/install.sh",
    "SECURITY.md",
    "rust-toolchain.toml",
]

VERSION_RE = re.compile(r"\bv?9\.\d+\.\d+\b")
WORKSPACE_RE = re.compile(r'(?m)^version = "(\d+\.\d+\.\d+)"')
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")

# Historical version mentions that must never count as drift or be rewritten
# (they describe past releases, not current version truth).
EXEMPT = {
    "SECURITY.md": {"9.0.0"},
}


def versions_in(text: str, exempt: frozenset[str] = frozenset()) -> list[str]:
    return [
        match.lstrip("v")
        for match in VERSION_RE.findall(text)
        if match.lstrip("v") not in exempt
    ]


def rewrite(text: str, target: str, exempt: frozenset[str] = frozenset()) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        numeric = match.group(0).lstrip("v")
        if numeric in exempt:
            return match.group(0)
        count += 1
        prefix = "v" if match.group(0).startswith("v") else ""
        return f"{prefix}{target}"

    return VERSION_RE.sub(repl, text), count


def workspace_version(root: Path) -> str:
    match = WORKSPACE_RE.search((root / "Cargo.toml").read_text(encoding="utf-8"))
    if not match:
        raise SystemExit("could not read the workspace version from Cargo.toml")
    return match.group(1)


def scan(root: Path) -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    missing: list[str] = []
    for rel in SURFACES:
        path = root / rel
        if not path.exists():
            missing.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        found.append((rel, versions_in(text, frozenset(EXEMPT.get(rel, set())))))
    if missing:
        print("missing version surfaces: " + ", ".join(missing), file=sys.stderr)
        raise SystemExit(2)
    return found


def check(root: Path, expected: str | None) -> int:
    target = expected or workspace_version(root)
    rows = scan(root)
    drift = False
    print(f"version truth — expected {target}")
    for rel, versions in rows:
        bad = sorted({v for v in versions if v != target})
        if bad:
            drift = True
            status = f"DRIFT: {', '.join(bad)}"
        elif not versions:
            status = "no reference found"
        else:
            status = "ok"
        print(f"  {rel:<42} {len(versions):>2} reference(s)  {status}")
    if drift:
        print(f"\nREFUSING: at least one surface disagrees with {target}")
        return 1
    print(f"\nall surfaces agree on {target}")
    return 0


def set_version(root: Path, target: str, dry_run: bool) -> int:
    if not SEMVER_RE.fullmatch(target):
        raise SystemExit(f"not a semantic version: {target!r}")
    total = 0
    for rel in SURFACES:
        path = root / rel
        original = path.read_text(encoding="utf-8")
        edited, count = rewrite(original, target, frozenset(EXEMPT.get(rel, set())))
        total += count
        if count == 0:
            print(f"  {rel:<42}  0 reference(s) — inspect this surface")
            continue
        verb = "would update" if dry_run else "updated"
        print(f"  {rel:<42} {count:>2} reference(s)  {verb}")
        if not dry_run:
            path.write_text(edited, encoding="utf-8")
            after = versions_in(
                path.read_text(encoding="utf-8"), frozenset(EXEMPT.get(rel, set()))
            )
            if any(v != target for v in after):
                raise SystemExit(f"{rel} did not converge on {target}")
    print(
        f"\n{'would replace' if dry_run else 'replaced'} {total} references → {target}"
    )
    if not dry_run:
        print("next: cargo check (refresh Cargo.lock), then run the release gates")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report drift, write nothing")
    mode.add_argument("--set", metavar="VERSION", help="rewrite every surface")
    parser.add_argument("--version", default=None, help="expected version for --check")
    parser.add_argument("--dry-run", action="store_true", help="with --set: print only")
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="repository root (default: this script's parent repo)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.check:
        return check(root, args.version)
    return set_version(root, args.set, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
