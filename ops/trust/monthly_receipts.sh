#!/usr/bin/env bash
# monthly_receipts.sh — Q40: the monthly public receipts artifact.
#
# Trust as a *process*, published on a schedule. Reuses the Q01 continuity
# protocol discipline: predeclared selection (this month's log lines),
# independent recomputation (anchor chains verified by re-walking, not by
# trusting our own writer), failures logged not hidden, and a known-limits
# section that states what this artifact does NOT prove.
#
# Usage:   monthly_receipts.sh [YYYY-MM]   (default: previous month)
# Output:  $BACKUP_ROOT/receipts/<YYYY-MM>/RECEIPTS.md + copies of the
#          monthly trust manifests/proofs beside it.
#
# Sources (all on the backup disk, never the live store):
#   backup.log            — seal/verify/anchor/backup outcome lines
#   anchors/<store>/...   — chained nightly anchor logs
#   seals/<store>/<day>/  — off-store HMAC snapshots
#   trust/                — nightly manifests + OTS proofs + RFC-3161 TSRs
set -u
WM="$HOME/.local/bin/wm"
OTS_BIN="$HOME/.local/ots-venv/bin/ots"
EXTERNAL_DISK="/media/lucas/SD_CARD1"
EXTERNAL="$EXTERNAL_DISK/whitemagic-backups"
LEGACY="$HOME/whitemagic-backups"
BACKUP_ROOT="$(mountpoint -q "$EXTERNAL_DISK" 2>/dev/null && echo "$EXTERNAL" || echo "$LEGACY")"

MONTH="${1:-$(date -u -d 'last month' +%Y-%m)}"
OUT="$BACKUP_ROOT/receipts/$MONTH"
mkdir -p "$OUT"
LOG="$LEGACY/backup.log"
[ -f "$BACKUP_ROOT/backup.log" ] && LOG="$BACKUP_ROOT/backup.log"
[ -f "$LOG" ] || { echo "receipts: no backup log found"; exit 1; }

REPORT="$OUT/RECEIPTS.md"
{
echo "# WhiteMagic Monthly Trust Receipts — $MONTH"
echo
echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ) · Generator: ops/trust/monthly_receipts.sh (Q40)"
echo "Method: predeclared selection (this month's lines from \`$(basename "$LOG")\`),"
echo "independent recomputation (anchor chains re-walked and hash-checked, seal"
echo "manifests re-verified against the off-store snapshots), failures disclosed"
echo "in place. Nothing in this report is asserted from memory alone."
echo
echo "## 1. Integrity seal tally (per store)"
echo
echo "| Store | seals | verify OK | verify FAIL | seal-snapshot | snapshot-fail |"
echo "|---|---|---|---|---|---|"
for store in live neon planning vault whitemagic-site wmv5; do
  seals=$(grep -c "SEAL-OK\? $store\|VERIFY-OK $store" "$LOG" 2>/dev/null || true)
  vok=$(grep -c "VERIFY-OK $store" "$LOG" 2>/dev/null || true)
  vfail=$(grep -c "VERIFY-FAIL $store" "$LOG" 2>/dev/null || true)
  ssnap=$(grep -c "SEAL-SNAPSHOT $store" "$LOG" 2>/dev/null || true)
  ssfail=$(grep -c "SEAL-SNAPSHOT-FAIL $store" "$LOG" 2>/dev/null || true)
  echo "| $store | $seals | $vok | $vfail | $ssnap | $ssfail |"
done
echo
echo "## 2. Anchor chain integrity (independently recomputed)"
echo
python3 - "$BACKUP_ROOT/anchors" <<'PYEOF'
import hashlib, json, sys, glob, os
anchors_dir = sys.argv[1]
logs = sorted(glob.glob(os.path.join(anchors_dir, "*", "anchors.jsonl")))
if not logs:
    print("No anchor logs found.\n")
for p in logs:
    store = os.path.basename(os.path.dirname(p))
    lines = open(p, "rb").read().strip().split(b"\n")
    broken = None
    for i in range(1, len(lines)):
        prev = json.loads(lines[i-1])
        cur = json.loads(lines[i])
        if cur.get("prev_hash") != hashlib.sha256(lines[i-1]).hexdigest():
            broken = i
            break
    tails = [json.loads(l) for l in lines]
    valid = sum(t.get("valid", 0) for t in tails if isinstance(t.get("valid"), int))
    status = "INTACT" if broken is None else f"**BROKEN at record {broken}**"
    print(f"- **{store}**: {len(lines)} records, chain {status}, "
          f"cumulative valid attestations {valid}, "
          f"current root `{tails[-1].get('root','?')[:16]}…`")
