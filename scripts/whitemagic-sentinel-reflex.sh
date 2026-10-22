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

# Parse the verdict with a real JSON parser. The old grep|head -n1 form matched
# the first "status" key anywhere in the document, so a nested field could
# masquerade as the system verdict.
STATUS=$(printf '%s' "$REPORT_JSON" | jq -r '.status // empty' 2>/dev/null || true)
if [ -z "$STATUS" ]; then
    STATUS=$(echo "$REPORT_JSON" | grep -o '"status": *"[^"]*"' | head -n1 | cut -d'"' -f4)
fi
REPORT_STATUS="$STATUS"

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
WATCHDOG_ALERT=""
WATCHDOG_ALERT_SUPPRESSED=0
WATCHDOG_ALERT_SERVICE=""
WATCHDOG_OPEN=0
WATCHDOG_OPEN_SERVICES=""
WATCHDOG_OPEN_GENERATIONS=""
WATCHDOG_INFO=""

check_and_heal_service() {
    local service_name="$1"
    local probe_url="$2"
    local recovery_mode="${3:-restart}"

    if curl -s -f --max-time 3 "$probe_url" >/dev/null 2>&1; then
        # A healthy probe ends the consecutive-failure streak for this service.
        # Keep entries for other services and replace the state atomically.
        if [ -f "$WATCHDOG_STATE" ]; then
            local tmp_state
            tmp_state=$(mktemp "${WATCHDOG_STATE}.XXXXXX")
            if jq --arg s "$service_name" 'del(.[$s])' "$WATCHDOG_STATE" >"$tmp_state" 2>/dev/null; then
                mv -f "$tmp_state" "$WATCHDOG_STATE"
            else
                rm -f "$tmp_state"
                echo "[$(date -u +%FT%TZ)] WARNING: Could not clear watchdog state for $service_name." >&2
            fi
        fi
        return 0
    fi

    echo "[$(date -u +%FT%TZ)] Watchdog probe failed for $service_name ($probe_url)!"

    # Informational probes stay visible without paging or state. The observe
    # mode below counts failures and pages after the normal bounded threshold,
    # but never restarts a dependency service.
    if [ "$recovery_mode" = "info" ]; then
        WATCHDOG_INFO="${WATCHDOG_INFO}${WATCHDOG_INFO:+$'\n'}- informational probe failing: $service_name at $probe_url"
        return 2
    fi

    # Read circuit breaker state. `first_seen` marks the beginning of the current
    # failing streak and is only re-stamped when a new streak starts.
    local fail_count=0
    local first_seen=0
    local alerted_at=0
    if [ -f "$WATCHDOG_STATE" ]; then
        fail_count=$(jq -r --arg s "$service_name" '.[$s].failures // 0' "$WATCHDOG_STATE" 2>/dev/null || echo 0)
        first_seen=$(jq -r --arg s "$service_name" '.[$s].first_seen // 0' "$WATCHDOG_STATE" 2>/dev/null || echo 0)
        alerted_at=$(jq -r --arg s "$service_name" '.[$s].alerted_at // 0' "$WATCHDOG_STATE" 2>/dev/null || echo 0)
    fi
    if [ "$fail_count" -eq 0 ]; then
        first_seen=$NOW_EPOCH
    fi
    fail_count=$((fail_count + 1))

    # Update circuit state. NOTE: the old "reset if last_trip > 900s" rule could
    # never fire, because last_trip was refreshed on every failing run, so a
    # streak climbed 6,7,8,... unopposed. Streaks now end only on a healthy probe.
    local tmp_state
    tmp_state=$(jq -n \
        --arg s "$service_name" \
        --argjson count "$fail_count" \
        --argjson fs "$first_seen" \
        --argjson now "$NOW_EPOCH" \
        --argjson alerted "$alerted_at" \
        '{( $s ): ({failures: $count, first_seen: $fs, last_trip: $now} + (if $alerted > 0 then {alerted_at: $alerted} else {} end))}')
    if [ -f "$WATCHDOG_STATE" ]; then
        tmp_state=$(jq -s '.[0] * .[1]' "$WATCHDOG_STATE" <(echo "$tmp_state") 2>/dev/null || echo "$tmp_state")
    fi
    echo "$tmp_state" > "$WATCHDOG_STATE"

    # Circuit Breaker Check: Trip if failures exceed 3 within window
    if [ "$fail_count" -gt 3 ]; then
        echo "[$(date -u +%FT%TZ)] CIRCUIT BREAKER OPEN for $service_name ($fail_count consecutive failures since $(date -u -d "@$first_seen" +%FT%TZ 2>/dev/null || echo "$first_seen")). Suppressing restart flapping."
        WATCHDOG_OPEN=1
        WATCHDOG_OPEN_SERVICES="${WATCHDOG_OPEN_SERVICES}${WATCHDOG_OPEN_SERVICES:+, }$service_name"
        WATCHDOG_OPEN_GENERATIONS="${WATCHDOG_OPEN_GENERATIONS}${WATCHDOG_OPEN_GENERATIONS:+,}${service_name}@${first_seen}"
        # Hard 15-minute cooldown per service. The old rule also required the
        # *report* status to be nominal/warning, so a genuinely critical report
        # re-alerted on every single run — 15 posts for one condition.
        if [ "$alerted_at" -eq 0 ] || [ $((NOW_EPOCH - alerted_at)) -ge 900 ]; then
            if [ "$recovery_mode" = "observe" ]; then
                WATCHDOG_ALERT="Gateway readiness discovery probe failed: authd tools/list via $probe_url ($fail_count consecutive failures; backend /health is checked separately; no automatic restart was attempted)."
            else
                WATCHDOG_ALERT="Service probe failed: $service_name at $probe_url ($fail_count consecutive failures; watchdog circuit breaker open)."
            fi
            WATCHDOG_ALERT_SERVICE="$service_name"
        else
            WATCHDOG_ALERT_SUPPRESSED=1
            echo "[$(date -u +%FT%TZ)] Circuit-open alert suppressed for $service_name: last notification was $((NOW_EPOCH - alerted_at))s ago (15-minute cooldown)."
        fi
        return 1
    fi

    if [ "$recovery_mode" = "observe" ]; then
        echo "[$(date -u +%FT%TZ)] Watchdog bounded observation: attempt $fail_count/3 for $service_name; no service restart will be attempted."
        return 0
    fi

    echo "[$(date -u +%FT%TZ)] Watchdog bounded recovery: attempt $fail_count/3 for $service_name..."
    if command -v systemctl >/dev/null 2>&1; then
        if sudo -n systemctl restart "$service_name" 2>/dev/null; then
            echo "[$(date -u +%FT%TZ)] Successfully bounced $service_name."
        fi
    fi
}

