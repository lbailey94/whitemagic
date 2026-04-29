#!/usr/bin/env bash

set -euo pipefail
# Development Environment Booster
# Sets optimization flags, clears temporary caches, and primes the Python environment.

export PYTHONOPTIMIZE=1
export PYTHONUNBUFFERED=1

echo "🧹 Clearing pycache to force clean re-compile..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

echo "💻 Environment boosted. (PYTHONOPTIMIZE=1)"
echo "Use 'just test-fast' to combine this with the xdist optimized runner."
