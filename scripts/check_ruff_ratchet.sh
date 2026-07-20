#!/usr/bin/env bash
# CI ratchet: fail if ruff findings grow beyond the baseline.
# Baseline: 1079 findings as of 2026-07-19 (started at 1082, fixed 3 I001 import-sorts).
# This gate prevents new lint debt from being introduced.
# To lower the baseline, fix findings and update BASELINE below.
set -euo pipefail

BASELINE=1079

cd "$(dirname "$0")/.."

if [ -x ".venv/bin/ruff" ]; then
  RUFF=".venv/bin/ruff"
elif command -v ruff &>/dev/null; then
  RUFF="ruff"
else
  echo "⚠ ruff not found — skipping ruff ratchet gate"
  exit 0
fi

COUNT=$($RUFF check core/whitemagic core/tests 2>&1 | grep -oE 'Found [0-9]+ errors' | grep -oE '[0-9]+' || true)

if [ "$COUNT" -gt "$BASELINE" ]; then
  echo "❌ Ruff findings increased: $COUNT > baseline $BASELINE"
  echo "Fix the new findings or intentionally raise the baseline with justification."
  exit 1
else
  echo "✅ Ruff findings: $COUNT (baseline: $BASELINE)"
  if [ "$COUNT" -lt "$BASELINE" ]; then
    echo "💡 Findings decreased by $((BASELINE - COUNT)) — consider lowering the baseline."
  fi
fi
