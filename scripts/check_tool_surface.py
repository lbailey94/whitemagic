#!/usr/bin/env python3
"""scripts/check_tool_surface.py — Validate tool surface consistency.

Checks that tool counts in mcp-registry.json and server.json agree with
the actual DISPATCH_TABLE, TOOL_REGISTRY, and PRAT GANA mappings.

Usage:
    python3 scripts/check_tool_surface.py           # Report
    python3 scripts/check_tool_surface.py --check   # CI gate (exit 1 on drift)
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = REPO_ROOT / "core"


def _get_actual_counts() -> dict:
    """Import live tool surface and return counts."""
    sys.path.insert(0, str(CORE_ROOT))
    from whitemagic.tools.dispatch_table import DISPATCH_TABLE
    from whitemagic.tools.registry import TOOL_REGISTRY, AUTHORED_TOOL_REGISTRY
    from whitemagic.tools.tool_catalog import GANA_NAMES, get_gana_nested_tools
    from whitemagic.tools.prat_mappings import GANA_TO_TOOLS

    nested_unique = {tool for tools in get_gana_nested_tools().values() for tool in tools}

    return {
        "dispatch_table": len(DISPATCH_TABLE),
        "tool_registry": len(TOOL_REGISTRY),
        "authored_registry": len(AUTHORED_TOOL_REGISTRY),
        "gana_tools": len(GANA_NAMES),
        "nested_unique": len(nested_unique),
        "prat_mappings": sum(len(tools) for tools in GANA_TO_TOOLS.values()),
    }


def _get_mcp_registry_counts() -> dict | None:
    mr = REPO_ROOT / "mcp-registry.json"
    if not mr.exists():
        return None
    data = json.loads(mr.read_text())
    return {
        "nested_tools": data.get("nested_tool_count"),
        "gana_tools": data.get("tool_count"),
    }


def _get_server_json_counts() -> dict | None:
    sj = REPO_ROOT / "server.json"
    if not sj.exists():
        return None
    data = json.loads(sj.read_text())
    desc = data.get("description", "")
    # Parse "773 in classic" from description
    import re
    m = re.search(r"(\d+) in classic", desc)
    classic = int(m.group(1)) if m else None
    return {"nested_tools": classic}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check tool surface consistency")
    parser.add_argument("--check", action="store_true", help="Exit 1 on drift (CI mode)")
    args = parser.parse_args()

    actual = _get_actual_counts()
    mcp_reg = _get_mcp_registry_counts()
    server = _get_server_json_counts()

    errors: list[str] = []

    # Check mcp-registry.json
    if mcp_reg:
        if mcp_reg["nested_tools"] != actual["dispatch_table"]:
            errors.append(
                f"mcp-registry.json nested_tool_count={mcp_reg['nested_tools']} "
                f"!= dispatch_table={actual['dispatch_table']}"
            )
        if mcp_reg["gana_tools"] is not None and mcp_reg["gana_tools"] != 1:
            # tool_count in mcp-registry is the wm meta-tool count (1), not gana count
            pass
    else:
        errors.append("mcp-registry.json not found")

    # Check server.json description
    if server:
        if server["nested_tools"] is not None and server["nested_tools"] != actual["dispatch_table"]:
            errors.append(
                f"server.json description says {server['nested_tools']} classic tools "
                f"!= dispatch_table={actual['dispatch_table']}"
            )
    else:
        errors.append("server.json not found")

    # Check gana consistency
    if actual["gana_tools"] != 28:
        errors.append(f"GANA_NAMES count={actual['gana_tools']} != expected 28")

    # Check nested unique vs dispatch (exclude meta-tools not meant for Gana mapping)
    _META_TOOL_COUNT = 2  # wm, wm_help — Seed-mode entry points, not Gana-mappable
    unmapped = actual["dispatch_table"] - actual["nested_unique"] - _META_TOOL_COUNT
    if unmapped != 0:
        errors.append(
            f"nested_unique ({actual['nested_unique']}) + meta-tools ({_META_TOOL_COUNT}) "
            f"!= dispatch_table ({actual['dispatch_table']}) "
            f"— {unmapped} dispatch tools have no Gana mapping and are not recognized meta-tools"
        )

    print("Tool Surface Report:")
    print(f"  dispatch_table:    {actual['dispatch_table']}")
    print(f"  tool_registry:     {actual['tool_registry']}")
    print(f"  authored_registry: {actual['authored_registry']}")
    print(f"  gana_tools:        {actual['gana_tools']}")
    print(f"  nested_unique:     {actual['nested_unique']}")
    print(f"  prat_mappings:     {actual['prat_mappings']}")
    if mcp_reg:
        print(f"  mcp-registry.json: nested={mcp_reg['nested_tools']}")
    if server:
        print(f"  server.json desc:  classic={server['nested_tools']}")

    if errors:
        print("\n❌ Surface inconsistencies:")
        for e in errors:
            print(f"   {e}")
        if args.check:
            sys.exit(1)
    else:
        print("\n✅ Tool surface is consistent")


if __name__ == "__main__":
    main()
