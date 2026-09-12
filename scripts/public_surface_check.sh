#!/usr/bin/env bash
# Public-surface guard — refuse to push private/internal material.
#
# Checks every tracked file against the private/internal path list and scans
# tracked content for personal strings. Installed as a pre-push hook; can also
# be run directly or from CI.
#
# Override (rare, deliberate): WM_GUARD_ALLOW=1 git push ...
set -uo pipefail

if [ "${WM_GUARD_ALLOW:-0}" = "1" ]; then
    echo "public-surface guard: bypassed via WM_GUARD_ALLOW=1"
    exit 0
fi

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "guard: not a git repo"; exit 0; }
cd "$ROOT" || exit 0

FAIL=0

FORBIDDEN_PATHS=(
    "docs/lineage/"
    "docs/V9_"
    "docs/V9_2"
    "docs/GAP_LEDGER.md"
    "docs/GAP_ANALYSIS"
    "docs/CAPABILITY_LEDGER.md"
    "docs/VALKYRIE_LORA_RECIPE.md"
    "docs/BULK_OPERATIONS.md"
    "docs/INGEST_COEXISTENCE.md"
    "docs/PRICING_ETHICS.md"
    "docs/VOICE_TONE_GUIDE.md"
    "docs/WEB_RESEARCH_BACKENDS.md"
    "docs/MEMORY_TYPOLOGY_V8.md"
    "docs/RELEASE_CADENCE.md"
    "docs/ROADMAP_V9_1.md"
    "docs/NEXT_SESSION.md"
    "docs/PROGRESS.md"
    "docs/RELEASE_READINESS.md"
    "docs/TRACK_E_"
    "docs/REVIEW_BRIEF_"
    "docs/2026-"
    "docs/Q05_"
    "docs/Q32_"
    "docs/Q39_"
    "docs/S9_"
    "crates/wm-memory/examples/"
    "benchmarks/results/"
    "benchmarks/validation/"
    "benchmarks/smoke/"
    "AGENTS.md"
    "STRATEGY_V5.md"
    "STRATEGY_V6.md"
)

while IFS= read -r f; do
    for p in "${FORBIDDEN_PATHS[@]}"; do
        case "$f" in
            "$p"*|*/"$p"*)
                echo "BLOCKED path: $f"
                FAIL=1
                ;;
        esac
    done
done < <(git ls-files)

PERSONAL_PATTERNS=(
    "resident co-creator"
    "Lucas's Sacred Rule"
    "Lucas's sacred rule"
    "Lucas's Law of Non-Destructive"
    "Lucas ruling"
    "Letters to Aria"
    "valkyrie_dm"
    "Memoir Layer"
)

for pat in "${PERSONAL_PATTERNS[@]}"; do
    hits=$(git grep -I -n -F -- "$pat" -- . ':!scripts/public_surface_check.sh' 2>/dev/null | head -3)
    if [ -n "$hits" ]; then
        echo "BLOCKED content '$pat':"
        echo "$hits"
        FAIL=1
    fi
done

# Credential scan of the outgoing commits (best effort, fast range).
if command -v gitleaks >/dev/null 2>&1; then
    RANGE=""
    while read -r local_ref local_sha remote_ref remote_sha; do
        [ "$local_sha" = "0000000000000000000000000000000000000000" ] && continue
        if [ "$remote_sha" = "0000000000000000000000000000000000000000" ]; then
            RANGE="$local_sha"
        else
            RANGE="$remote_sha..$local_sha"
        fi
    done
    if [ -n "$RANGE" ]; then
        if ! gitleaks detect --source . --no-banner --redact \
                --log-opts="$RANGE" >/tmp/wm-guard-gitleaks.log 2>&1; then
            echo "BLOCKED: gitleaks findings in outgoing commits (see /tmp/wm-guard-gitleaks.log)"
            FAIL=1
        fi
    fi
fi

if [ "$FAIL" -eq 0 ]; then
    echo "public-surface guard: clean"
fi
exit "$FAIL"
