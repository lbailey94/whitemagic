#!/bin/bash
# Pin running llama-server processes to specific CPU cores
# Reduces CPU contention between models on multi-core systems
#
# Layout for i5-8350U (4 cores / 8 threads):
#   Core 0 (CPUs 0,4) → Qwen 0.5B (port 8081, -t 2)
#   Core 1 (CPUs 1,5) → Qwen 1.5B (port 8082, -t 2)
#   Cores 2-3 (CPUs 2,3,6,7) → Qwen 3B (port 8080, -t 4)

set -e

# Find llama-server PIDs by port
pin_server() {
    local port=$1 cpus=$2 name=$3
    local pid=$(pgrep -f "llama-server.*--port $port" | head -1)
    if [ -z "$pid" ]; then
        echo "  $name (port $port): not running"
        return 0
    fi
    taskset -cp "$cpus" "$pid" 2>&1 | sed "s/^/  $name: /"
}

echo "=== Pinning llama-server processes to CPU cores ==="
pin_server 8081 "0,4" "Qwen 0.5B"
pin_server 8082 "1,5" "Qwen 1.5B"
pin_server 8080 "2,3,6,7" "Qwen 3B"
echo "=== Done ==="
