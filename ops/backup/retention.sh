#!/bin/bash
# Pure helpers: sourcing never touches stores, services, or evidence.
# Only the dated directory layouts emitted by wm backup and seal_store qualify.
prune_dated_directories() {
  local root="$1" keep="$2" pattern="$3" entry name
  [[ "$keep" =~ ^[0-9]+$ ]] && [ "$keep" -gt 0 ] || return 2
  [ -d "$root" ] && [ ! -L "$root" ] || return 0
  local candidates=()
  for entry in "$root"/*; do
    [ -d "$entry" ] && [ ! -L "$entry" ] || continue
    name="${entry##*/}"
    [[ "$name" =~ $pattern ]] && candidates+=("$name")
  done
  [ "${#candidates[@]}" -gt "$keep" ] || return 0
  # UTC fixed-width names sort chronologically; no whitespace pathname parsing.
  mapfile -t candidates < <(printf '%s\n' "${candidates[@]}" | LC_ALL=C sort -r)
  for name in "${candidates[@]:keep}"; do
    rm -rf -- "$root/$name" || return 1
  done
}

prune_backup_retention() {
  local root="$1" keep="$2" overrides="${3:-}" seal_keep="${4:-$2}" store name sk
  [[ "$keep" =~ ^[0-9]+$ ]] && [ "$keep" -gt 0 ] || return 2
  [[ "$seal_keep" =~ ^[0-9]+$ ]] && [ "$seal_keep" -gt 0 ] || return 2
  [ -d "$root" ] && [ ! -L "$root" ] || return 0
  for store in "$root"/*; do
    [ -d "$store" ] && [ ! -L "$store" ] || continue
    case "${store##*/}" in anchors|seals|trust) continue ;; esac
    # Per-store override ("name:keep,name:keep"): big stores stay lean, small
    # stores keep a longer history (their snapshots are megabytes, not GBs).
    sk="$keep"
    if [ -n "$overrides" ]; then
      local pair
      for pair in $(printf '%s' "$overrides" | tr ',' ' '); do
        [ "${pair%%:*}" = "${store##*/}" ] && sk="${pair##*:}"
      done
    fi
    [[ "$sk" =~ ^[0-9]+$ ]] || sk="$keep"
    prune_dated_directories "$store" "$sk" '^whitemagic-backup-[0-9]{8}T[0-9]{6}Z$' || return
  done
  [ -d "$root/seals" ] && [ ! -L "$root/seals" ] || return 0
  for store in "$root"/seals/*; do
    prune_dated_directories "$store" "$seal_keep" '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' || return
  done
}
