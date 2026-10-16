#!/usr/bin/env python3
"""Version-truth checker/updater for WhiteMagic release bumps.

The workspace version in `Cargo.toml` is canonical; every other surface that
hardcodes the product version must agree before a tag. Each release used to do
this by hand (the "version-truth pass"), and `scripts/release.sh` only bumped
three of the fifteen surfaces — leaving Docker labels, the MCPB manifest, the
hosted server card, CITATION, docs and install examples to drift.

CHANGELOG.md is not a version surface (its strings are historical records),
but the release-ceremony gate checks it separately: the target version must
not still sit under `[Unreleased]`, and it must have a dated `## [x.y.z]`
section — the v9.1.5 tag shipped with an "unreleased (draft)" heading.

Usage:
    version_truth.py --check [--version X]
    version_truth.py --set X [--dry-run]
    version_truth.py --open-changelog X [--dry-run]

    --check compares every surface with the workspace version (or --version X
    when the bump already happened but the tag has not).
    --set replaces every 9.x.y reference on the curated surfaces; run
    `cargo check` afterwards to refresh Cargo.lock.
    --open-changelog turns the `[Unreleased]` heading into the dated target
    heading the ceremony gate requires (release morning used to hand-edit it).

Exit codes:
    0  every surface agrees (check) / rewrite completed (set)
    1  drift found (check)
    2  usage or missing-surface problems
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

# Surfaces that carry the product version. Keep in sync with reality:
# `rg -n '9\.[0-9]+\.[0-9]+' --glob '!target' --glob '!Cargo.lock'` should not
# find other non-historical files.
SURFACES = [
    "Cargo.toml",
    "npm/whitemagic-mcp/package.json",
    "npm/whitemagic-mcp/server.json",
    "npm/whitemagic-mcp/mcpb/manifest.json",
    "npm/whitemagic-mcp/README.md",
    "CITATION.cff",
    "README.md",
    "skill.md",
    "scripts/install.sh",
]

VERSION_RE = re.compile(r"\bv?(?:10\.\d+(?:\.\d+)?(?:-alpha(?:\.\d+)?)?|9\.\d+\.\d+)\b")
WORKSPACE_RE = re.compile(r'(?m)^version = "([^"]+)"')
SEMVER_RE = re.compile(r"\d+\.\d+(\.\d+)?(-[a-zA-Z0-9.]+)?")

CHANGELOG = "CHANGELOG.md"
UNRELEASED_RE = re.compile(r"(?m)^## \[Unreleased\][^\n]*?(\d+\.\d+(?:\.\d+)?)")
RELEASED_HEADING_RE = re.compile(r"^## \[(\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9.]+)?)]")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

# Historical version mentions that must never count as drift or be rewritten.
EXEMPT: dict[str, set[str]] = {}

# Cross-channel version mentions tied to a specific context line (e.g.,
# README.md's Install path bullet explaining that Windows/Intel macOS remain on
# the stable Gen 2 v9.3.4 release line while v10 is on the open-alpha matrix).
# Unlike a blanket file-wide exemption, this:
#   1. Allows the pinned stable version ONLY inside the matching context span,
#   2. Rejects the stable version if it appears as drift elsewhere in the file,
#   3. Rejects rewriting or deleting the stable fallback when the Install path
#      section is present.
CHANNEL_CONTEXTS: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "README.md": [
        (
            re.compile(r"remain on the stable Gen 2 `(v?(?:10\.\d+(?:\.\d+)?(?:-alpha(?:\.\d+)?)?|9\.\d+\.\d+))` release line"),
            "9.3.4",
        ),
    ],
}


def versions_in(
    text: str,
    exempt: frozenset[str] = frozenset(),
    channel_contexts: list[tuple[re.Pattern[str], str]] | None = None,
) -> list[str]:
    results: list[str] = []
    contexts = channel_contexts or []
    for line in text.splitlines():
        pinned_spans: list[tuple[int, int]] = []
        for pattern, expected_pin in contexts:
            for cm in pattern.finditer(line):
                actual_pin = cm.group(1).lstrip("v")
                if actual_pin == expected_pin:
                    pinned_spans.append(cm.span(1))
        for m in VERSION_RE.finditer(line):
            if any( m.start() >= s and m.end() <= e for s, e in pinned_spans ):
                continue
            ver = m.group(0).lstrip("v")
            if ver not in exempt:
                results.append(ver)
    return results


def check_channel_contexts(rel: str, text: str) -> list[str]:
    """Verify that any channel-pinned context in `rel` carries its expected version."""
    errors: list[str] = []
    contexts = CHANNEL_CONTEXTS.get(rel, [])
    if not contexts:
        return errors
    for pattern, expected_pin in contexts:
        matches = list(pattern.finditer(text))
        if matches:
            for cm in matches:
                actual_pin = cm.group(1).lstrip("v")
                if actual_pin != expected_pin:
                    errors.append(f"stable-channel pin {actual_pin} != {expected_pin}")
        elif "- **Install path:" in text:
            errors.append(f"missing required stable-channel fallback pin ({expected_pin})")
    return errors


def rewrite(
    text: str,
    target: str,
    exempt: frozenset[str] = frozenset(),
    channel_contexts: list[tuple[re.Pattern[str], str]] | None = None,
) -> tuple[str, int]:
    count = 0
    contexts = channel_contexts or []
    out_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        pinned_spans: list[tuple[int, int]] = []
        for pattern, expected_pin in contexts:
            for cm in pattern.finditer(line):
                if cm.group(1).lstrip("v") == expected_pin:
                    pinned_spans.append(cm.span(1))

        def repl(match: re.Match[str]) -> str:
            nonlocal count
            if any(match.start() >= s and match.end() <= e for s, e in pinned_spans):
                return match.group(0)
            numeric = match.group(0).lstrip("v")
            if numeric in exempt:
                return match.group(0)
            count += 1
            prefix = "v" if match.group(0).startswith("v") else ""
            return f"{prefix}{target}"

        out_lines.append(VERSION_RE.sub(repl, line))
    return "".join(out_lines), count


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
        vers = versions_in(
            text,
            frozenset(EXEMPT.get(rel, set())),
            CHANNEL_CONTEXTS.get(rel),
        )
        found.append((rel, vers))
    if missing:
        print("missing version surfaces: " + ", ".join(missing), file=sys.stderr)
        raise SystemExit(2)
    return found


def check_ceremony(root: Path, target: str) -> bool:
    """Ceremony checks the flat version scan cannot express.

    Fails when the changelog still marks the target version `[Unreleased]`
    (the v9.1.5 tag shipped with a draft heading) or lacks a dated
    `## [target]` section.
    """
    path = root / CHANGELOG
    if not path.exists():
        print(f"  {CHANGELOG:<42} MISSING: cannot verify the release ceremony")
        return False
    text = path.read_text(encoding="utf-8")
    ok = True
    base_target = target[:-2] if target.endswith(".0") else target
    accepted = {target, base_target, f"{base_target}.0"}
    unreleased = UNRELEASED_RE.search(text)
    if unreleased and unreleased.group(1) in accepted:
        print(f"  {CHANGELOG:<42} DRIFT: {target} is still under [Unreleased]")
        ok = False
    section: str | None = None
    for line in text.splitlines():
        match = RELEASED_HEADING_RE.match(line)
        if match and match.group(1) in accepted:
            section = line
            break
    if section is None:
        print(f"  {CHANGELOG:<42} DRIFT: no '## [{target}]' section")
        ok = False
    elif not DATE_RE.search(section):
        print(f"  {CHANGELOG:<42} DRIFT: '## [{target}]' has no date")
        ok = False
    return ok


def check(root: Path, expected: str | None) -> int:
    target = expected or workspace_version(root)
    base_target = target[:-2] if target.endswith(".0") else target
    accepted = {target, base_target, f"{base_target}.0"}
    rows = scan(root)
    drift = False
    print(f"version truth — expected {target}")
    for rel, versions in rows:
        bad = sorted({v for v in versions if v not in accepted})
        channel_errors = check_channel_contexts(rel, (root / rel).read_text(encoding="utf-8"))
        if bad or channel_errors:
            drift = True
            details = bad + channel_errors
            status = f"DRIFT: {', '.join(details)}"
        elif not versions:
            status = "no reference found"
        else:
            status = "ok"
        print(f"  {rel:<42} {len(versions):>2} reference(s)  {status}")
    ceremony_ok = check_ceremony(root, target)
    if drift or not ceremony_ok:
        print(f"\nREFUSING: version truth is not green for {target}")
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
        edited, count = rewrite(
            original,
            target,
            frozenset(EXEMPT.get(rel, set())),
            CHANNEL_CONTEXTS.get(rel),
        )
        total += count
        if count == 0:
            print(f"  {rel:<42}  0 reference(s) — inspect this surface")
            continue
        verb = "would update" if dry_run else "updated"
        print(f"  {rel:<42} {count:>2} reference(s)  {verb}")
        if not dry_run:
            path.write_text(edited, encoding="utf-8")
            after = versions_in(
                path.read_text(encoding="utf-8"),
                frozenset(EXEMPT.get(rel, set())),
                CHANNEL_CONTEXTS.get(rel),
            )
            if any(v != target for v in after):
                raise SystemExit(f"{rel} did not converge on {target}")
    print(
        f"\n{'would replace' if dry_run else 'replaced'} {total} references → {target}"
    )
    if not dry_run:
        print("next: cargo check (refresh Cargo.lock), then run the release gates")
    return 0


def open_changelog(root: Path, target: str, dry_run: bool) -> int:
    """Replace the `[Unreleased]` heading with a dated `[target]` heading.

    Release morning used to hand-edit this heading, and forgetting it fails
    CI's version-truth gate (the v9.1.5 lesson) — after the tag-triggered
    workflow has already started. Theme text after the standard
    `— X.Y.Z in progress (date)` clause is preserved.
    """
    if not SEMVER_RE.fullmatch(target):
        raise SystemExit(f"not a semantic version: {target!r}")
    path = root / CHANGELOG
    text = path.read_text(encoding="utf-8")
    unreleased = re.search(r"(?m)^## \[Unreleased\][^\n]*$", text)
    if unreleased is None:
        if re.search(
            rf"(?m)^## \[{re.escape(target)}\][^\n]*\d{{4}}-\d{{2}}-\d{{2}}", text
        ):
            print(f"  {CHANGELOG:<42} [{target}] already open")
            return 0
        print(
            f"  {CHANGELOG:<42} MISSING: no [Unreleased] heading to open",
            file=sys.stderr,
        )
        return 1
    tail = unreleased.group(0)[len("## [Unreleased]") :]
    stripped = re.sub(
        r"^\s*—\s*\d+\.\d+\.\d+\s+in progress\s*\(\d{4}-\d{2}-\d{2}\)\s*", "", tail
    ).strip()
    heading = f"## [{target}] — {date.today().isoformat()}"
    if stripped:
        heading += f" {stripped}"
    if dry_run:
        print(f"  {CHANGELOG:<42} would open: {heading}")
        return 0
    text = text[: unreleased.start()] + heading + text[unreleased.end() :]
    path.write_text(text, encoding="utf-8")
    print(f"  {CHANGELOG:<42} opened: {heading}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report drift, write nothing")
    mode.add_argument("--set", metavar="VERSION", help="rewrite every surface")
    mode.add_argument(
        "--open-changelog",
        metavar="VERSION",
        help="turn the [Unreleased] heading into a dated [VERSION] heading",
    )
    parser.add_argument("--version", default=None, help="expected version for --check")
    parser.add_argument(
        "--dry-run", action="store_true", help="with --set/--open-changelog: print only"
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="repository root (default: this script's parent repo)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.check:
        return check(root, args.version)
    if args.open_changelog:
        return open_changelog(root, args.open_changelog, args.dry_run)
    return set_version(root, args.set, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
