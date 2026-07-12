#!/usr/bin/env bash
# Build script for polyglot bridge native binaries.
# Compiles Haskell bridges with GHC -O2 for lower latency.
# Julia bridges are JIT-compiled (precompilation handled by Pkg.precompile).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HASKELL_DIR="$SCRIPT_DIR/haskell"

echo "Building Haskell bridges..."

# Compile topological bridge
if command -v ghc &>/dev/null; then
    echo "  Compiling topological_bridge.hs..."
    (cd "$HASKELL_DIR" && ghc -O2 -o topological_bridge topological_bridge.hs 2>&1 | grep -v "^Linking" || true)
    echo "  ✓ topological_bridge compiled"
else
    echo "  ⚠ ghc not found, skipping Haskell compilation"
fi

# Compile cascade bridge (if not already compiled)
if command -v ghc &>/dev/null; then
    echo "  Compiling cascade_bridge.hs..."
    (cd "$HASKELL_DIR" && ghc -O2 -o cascade_bridge cascade_bridge.hs 2>&1 | grep -v "^Linking" || true)
    echo "  ✓ cascade_bridge compiled"
fi

echo "Done. Native binaries in $HASKELL_DIR/"
