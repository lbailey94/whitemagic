#!/usr/bin/env python3
"""scripts/generate_mcp_registry.py — Auto-generate mcp-registry.json from dispatch table.

Fixes F-24: the old mcp-registry.json had a hardcoded tool count that drifted
from the actual DISPATCH_TABLE size. This script generates the authoritative count
at build/commit time.

Usage:
    python3 scripts/generate_mcp_registry.py           # Update core/mcp-registry.json
    python3 scripts/generate_mcp_registry.py --check   # CI mode: fail if file is stale
    python3 scripts/generate_mcp_registry.py --stdout  # Print to stdout only

Add to CI (lint job or packaging job):
    python3 scripts/generate_mcp_registry.py --check
"""

import argparse
import json
import sys
from pathlib import Path


def get_tool_counts() -> dict:
    """Import dispatch table and count tools."""
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    from whitemagic.tools.dispatch_table import DISPATCH_TABLE
    from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY
    from whitemagic.tools.dispatch_intelligence import DISPATCH_INTELLIGENCE
    from whitemagic.tools.dispatch_agents import DISPATCH_AGENTS
    from whitemagic.tools.dispatch_security import DISPATCH_SECURITY

    return {
        "total": len(DISPATCH_TABLE),
        "by_domain": {
            "memory": len(DISPATCH_MEMORY),
            "intelligence": len(DISPATCH_INTELLIGENCE),
            "agents": len(DISPATCH_AGENTS),
            "security": len(DISPATCH_SECURITY),
            "operational": len(DISPATCH_TABLE)
            - len(DISPATCH_MEMORY)
            - len(DISPATCH_INTELLIGENCE)
            - len(DISPATCH_AGENTS)
            - len(DISPATCH_SECURITY),
        },
    }


def build_registry(counts: dict) -> dict:
    """Build the full registry JSON structure."""
    return {
        "_generated_by": "scripts/generate_mcp_registry.py",
        "_note": "Auto-generated — do not edit manually. Run: python3 scripts/generate_mcp_registry.py",
        "gana_tools": 28,
        "nested_tools": counts["total"],
        "tool_domains": counts["by_domain"],
        "modes": {
            "prat": {
                "description": "PRAT mode: 28 Gana meta-tools (recommended for Claude Desktop)",
                "tool_count": 28,
                "env": "WM_MCP_PRAT=1",
            },
            "flat": {
                "description": "Flat mode: all individual tools exposed directly",
                "tool_count": counts["total"],
                "env": "WM_MCP_PRAT=0",
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mcp-registry.json")
    parser.add_argument(
        "--check", action="store_true", help="Fail if file is stale (CI mode)"
    )
    parser.add_argument(
        "--stdout", action="store_true", help="Print to stdout instead of writing file"
    )
    args = parser.parse_args()

    registry_path = Path(__file__).resolve().parent.parent / "mcp-registry.json"

    counts = get_tool_counts()
    registry = build_registry(counts)
    registry_json = json.dumps(registry, indent=2) + "\n"

    if args.stdout:
        print(registry_json)
        return

    if args.check:
        if registry_path.exists():
            existing = registry_path.read_text()
            if existing == registry_json:
                print(f"✅ mcp-registry.json is up to date ({counts['total']} tools)")
                return
            else:
                print(
                    "❌ mcp-registry.json is STALE — run: python3 scripts/generate_mcp_registry.py"
                )
                print(f"   Expected nested_tools: {counts['total']}")
                sys.exit(1)
        else:
            print(
                "❌ mcp-registry.json does not exist — run: python3 scripts/generate_mcp_registry.py"
            )
            sys.exit(1)

    registry_path.write_text(registry_json)
    print(f"✅ Wrote {registry_path} ({counts['total']} total tools)")
    print(f"   Domains: {counts['by_domain']}")


if __name__ == "__main__":
    main()
