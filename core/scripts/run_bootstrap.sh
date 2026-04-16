#!/bin/bash

cd /home/lucas/Desktop/whitemagicdev

echo "Cleaning SHM..."
rm -f /dev/shm/whitemagic_event_ring

echo "Starting Koka Fast Brain..."
/home/lucas/Desktop/whitemagicdev/whitemagic-koka/unified_fast_brain > /home/lucas/Desktop/whitemagicdev/koka_bootstrap_out.log &
KOKA_PID=$!

sleep 1

echo "Starting Elixir Bootstrap Stream..."
cd /home/lucas/Desktop/whitemagicdev/elixir
mix run /home/lucas/Desktop/whitemagicdev/scripts/bootstrap_fast_brain.exs

echo "Waiting for Koka to process events..."
sleep 10

echo "Terminating Koka..."
kill -9 $KOKA_PID

echo "Finished Bootstrap."
