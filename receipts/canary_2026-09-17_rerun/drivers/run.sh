#!/usr/bin/env bash
# Canary re-run on the current tip — reproduces receipts/canary_2026-09-17 cells
# against the current binary. Writes only into receipts/canary_2026-09-17_rerun/.
set -euo pipefail
ROOT=/home/lucas/Desktop/WMgen3
OUT=$ROOT/receipts/canary_2026-09-17_rerun
RUN=/tmp/opencode/canary_rerun
BIN=$ROOT/target/release/wm-gen3
CACHE=/home/lucas/Desktop/WHITEMAGIC/WMv9/.fastembed_cache
FIX=$OUT/fixtures

rm -rf "$RUN/stores"
mkdir -p "$RUN/stores"

run() {
  local name=$1 store=$2 fixture=$3
  shift 3
  env "$@" \
    WM_GEN3_JOURNAL="$OUT/journals/$name.journal.jsonl" \
    WM_GEN3_JOURNAL_HASH_OUT="$OUT/journals/$name.journal.sha256" \
    "$BIN" serve --store "$RUN/stores/$store" < "$FIX/$fixture" > "$OUT/responses/$name.responses.jsonl"
  printf 'ok %s\n' "$name"
}

run A1 A A_full.jsonl WM_GEN3_ARBITRATION=structural
run A2 A2 A_full.jsonl WM_GEN3_SWEEP=0 WM_GEN3_ARBITRATION=structural
run A3 A A_query_only.jsonl WM_GEN3_SWEEP=0 WM_GEN3_ARBITRATION=structural
run B_count B_count B_full.jsonl WM_GEN3_PROJECTION=1 WM_GEN3_PROJECTION_GATED=count WM_GEN3_SWEEP=0 WM_GEN3_ARBITRATION=structural WM_GEN3_EMBED_CACHE="$CACHE"
run B_floor B_floor B_full.jsonl WM_GEN3_PROJECTION=1 WM_GEN3_PROJECTION_GATED=1 WM_GEN3_SWEEP=0 WM_GEN3_ARBITRATION=structural WM_GEN3_EMBED_CACHE="$CACHE"
run B_off B_off B_full.jsonl WM_GEN3_PROJECTION=1 WM_GEN3_SWEEP=0 WM_GEN3_ARBITRATION=structural WM_GEN3_EMBED_CACHE="$CACHE"
run B_soff B_soff B_full.jsonl WM_GEN3_PROJECTION=0 WM_GEN3_SWEEP=0 WM_GEN3_ARBITRATION=structural

{
  printf 'binary: %s\n' "$BIN"
  printf 'binary_sha256: %s\n' "$(sha256sum "$BIN" | cut -d' ' -f1)"
  rz=$(rustc --version)
  cz=$(cargo --version)
  printf 'rustc: %s\n' "$rz"
  printf 'cargo: %s\n' "$cz"
  printf 'host: %s\n' "$(uname -srmo)"
  printf 'date: %s\n' "$(date -Is)"
} > "$OUT/ENVIRONMENT.txt"

for j in A1 A2 A3 B_count B_floor B_off B_soff; do
  printf '== %s ==\n' "$j"
  python3 "$OUT/drivers/analyze.py" "$OUT/journals/$j.journal.jsonl"
done > /tmp/opencode/canary_rerun_summary.txt

printf 'rerun complete\n'
