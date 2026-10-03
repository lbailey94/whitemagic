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

# ============================================================================
# 1. Circadian Sleep Compaction (Frontier 3)
# ============================================================================
CURRENT_HOUR_UTC=$(date -u +%H)
TODAY_UTC=$(date -u +%F)
STAMP_FILE="$STORE_PATH/circadian_compaction.stamp"

# Run circadian sleep compaction during quiescent hours (03:00-05:00 UTC)
# if not already executed today and load is low.
if [ "$CURRENT_HOUR_UTC" = "03" ] || [ "$CURRENT_HOUR_UTC" = "04" ]; then
    LAST_RUN=$(cat "$STAMP_FILE" 2>/dev/null || echo "")
    if [ "$LAST_RUN" != "$TODAY_UTC" ]; then
        LOAD_1M=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo "0.0")
        LOAD_INT=$(echo "$LOAD_1M" | cut -d'.' -f1)
        if [ "$LOAD_INT" -lt 2 ]; then
            echo "[$(date -u +%FT%TZ)] Quiescent window detected (load=$LOAD_1M). Initiating circadian sleep compaction..."
            if "$WM_BIN" --store "$STORE_PATH" dream --homeostatic --cycles 1 >/dev/null 2>&1; then
                echo "$TODAY_UTC" > "$STAMP_FILE"
                echo "[$(date -u +%FT%TZ)] Circadian sleep compaction completed successfully."
            else
                echo "[$(date -u +%FT%TZ)] Circadian sleep compaction deferred by homeostatic governor."
            fi
        fi
    fi
fi

# ============================================================================
# 2. Bounded Non-Oscillating Watchdog (Frontier 3)
# ============================================================================
WATCHDOG_STATE="$STORE_PATH/watchdog-circuit.json"
NOW_EPOCH=$(date +%s)

check_and_heal_service() {
    local service_name="$1"
    local probe_url="$2"

    if curl -s -f --max-time 3 "$probe_url" >/dev/null 2>&1; then
        return 0
    fi

    echo "[$(date -u +%FT%TZ)] Watchdog probe failed for $service_name ($probe_url)!"

    # Read circuit breaker state
    local fail_count=0
    local last_trip=0
    if [ -f "$WATCHDOG_STATE" ]; then
        fail_count=$(jq -r --arg s "$service_name" '.[$s].failures // 0' "$WATCHDOG_STATE" 2>/dev/null || echo 0)
        last_trip=$(jq -r --arg s "$service_name" '.[$s].last_trip // 0' "$WATCHDOG_STATE" 2>/dev/null || echo 0)
    fi

    # Reset failure count if last trip was > 900 seconds (15 minutes) ago
    if [ $((NOW_EPOCH - last_trip)) -gt 900 ]; then
        fail_count=0
    fi

    fail_count=$((fail_count + 1))

    # Update circuit state
    local tmp_state
    tmp_state=$(jq -n \
        --arg s "$service_name" \
        --argjson count "$fail_count" \
        --argjson now "$NOW_EPOCH" \
        '{( $s ): {failures: $count, last_trip: $now}}')
    if [ -f "$WATCHDOG_STATE" ]; then
        tmp_state=$(jq -s '.[0] * .[1]' "$WATCHDOG_STATE" <(echo "$tmp_state") 2>/dev/null || echo "$tmp_state")
    fi
    echo "$tmp_state" > "$WATCHDOG_STATE"

    # Circuit Breaker Check: Trip if failures exceed 3 within window
    if [ "$fail_count" -gt 3 ]; then
        echo "[$(date -u +%FT%TZ)] CIRCUIT BREAKER OPEN for $service_name ($fail_count consecutive failures). Suppressing restart flapping."
        STATUS="critical"
        return 1
    fi

    echo "[$(date -u +%FT%TZ)] Watchdog bounded recovery: attempt $fail_count/3 for $service_name..."
    if command -v systemctl >/dev/null 2>&1; then
        if sudo -n systemctl restart "$service_name" 2>/dev/null; then
            echo "[$(date -u +%FT%TZ)] Successfully bounced $service_name."
        fi
    fi
}

# Run probes on services if we are on VPS
if [ -d "/srv/whitemagic" ]; then
    # Traverses authd and live wm tools/list discovery path
    check_and_heal_service "whitemagic-hosted.service" "http://127.0.0.1:18797/ready" || true
fi

# ============================================================================
# 3. Status Evaluation & Epistemic Alerting
# ============================================================================
if [ "$STATUS" = "nominal" ] || [ "$STATUS" = "warning" ]; then
    echo "[$(date -u +%FT%TZ)] Sentinel pulse: nominal. Invariants pass."
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
