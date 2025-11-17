#!/bin/bash
# WhiteMagic Terminal Helper - v1.0
# Makes WhiteMagic accessible via simple bash commands

# Auto-load context on terminal start
wm_init() {
    echo "🪄 WhiteMagic Terminal Helper v1.0"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Show quick status
    if command -v whitemagic &> /dev/null; then
        echo "✅ WhiteMagic CLI installed"
        whitemagic --version
    else
        echo "⚠️  WhiteMagic CLI not found"
        echo "   Install: pip install whitemagic"
    fi
    
    # Show key commands
    echo ""
    echo "Quick Commands:"
    echo "  wm_status    - Project status"
    echo "  wm_audit     - Run audit (coming v2.2.8)"
    echo "  wm_parallel  - Parallel operations"
    echo "  wm_help      - Show all commands"
    echo ""
}

# Quick status
wm_status() {
    echo "📊 WhiteMagic Status"
    echo "━━━━━━━━━━━━━━━━━━━━"
    
    # Version
    if [ -f "VERSION" ]; then
        echo "Version: $(cat VERSION)"
    fi
    
    # Memory counts
    if [ -d "memory" ]; then
        short_count=$(find memory/short_term -name "*.md" 2>/dev/null | wc -l)
        long_count=$(find memory/long_term -name "*.md" 2>/dev/null | wc -l)
        echo "Memories: ${short_count} short-term, ${long_count} long-term"
    fi
    
    # Git status
    if git rev-parse --git-dir > /dev/null 2>&1; then
        branch=$(git branch --show-current)
        echo "Branch: ${branch}"
    fi
}

# Parallel helper (coming v2.2.8)
wm_parallel() {
    echo "⚡ Parallel Operations (v2.2.8+)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Coming soon:"
    echo "  whitemagic parallel status"
    echo "  whitemagic parallel run --workers 64 <cmd>"
}

# Audit helper (coming v2.2.8)
wm_audit() {
    echo "🔍 Project Audit (v2.2.8+)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Coming soon:"
    echo "  whitemagic audit --full"
    echo "  whitemagic docs-check --fix"
    echo ""
    echo "Manual checks:"
    
    # Version drift check
    if [ -f "VERSION" ]; then
        version=$(cat VERSION)
        echo "✓ VERSION: ${version}"
        
        # Check pyproject.toml
        if grep -q "version.*=.*\"${version}\"" pyproject.toml 2>/dev/null; then
            echo "✓ pyproject.toml: ${version}"
        else
            echo "⚠️  pyproject.toml: version mismatch"
        fi
        
        # Check MCP package.json
        if grep -q "\"version\".*:.*\"${version}\"" whitemagic-mcp/package.json 2>/dev/null; then
            echo "✓ MCP package.json: ${version}"
        else
            echo "⚠️  MCP package.json: version mismatch"
        fi
    fi
}

# Help
wm_help() {
    cat << 'EOF'
🪄 WhiteMagic Terminal Helper

QUICK COMMANDS:
  wm_init      - Initialize WhiteMagic session
  wm_status    - Show project status
  wm_audit     - Run project audit
  wm_parallel  - Parallel operations info
  wm_help      - Show this help

WHITEMAGIC CLI:
  whitemagic create "title" "content"
  whitemagic search "query"
  whitemagic list
  whitemagic context --tier 1
  whitemagic track <category> <metric> <value>
  whitemagic ai-init  # AI assistant onboarding

PARALLEL (v2.2.8+):
  whitemagic parallel status
  whitemagic parallel run --workers 64 <command>
  whitemagic terrain assess --task "description"

AUDIT (v2.2.8+):
  whitemagic audit --full
  whitemagic docs-check --fix
  whitemagic exec plan --commands <json>

PHILOSOPHY:
  🌳 Wu Xing (五行): Wood → Fire → Earth → Metal → Water
  ☯️  I Ching: 8 trigrams → 64 hexagrams (threading tiers)
  ⚔️  Art of War: Terrain assessment for task planning

DOCUMENTATION:
  docs/guides/QUICKSTART.md
  docs/guides/PARALLEL_OPERATIONS.md
  docs/guides/SESSION_MANAGEMENT.md
  docs/USER_GUIDE.md

For more: https://github.com/lbailey94/whitemagic
EOF
}

# Auto-run on source
if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    # Script is being sourced, run init
    wm_init
fi
