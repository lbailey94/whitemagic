#!/bin/bash
# MCP Test Suite Runner for v2.1.3
set -e

echo "🔧 WhiteMagic MCP v2.1.3 - Test Suite"
echo "======================================"

cd "$(dirname "$0")/../whitemagic-mcp"

# 1. Check Node.js
echo -e "\n📋 Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi
NODE_VERSION=$(node --version)
echo "✅ Node.js: $NODE_VERSION"

# 2. Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found"
    exit 1
fi
NPM_VERSION=$(npm --version)
echo "✅ npm: $NPM_VERSION"

# 3. Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "\n📦 Installing dependencies..."
    npm install
fi

# 4. Build TypeScript
echo -e "\n🔨 Building TypeScript..."
npm run build

# 5. Run test suite
echo -e "\n🧪 Running MCP test suite..."
npm test

# 6. Summary
echo -e "\n"
echo "======================================"
echo "🎉 MCP Test Suite Complete"
echo "======================================"
echo ""
