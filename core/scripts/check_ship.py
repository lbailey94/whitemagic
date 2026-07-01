"""Ship surface validation script for make check-ship."""

import json
import sys
from whitemagic.tools.unified_api import call_tool

# Directories excluded by MANIFEST.in (not part of shipping surface)
EXCLUDED_PREFIXES = (
    "_aria/",
    "_memories/",
    "archives/",
    "artifacts/",
    "campaigns",
    "monte_carlo_output/",
    "scripts/",
    "tests/adhoc/",
    ".mypy_cache/",
    ".pytest_cache/",
    "__pycache__/",
)


def is_excluded(path: str) -> bool:
    """Check if a path is in an excluded directory."""
    return path.startswith(EXCLUDED_PREFIXES) or "/__pycache__/" in path


result = call_tool("ship.check")
if result.get("status") != "success":
    print("ship.check failed:", result.get("error", "unknown error"))
    sys.exit(1)

details = result.get("details", {})

# Filter issues to only include ship-reachable paths
filtered_issues = []
for issue in details.get("issues", []):
    hits = issue.get("hits", [])
    filtered_hits = [h for h in hits if not is_excluded(h[0])]
    if filtered_hits:
        filtered_issues.append({"kind": issue["kind"], "hits": filtered_hits})

output = {
    "checks": details.get("checks", 0),
    "issues": filtered_issues,
    "ok": len(filtered_issues) == 0,
    "notes": [
        "This is a heuristic scan; treat findings as prompts for manual review.",
        "Excluded directories filtered: _aria/, campaigns/, scripts/, tests/adhoc/, cache dirs",
    ],
    "project_root": details.get("project_root", ""),
}
print(json.dumps(output, indent=2, sort_keys=True))

if not output["ok"]:
    print("\n⚠ Ship check found issues in ship-reachable files (see above)")
    sys.exit(1)
else:
    print("\n✓ Ship surface is clean")
