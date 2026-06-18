#!/bin/bash

set -euo pipefail

# Resolve the dev root from env or a sensible default.
DEV_ROOT="${WHITEMAGIC_DEV_ROOT:-$HOME/Desktop/whitemagicdev}"

if [ ! -d "$DEV_ROOT" ]; then
    echo "ERROR: DEV_ROOT does not exist: $DEV_ROOT" >&2
    echo "Set WHITEMAGIC_DEV_ROOT to the path of the whitemagicdev checkout." >&2
    exit 1
fi

cd "$DEV_ROOT"

echo "Cleaning SHM..."
rm -f /dev/shm/whitemagic_event_ring

echo "Starting Koka Fast Brain..."
"$DEV_ROOT/whitemagic-koka/unified_fast_brain" > "$DEV_ROOT/koka_bootstrap_out.log" &
KOKA_PID=$!

sleep 1

echo "Starting Elixir Bootstrap Stream..."
cd "$DEV_ROOT/elixir"
mix run "$DEV_ROOT/scripts/bootstrap_fast_brain.exs"

echo "Waiting for Koka to process events..."
sleep 10

echo "Terminating Koka..."
kill -9 $KOKA_PID

echo "Finished Bootstrap."
