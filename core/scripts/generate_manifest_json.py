#!/usr/bin/env python3
"""Generate /api/manifest.json for AI-primary site architecture.

Introspects the live WhiteMagic tool surface and produces a machine-readable
manifest that agents can discover and consume.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from whitemagic.tools.tool_surface import (
    get_callable_tool_definitions,
    get_gana_metadata,
    get_surface_counts,
)


def generate_manifest() -> dict:
    definitions = get_callable_tool_definitions()
    gana_meta = get_gana_metadata()
    counts = get_surface_counts()

    tools = []
    for tool in definitions:
        tools.append(
            {
                "name": tool.name,
                "description": tool.description,
                "category": str(tool.category.value),
                "safety": str(tool.safety.value),
                "stability": str(tool.stability.value),
                "input_schema": tool.input_schema,
                "gana": tool.gana,
                "garden": tool.garden,
                "quadrant": tool.quadrant,
                "element": tool.element,
                "permissions": list(tool.permissions),
            }
        )

    ganas = {}
    for name, (desc, nested) in gana_meta.items():
        ganas[name] = {"description": desc, "tools": nested}

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": {
            "name": "WhiteMagic",
            "version": "22.2.0",
            "url": "https://whitemagic.dev",
            "repository": "https://github.com/whitemagic-ai/whitemagic",
            "license": "MIT",
        },
        "counts": {
            "authored_tools": counts["authored_tools"],
            "callable_tools": counts["callable_tools"],
            "gana_tools": counts["gana_tools"],
            "dispatch_tools": counts["dispatch_tools"],
            "nested_unique_tools": counts["nested_unique_tools"],
            "by_stability": counts["by_stability"],
        },
        "ganas": ganas,
        "tools": tools,
    }


def main() -> int:
    manifest = generate_manifest()
    output_path = Path("apps/site/public/api/manifest.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Manifest written to {output_path}")
    print(f"Tools: {manifest['counts']['callable_tools']}")
    print(f"Ganas: {manifest['counts']['gana_tools']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
