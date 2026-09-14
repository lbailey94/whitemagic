#!/bin/bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/retention.sh"
fixture=$(mktemp -d -t wm-retention-test-XXXXXX)
trap 'rm -rf -- "$fixture"' EXIT
for evidence in trust anchors; do
  mkdir -p "$fixture/$evidence/store"
  printf 'original evidence\n' > "$fixture/$evidence/store/receipt"
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
if prune_backup_retention "$fixture" invalid; then exit 1; fi
# Exercise the actual nightly retention entry block without any earlier service,
# store, sealing, or timestamp operations. Its sibling helper is deliberately absent.
entry=$(sed -n '/^if source .*retention.sh/,/^fi$/p' "$(dirname "${BASH_SOURCE[0]}")/wm-nightly-backup.sh")
test -n "$entry"
printf 'set -eu\nBACKUP_ROOT="$1"\nKEEP=2\nLOG="$1/missing-helper.log"\n%s\n' "$entry" > "$fixture/missing-helper.sh"
bash "$fixture/missing-helper.sh" "$fixture" 2>/dev/null
grep -q 'RETENTION-FAIL (sibling retention.sh unavailable; pruning refused)' "$fixture/missing-helper.log"
test -d "$fixture/store with spaces/whitemagic-backup-20260903T000000Z"
echo 'PASS: positive retention, repeated run, evidence, unknown paths, spaces, symlinks, invalid keep'
