#!/usr/bin/env python3
"""Sync stub_allowlist.json from STUB_REGISTRY.md.

Parses the Active Stubs table in STUB_REGISTRY.md and generates
stub_allowlist.json so that check_stubs.py can skip allowlisted stubs.

Usage:
    python core/scripts/sync_stub_registry.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_MD = REPO_ROOT / "STUB_REGISTRY.md"
ALLOWLIST_JSON = REPO_ROOT / "core" / "scripts" / "stub_allowlist.json"


def parse_registry(md_path: Path) -> list[str]:
    """Parse the Active Stubs table from STUB_REGISTRY.md."""
    if not md_path.exists():
        return []

    content = md_path.read_text(encoding="utf-8")

    # Find the Active Stubs section
    active_match = re.search(
        r"## Active Stubs\s*\n(.*?)(?=\n## )",
        content,
        re.DOTALL,
    )
    if not active_match:
        return []

    table_text = active_match.group(1)

    # Parse table rows: | module | :line:func | reason | date | added |
    entries = []
    for line in table_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line or "Module" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        # parts[0] is empty (before first |), parts[-1] is empty (after last |)
        if len(parts) < 4:
            continue
        module = parts[1].strip("`")
        location = parts[2].strip("`")
        # location is like :92:_create_missing_dep_command
        # Build the allowlist key: core/whitemagic/<module>:<line>:<func>
        # module is like cli/lazy_groups.py
        key = f"core/whitemagic/{module}{location}"
        entries.append(key)

    return sorted(entries)


def main() -> int:
    if not REGISTRY_MD.exists():
        print(f"ERROR: {REGISTRY_MD} not found")
        return 1

    entries = parse_registry(REGISTRY_MD)

    ALLOWLIST_JSON.write_text(
        json.dumps(entries, indent=2) + "\n" if entries else "[]\n",
        encoding="utf-8",
    )

    print(f"Synced {len(entries)} stub entries to {ALLOWLIST_JSON.name}")
    for entry in entries:
        print(f"  {entry}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
