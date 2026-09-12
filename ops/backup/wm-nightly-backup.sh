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
EXTERNAL_DISK=""
for d in "/media/lucas/4198-16FD" "/media/lucas/SD_CARD1"; do
  if mountpoint -q "$d" 2>/dev/null; then
    EXTERNAL_DISK="$d"
    break
  fi
done
EXTERNAL="${EXTERNAL_DISK:+$EXTERNAL_DISK/whitemagic-backups}"
LEGACY="$HOME/whitemagic-backups"
LOG="$LEGACY/backup.log"

mkdir -p "$LEGACY"

if [ ! -x "$WM" ]; then
  echo "$(date -Is) FAIL binary missing: $WM" >>"$LOG"
  exit 1
fi

# Target: the SD card when mounted, the legacy NVMe path with a loud WARN
# when it is not. Never skip the backup; never fall back silently.
if [ -n "$EXTERNAL_DISK" ]; then
  BACKUP_ROOT="$EXTERNAL"
  mkdir -p "$BACKUP_ROOT"
else
  BACKUP_ROOT="$LEGACY"
  echo "$(date -Is) WARN backup disk not mounted — falling back to NVMe ($LEGACY). NVMe wear continues until the card is remounted." >>"$LOG"
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
stopped=()
for unit in $WRITABLE_UNITS; do
  if systemctl --user is-active --quiet "wm-serve@$unit" 2>/dev/null; then
    stopped+=("$unit")
  fi
done
if [ ${#stopped[@]} -gt 0 ]; then
  systemctl --user stop "${stopped[@]/#/wm-serve@}"
  echo "$(date -Is) paused units: ${stopped[*]}" >>"$LOG"
fi
restore_units() {
  if [ ${#stopped[@]} -gt 0 ]; then
    systemctl --user start "${stopped[@]/#/wm-serve@}"
    echo "$(date -Is) resumed units: ${stopped[*]}" >>"$LOG"
  fi
}
trap restore_units EXIT

for store in $RW_STORES; do
  seal_store "$store" && anchor_store "$store" && backup_store "$store"
done
for store in $RO_STORES; do
  seal_store "$store" && anchor_store "$store" && backup_store "$store"
done

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
  local day="$1" manifest manifest_digest n_ots upgraded pending
  manifest="$TRUST/trust-$day.json"
  python3 - "$ANCHORS" "$SEALS" "$manifest" "$day" <<'PYEOF'
import hashlib, json, os, sys, glob

anchors_dir, seals_dir, out, day = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def tail_record(path):
    try:
        with open(path, "rb") as f:
            last = f.read().strip().split(b"\n")[-1].decode()
        r = json.loads(last)
        return {k: r.get(k) for k in ("root", "prev_hash", "leaf_count", "valid", "stale", "invalid")}
    except Exception as e:
        return {"error": str(e)}

manifest = {
    "type": "wm-nightly-trust-manifest",
    "v": 1,
    "utc_date": day,
    "stores": {},
}

# 2026-09-10 Q36 follow-up: fold the site prescience ledger (81-row public
# register, whitemagic-site/public/api/prescience.json) into the manifest so
# its state is covered by the dual-authority stamps every night — closes the
# "prescience-ledger timestamps not covered by the anchor" gap by nightly
# digest inclusion (chain-level coverage; per-row attestations remain future work).
_prescience = os.path.expanduser("~/Desktop/WHITEMAGIC/whitemagic-site/public/api/prescience.json")
manifest["site"] = {}
if os.path.isfile(_prescience):
    manifest["site"]["prescience_ledger"] = {
        "path": "~" + _prescience[len(os.path.expanduser("~")):],
        "sha256": sha256_file(_prescience),
        "bytes": os.path.getsize(_prescience),
        "mtime_utc": __import__("datetime").datetime.utcfromtimestamp(os.path.getmtime(_prescience)).isoformat() + "Z",
    }
else:
    manifest["site"]["prescience_ledger"] = {"error": "file missing"}
for log_path in sorted(glob.glob(os.path.join(anchors_dir, "*", "anchors.jsonl"))):
    store = os.path.basename(os.path.dirname(log_path))
    rec = tail_record(log_path)
    n_lines = sum(1 for _ in open(log_path, "rb"))
    manifest["stores"][store] = {
        "anchors_log_sha256": sha256_file(log_path),
        "anchors_records": n_lines,
        "anchor_tail": rec,
        "coverage": f"{rec.get('valid', 0)} valid attestations"
                    if isinstance(rec.get('valid'), int) else "unknown",
    }
# newest seal snapshot per store: commit its manifest+key digests
for store_dir in sorted(glob.glob(os.path.join(seals_dir, "*"))):
    store = os.path.basename(store_dir)
    days = sorted(os.listdir(store_dir))
    if not days:
        continue
    newest = os.path.join(store_dir, days[-1])
    entry = {"snapshot_day": days[-1]}
    for fname in sorted(os.listdir(newest)):
        entry[f"{fname}_sha256"] = sha256_file(os.path.join(newest, fname))
    manifest["stores"].setdefault(store, {})["seal_snapshot"] = entry

with open(out, "w") as f:
    json.dump(manifest, f, indent=2, sort_keys=True)
print(f"manifest: {len(manifest['stores'])} stores, {sum(1 for s in manifest['stores'].values() if 'anchors_log_sha256' in s)} anchor logs")
PYEOF
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

# Retention: keep newest KEEP dirs per store
for d in "$BACKUP_ROOT"/*/; do
  ls -1dt "$d"* 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -rf
done
# Seal snapshots: same retention per store (one dir per UTC day).
for d in "$SEALS"/*/; do
  ls -1dt "$d"* 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -rf
done
