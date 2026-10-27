#!/usr/bin/env python3
"""Fail-closed channel policy for native WhiteMagic release promotion."""
from __future__ import annotations

import argparse
import re


VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$")


def npm_selector(version: str, prerelease: bool) -> str:
    """Keep the open-alpha Gen3 line off stable selectors, even if misflagged."""
    match = VERSION_RE.fullmatch(version)
    if not match:
        raise ValueError("version must be a full semantic version")
    if int(match.group(1)) == 9 and not prerelease and "-" not in version:
        return "latest"
    return "next"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("release_prerelease", choices=("true", "false"))
    args = parser.parse_args()
    prerelease = args.release_prerelease == "true"
    try:
        selector = npm_selector(args.version, prerelease)
    except ValueError as exc:
        parser.error(str(exc))
    print(selector)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
