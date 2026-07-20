#!/usr/bin/env bash
# Test tier runner for WhiteMagic CI lanes (P3.3).
#
# Usage:
#   ./tests/tiers.sh contract    # Lane A: contract + unit (fast gate)
#   ./tests/tiers.sh integration # Lane B: integration
#   ./tests/tiers.sh nightly     # Lane C: full suite + random order
#   ./tests/tiers.sh performance # Benchmarks only
#
# Environment:
#   PYTHONPATH must point to core/
#   WM_STATE_ROOT, WM_SILENT_INIT, WM_SKIP_POLYGLOT set by conftest

set -euo pipefail

TIER="${1:-contract}"
PYTEST="python3 -m pytest"
COMMON_OPTS="-o addopts='--timeout=30 -n auto --dist loadscope'"

case "$TIER" in
  contract)
    # Lane A: Pull-request fast gate
    # Contract tests (verify/) + unit tests (unit/) — no network, no models
    echo "=== Lane A: Contract + Unit ==="
    PYTHONPATH=. $PYTEST tests/verify/ tests/unit/ \
      -m "not network and not bridge and not slow" \
      --timeout=30 -n auto --dist loadscope \
      -q
    ;;
  integration)
    # Lane B: Pull-request integration
    echo "=== Lane B: Integration ==="
    PYTHONPATH=. $PYTEST tests/integration/ \
      -m "not network and not slow" \
      --timeout=60 -n auto --dist loadscope \
      -q
    ;;
  nightly)
    # Lane C: Nightly — full suite with random order
    echo "=== Lane C: Nightly (full + random) ==="
    PYTHONPATH=. $PYTEST tests/verify/ tests/unit/ tests/integration/ \
      -p randomly \
      --randomly-seed=42 \
      --timeout=120 -n auto --dist loadscope \
      -q
    echo "=== Lane C: Nightly (random seed 777) ==="
    PYTHONPATH=. $PYTEST tests/verify/ tests/unit/ tests/integration/ \
      -p randomly \
      --randomly-seed=777 \
      --timeout=120 -n auto --dist loadscope \
      -q
    ;;
  performance)
    # Benchmarks only (not in default CI)
    echo "=== Performance ==="
    PYTHONPATH=. $PYTEST tests/benchmarks/ \
      -m "performance" \
      --timeout=300 \
      -q
    ;;
  *)
    echo "Usage: $0 {contract|integration|nightly|performance}"
    exit 1
    ;;
esac
