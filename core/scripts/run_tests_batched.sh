#!/bin/bash
# Batched test runner — splits tests into parallel groups to prevent laptop hangs.
# Usage:
#   ./scripts/run_tests_batched.sh              # Fast tier (unit only, parallel)
#   ./scripts/run_tests_batched.sh --full       # Full suite (unit + integration, parallel)
#   ./scripts/run_tests_batched.sh --module memory  # Specific module
#   ./scripts/run_tests_batched.sh --serial    # Force serial (no xdist)

set -e
cd "$(dirname "$0")/.."

source ../.venv/bin/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null || true

# Default: unit tests only, parallel
MODE="unit"
PARALLEL="-n auto --dist=loadscope"
TIMEOUT=30
EXTRA_ARGS=""

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --full)    MODE="full"; shift ;;
        --module)  MODE="module"; MODULE="$2"; shift 2 ;;
        --serial)  PARALLEL=""; shift ;;
        --fast)    MODE="fast"; shift ;;
        *)         EXTRA_ARGS="$EXTRA_ARGS $1"; shift ;;
    esac
done

case $MODE in
    fast)
        # Tier 1: Fast feedback (<30s) — parallel, short timeout
        echo "=== Fast tier (unit, parallel, 5s timeout) ==="
        python -m pytest tests/unit/ \
            $PARALLEL \
            -q --timeout=5 -x --tb=short \
            --ignore=tests/unit/galactic \
            $EXTRA_ARGS
        ;;
    unit)
        # Tier 1+: All unit tests — parallel, 30s timeout
        echo "=== Unit tier (parallel, 30s timeout) ==="
        python -m pytest tests/unit/ \
            $PARALLEL \
            -q --timeout=$TIMEOUT --tb=short \
            $EXTRA_ARGS
        ;;
    full)
        # Tier 3: Full suite — parallel, 30s timeout, exclude archives
        echo "=== Full suite (parallel, 30s timeout) ==="
        python -m pytest tests/ \
            $PARALLEL \
            -q --timeout=$TIMEOUT --tb=short \
            --ignore=tests/archive_v14 \
            --ignore=tests/archive_v11 \
            --ignore=tests/archive \
            --ignore=tests/archive_polyglot \
            --ignore=tests/legacy \
            --ignore=tests/adhoc \
            --ignore=tests/verify \
            $EXTRA_ARGS
        ;;
    module)
        # Specific module — parallel
        echo "=== Module: $MODULE (parallel) ==="
        python -m pytest tests/unit/test_${MODULE}*.py tests/unit/*/${MODULE}*/ \
            $PARALLEL \
            -q --timeout=$TIMEOUT --tb=short -v \
            $EXTRA_ARGS
        ;;
esac