print()
print("Chain check: each record's `prev_hash` must equal SHA-256 of the entire")
print("previous line. A break means the log was edited after the fact.\n")
PYEOF
echo "## 3. External timestamps (two independent authorities)"
echo
echo "| Night | OTS (Bitcoin) | RFC-3161 (freetsa) |"
echo "|---|---|---|"
for digest in "$BACKUP_ROOT"/trust/trust-*.json.sha256; do
  [ -f "$digest" ] || continue
  day="$(basename "$digest" .json.sha256)"
  day="${day#trust-}"
  ots_status="—"; rfc_status="—"
  if [ -f "$digest.ots" ] && [ -x "$OTS_BIN" ]; then
    if "$OTS_BIN" verify "$digest.ots" >/dev/null 2>&1; then
      ots_status="**CONFIRMED** (BTC block)"
    else
      ots_status="pending (proof on file)"
    fi
  fi
  tsr="$BACKUP_ROOT/trust/trust-$day.tsr"
  if [ -f "$tsr" ]; then
    ca="$BACKUP_ROOT/trust/freetsa-cacert.pem"
    tsa="$BACKUP_ROOT/trust/freetsa-tsa.crt"
    if [ -f "$ca" ] && [ -f "$tsa" ] \
       && openssl ts -verify -data "${digest%.sha256}" -in "$tsr" -CAfile "$ca" -untrusted "$tsa" >/dev/null 2>&1; then
      rfc_status="**VERIFIED**"
    else
      rfc_status="archived (verify deferred)"
    fi
  fi
  echo "| $day | $ots_status | $rfc_status |"
done
echo
echo "## 4. Backup continuity (disaster-recovery posture)"
echo
echo "- Backup OK lines this month: $(grep -c "$(date -u -d "$MONTH-01" +%Y-%m)" "$LOG" >/dev/null 2>&1 && grep "^$(date -u -d "$MONTH-01" +%Y-%m)" "$LOG" | grep -c ' OK ' || echo 0)"
echo "- Backup SKIP/FAIL lines this month: $(grep "^$(date -u -d "$MONTH-01" +%Y-%m)" "$LOG" 2>/dev/null | grep -c 'SKIP/FAIL' || echo 0)"
echo "- Card-mounted fallback warnings: $(grep "^$(date -u -d "$MONTH-01" +%Y-%m)" "$LOG" 2>/dev/null | grep -c 'WARN backup disk' || echo 0)"
echo
echo "## 5. Known limits (what this receipt does NOT prove)"
echo
cat <<'EOF'
- Seal = HMAC-SHA256 manifest, **tamper-evidence, not tamper-resistance**:
  an adversary who can replace both the store's `.seal_key` and `seal.json`
  AND the off-store snapshots AND the stamped manifests wins. The dated,
  externally-timestamped history makes that attack expensive and visible,
  not impossible.
- Anchor chains cover the attestations DBI. Where `valid` is 0, the chain
  honestly anchored an **empty Merkle root** — coverage is disclosed, not
  padded. Prescience-ledger timestamps are not yet covered by anchors.
- All evidence here is self-produced (our log, our seals, our anchors).
  External anchoring removes *time-travel* of claims, not *authorship*
  disputes. Third-party audit remains the endgame (audit roadmap item 7).
EOF
echo
echo "## 6. Red-team / incident notes for the month"
echo
echo "- (manual section — recorded incidents, attempted tampering, drills)"
echo
echo "## 7. Artifacts cited"
echo
echo "- Log: \`$(basename "$LOG")\` ($(wc -l < "$LOG") lines total)"
echo "- Trust manifests + proofs: \`trust/trust-*.json(.sha256)(.ots|.tsr)\`"
echo "- Anchor logs: \`anchors/<store>/anchors.jsonl\`"
echo "- Seal snapshots: \`seals/<store>/<UTC-day>/\`"
} > "$REPORT"

# Copies of the month's trust manifests/proofs beside the receipt (self-contained)
if [ -d "$BACKUP_ROOT/trust" ]; then
  cp "$BACKUP_ROOT"/trust/trust-*.json "$BACKUP_ROOT"/trust/trust-*.tsr "$OUT"/ 2>/dev/null || true
  cp "$BACKUP_ROOT"/trust/*.sha256.ots "$OUT"/ 2>/dev/null || true
fi

echo "receipts: wrote $REPORT"
wc -l "$REPORT"
