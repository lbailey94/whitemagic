#!/bin/bash
# Inventory a mounted volume for WhiteMagic evidence. READ-ONLY: lists, never
# writes, mounts, unmounts, or repairs anything.
# Usage: bash ops/backup/inventory-volume.sh /media/lucas/<volume>
set -u
VOL="${1:?usage: inventory-volume.sh <mount-point>}"
if [ ! -d "$VOL" ]; then
  echo "not a directory: $VOL" >&2
  exit 2
fi

echo "=== volume identity ==="
findmnt -n -o TARGET,SOURCE,FSTYPE,OPTIONS --target "$VOL" 2>/dev/null | head -1
src="$(findmnt -n -o SOURCE --target "$VOL" 2>/dev/null || true)"
if [ -n "$src" ]; then
  lsblk -n -o NAME,LABEL,UUID,SIZE,RO "$src" 2>/dev/null | head -3
fi

ROOT="$VOL/whitemagic-backups"
if [ ! -d "$ROOT" ]; then
  echo "no whitemagic-backups tree at $ROOT"
else
  echo
  echo "=== top-level entries ==="
  for d in "$ROOT"/*/; do
    printf "%-20s %s entries\n" "$(basename "$d")" "$(ls -1 "$d" 2>/dev/null | wc -l)"
  done
  echo
  echo "=== seals per store (UTC dates) ==="
  for s in "$ROOT"/seals/*/; do
    [ -d "$s" ] || continue
    printf "%-20s: " "$(basename "$s")"
    ls -1 "$s" 2>/dev/null | sort | tr '\n' ' '
    echo
  done
  echo
  echo "=== trust evidence ==="
  ls -la "$ROOT/trust" 2>/dev/null | grep -v '^total' | awk '{print $NF, $5, $6, $7, $8}' | head -30
  echo
  echo "=== anchor logs (lines) ==="
  for a in "$ROOT"/anchors/*/; do
    [ -d "$a" ] || continue
    printf "%-20s: " "$(basename "$a")"
    if [ -f "$a/anchors.jsonl" ]; then wc -l < "$a/anchors.jsonl"; else echo "-"; fi
  done
  echo
  echo "=== newest snapshots per store (3) ==="
  for d in "$ROOT"/*/; do
    case "$(basename "$d")" in anchors|seals|trust) continue ;; esac
    printf "%-20s: " "$(basename "$d")"
    ls -1 "$d" 2>/dev/null | sort | tail -3 | tr '\n' ' '
    echo
  done
fi

echo
echo "=== archives ==="
ls -la "$VOL/whitemagic-archives" 2>/dev/null | tail -n +2 | head -25