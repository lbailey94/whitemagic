#!/usr/bin/env bash
# Build the Smithery/MCPB distribution bundle for whitemagic-mcp.
# Usage: npm/whitemagic-mcp/mcpb/build.sh
# Output: npm/whitemagic-mcp/dist/server.mcpb (zip per MCPB spec 0.3).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
pkg="$(cd "$here/.." && pwd)"
out="$pkg/dist"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

pkgver="$(python3 -c "import json;print(json.load(open('$pkg/package.json'))['version'])")"
manver="$(python3 -c "import json;print(json.load(open('$here/manifest.json'))['version'])")"
if [ "$pkgver" != "$manver" ]; then
  echo "version mismatch: package.json=$pkgver manifest.json=$manver" >&2
  exit 1
fi

mkdir -p "$out" "$stage/bin"
cp "$here/manifest.json" "$stage/manifest.json"
cp "$pkg/bin/cli.mjs" "$stage/bin/cli.mjs"
cp "$pkg/package.json" "$stage/package.json"
cp "$pkg/LICENSE" "$stage/LICENSE"
cp "$pkg/README.md" "$stage/README.md"

rm -f "$out/server.mcpb"
if command -v mcpb >/dev/null 2>&1; then
  mcpb pack "$stage" "$out/server.mcpb" >/dev/null
elif npx -y @anthropic-ai/mcpb pack "$stage" "$out/server.mcpb" >/dev/null 2>&1; then
  :
else
  echo "mcpb CLI unavailable; falling back to zip (valid per MCPB spec 0.3)" >&2
  (cd "$stage" && zip -q -r "$out/server.mcpb" . -x '.*')
fi
# Smithery registry variant: declares tool schemas in the manifest.
# Upstream CLI/registry bug (arcadeai-labs/smithery-cli#787): an MCPB bundle
# with no `tools` is rejected with 400 "No values to set", and tools without
# `inputSchema` are rejected as invalid — so we hand-pack a variant whose
# manifest carries the released schemas (tools.snapshot.json) and publish
# that one. Refresh the snapshot each release:
#   tools/list against the released binary -> mcpb/tools.snapshot.json
if [ -f "$here/tools.snapshot.json" ]; then
  python3 - "$stage" "$here/tools.snapshot.json" <<'PY'
import json, sys
stage, snap = sys.argv[1], sys.argv[2]
m = json.load(open(f"{stage}/manifest.json"))
m["tools"] = json.load(open(snap))
m["prompts"] = [
    {
        "name": "session_continuity",
        "description": "Recall project context, key decisions, and where the previous session left off before starting work.",
        "arguments": [
            {
                "name": "scope",
                "description": "Optional topic or subsystem to focus continuity recall on (e.g. auth, memory, ci).",
                "required": False,
            }
        ],
    },
    {
        "name": "memory_debug",
        "description": "Ground an error or bug investigation in WhiteMagic episodic memory to retrieve prior solutions and test cases.",
        "arguments": [
            {
                "name": "error_or_topic",
                "description": "Error message, stack trace snippet, or topic to search past solutions for.",
                "required": True,
            }
        ],
    },
    {
        "name": "dharma_governance_audit",
        "description": "Review current system governance posture against Ahimsa principles, Landlock boundaries, and recent write audit entries.",
        "arguments": [],
    },
]
json.dump(m, open(f"{stage}/manifest.json", "w"), indent=2)
PY
  rm -f "$out/server-smithery.mcpb"
  (cd "$stage" && zip -q -r "$out/server-smithery.mcpb" . -x '.*')
  echo "built $out/server-smithery.mcpb ($(stat -c%s "$out/server-smithery.mcpb") bytes, v$pkgver)"
fi

echo "built $out/server.mcpb ($(stat -c%s "$out/server.mcpb") bytes, v$pkgver)"