# Run probes on services if we are on VPS
if [ "${WM_WATCHDOG_ENABLED:-}" = "1" ] || { [ -z "${WM_WATCHDOG_ENABLED:-}" ] && [ -d "/srv/whitemagic" ]; }; then
    # Keep upstream process health separate from gateway MCP discovery. A
    # backend /health success does not prove authd can serve tools/list.
    check_and_heal_service "whitemagic-hosted.service" "http://127.0.0.1:18789/health" alert || true
    # readiness.py performs the bounded, body-aware authd -> wm tools/list
    # discovery check (2s upstream timeout). fresh=1 bypasses its 300s cache;
    # curl remains bounded at 3s. Sustained gateway failures page but do not
    # restart the backend or gateway automatically.
    check_and_heal_service "whitemagic-gateway.service" "http://127.0.0.1:18797/ready?fresh=1" observe || true
fi

# ============================================================================
# 3. Status Evaluation & Epistemic Alerting
# ============================================================================
# One alert severity, derived once and used for both title and body. Previously
# the title used $STATUS (which the watchdog overwrote to "critical") while the
# body came from a *second* `sentinel check --prompt` call that said "warning" —
# so a single post contradicted itself.
ALERT_STATUS="$REPORT_STATUS"
if [ "$WATCHDOG_OPEN" = "1" ]; then
    ALERT_STATUS="critical"
fi

if [ "$ALERT_STATUS" != "critical" ]; then
    echo "[$(date -u +%FT%TZ)] Sentinel pulse: nominal. Invariants pass."
    if [ -n "$WATCHDOG_INFO" ]; then
        echo "$WATCHDOG_INFO"
    fi
    exit 0
fi

# Condition signature: an unchanged condition inherits the cooldown, while a
# *changed* condition (new failing service, report escalated) alerts immediately.
ALERT_SIG="report=${REPORT_STATUS};watchdog=${WATCHDOG_OPEN_GENERATIONS:-none}"
LAST_ALERT_AT=0
if [ -f "$WATCHDOG_STATE" ]; then
    LAST_ALERT_AT=$(jq -r --arg k "$ALERT_SIG" '.["_cooldown"][$k] // 0' "$WATCHDOG_STATE" 2>/dev/null || echo 0)
fi
if [ "$LAST_ALERT_AT" -gt 0 ] && [ $((NOW_EPOCH - LAST_ALERT_AT)) -lt 900 ]; then
    echo "[$(date -u +%FT%TZ)] Alert suppressed: condition '$ALERT_SIG' was already notified $((NOW_EPOCH - LAST_ALERT_AT))s ago (15-minute cooldown)."
    exit 0
fi

echo "[$(date -u +%FT%TZ)] ALERT: severity '$ALERT_STATUS' on $NODE_ID (report=$REPORT_STATUS watchdog=${WATCHDOG_OPEN_SERVICES:-none})."

