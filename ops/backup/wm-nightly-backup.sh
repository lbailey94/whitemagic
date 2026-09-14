#!/bin/bash
# Nightly full-store backups for all WhiteMagic stores.
# Installed 2026-08-24 after the legacy-store loss (no backups existed).
# Paths fixed 2026-08-26 after the WHITEMAGIC/ folder reorganization.
# 2026-08-28 Phase 1 cutover: writable stores are served 24/7 by systemd
# units, so this script briefly stops those units around each backup
# (wm backup requires no live writer — torn copies are worse than none)
# and restarts them on every exit path. Binary pinned at ~/.local/bin/wm
# (target/release gets wiped by build cleanups).
# 2026-08-28 Phase 3 (SSD irony tax): backup target moved OFF the NVMe to
# the SD card (USB reader, exfat). The NVMe hosts the live stores; writing
# the backups to it doubled daily NAND wear. Fallback is LOUD: if the card
# is not mounted, backups still happen (the 2026-08-24 rule — a store
# without a verified backup is one mistake away from gone — outranks the
# wear concern) but the log screams about it. Each OK line records the
# backup size so the write-budget story covers backup volume too.
# 2026-09-14 fragmentation fix: SD_CARD1 is canonical (checked first); the
# unmounted case stages under ~/whitemagic-backups/nvme-fallback and the
# next card-present run folds that into the card tree before retention, so
# one chain always survives. Canonical history was seeded on the card the
# same day (home store snapshots through Sep 8/9 + wmv9 seed + vault from
# whitemagic-archives/local-backups-20260913).
# 2026-09-02 O-1 (nightly seal): every backup is preceded by `wm seal`
# (HMAC-SHA256 manifest) + `wm verify` on the live store, and BOTH
# seal.json and .seal_key are snapshotted OFF-STORE into a dated
# seals/<store>/<date>/ dir beside the backups. The in-store key+manifest
# can be replaced by anyone who can write the store (documented wm-seal
# limit); the off-store dated snapshots are what make re-sealing
# detectable in hindsight — a store file whose hash breaks a chain of
# dated seals has been edited and re-sealed, full stop. Date-stamped
# append, never overwrite: the history IS the evidence.
# Retention: keep the newest N backup dirs per store.
set -u
WM="$HOME/.local/bin/wm"
BASE="$HOME/Desktop/WHITEMAGIC/data/WMdata/projects"
KEEP=7
# --trust-only: run only the trust manifest + external stamping pass against
# the existing backup root (no store passes, no unit stops). Used to repair
# evidence after a TSA or builder outage without re-copying stores.
TRUST_ONLY=false
case "${1:-}" in
  --trust-only) TRUST_ONLY=true ;;
  "") ;;
  *) echo "unknown flag: $1 (usage: wm-nightly-backup.sh [--trust-only])" >&2; exit 2 ;;
esac
EXTERNAL_DISK=""
for d in "/media/lucas/SD_CARD1" "/media/lucas/4198-16FD"; do
  if mountpoint -q "$d" 2>/dev/null; then
    EXTERNAL_DISK="$d"
    break
  fi
done
EXTERNAL="${EXTERNAL_DISK:+$EXTERNAL_DISK/whitemagic-backups}"
LEGACY="$HOME/whitemagic-backups"
# NVMe fallback is a STAGING area, never a second history. When no card is
# mounted snapshots land here; the next card-present run folds them into the
# canonical tree before retention. The 2026-09-14 split: SD_CARD1 was mounted
# with no tree while store snapshots sat on the NVMe, so the next nightly
# would have started a fresh chain. See CATCHUP below.
FALLBACK="$LEGACY/nvme-fallback"
LOG="$LEGACY/backup.log"

mkdir -p "$LEGACY"

if [ ! -x "$WM" ]; then
  echo "$(date -Is) FAIL binary missing: $WM" >>"$LOG"
  exit 1
fi

