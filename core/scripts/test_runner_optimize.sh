#!/usr/bin/env bash
# Optimized test runner leveraging pytest-xdist for maximum parallelization across cores.

set -e

echo "🚀 Launching Optimized Test Runner via xdist..."
cd "$(dirname "$0")/.." # Go to core/
.venv/bin/python3 -m pip install -q pytest-xdist || true
PYTHONPATH=. .venv/bin/python3 -m pytest tests/ -n auto --dist=loadgroup -v "$@"
