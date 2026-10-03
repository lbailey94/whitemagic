#!/usr/bin/env bash
# WhiteMagic Gen3 — Autonomic Sentinel Reflex Hook
# Evaluates system homeostasis, packages anomalies into epistemic prompt envelope,
# and alerts operator / executive agents if degraded or critical.

set -euo pipefail

WM_BIN="${WM_BIN:-$HOME/.local/bin/wm}"
STORE_PATH="${WM_STORE:-/srv/whitemagic/system-store}"
NODE_ID="${WM_NODE_ID:-$(hostname)}"
export SANGHA_ROOT="${SANGHA_ROOT:-/srv/whitemagic/sangha}"

REPORT_JSON=$("$WM_BIN" --store "$STORE_PATH" sentinel check --json 2>/dev/null || true)
if [ -z "$REPORT_JSON" ]; then
    echo "ERROR: Failed to run wm sentinel check" >&2
    exit 1
fi

STATUS=$(echo "$REPORT_JSON" | grep -o '"status": *"[^"]*"' | head -n1 | cut -d'"' -f4)

if [ "$STATUS" = "nominal" ] || [ "$STATUS" = "warning" ]; then
    echo "[$(date -u +%FT%TZ)] Sentinel pulse: $STATUS. No intervention required."
    exit 0
fi

echo "[$(date -u +%FT%TZ)] WARNING: Sentinel reported status '$STATUS' on $NODE_ID!"

# Generate epistemic self-prompt envelope
PROMPT_ENVELOPE=$("$WM_BIN" --store "$STORE_PATH" sentinel check --prompt)

# Post alert to canonical Sangha agora via bridge or CLI
if curl -s -f http://127.0.0.1:8787/api/status >/dev/null 2>&1; then
    PAYLOAD=$(jq -n \
        --arg title "Sentinel Alert: $NODE_ID is $STATUS" \
        --arg body "$PROMPT_ENVELOPE" \
        --arg target "@lucas" \
        --arg author "sentinel ($NODE_ID)" \
        --arg seat "vps" \
        --arg type "flag" \
        '{title: $title, body: $body, target: $target, author: $author, seat: $seat, type: $type}')
    RESP=$(curl -s -X POST http://127.0.0.1:8787/api/post -H "Content-Type: application/json" -d "$PAYLOAD" || true)
    echo "Posted alert to canonical Sangha agora via HTTP bridge: $RESP"
elif command -v sangha >/dev/null 2>&1; then
    echo "$PROMPT_ENVELOPE" | sangha post --target "@lucas" --title "Sentinel Alert: $NODE_ID is $STATUS"
    echo "Posted alert to local Sangha whiteboard."
fi

echo "$PROMPT_ENVELOPE"
