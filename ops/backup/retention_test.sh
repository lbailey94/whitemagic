#!/bin/bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/retention.sh"
fixture=$(mktemp -d -t wm-retention-test-XXXXXX)
trap 'rm -rf -- "$fixture"' EXIT
for evidence in trust anchors; do
  mkdir -p "$fixture/$evidence/store"
  printf 'original evidence\n' > "$fixture/$evidence/store/receipt"
done
# The 2026-09-14 incident class: dated trust evidence at the evidence-dir ROOT
# must survive pruning (it used to be treated as per-store snapshot dirs).
for day in 10 11 13; do
  printf 'manifest %s\n' "$day" > "$fixture/trust/trust-202609${day}.json"
  printf 'digest %s\n' "$day" > "$fixture/trust/trust-202609${day}.json.sha256"
  printf 'proof %s\n' "$day" > "$fixture/trust/trust-202609${day}.json.sha256.ots"
done
mkdir -p "$fixture/seals/store" "$fixture/store with spaces"
for day in 01 02 03 04; do
  mkdir -p "$fixture/store with spaces/whitemagic-backup-202609${day}T000000Z"
  mkdir -p "$fixture/seals/store/2026-09-${day}"
done
mkdir -p "$fixture/store with spaces/not a snapshot" "$fixture/store with spaces/whitemagic-backup-malformed"
printf 'unknown\n' > "$fixture/store with spaces/notes"
ln -s "$fixture/trust" "$fixture/store with spaces/whitemagic-backup-20260801T000000Z"
prune_backup_retention "$fixture" 2
prune_backup_retention "$fixture" 2
for day in 03 04; do
  test -d "$fixture/store with spaces/whitemagic-backup-202609${day}T000000Z"
  test -d "$fixture/seals/store/2026-09-${day}"
done
for day in 01 02; do
  test ! -e "$fixture/store with spaces/whitemagic-backup-202609${day}T000000Z"
  test ! -e "$fixture/seals/store/2026-09-${day}"
done
test -d "$fixture/store with spaces/not a snapshot"
test -d "$fixture/store with spaces/whitemagic-backup-malformed"
test -f "$fixture/store with spaces/notes"
test -L "$fixture/store with spaces/whitemagic-backup-20260801T000000Z"
for evidence in trust anchors; do
  test "$(cat "$fixture/$evidence/store/receipt")" = 'original evidence'
done
for day in 10 11 13; do
  test -f "$fixture/trust/trust-202609${day}.json"
  test -f "$fixture/trust/trust-202609${day}.json.sha256"
  test -f "$fixture/trust/trust-202609${day}.json.sha256.ots"
done
if prune_backup_retention "$fixture" invalid; then exit 1; fi
mkdir -p "$fixture/linked-root" "$fixture/external-seals/store/2026-01-01" "$fixture/external-seals/store/2026-01-02"
ln -s "$fixture/external-seals" "$fixture/linked-root/seals"
prune_backup_retention "$fixture/linked-root" 1
test -d "$fixture/external-seals/store/2026-01-01"
# Exercise the actual nightly retention entry block without any earlier service,
# store, sealing, or timestamp operations. Its sibling helper is deliberately absent.
entry=$(sed -n '/^if source .*retention.sh/,/^fi$/p' "$(dirname "${BASH_SOURCE[0]}")/wm-nightly-backup.sh")
test -n "$entry"
printf 'set -eu\nBACKUP_ROOT="$1"\nKEEP=2\nLOG="$1/missing-helper.log"\n%s\n' "$entry" > "$fixture/missing-helper.sh"
bash "$fixture/missing-helper.sh" "$fixture" 2>/dev/null
grep -q 'RETENTION-FAIL (sibling retention.sh unavailable; pruning refused)' "$fixture/missing-helper.log"
test -d "$fixture/store with spaces/whitemagic-backup-20260903T000000Z"
# Evidence-presence guard: extract both guard functions from the runner and
# verify a missing manifest/digest/proof is logged, not silent.
runner="$(dirname "${BASH_SOURCE[0]}")/wm-nightly-backup.sh"
guard_fn="$(sed -n '/^evidence_require() {/,/^}$/p' "$runner")"
guard_fn+=$'\n'"$(sed -n '/^verify_evidence_presence() {/,/^}$/p' "$runner")"
test -n "$guard_fn"
mkdir -p "$fixture/guard/trust" "$fixture/guard/seals"
printf 'digest only\n' > "$fixture/guard/trust/trust-$(date -u +%Y%m%d).json.sha256"
printf 'set -u\nTRUST="$1/trust"\nSEALS="$1/seals"\nRW_STORES=""\nRO_STORES=""\nTRUST_ONLY=true\nLOG="$1/guard.log"\nEVIDENCE_MISSING=0\n%s\nverify_evidence_presence\n' "$guard_fn" > "$fixture/guard.sh"
bash "$fixture/guard.sh" "$fixture/guard" 2>/dev/null
grep -q 'EVIDENCE-MISSING trust manifest ' "$fixture/guard/guard.log"
grep -q 'EVIDENCE-MISSING OTS proof ' "$fixture/guard/guard.log"
grep -q 'EVIDENCE-MISSING RFC3161 response ' "$fixture/guard/guard.log"
grep -q 'EVIDENCE-SUMMARY 3 item(s) missing' "$fixture/guard/guard.log"
echo 'PASS: positive retention, repeated run, evidence, dated trust evidence, unknown paths, spaces, symlinks, invalid keep, evidence guard'
