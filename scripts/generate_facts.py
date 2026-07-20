#!/usr/bin/env python3
"""Generate public facts for WhiteMagic from canonical sources.

Derives all public-facing counts (callable tools, dispatch entries,
authored definitions, stable tools, Ganas, galaxies, etc.) from the
actual codebase rather than manually maintained numbers.

Usage:
    python3 scripts/generate_facts.py           # Print facts as JSON
    python3 scripts/generate_facts.py --check    # Exit 1 if facts differ from docs
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure core is importable
CORE = Path(__file__).parent.parent / "core"
sys.path.insert(0, str(CORE))


def generate_facts() -> dict:
    """Generate facts from canonical sources."""
    import os
    os.environ.setdefault("WM_STATE_ROOT", "/tmp/wm_facts_gen")
    os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
    os.environ.setdefault("WM_SILENT_INIT", "1")

    from whitemagic.tools.registry import TOOL_REGISTRY, get_authored_tools
    from whitemagic.tools.tool_catalog import GANA_NAMES
    from whitemagic.tools.tool_types import ToolStability, ToolSafety
    from whitemagic.tools.dispatch_table import DISPATCH_TABLE
    from whitemagic.tools.stable_surface import STABLE_TOOL_NAMES
    from whitemagic.core.memory.galaxy_taxonomy import GALAXY_ORDER, GALAXY_ZONES, GALAXY_DEPRECATED
    from whitemagic.tools.prat_mappings import TOOL_TO_GANA

    dispatch_names = set(DISPATCH_TABLE.keys())
    registry_names = {td.name for td in TOOL_REGISTRY}
    authored_names = {td.name for td in get_authored_tools()}
    gana_set = set(GANA_NAMES)
    stable_names = {td.name for td in TOOL_REGISTRY if td.stability == ToolStability.STABLE}

    safety_counts: dict[str, int] = {}
    for td in TOOL_REGISTRY:
        safety_counts[td.safety.value] = safety_counts.get(td.safety.value, 0) + 1

    stability_counts: dict[str, int] = {}
    for td in TOOL_REGISTRY:
        stability_counts[td.stability.value] = stability_counts.get(td.stability.value, 0) + 1

    zone_counts: dict[str, int] = {}
    for g in GALAXY_ORDER:
        z = GALAXY_ZONES[g]
        zone_counts[z] = zone_counts.get(z, 0) + 1

    return {
        "version": "25.0.1",
        "callable_tools": len(TOOL_REGISTRY),
        "dispatch_entries": len(dispatch_names),
        "authored_definitions": len(authored_names),
        "synthesized_definitions": len(registry_names - authored_names - gana_set),
        "gana_meta_tools": len(GANA_NAMES),
        "stable_tools": len(stable_names),
        "stable_promoted": len(STABLE_TOOL_NAMES),
        "canonical_galaxies": len(GALAXY_ORDER),
        "deprecated_galaxy_aliases": len(GALAXY_DEPRECATED),
        "prat_mappings": len(TOOL_TO_GANA),
        "safety_breakdown": safety_counts,
        "stability_breakdown": stability_counts,
        "galaxy_zone_breakdown": zone_counts,
        "unauthored_tools": len(registry_names - authored_names - gana_set),
        "unmapped_dispatch": len(dispatch_names - registry_names - gana_set),
    }


def main() -> None:
    check_mode = "--check" in sys.argv
    write_mode = "--write" in sys.argv
    facts = generate_facts()
    facts_json = json.dumps(facts, indent=2, sort_keys=True)

    if write_mode:
        facts_file = CORE.parent / "docs" / "PROJECT_STATE.md"
        start_marker = "<!-- GENERATED_FACTS_START -->"
        end_marker = "<!-- GENERATED_FACTS_END -->"
        if not facts_file.exists():
            print(f"ERROR: {facts_file} does not exist.")
            sys.exit(1)
        content = facts_file.read_text()
        if start_marker not in content or end_marker not in content:
            print(f"ERROR: markers not found in {facts_file}.")
            sys.exit(1)
        before, _, rest = content.partition(start_marker)
        _, _, after = rest.partition(end_marker)
        updated = f"{before}{start_marker}\n```json\n{facts_json}\n```\n{end_marker}{after}"
        facts_file.write_text(updated)
        print(f"Updated facts block in {facts_file}")
        sys.exit(0)

    if check_mode:
        facts_file = CORE.parent / "docs" / "PROJECT_STATE.md"
        if facts_file.exists():
            existing = facts_file.read_text()
            if facts_json not in existing:
                print(f"ERROR: Facts in {facts_file} are stale.")
                print(f"Current facts:\n{facts_json}")
                sys.exit(1)
            print("Facts are up to date.")
            sys.exit(0)
        else:
            print(f"ERROR: {facts_file} does not exist. Run without --check first.")
            sys.exit(1)
    else:
        print(facts_json)


if __name__ == "__main__":
    main()