# Generate epistemic self-prompt envelope
PROMPT_ENVELOPE=$("$WM_BIN" --store "$STORE_PATH" sentinel check --prompt)
# Lead with an explicit, self-consistent severity block so the title and body
# can never disagree about what tripped.
HEADER=$'# SENTINEL ALERT\n\n'
HEADER+="- **Alert severity**: **$ALERT_STATUS**"$'\n'
HEADER+="- **System report status**: **$REPORT_STATUS**"$'\n'
if [ "$WATCHDOG_OPEN" = "1" ]; then
    HEADER+="- **Watchdog**: circuit open for ${WATCHDOG_OPEN_SERVICES}"$'\n'
    if [[ "$WATCHDOG_OPEN_SERVICES" == *"whitemagic-gateway.service"* ]]; then
        HEADER+="- **Gateway readiness**: authd tools/list discovery failed; backend health is checked separately."$'\n'
    fi
fi
if [ -n "$WATCHDOG_INFO" ]; then
    HEADER+="- **Informational**: readiness shim not ready (does not page)"$'\n'
fi
HEADER+=$'\n'
PROMPT_ENVELOPE="$HEADER$PROMPT_ENVELOPE"
if [ -n "$WATCHDOG_ALERT" ]; then
    PROMPT_ENVELOPE+=$'\n\n## Watchdog Probe Evidence\n<untrusted_evidence>\n'
    PROMPT_ENVELOPE+="$WATCHDOG_ALERT"
    PROMPT_ENVELOPE+=$'\n</untrusted_evidence>\n'
fi

# Post alert to canonical Sangha agora via bridge or CLI
POST_DELIVERED=0
if curl -s -f http://127.0.0.1:8787/api/status >/dev/null 2>&1; then
    PAYLOAD=$(jq -n \
        --arg title "Sentinel Alert: $NODE_ID is $ALERT_STATUS" \
        --arg body "$PROMPT_ENVELOPE" \
        --arg target "@lucas" \
        --arg author "sentinel ($NODE_ID)" \
        --arg seat "vps" \
        --arg type "flag" \
        --arg provenance "computed" \
        '{title: $title, body: $body, target: $target, author: $author, seat: $seat, type: $type, provenance: $provenance}')
    if RESP=$(curl -sSf -X POST http://127.0.0.1:8787/api/post -H "Content-Type: application/json" -d "$PAYLOAD"); then
        POST_DELIVERED=1
        echo "Posted alert to canonical Sangha agora via HTTP bridge: $RESP"
    else
        echo "ERROR: Could not post alert to canonical Sangha bridge; it will be retried." >&2
    fi
elif command -v sangha >/dev/null 2>&1; then
    if echo "$PROMPT_ENVELOPE" | sangha post --target "@lucas" --title "Sentinel Alert: $NODE_ID is $ALERT_STATUS" --type flag --provenance computed --room ops; then
        POST_DELIVERED=1
        echo "Posted alert to local Sangha whiteboard."
    else
        echo "ERROR: Could not post alert to local Sangha; it will be retried." >&2
    fi
fi

# Record the cooldown only after delivery is confirmed, so a failed post retries
# on the next run instead of silently swallowing the alert for 15 minutes. Seed
# the state from an empty JSON object when an independent critical report arrives
# before any watchdog failure has created the state file.
if [ "$POST_DELIVERED" = "1" ]; then
    tmp_state=$(mktemp "${WATCHDOG_STATE}.XXXXXX")
    if { if [ -f "$WATCHDOG_STATE" ]; then cat "$WATCHDOG_STATE"; else printf '{}\n'; fi; } | jq --arg k "$ALERT_SIG" --argjson now "$NOW_EPOCH" \
        '.["_cooldown"] = ((.["_cooldown"] // {}) + {($k): $now})
         | .["_cooldown"] |= with_entries(select($now - .value < 604800))' \
        >"$tmp_state" 2>/dev/null; then
        mv -f "$tmp_state" "$WATCHDOG_STATE"
    else
        rm -f "$tmp_state"
        echo "WARNING: Could not persist alert cooldown; a repeat may be sent." >&2
    fi
    if [ -n "$WATCHDOG_ALERT_SERVICE" ]; then
        tmp_state=$(mktemp "${WATCHDOG_STATE}.XXXXXX")
        if jq --arg s "$WATCHDOG_ALERT_SERVICE" --argjson now "$NOW_EPOCH" \
            'if .[$s] then .[$s].alerted_at = $now else . end' "$WATCHDOG_STATE" >"$tmp_state" 2>/dev/null; then
            mv -f "$tmp_state" "$WATCHDOG_STATE"
        else
            rm -f "$tmp_state"
        fi
    fi
fi

echo "$PROMPT_ENVELOPE"
