#!/usr/bin/env bash
# Build the dynamic MCPB distribution bundle for whitemagic-mcp.
# Usage: npm/whitemagic-mcp/mcpb/build.sh
# Output: npm/whitemagic-mcp/dist/server.mcpb (zip per MCPB spec 0.3).
# WM_MCPB_OUTPUT_DIR selects an isolated output directory; WM_MCPB_PACKER=zip
# uses the offline zip path even when the optional mcpb CLI is installed.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
pkg="$(cd "$here/.." && pwd)"
out="${WM_MCPB_OUTPUT_DIR:-$pkg/dist}"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

pkgver="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$pkg/package.json")"
manver="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$here/manifest.json")"
if [ "$pkgver" != "$manver" ]; then
  echo "version mismatch: package.json=$pkgver manifest.json=$manver" >&2
  exit 1
fi

packer="${WM_MCPB_PACKER:-auto}"
case "$packer" in
  auto|zip|mcpb) ;;
  *) echo "unsupported MCPB packer: $packer (use auto, zip or mcpb)" >&2; exit 1 ;;
esac

mkdir -p "$out" "$stage/bin"
out="$(cd "$out" && pwd)"
cp "$here/manifest.json" "$stage/manifest.json"
# The launcher imports lib.mjs; keep its complete owning bin tree together,
# exactly as the npm package does, rather than copying only the entry point.
cp -R "$pkg/bin/." "$stage/bin/"
cp "$pkg/package.json" "$stage/package.json"
cp "$pkg/LICENSE" "$stage/LICENSE"
cp "$pkg/README.md" "$stage/README.md"

# The retained tools.snapshot.json is historical, unqualified full-profile
# metadata. It is not bound to this release/profile and must not be injected
# into the lean dynamic bundle or left behind for a wildcard upload. The tag
# workflow does not require a Smithery static-variant asset. Re-enable that
# variant only after a separately qualified version/profile-bound snapshot.
rm -f "$out/server-smithery.mcpb" "$out/server.mcpb"
if [ "$packer" = mcpb ] || { [ "$packer" = auto ] && command -v mcpb >/dev/null 2>&1; }; then
  mcpb pack "$stage" "$out/server.mcpb" >/dev/null
else
  (cd "$stage" && zip -q -r "$out/server.mcpb" . -x '.*')
fi

echo "Smithery static variant omitted: no qualified version/profile-bound tool snapshot."
bytes="$(wc -c < "$out/server.mcpb" | tr -d '[:space:]')"
echo "built $out/server.mcpb ($bytes bytes, v$pkgver)"
