#!/usr/bin/env bash
# CI ratchet: fail if new os.getenv("WM_") calls appear outside config/.
# Baseline: all existing os.getenv("WM_") call sites outside config/ as of 2026-07-19.
# This stops the bleeding while P4.4 config migration proceeds.
# To lower the baseline, migrate calls to config/ and update this script.
set -euo pipefail

cd "$(dirname "$0")/.."

# Count os.getenv calls with WM_ prefix outside config/ directory
# Exclude tests (test code legitimately sets env vars) and __pycache__
VIOLATIONS=$(grep -rn 'os\.getenv.*"WM_' core/whitemagic/ \
  --include="*.py" \
  --exclude-dir="__pycache__" \
  --exclude-dir="config" \
  | grep -v "test_" \
  | wc -l)

BASELINE=67

if [ "$VIOLATIONS" -gt "$BASELINE" ]; then
  echo "❌ New os.getenv(\"WM_\") calls outside config/: $VIOLATIONS > baseline $BASELINE"
  echo "Move new env var reads to whitemagic/config/ or update the baseline with justification."
  exit 1
else
  echo "✅ os.getenv(\"WM_\") outside config/: $VIOLATIONS (baseline: $BASELINE)"
fi
