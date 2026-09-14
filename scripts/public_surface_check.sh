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
    "docs/TRUST_TIER_PRICING_SKETCH_"
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
    "docs/ACS_ALIGNMENT.md"
    "docs/ARCHIVE_CAPABILITY_MAP.md"
    "docs/ARCHIVE_FINDINGS.md"
    "docs/CHIPS_ARCHITECTURE.md"
    "docs/CONFORMAL_PREDICTION.md"
    "docs/GATE2_RECRUITMENT_KIT.md"
    "docs/IMAGINATION_ENGINE.md"
    "docs/MCP_REGISTRY_LISTING.md"
    "docs/MIGRATION.md"
    "docs/MODEL_GUIDE.md"
    "docs/MULTI_PROJECT_MEMORY.md"
    "docs/OPERATIONS.md"
    "docs/OWASP_LLM_TOP10_MAPPING.md"
    "docs/PET_HARDENING.md"
    "docs/POLYGLOT_SIMD_MEMORY_STRATEGY.md"
    "docs/PRE_RELEASE_LAUNCH_PLAN.md"
    "docs/PRODUCT_CUT.md"
    "docs/REDTEAM_STRATEGY.md"
    "docs/RETRIEVAL_DEVELOPMENT_PLAN.md"
    "docs/RETRIEVAL_RESEARCH_ROADMAP.md"
    "docs/SANGHA_SECURITY.md"
    "docs/STRANGER_SIMULATION_SCRIPT.md"
    "docs/STRATEGY.md"
    "docs/TANTIVY_RECALL_QUALITY_FIX.md"
    "docs/TIMELINE_CONVERGENCE.md"
    "docs/TIMESTAMP_CONVENTIONS.md"
    "docs/TWO_LAPTOP_REHEARSAL.md"
    "docs/V6_"
    "docs/V7_PRODUCT_READINESS.md"
    "docs/V8_MEMORY_RESEARCH_AGENDA.md"
    "docs/VECTOR_SEARCH_ROADMAP.md"
    "docs/notes/"
    "crates/wm-memory/examples/"
    "crates/wm-tools/examples/"
    "benchmarks/results/"
    "benchmarks/validation/"
    "benchmarks/smoke/"
    "npm/whitemagic-mcp/dist/"
    "scripts/tests/q07_"
    "scripts/tests/q11_"
    "scripts/tests/test_heritage_pilot_"
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
    "inspiron"
    "t4800s"
    "zorin"
)

for pat in "${PERSONAL_PATTERNS[@]}"; do
    hits=$(git grep -I -n -i -F -- "$pat" -- . ':!scripts/public_surface_check.sh' ':!benchmarks/data/' 2>/dev/null | head -3)
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
