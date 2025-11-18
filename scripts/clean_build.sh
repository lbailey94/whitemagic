#!/bin/bash
# Clean all build artifacts before release

set -e

echo "🧹 Cleaning build artifacts..."
echo ""

# Python main package
echo "  • Main package (dist/, build/, *.egg-info)"
rm -rf dist/ build/ *.egg-info
rm -rf whitemagic.egg-info/

# Python client
echo "  • Python client"
rm -rf clients/python/dist/ clients/python/build/
rm -rf clients/python/*.egg-info

# TypeScript client
echo "  • TypeScript client"
rm -rf clients/typescript/dist/

# MCP server
echo "  • MCP server"
rm -rf whitemagic-mcp/dist/

echo ""
echo "✅ Clean complete!"
echo ""
echo "Now run:"
echo "  python3 -m build"
echo "  cd clients/python && python3 -m build && cd ../.."
echo "  cd clients/typescript && npm run build && cd ../.."
echo "  cd whitemagic-mcp && npm run build && cd .."
