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
echo "built $out/server.mcpb ($(stat -c%s "$out/server.mcpb") bytes, v$pkgver)"