# Target: the SD card when mounted, the NVMe staging path with a loud WARN
# when it is not. Never skip the backup; never fall back silently; never let
# the fallback become a second history.
if [ -n "$EXTERNAL_DISK" ]; then
  BACKUP_ROOT="$EXTERNAL"
  mkdir -p "$BACKUP_ROOT"
  # Volume identity (label/uuid) so card rotation is visible in history rather
  # than silently splitting evidence across cards. 2026-09-14 forensics: the
  # Sep 9/10 seals went to a different SD_CARD1-labeled volume, Sep 11 to
  # 4198-16FD, and the current card (FA99-F6E6) was seeded fresh by the fold —
  # the "missing seals" were never pruned, they are on other media.
  vol=""
  if command -v findmnt >/dev/null 2>&1 && command -v lsblk >/dev/null 2>&1; then
    vsrc="$(findmnt -n -o SOURCE --target "$BACKUP_ROOT" 2>/dev/null || true)"
    if [ -n "$vsrc" ]; then
      vol="$(lsblk -n -o LABEL,UUID "$vsrc" 2>/dev/null | tr -s ' ' '/' | sed 's|/$||')"
    fi
  fi
  echo "$(date -Is) TARGET $BACKUP_ROOT (card $EXTERNAL_DISK mounted; volume ${vol:-unknown})" >>"$LOG"
  if [ -d "$FALLBACK" ] && [ -n "$(ls -A "$FALLBACK" 2>/dev/null)" ]; then
    echo "$(date -Is) CATCHUP folding NVMe fallback into $BACKUP_ROOT" >>"$LOG"
    if rsync -a "$FALLBACK/" "$BACKUP_ROOT/" >>"$LOG" 2>&1; then
      rm -rf "$FALLBACK"
      echo "$(date -Is) CATCHUP-OK fallback folded and cleared" >>"$LOG"
    else
      echo "$(date -Is) CATCHUP-FAIL fallback left in place (retry next card run)" >>"$LOG"
    fi
  fi
else
  BACKUP_ROOT="$FALLBACK"
  mkdir -p "$BACKUP_ROOT"
  echo "$(date -Is) WARN backup disk not mounted — staging on NVMe ($FALLBACK); folded into the card on the next card-present run." >>"$LOG"
fi
SEALS="$BACKUP_ROOT/seals"
mkdir -p "$SEALS"

# Writable stores: served by wm-serve@<name> units, need stop/backup/start.
# Read-only stores (vault, live): no writer lock, back up directly.
WRITABLE_UNITS="wmv9 neon site planning"
RW_STORES="$BASE/wmv9 $BASE/neon $BASE/whitemagic-site $BASE/planning"
RO_STORES="$BASE/vault $HOME/Desktop/WHITEMAGIC/data/WMdata/live"

# O-1: HMAC-seal the store, verify it, and snapshot BOTH the manifest and
# the signing key off-store. The seal/verify pair catches in-place edits
# that did not bother to re-seal (corruption and the casual case); the
# dated off-store snapshot catches the thorough case — a re-seal is only
# invisible until compared against the seal history.
seal_store() {
  local store="$1"
  local name day
  name="$(basename "$store")"
  day="$(date -u +%Y-%m-%d)"
  if ! "$WM" seal --store "$store" >>"$LOG" 2>&1; then
    echo "$(date -Is) SEAL-FAIL $name" >>"$LOG"
    return 1
  fi
  if "$WM" verify --store "$store" >>"$LOG" 2>&1; then
    echo "$(date -Is) VERIFY-OK $name" >>"$LOG"
  else
    echo "$(date -Is) VERIFY-FAIL $name — store files do not match the fresh seal; investigating is not optional" >>"$LOG"
  fi
  mkdir -p "$SEALS/$name/$day"
  cp "$store/lmdb/seal.json" "$SEALS/$name/$day/seal.json" 2>/dev/null \
    && cp "$store/lmdb/.seal_key" "$SEALS/$name/$day/.seal_key" 2>/dev/null \
    && chmod 600 "$SEALS/$name/$day/.seal_key" \
    && echo "$(date -Is) SEAL-SNAPSHOT $name -> $SEALS/$name/$day" >>"$LOG" \
    || echo "$(date -Is) SEAL-SNAPSHOT-FAIL $name (manifest/key copy failed)" >>"$LOG"
}

# 2026-09-04 D5/Slice A (nightly anchor): after seal/verify, `wm anchor`
# Merkle-anchors the store's record attestations and appends the report to
# a chained per-store JSONL log beside the backups. Skipped loudly (not
# silently) when the pinned binary predates the subcommand; anchor failure
# never fails the backup — the evidence step must not endanger the
# disaster-recovery step.
ANCHORS="$BACKUP_ROOT/anchors"
mkdir -p "$ANCHORS"
# Capability probe once: the deployed binary gains `wm anchor` at the next
# fleet rebuild (Slice A). Until then every store logs ANCHOR-SKIP.
if "$WM" anchor --help >/dev/null 2>&1; then
  HAVE_ANCHOR=1
