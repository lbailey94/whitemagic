#!/usr/bin/env bash
# retention_run.sh — weekly telemetry retention on the home gateway store.
#
# Order matters: the read-only planner (v9.1.5+) is never gated, so pre-prune
# evidence is always logged; the confirmed prune is destructive and can still
# be vetoed by the dharma gate under system stress — it fails red here, and
# the next weekly run retries. Output goes to the journal (systemd oneshot).
set -u
URL="${WM_TELEMETRY_URL:-http://127.0.0.1:18790/mcp}"

call() {
  local tool="$1" args="$2"
  curl -sS -m 120 -X POST "$URL" \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$tool\",\"arguments\":$args}}"
}

echo "[retention $(date -u +%Y-%m-%dT%H:%M:%SZ)] planner (read-only):"
planner="$(call telemetry.retention '{}')"
echo "$planner"
if printf '%s' "$planner" | grep -q '"error"'; then
  echo "[retention] planner unavailable (pre-9.1.5 fleet?) — proceeding to prune"
fi

echo
echo "[retention] prune (confirmed):"
prune="$(call telemetry.prune '{"dry_run":false,"confirm":true}')"
echo "$prune"
if printf '%s' "$prune" | grep -q '"error"'; then
  echo "[retention] prune failed or was vetoed — operator action may be needed"
  exit 1
fi
