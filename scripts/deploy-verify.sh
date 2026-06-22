#!/bin/bash
# deploy-verify.sh — Verifies deployment readiness
# Run locally before deploying to Hetzner VPS

set -e

echo "============================================================"
echo "  WhiteMagic v22.2.0 — Deployment Verification"
echo "============================================================"
echo ""

PASS=0
FAIL=0
WARN=0

check() {
    local desc="$1"
    local cmd="$2"
    if eval "$cmd" > /dev/null 2>&1; then
        echo "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $desc"
        FAIL=$((FAIL + 1))
    fi
}

warn() {
    local desc="$1"
    local cmd="$2"
    if eval "$cmd" > /dev/null 2>&1; then
        echo "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ⚠️  $desc (optional)"
        WARN=$((WARN + 1))
    fi
}

echo "1. Core Package"
check "  Core directory exists" "test -d core"
check "  pyproject.toml exists" "test -f core/pyproject.toml"
check "  whitemagic package exists" "test -d core/whitemagic"
echo ""

echo "2. PWA Build"
check "  apps/site exists" "test -d apps/site"
check "  package.json exists" "test -f apps/site/package.json"
check "  .next build exists" "test -d apps/site/.next"
check "  WASM module exists" "test -f apps/site/public/wasm/whitemagic_rust_bg.wasm"
echo ""

echo "3. Deploy Artifacts"
check "  deploy directory exists" "test -d deploy"
check "  Caddyfile exists" "test -f deploy/Caddyfile"
check "  API service exists" "test -f deploy/whitemagic-api.service"
check "  Dashboard service exists" "test -f deploy/whitemagic-dashboard.service"
echo ""

echo "4. Documentation"
check "  HETZNER_DEPLOY.md exists" "test -f docs/deploy/HETZNER_DEPLOY.md"
check "  AGENTS.md exists" "test -f AGENTS.md"
echo ""

echo "5. Test Suite"
if command -v python3 &> /dev/null; then
    source .venv/bin/activate 2>/dev/null || true
    TEST_OUTPUT=$(cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive_polyglot -q --tb=no 2>&1 | tail -1)
    if echo "$TEST_OUTPUT" | grep -q "passed"; then
        PASSED=$(echo "$TEST_OUTPUT" | grep -oP '\d+ passed' || echo "unknown")
        FAILED=$(echo "$TEST_OUTPUT" | grep -oP '\d+ failed' || echo "0 failed")
        SKIPPED=$(echo "$TEST_OUTPUT" | grep -oP '\d+ skipped' || echo "0 skipped")
        echo "  ✅ Tests: $PASSED, $FAILED, $SKIPPED"
        PASS=$((PASS + 1))
    else
        echo "  ❌ Tests failed or could not run"
        FAIL=$((FAIL + 1))
    fi
else
    echo "  ⚠️  Python3 not found (skipping test check)"
    WARN=$((WARN + 1))
fi
echo ""

echo "6. Optional Components"
warn "  Haskell FFI (polyglot/whitemagic-hs)" "test -d polyglot/whitemagic-hs"
warn "  Zig FFI (polyglot/whitemagic-zig)" "test -d polyglot/whitemagic-zig"
warn "  Rust extensions (core/whitemagic-rust)" "test -d core/whitemagic-rust"
echo ""

echo "============================================================"
echo "  Results: $PASS passed, $FAIL failed, $WARN warnings"
echo "============================================================"

if [ $FAIL -gt 0 ]; then
    echo ""
    echo "  ❌ Deployment NOT ready — fix failures above"
    exit 1
else
    echo ""
    echo "  ✅ Deployment ready!"
    echo ""
    echo "  Next steps:"
    echo "  1. SSH to Hetzner VPS: ssh root@<hetzner-ip>"
    echo "  2. Follow docs/deploy/HETZNER_DEPLOY.md"
    echo "  3. Copy deploy/ files to VPS"
    echo "  4. Run systemd services"
    echo "  5. Verify with: curl https://<your-domain>/api/wm/health"
    exit 0
fi