else
  HAVE_ANCHOR=0
fi
anchor_store() {
  local store="$1"
  local name
  name="$(basename "$store")"
  if [ "$HAVE_ANCHOR" -eq 0 ]; then
    echo "$(date -Is) ANCHOR-SKIP $name (binary predates 'wm anchor' — lands with the next fleet rebuild)" >>"$LOG"
    return 0
  fi
  mkdir -p "$ANCHORS/$name"
  if "$WM" anchor --store "$store" --publish "$ANCHORS/$name/anchors.jsonl" >>"$LOG" 2>&1; then
    echo "$(date -Is) ANCHOR-OK $name -> $ANCHORS/$name/anchors.jsonl" >>"$LOG"
  else
    echo "$(date -Is) ANCHOR-FAIL $name (invalid attestation signature(s) or store error — see log above; backup continues)" >>"$LOG"
  fi
  return 0
}

backup_store() {
  local store="$1"
  local name size
  name="$(basename "$store")"
  if "$WM" backup --store "$store" --out "$BACKUP_ROOT/$name" >>"$LOG" 2>&1; then
    # Record the fresh backup's size in the log line (write-budget story).
    size="$(du -sh "$BACKUP_ROOT/$name" 2>/dev/null | tail -1 | awk '{print $1}')"
    echo "$(date -Is) OK $name (newest total: ${size:-?})" >>"$LOG"
  else
    echo "$(date -Is) SKIP/FAIL $name (locked or error — see log above)" >>"$LOG"
  fi
}

