#!/usr/bin/env bash
# WMgen3 closure static checks (docs/CLOSURE_TESTS.md §1.1-B/C, §2.1).
#
# Scope: the plastic layer (core adaptive modules) and the process host (the
# harness adapter). The constitution mutation surface may be named only by
# constitution.rs itself and the external authority path (admin.rs).
set -euo pipefail
cd "$(dirname "$0")/.."

fail() { echo "CLOSURE SCAN FAILED: $1" >&2; exit 1; }

echo "[1/3] dependency rule: no Gen2 (wm-*) crate in the Gen3 tree"
for pkg in wm-gen3-core wm-gen3-harness; do
  if cargo tree -p "$pkg" --offline 2>/dev/null | grep -E '(^|[ │├└])wm-(core|memory|dispatch|cognitive|governance|tools|mcp|sangha|substrate|bicameral|simulation|selfmodel|workspace|conformal|polyglot)([ =]|$)' >/dev/null; then
    fail "forbidden wm-* dependency present in $pkg"
  fi
done
echo "      ok"

echo "[2/3] plastic layer / host never reference the constitution mutation surface"
SCAN_FILES=(
  crates/wm-gen3-core/src/adaptive.rs
  crates/wm-gen3-core/src/ops.rs
  crates/wm-gen3-core/src/field.rs
  crates/wm-gen3-core/src/store.rs
  crates/wm-gen3-core/src/journal.rs
  crates/wm-gen3-core/src/projection.rs
  crates/wm-gen3-harness/src/main.rs
)
for f in "${SCAN_FILES[@]}"; do
  if awk '/^#\[cfg\(test\)\]/{exit} {print}' "$f" \
      | grep -nE '(&mut[[:space:]]+Constitution|Constitution::new|\.apply\(|crate::admin)' >/dev/null; then
    fail "$f production code references the mutation surface (Closure 1 static rule)"
  fi
done
echo "      ok"

echo "[3/3] no authoritative thread spawns outside the physical-I/O transport (Article 4)"
# Article 4: threads may exist only for physical I/O/listening. CommitCapability is
# !Send/!Sync, so a spawned task cannot hold mutation authority; this scan additionally
# keeps every spawn site inside the physical transports. There are three:
#   - transport.rs: frame I/O
#   - mesh.rs:      TCP listener accept loop + per-connection frame handler
#   - mcp_server.rs (harness): the HTTP/TCP serve_network accept loop (transport host)
#   - bin/wm_node.rs (harness): the wm-node Unix-socket accept loop (transport host)
# The mesh allowlist is a ratified boundary decision (2026-09-27 macOS port report):
# receipts/BOUNDARY_MESH_TRANSPORT_SPAWNS_2026-09-27.md; wm-node's extension is
# receipts/BOUNDARY_WM_NODE_TRANSPORT_SPAWNS_2026-10-07.md. Tests that genuinely need a
# thread must extend this rule deliberately (with a receipt), not by relaxing the scan.
SPAWN_HITS=$(grep -rnE 'thread::spawn|rayon::spawn' crates/wm-gen3-core/src crates/wm-gen3-harness/src --include='*.rs' || true)
if [ -n "$SPAWN_HITS" ]; then
  BAD=$(echo "$SPAWN_HITS" | grep -vE '^crates/wm-gen3-core/src/(transport|mesh)\.rs:|^crates/wm-gen3-harness/src/(mcp_server\.rs|bin/wm_node\.rs):' || true)
  if [ -n "$BAD" ]; then
    fail "thread spawn outside the physical-I/O transport: $BAD"
  fi
fi
echo "      ok"

echo "closure static scans: PASS"
