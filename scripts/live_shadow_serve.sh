#!/usr/bin/env bash
# Start `wm serve` against the live store with the NLU embedding router in
# shadow mode — every real MCP query accumulates shadow stats, persisted to
# <store>/lmdb/mutable_shadow_stats.json on shutdown.
#
# Prereq: the embedder service must be running:
#   systemctl --user enable --now whitemagic-embedder.service
#
# Usage: scripts/live_shadow_serve.sh [store]
set -euo pipefail

STORE="${1:-$HOME/Desktop/WMdata/live}"

export WM_EMBEDDER_ENDPOINT="${WM_EMBEDDER_ENDPOINT:-http://127.0.0.1:8081}"
export WM_EMBEDDER_MODEL="${WM_EMBEDDER_MODEL:-local}"
export WM_EMBEDDER_DIM="${WM_EMBEDDER_DIM:-384}"
export WM_EMBEDDER_TIMEOUT_MS="${WM_EMBEDDER_TIMEOUT_MS:-120000}"
export WM_DISPATCH_TOOL_RPM="${WM_DISPATCH_TOOL_RPM:-600}"
export WM_DISPATCH_GLOBAL_RPM="${WM_DISPATCH_GLOBAL_RPM:-3000}"
export WM_DISPATCH_BURST="${WM_DISPATCH_BURST:-50}"
export RUST_LOG="${RUST_LOG:-info}"

echo "live shadow serve → store: $STORE  embedder: $WM_EMBEDDER_ENDPOINT (dim $WM_EMBEDDER_DIM)"
echo "dispatch limits: ${WM_DISPATCH_TOOL_RPM} RPM/tool, ${WM_DISPATCH_GLOBAL_RPM} RPM global, burst ${WM_DISPATCH_BURST}"
exec "$(dirname "$0")/../target/debug/wm" serve --store "$STORE"