# Stop the writable units (only those actually running), always restart.
# --trust-only skips the store passes entirely (evidence repair after a TSA
# or builder outage); the trap stays installed so a partial stop always
# resumes, though nothing is stopped in that mode.
stopped=()
restore_units() {
  if [ ${#stopped[@]} -gt 0 ]; then
    systemctl --user start "${stopped[@]/#/wm-serve@}"
    echo "$(date -Is) resumed units: ${stopped[*]}" >>"$LOG"
  fi
}
trap restore_units EXIT

if ! $TRUST_ONLY; then
  for unit in $WRITABLE_UNITS; do
    if systemctl --user is-active --quiet "wm-serve@$unit" 2>/dev/null; then
      stopped+=("$unit")
    fi
  done
  if [ ${#stopped[@]} -gt 0 ]; then
    systemctl --user stop "${stopped[@]/#/wm-serve@}"
    echo "$(date -Is) paused units: ${stopped[*]}" >>"$LOG"
  fi

  for store in $RW_STORES; do
    seal_store "$store" && anchor_store "$store" && backup_store "$store"
  done
  for store in $RO_STORES; do
    seal_store "$store" && anchor_store "$store" && backup_store "$store"
  done
fi

# 2026-09-10 Q36 (external trust anchoring): the seal snapshots and the
# chained anchor logs are local evidence — an adversary with the disk (or
# an over-eager night) could rewrite both. The nightly trust manifest
# commits their digests into one file, and that file gets stamped by TWO
# independent external timestamp authorities:
#   1. OpenTimestamps (Bitcoin-anchored; proof starts "pending", upgrades
#      once the block is mined — usually within hours)
#   2. RFC-3161 (freetsa.org; verifiable against their CA cert, kept here)
# A manifest digest stamped by both authorities is what makes seal history
# and anchor chains *independently verifiable* — citation-grade trust, not
# self-attestation. Stamping failures never fail the backup (evidence must
# not endanger disaster recovery); they log loudly and are tallied by the
# monthly receipts (Q40).
# Honesty note: the manifest carries each store's anchor leaf_count/valid
# counts. Until attestations exist in a store's DBI, its chain honestly
# covers zero records (empty Merkle root) — receipts will disclose that
# coverage, not hide it.
TRUST="$BACKUP_ROOT/trust"
mkdir -p "$TRUST"
OTS_BIN="$HOME/.local/ots-venv/bin/ots"
FREETSA_URL="https://freetsa.org/tsr"
FREETSA_CA="$TRUST/freetsa-cacert.pem"

trust_stamp() {
  local day="$1" manifest manifest_digest n_ots upgraded pending builder
  manifest="$TRUST/trust-$day.json"
  # Sibling path works when run from the repo; the installed copy lives in
  # ~/.local/bin, where the sibling does not exist — fall back to the repo
  # (the 2026-09-14 trust outage: rc=2, python could not open the builder).
  builder="$(dirname "$0")/../trust/build_trust_manifest.py"
  if [ ! -f "$builder" ]; then
    builder="$HOME/Desktop/WHITEMAGIC/WMv9/ops/trust/build_trust_manifest.py"
  fi
  if [ ! -f "$builder" ]; then
    echo "$(date -Is) TRUST-MANIFEST-FAIL (builder missing: $builder) — external stamping skipped" >>"$LOG"
    return 0
  fi
  python3 "$builder" --anchors "$ANCHORS" --seals "$SEALS" --out "$manifest"
  local rc=$?
  if [ $rc -ne 0 ] || [ ! -s "$manifest" ]; then
    echo "$(date -Is) TRUST-MANIFEST-FAIL (rc=$rc) — external stamping skipped this night" >>"$LOG"
    return 0
  fi
  # OTS layer: stamp the manifest digest file
  manifest_digest="$manifest.sha256"
  printf '%s  trust-%s.json\n' "$(sha256sum "$manifest" | awk '{print $1}')" "$day" > "$manifest_digest"
  if [ -x "$OTS_BIN" ]; then
    if "$OTS_BIN" stamp "$manifest_digest" >>"$LOG" 2>&1 && [ -f "$manifest_digest.ots" ]; then
      echo "$(date -Is) TRUST-STAMP-OTS trust-$day (proof pending BTC inclusion; upgrades nightly)" >>"$LOG"
    else
      echo "$(date -Is) TRUST-STAMP-OTS-FAIL trust-$day (pool unreachable? backup continues)" >>"$LOG"
    fi
    # upgrade + status pass over every existing proof
    n_ots=0; upgraded=0; pending=0
    for ots_file in "$TRUST"/*.sha256.ots; do
      [ -f "$ots_file" ] || continue
      n_ots=$((n_ots + 1))
      before="$(stat -c %s "$ots_file" 2>/dev/null)"
      "$OTS_BIN" upgrade "$ots_file" >>"$LOG" 2>&1
      if [ "$(stat -c %s "$ots_file" 2>/dev/null)" != "$before" ]; then
        upgraded=$((upgraded + 1))
      fi
    done
    echo "$(date -Is) TRUST-UPGRADE pass: $n_ots proofs on file, $upgraded grew this pass (rest pending or confirmed)" >>"$LOG"
  else
    echo "$(date -Is) TRUST-STAMP-OTS-SKIP (ots client missing at $OTS_BIN)" >>"$LOG"
  fi
  # RFC-3161 layer (freetsa.org): second independent authority, cheap belt+suspenders
  if [ ! -f "$FREETSA_CA" ]; then
    curl -sf --max-time 20 'https://freetsa.org/files/cacert.pem' -o "$FREETSA_CA" 2>/dev/null \
      || echo "$(date -Is) TRUST-FREETSA-CA-MISSING (fetch failed; TSR still archived, verify deferred)" >>"$LOG"
  fi
  local tsa_cert="$TRUST/freetsa-tsa.crt"
  if [ ! -f "$tsa_cert" ]; then
    curl -sf --max-time 20 'https://freetsa.org/files/tsa.crt' -o "$tsa_cert" 2>/dev/null || true
  fi
  local tsq="$TRUST/trust-$day.tsq" tsr="$TRUST/trust-$day.tsr"
  if openssl ts -query -data "$manifest" -sha256 -out "$tsq" 2>>"$LOG" \
     && curl -sf --max-time 25 -H 'Content-Type: application/timestamp-query' \
        --data-binary @"$tsq" "$FREETSA_URL" -o "$tsr" 2>>"$LOG" \
     && [ -s "$tsr" ]; then
    if [ -f "$FREETSA_CA" ] && [ -f "$tsa_cert" ] \
       && openssl ts -verify -data "$manifest" -in "$tsr" -CAfile "$FREETSA_CA" -untrusted "$tsa_cert" >>"$LOG" 2>&1; then
      echo "$(date -Is) TRUST-STAMP-RFC3161-VERIFIED trust-$day" >>"$LOG"
    else
      echo "$(date -Is) TRUST-STAMP-RFC3161-ARCHIVED trust-$day (TSR saved; verify deferred — CA/cert or openssl issue)" >>"$LOG"
    fi
    rm -f "$tsq"
  else
    echo "$(date -Is) TRUST-STAMP-RFC3161-FAIL trust-$day (TSA unreachable? backup continues)" >>"$LOG"
  fi
}

trust_stamp "$(date -u +%Y%m%d)"

# 2026-09-13 (hygiene): public-surface guard — the repo that ships publicly
# gets audited every night so a device name, personal string, or forbidden
# path cannot sit on the public surface unnoticed. Advisory by design: a
# blocking finding logs loudly but never fails the backup (disaster
# recovery outranks hygiene, same rule as stamping).
PUBLIC_REPO="$HOME/Desktop/WHITEMAGIC/WMv9"
if [ -f "$PUBLIC_REPO/scripts/public_surface_check.sh" ] && [ -d "$PUBLIC_REPO/.git" ]; then
  if (cd "$PUBLIC_REPO" && bash scripts/public_surface_check.sh) >>"$LOG" 2>&1; then
    echo "$(date -Is) PUBLIC-SURFACE-CLEAN $PUBLIC_REPO" >>"$LOG"
  else
    echo "$(date -Is) PUBLIC-SURFACE-BLOCKED $PUBLIC_REPO (guard findings in log above — inspect before any push)" >>"$LOG"
  fi
else
  echo "$(date -Is) PUBLIC-SURFACE-SKIP (guard or repo missing at $PUBLIC_REPO)" >>"$LOG"
fi

# Retention: keep newest KEEP dirs per STORE. Evidence dirs are exempt:
# `trust/` is a flat dir of dated manifests/digests/proofs/certs (the generic
# loop deleted the RFC3161 CA certs and the Sep-13 manifest+digest+tsr on
# 2026-09-14, orphaning that day's OTS proof); `anchors/` and `seals/` are
# per-store dirs whose retention is either unbounded by design (anchor
# chains are the evidence) or handled by the dedicated seal loop below.
if source "$(dirname "${BASH_SOURCE[0]}")/retention.sh"; then
  prune_backup_retention "$BACKUP_ROOT" "$KEEP" \
    || echo "$(date -Is) RETENTION-FAIL (invalid retention or removal failure)" >>"$LOG"
else
  echo "$(date -Is) RETENTION-FAIL (sibling retention.sh unavailable; pruning refused)" >>"$LOG"
fi

# 2026-09-14 (incident follow-through): evidence-presence guard. Retention and
# interrupted runs can both remove or never create the day's evidence, and both
# used to do it silently (the Sep-13 trust manifest was pruned unnoticed until a
# morning check). Assert the day's evidence exists at the end of every run and
# log EVIDENCE-MISSING loudly for each absent item. Advisory by design: the
# backup result still stands (recovery outranks hygiene), but a missing
# manifest, digest, proof or seal snapshot is never invisible again.
EVIDENCE_MISSING=0
evidence_require() {
  if [ ! -e "$1" ]; then
    echo "$(date -Is) EVIDENCE-MISSING $2 ($1)" >>"$LOG"
    EVIDENCE_MISSING=$((EVIDENCE_MISSING + 1))
  fi
}

verify_evidence_presence() {
  local dayc dayd store name scope
  dayc="$(date -u +%Y%m%d)"
  dayd="$(date -u +%Y-%m-%d)"
  scope="trust manifest/digest/OTS/TSR"
  evidence_require "$TRUST/trust-$dayc.json" "trust manifest trust-$dayc.json"
  evidence_require "$TRUST/trust-$dayc.json.sha256" "trust digest trust-$dayc.json.sha256"
  evidence_require "$TRUST/trust-$dayc.json.sha256.ots" "OTS proof trust-$dayc.json.sha256.ots"
  evidence_require "$TRUST/trust-$dayc.tsr" "RFC3161 response trust-$dayc.tsr"
  if ! $TRUST_ONLY; then
    scope="$scope + seal snapshots"
    for store in $RW_STORES $RO_STORES; do
      name="$(basename "$store")"
      evidence_require "$SEALS/$name/$dayd" "seal snapshot $name/$dayd"
    done
  fi
  if [ "$EVIDENCE_MISSING" -eq 0 ]; then
    echo "$(date -Is) EVIDENCE-OK ($scope)" >>"$LOG"
  else
    echo "$(date -Is) EVIDENCE-SUMMARY $EVIDENCE_MISSING item(s) missing — see EVIDENCE-MISSING lines above" >>"$LOG"
  fi
}
verify_evidence_presence
