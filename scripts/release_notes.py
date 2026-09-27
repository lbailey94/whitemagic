#!/usr/bin/env python3
"""Generate the GitHub release body for a tagged WhiteMagic release.

The release page is an onboarding surface: someone arriving from a package
registry or a search result should see what changed, how to install, and
which platforms are gated — without leaving GitHub (2026-09-27 external
review: v9.2.8's body was a benchmark stub).

Usage:
    python3 scripts/release_notes.py --version 9.2.9 --out release-notes.md

Exit codes: 0 written, 2 usage/input error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

INSTALL = """curl -fsSL https://www.whitemagic.dev/install.sh | sh"""

CHANNELS = (
    "Or: `npx whitemagic-mcp serve` (npm) · `cargo install whitemagic` "
    "(crates.io) · `docker run -i lbailey94/whitemagic:9 serve` (Docker Hub)."
)

PLATFORMS = (
    "Linux x86-64, Linux arm64, and macOS arm64 are install-gated "
    "(checksum-verified installers). macOS x86_64 and Windows x86_64 binaries "
    "are published in every release but their install paths are not gated yet."
)

CHANGELOG_URL = "https://github.com/lbailey94/whitemagic/blob/main/CHANGELOG.md"


def extract_section(changelog: str, version: str) -> str | None:
    """Return the `## [<version>]` section body (without the heading)."""
    lines = changelog.splitlines()
    start = None
    pattern = re.compile(rf"^## \[{re.escape(version)}\]")
    for i, line in enumerate(lines):
        if pattern.match(line):
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## ["):
            end = j
            break
    body = "\n".join(lines[start:end]).strip("\n")
    return body or None


def render(version: str, section: str) -> str:
    return f"""# WhiteMagic {version}

Local-first memory and continuity for MCP agents. Full history:
[CHANGELOG.md]({CHANGELOG_URL}).

## Install

```bash
{INSTALL}
```

{CHANNELS}

## Platforms

{PLATFORMS}

## What changed in {version}

{section}

---

Release assets are checksummed: verify with `sha256sum -c` (Linux/macOS) or
the matching `.sha256` file, then move the binary to `~/.local/bin/wm`.
After installing: `wm grimoire` proves the environment, `wm connect --write`
wires your MCP clients, and `wm quickstart` is the optional two-process
continuity demo.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="release version, e.g. 9.2.9 or v9.2.9")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="path to CHANGELOG.md")
    parser.add_argument("--out", help="write to this file (default: stdout)")
    args = parser.parse_args()

    version = args.version.lstrip("v")
    changelog_path = Path(args.changelog)
    if not changelog_path.is_file():
        print(f"changelog not found: {changelog_path}", file=sys.stderr)
        return 2
    section = extract_section(changelog_path.read_text(encoding="utf-8"), version)
    if section is None:
        print(f"no [{version}] section in {changelog_path}", file=sys.stderr)
        return 2

    notes = render(version, section)
    if args.out:
        Path(args.out).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
