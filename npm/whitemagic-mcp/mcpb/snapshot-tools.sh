#!/usr/bin/env bash
# Regenerate mcpb/tools.snapshot.json from the released binary.
# Usage: npm/whitemagic-mcp/mcpb/snapshot-tools.sh [wm-version]
# The snapshot feeds the Smithery variant manifest; sanitizes the runtime
# mode/scope suffix so no local paths appear in the published listing.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
ver="${1:-$(python3 -c "import json;print(json.load(open('$here/../package.json'))['version'])")}"
bin="${HOME}/.cache/whitemagic/bin/v${ver}/wm-linux-x86_64-musl"
store="$(mktemp -d)"
trap 'rm -rf "$store"' EXIT
if [ ! -x "$bin" ]; then
  echo "binary not cached: $bin — run npx whitemagic-mcp --version first" >&2
  exit 1
fi
printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"snapshot","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | "$bin" serve --profile curated --store "$store" 2>/dev/null > "$store/out.jsonl"
python3 - "$store/out.jsonl" "$here/tools.snapshot.json" <<'PY'
import json, re, sys
tools = None
for line in open(sys.argv[1]):
    try:
        d = json.loads(line)
    except Exception:
        continue
    if d.get("id") == 2:
        tools = d["result"]["tools"]
if not tools:
    raise SystemExit("no tools/list response")
clean = []
for t in tools:
    desc = re.sub(r"\s+(Mode|Scope): [^.]*\.", "", t.get("description", "")).strip()
    clean.append({"name": t["name"], "description": desc, "inputSchema": t["inputSchema"]})
json.dump(clean, open(sys.argv[2], "w"), indent=2)
open(sys.argv[2], "a").write("\n")
print(f"snapshot: {len(clean)} tools -> {sys.argv[2]}")
PY
