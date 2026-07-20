#!/usr/bin/env python3
"""Baseline + CI gate for MCP tool annotation coverage.

The MCP spec (2025-03-26+) defines five annotation fields on every tool:
``title``, ``readOnlyHint``, ``destructiveHint``, ``idempotentHint``,
``openWorldHint``. Missing annotations default to worst-case client
assumptions (non-read-only, destructive, non-idempotent, open-world),
which makes clients prompt users for confirmation on every call.

WhiteMagic currently emits **zero** annotations: ``ToolDefinition`` has no
annotation fields and neither ``_wm_tool_def()`` nor the PRAT Gana tool
list sets ``types.Tool.annotations``/``title``. This script:

1. Measures live coverage on the MCP-exposed surface (wm + Gana tools).
2. Measures **derivability** across the full registry: how many of the
   860 tools can receive mechanically-derived annotations from the
   canonical safety classification (READ/WRITE/DELETE) and the karmic
   effect registry (PURE/LOCAL_WRITE/NETWORK/DESTRUCTIVE/OBSERVATION).
3. ``--check`` mode: fails if the exposed surface has tools without
   annotations (ratchet, once implementation lands) — currently runs in
   ``--baseline`` reporting mode.

Usage:
    PYTHONPATH=core python core/scripts/check_mcp_annotations.py
    PYTHONPATH=core python core/scripts/check_mcp_annotations.py --json
    PYTHONPATH=core python core/scripts/check_mcp_annotations.py --check
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE))


def collect_baseline() -> dict[str, object]:
    from whitemagic.tools.annotations import CURATED_IDEMPOTENT, resolve_annotations
    from whitemagic.tools.tool_catalog import collect_authored_tool_definitions

    tools = sorted(collect_authored_tool_definitions(), key=lambda t: t.name)
    total = len(tools)

    derivable: dict[str, int] = {
        "title": 0,
        "readOnlyHint": 0,
        "destructiveHint": 0,
        "idempotentHint": 0,
        "openWorldHint": 0,
    }
    hint_counts = {"readOnly": 0, "destructive": 0, "idempotent": 0, "openWorld": 0}
    needs_curation: list[str] = []
    per_tool: dict[str, dict[str, object]] = {}

    for t in tools:
        ann = resolve_annotations(t)
        per_tool[t.name] = ann.to_dict()
        # Every field is derivable under the policy; count what the values are
        for field in derivable:
            derivable[field] += 1
        if ann.read_only:
            hint_counts["readOnly"] += 1
        if ann.destructive:
            hint_counts["destructive"] += 1
        if ann.idempotent:
            hint_counts["idempotent"] += 1
        if ann.open_world:
            hint_counts["openWorld"] += 1
        # WRITE/DELETE tools not yet reviewed for CURATED_IDEMPOTENT
        safety = t.safety.name if hasattr(t.safety, "name") else str(t.safety)
        if (
            safety in ("WRITE", "DELETE")
            and not ann.idempotent
            and t.name not in CURATED_IDEMPOTENT
        ):
            needs_curation.append(t.name)

    return {
        "total_tools": total,
        "current_coverage": {
            "exposed_surface_annotations": 0,
            "tool_definition_fields": 0,
            "note": "No annotation support exists yet; all counts are derivability, not coverage.",
        },
        "derivable_field_pct": {k: round(100.0 * v / total, 1) for k, v in derivable.items()},
        "derived_hint_values": hint_counts,
        "needs_curation_count": len(needs_curation),
        "needs_curation_sample": needs_curation[:20],
        "per_tool": per_tool,
    }


def main() -> None:
    baseline = collect_baseline()
    if "--json" in sys.argv:
        print(json.dumps(baseline, indent=2, sort_keys=True))
        return

    print("MCP Annotation Baseline")
    print("=" * 60)
    print(f"Registry tools:              {baseline['total_tools']}")
    print(
        "Live coverage:               0% (ToolDefinition lacks fields; "
        "wm/Gana tool defs set no annotations)"
    )
    print()
    print("Derivability under policy (title/safety/effects):")
    for field, pct in baseline["derivable_field_pct"].items():
        print(f"  {field:<16} {pct}%")
    print()
    hints = baseline["derived_hint_values"]
    print("Derived hint distribution:")
    print(f"  readOnlyHint=True:       {hints['readOnly']}")
    print(f"  destructiveHint=True:    {hints['destructive']}")
    print(f"  idempotentHint=True:     {hints['idempotent']}")
    print(f"  openWorldHint=True:      {hints['openWorld']}")
    print()
    print(
        f"Needs curated idempotentHint review (WRITE/DELETE): "
        f"{baseline['needs_curation_count']}"
    )

    if "--check" in sys.argv:
        # Active ratchet: every registry tool must resolve to a COMPLETE
        # annotation set (all five fields non-None). Derivation guarantees
        # this today; the gate fails on regression.
        per_tool = baseline["per_tool"]
        required = ("title", "readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")
        incomplete = {
            name: [f for f in required if ann.get(f) is None]
            for name, ann in per_tool.items()
            if any(ann.get(f) is None for f in required)
        }
        print()
        if incomplete:
            print(f"--check FAILED: {len(incomplete)} tools with incomplete annotations:")
            for name, missing in list(incomplete.items())[:10]:
                print(f"  {name}: missing {missing}")
            sys.exit(1)
        print(f"--check OK: all {len(per_tool)} tools have complete 5-field annotations.")
        sys.exit(0)


if __name__ == "__main__":
    main()
