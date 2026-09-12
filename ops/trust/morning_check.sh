#!/bin/bash
# Morning verification of the nightly trust run (2026-09-10, Q36 follow-up).
# One command to grade last night's 03:30 backup: stamps, manifest, arming,
# anchor tails. Run any time after ~04:00 (or after the run completes).
# Honest by design: a missing stamp is a FAIL, an empty anchor root is
# expected until attested creates accumulate (disclosed, not hidden).
set -u

BACKUP_DISK=""
for d in "/media/lucas/4198-16FD" "/media/lucas/SD_CARD1"; do
  if mountpoint -q "$d" 2>/dev/null; then
    BACKUP_DISK="$d"
    break
  fi
done
EXTERNAL="${BACKUP_DISK:+$BACKUP_DISK/whitemagic-backups}"
LEGACY="$HOME/whitemagic-backups"
LOG="$LEGACY/backup.log"
OTS_BIN="$HOME/.local/ots-venv/bin/ots"
WRITABLE_UNITS="wmv9 neon site planning"

if [ -n "$BACKUP_DISK" ]; then
  BACKUP_ROOT="$EXTERNAL"
else
  BACKUP_ROOT="$LEGACY"
  echo "WARN backup disk not mounted — checking legacy NVMe fallback"
fi
TRUST="$BACKUP_ROOT/trust"

fails=0
warns=0
ok()   { echo "  [OK]   $*"; }
warn() { echo "  [WARN] $*"; warns=$((warns+1)); }
fail() { echo "  [FAIL] $*"; fails=$((fails+1)); }

# Which nightly run are we grading? Today's manifest if it exists, else
# the newest one on file (weekend catch-up, ran before 03:30, etc.).
day="$(date -u +%Y%m%d)"
manifest="$TRUST/trust-$day.json"
if [ ! -f "$manifest" ]; then
  newest="$(ls -1t "$TRUST"/trust-*.json 2>/dev/null | head -1)"
  if [ -n "$newest" ]; then
    day="$(basename "$newest" .json | sed 's/trust-//')"
    manifest="$newest"
    warn "no manifest for UTC $day — grading newest on file: $(basename "$manifest")"
  fi
fi

echo "=== trust run $day (root: $BACKUP_ROOT) ==="

# 1. Stamp lines in the log for the graded day.
echo "-- stamp log lines"
stamp_lines="$(grep "TRUST-" "$LOG" 2>/dev/null | grep "$(date -u -d "$day" +%F 2>/dev/null || echo none)" || true)"
# The log stamps use local -Is dates; fall back to matching the trust-$day name.
if [ -z "$stamp_lines" ]; then
  stamp_lines="$(grep "trust-$day " "$LOG" 2>/dev/null || grep "trust-$day\b" "$LOG" 2>/dev/null || true)"
fi
if echo "$stamp_lines" | grep -q "TRUST-STAMP-OTS trust-$day"; then
  ok "OTS stamp logged"
else
  fail "no TRUST-STAMP-OTS line for trust-$day"
fi
if echo "$stamp_lines" | grep -q "TRUST-STAMP-RFC3161-VERIFIED trust-$day"; then
  ok "RFC-3161 stamp logged + verified"
elif echo "$stamp_lines" | grep -q "TRUST-STAMP-RFC3161-ARCHIVED trust-$day"; then
  warn "RFC-3161 TSR archived but not verified this run (check certs)"
else
  fail "no RFC-3161 stamp line for trust-$day"
fi
if [ -n "$stamp_lines" ]; then
  echo "$stamp_lines" | grep -E 'TRUST-(MANIFEST-FAIL|UPGRADE|FREETSA)' | sed 's/^/         /'
fi

# 2. Manifest + digest + OTS proof on disk.
echo "-- manifest artifacts"
if [ -f "$manifest" ]; then
  n_stores="$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))['stores']))" "$manifest" 2>/dev/null || echo '?')"
  ok "manifest exists ($n_stores stores): $(basename "$manifest")"
else
  fail "manifest missing: $manifest"
fi
if [ -f "$manifest.sha256" ]; then
  ok "digest file present: $(basename "$manifest").sha256"
else
  fail "digest file missing: $manifest.sha256"
fi
if [ -f "$manifest.sha256.ots" ]; then
  if [ -x "$OTS_BIN" ]; then
    if "$OTS_BIN" status "$manifest.sha256.ots" >/tmp/mc_ots_status.$$ 2>&1; then
      st="$(grep -iE 'confirmed|pending' /tmp/mc_ots_status.$$ | head -1 || true)"
      if echo "$st" | grep -qi confirmed; then
        ok "OTS proof CONFIRMED (BTC-anchored)"
      else
        ok "OTS proof pending BTC inclusion (normal for <48h)"
      fi
    else
      warn "ots status errored: $(head -1 /tmp/mc_ots_status.$$)"
    fi
    rm -f /tmp/mc_ots_status.$$
  else
    warn "ots client missing at $OTS_BIN"
  fi
else
  fail "OTS proof missing: $manifest.sha256.ots"
fi

# 3. RFC-3161 re-verify against archived TSR (independent of the log line).
tsr="$TRUST/trust-$day.tsr"
if [ -f "$tsr" ] && [ -f "$manifest" ] && [ -f "$TRUST/freetsa-cacert.pem" ] \
   && [ -f "$TRUST/freetsa-tsa.crt" ]; then
  if openssl ts -verify -data "$manifest" -in "$tsr" \
       -CAfile "$TRUST/freetsa-cacert.pem" -untrusted "$TRUST/freetsa-tsa.crt" \
       >/dev/null 2>&1; then
    ok "RFC-3161 re-verify against archived TSR: OK"
  else
    fail "RFC-3161 re-verify FAILED against archived TSR"
  fi
else
  warn "RFC-3161 artifacts incomplete (tsr/certs) — cannot re-verify"
fi

# 4. Unit arming: WM_MESH_KEY loaded in each writable unit's environment.
echo "-- unit arming"
for unit in $WRITABLE_UNITS; do
  pid="$(systemctl --user show "wm-serve@$unit" -p MainPID --value 2>/dev/null)"
  if [ -z "$pid" ] || [ "$pid" = "0" ]; then
    fail "wm-serve@$unit not running"
    continue
  fi
  if tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep -q '^WM_MESH_KEY='; then
    ok "wm-serve@$unit armed (WM_MESH_KEY in environ)"
  else
    fail "wm-serve@$unit running WITHOUT WM_MESH_KEY (restart pending?)"
  fi
done

# 5. Anchor tails: leaf counts (0 is honest until attested creates land).
echo "-- anchor tails"
if [ -f "$manifest" ]; then
  python3 - "$manifest" <<'PYEOF'
import json, sys
m = json.load(open(sys.argv[1]))
for store in sorted(m["stores"]):
    tail = m["stores"][store].get("anchor_tail") or {}
    if "root" in tail:
        empty = tail["root"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        state = "EMPTY ROOT (no attested creates yet)" if empty else "NON-EMPTY — live chain"
        print(f"  [{('WARN ' if empty else 'OK   ')}] {store}: leaf_count={tail.get('leaf_count')} valid={tail.get('valid')} — {state}")
    else:
        print(f"  [WARN ] {store}: no anchor tail ({tail.get('error', 'missing')})")
PYEOF
else
  warn "no manifest — cannot read anchor tails"
fi

echo "=== result: $fails fail(s), $warns warn(s) ==="
if [ "$fails" -gt 0 ]; then
  exit 1
fi
exit 0
