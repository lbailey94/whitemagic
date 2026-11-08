#!/usr/bin/env python3
"""Fail-closed channel policy for native WhiteMagic release promotion."""
from __future__ import annotations

import argparse
import re


VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$")
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")


def semver_key(version: str) -> tuple[tuple[int, int, int], bool, tuple[tuple[int, int | str], ...]]:
    match = SEMVER_RE.fullmatch(version.removeprefix("v"))
    if not match:
        raise ValueError("version must be a full semantic version")
    core = tuple(int(match.group(i)) for i in range(1, 4))
    prerelease = match.group(4)
    identifiers = tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in (prerelease.split(".") if prerelease else ())
    )
    # A stable version sorts after every prerelease of the same core.
    return core, prerelease is None, identifiers


def npm_selector(version: str, prerelease: bool, current: str | None = None) -> str:
    """Channel selector policy for WhiteMagic release promotion.

    Stable production lines (Gen2 v9.x, Gen3 living substrate v11.x+) target
    'latest' unless flagged as prerelease or superseded by a newer version.
    Gen3 experimental preview line (v10.x) targets 'next'.
    """
    match = VERSION_RE.fullmatch(version)
    if not match:
        raise ValueError("version must be a full semantic version")
    major = int(match.group(1))
    if (major == 9 or major >= 11) and not prerelease and "-" not in version:
        selector = "latest"
    else:
        selector = "next"
    if current and current != "<none>" and semver_key(version) < semver_key(current):
        return "skip"
    return selector


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("release_prerelease", choices=("true", "false"))
    parser.add_argument("current_version", nargs="?")
    args = parser.parse_args()
    prerelease = args.release_prerelease == "true"
    try:
        selector = npm_selector(args.version, prerelease, args.current_version)
    except ValueError as exc:
        parser.error(str(exc))
    print(selector)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
