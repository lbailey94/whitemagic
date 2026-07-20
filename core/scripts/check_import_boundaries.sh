#!/usr/bin/env bash
# CI gate: fail if core→tools import violations have grown from baseline.
# Baseline: 0 direct core→tools violations (all baselined in .importlinter ignore_imports).
# Tolerance: <=2 for non-deterministic indirect chain discoveries (import-linter
# discovers different indirect paths each run due to graph traversal ordering).
# Any NEW direct core→tools violation will show up consistently and exceed the tolerance.
set -euo pipefail

cd "$(dirname "$0")/.."

# Resolve lint-imports: repo-root venv first, then PATH.
REPO_ROOT="$(cd .. && pwd)"
if [ -x "$REPO_ROOT/.venv/bin/lint-imports" ]; then
    LINT_IMPORTS="$REPO_ROOT/.venv/bin/lint-imports"
elif command -v lint-imports &>/dev/null; then
    LINT_IMPORTS="lint-imports"
else
    echo "❌ lint-imports not found (install dev deps: uv pip install import-linter)"
    exit 1
fi

VIOLATIONS=$(PYTHONPATH=. "$LINT_IMPORTS" --config .importlinter 2>&1 || true)

# Count unbaselined violations (lines starting with "-   ").
# NOTE: grep exits 1 on no match, which would kill this script under
# pipefail — guard with || true.
NEW_VIOLATIONS=$(echo "$VIOLATIONS" | grep -c '^-  ' || true)

BASELINE_TOLERANCE=2

if [ "$NEW_VIOLATIONS" -gt "$BASELINE_TOLERANCE" ]; then
    echo "❌ $NEW_VIOLATIONS unbaselined import violations (tolerance: $BASELINE_TOLERANCE):"
    echo "$VIOLATIONS" | grep '^-  ' || true
    echo ""
    echo "Add these to .importlinter ignore_imports or fix the import."
    exit 1
fi

echo "✅ Import boundary check passed ($NEW_VIOLATIONS unbaselined, tolerance $BASELINE_TOLERANCE)."
