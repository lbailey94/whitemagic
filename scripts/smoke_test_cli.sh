#!/bin/bash
# WhiteMagic CLI Smoke Test Suite - v2.2.9
# Tests all CLI commands for basic functionality

set -e  # Exit on first error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0

# Test workspace
TEST_WS=$(mktemp -d)
export WHITEMAGIC_BASE_DIR="$TEST_WS"

echo "🧪 WhiteMagic CLI Smoke Test Suite"
echo "=================================="
echo "Test workspace: $TEST_WS"
echo ""

# Cleanup on exit
cleanup() {
    echo ""
    echo "🧹 Cleaning up test workspace..."
    rm -rf "$TEST_WS"
}
trap cleanup EXIT

# Test runner function
run_test() {
    local cmd="$1"
    local description="$2"
    local expect_failure="${3:-false}"
    
    ((TOTAL++))
    echo -n "Testing: $description... "
    
    if timeout 30 bash -c "$cmd" > /dev/null 2>&1; then
        if [ "$expect_failure" = "false" ]; then
            echo -e "${GREEN}✓ PASS${NC}"
            ((PASSED++))
        else
            echo -e "${YELLOW}⚠ UNEXPECTED SUCCESS${NC}"
            ((FAILED++))
        fi
    else
        if [ "$expect_failure" = "true" ]; then
            echo -e "${GREEN}✓ PASS (expected failure)${NC}"
            ((PASSED++))
        else
            echo -e "${RED}✗ FAIL${NC}"
            ((FAILED++))
        fi
    fi
}

# === Core Commands ===
echo "📦 Testing Core Commands"
echo "------------------------"

run_test "whitemagic --version" "Check version"
run_test "whitemagic --help" "Show help"

# === Memory Commands ===
echo ""
echo "💾 Testing Memory Commands"
echo "-------------------------"

run_test "whitemagic create 'Test Memory' 'Test content' --tags test,smoke" "Create short-term memory"
run_test "whitemagic create 'Long Term Test' 'Long term content' --type long_term --tags test" "Create long-term memory"
run_test "whitemagic list" "List memories"
run_test "whitemagic list --titles-only" "List titles only"
run_test "whitemagic search --query test" "Search memories"
run_test "whitemagic list-tags" "List tags"
run_test "whitemagic stats" "Show statistics"
run_test "whitemagic stats --json" "Show statistics (JSON)"

# === Context Commands ===
echo ""
echo "🧠 Testing Context Commands"
echo "---------------------------"

run_test "whitemagic context --tier 0" "Generate tier 0 context"
run_test "whitemagic context --tier 1" "Generate tier 1 context"
run_test "whitemagic context --tier 1 --role bug-fix" "Generate context with role"
run_test "whitemagic resume" "Resume command"

# === Automation Commands ===
echo ""
echo "🤖 Testing Automation Commands"
echo "------------------------------"

run_test "whitemagic audit" "Run audit"
run_test "whitemagic audit --full" "Run full audit"

# === Metrics Commands ===
echo ""
echo "📊 Testing Metrics Commands"
echo "---------------------------"

run_test "whitemagic metrics-summary" "Show metrics summary"
run_test "whitemagic metrics-track test_metric test_value 42" "Track metric"

# === New Phase 1 Commands ===
echo ""
echo "🆕 Testing Phase 1 v2.2.9 Commands"
echo "-----------------------------------"

run_test "whitemagic pad-new test-pad --description 'Test scratchpad'" "Create scratchpad"
run_test "whitemagic pad-list" "List scratchpads"
run_test "whitemagic confidence-stats" "Show confidence stats"

# === Template Commands ===
echo ""
echo "📄 Testing Template Commands"
echo "-----------------------------"

run_test "whitemagic template-list" "List templates"

# === Config Commands ===
echo ""
echo "⚙️  Testing Config Commands"
echo "---------------------------"

run_test "whitemagic config-show" "Show config"
run_test "whitemagic config-path" "Show config path"

# === Graph Commands ===
echo ""
echo "🕸️  Testing Graph Commands"
echo "--------------------------"

run_test "whitemagic graph-stats" "Show graph stats"

# === Backup Commands ===
echo ""
echo "💾 Testing Backup Commands"
echo "--------------------------"

run_test "whitemagic backup" "Create backup"
run_test "whitemagic list-backups" "List backups"

# === Consolidation ===
echo ""
echo "🗜️  Testing Consolidation"
echo "-------------------------"

run_test "whitemagic consolidate --dry-run" "Consolidate (dry run)"

# === Exec Command (with caution) ===
echo ""
echo "⚡ Testing Exec Command"
echo "----------------------"

run_test "whitemagic exec --cwd /tmp --timeout 5 echo test" "Execute safe command"

# === Summary ===
echo ""
echo "=================================="
echo "📊 Test Results Summary"
echo "=================================="
echo -e "Total Tests:  $TOTAL"
echo -e "Passed:       ${GREEN}$PASSED${NC}"
echo -e "Failed:       ${RED}$FAILED${NC}"
echo -e "Skipped:      ${YELLOW}$SKIPPED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  $FAILED test(s) failed${NC}"
    exit 1
fi
