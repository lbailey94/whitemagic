#!/bin/bash
# Build script for Koka native compilation (S023)
# Compiles Koka effects to native binaries for FFI

set -e

KOKA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$KOKA_DIR/.koka_build/native"
KOKA_BIN="${KOKA_PATH:-$(which koka 2>/dev/null || echo '/usr/local/bin/koka')}"

echo "=== WhiteMagic Koka Native Build ==="
echo "Koka directory: $KOKA_DIR"
echo "Build directory: $BUILD_DIR"
echo "Koka binary: $KOKA_BIN"
echo ""

# Create build directory
mkdir -p "$BUILD_DIR"

# Check Koka availability
if [ ! -x "$KOKA_BIN" ]; then
    echo "ERROR: Koka compiler not found at $KOKA_BIN"
    echo "Set KOKA_PATH environment variable or install Koka"
    exit 1
fi

KOKA_VERSION=$($KOKA_BIN --version 2>/dev/null | head -1 || echo "unknown")
echo "Koka version: $KOKA_VERSION"
echo ""

# Function to compile a Koka module
docompile_module() {
    local module=$1
    local output=$2
    local module_path="$KOKA_DIR/src/effects/$module.kk"
    
    if [ ! -f "$module_path" ]; then
        echo "WARNING: Module not found: $module_path"
        return 1
    fi
    
    echo "Compiling $module -> $output..."
    
    # Compile to native binary with JSON stdio interface
    cat > "$BUILD_DIR/${output}_runner.kk" << 'KOKA_RUNNER'
import $module
import std/core
import std/text/json

fun process-request(req: json-value): json-value
  // Parse request and dispatch to appropriate handler
  match req
    // Route to module operations
    _ -> json-object([("error", json-string("unknown request"))])

fun main() : io ()
  val input = readline()
  match parse-json(input)
    Ok(req) ->
      val result = process-request(req)
      println(result.show)
    Error(e) ->
      println(json-object([("error", json-string(e))]).show)
KOKA_RUNNER
    
    # Replace module placeholder
    sed -i "s/\$module/$module/g" "$BUILD_DIR/${output}_runner.kk"
    
    # Compile
    if $KOKA_BIN -o "$BUILD_DIR/$output" "$BUILD_DIR/${output}_runner.kk" 2>&1; then
        echo "  ✓ Compiled: $BUILD_DIR/$output"
        return 0
    else
        echo "  ✗ Failed to compile: $module"
        return 1
    fi
}

# Compile core effect modules
echo "=== Compiling Effect Modules ==="

MODULES=(
    "prat_effects:prat"
    "prat_resonance:resonance"
    "gan_ying:gan_ying"
    "gana_base:gana"
    "circuit_breaker:circuit"
    "retry_logic:retry"
    "session_state:session"
    "resource_pools:resources"
    "batch_ipc:batch_ipc"
)

COMPILED=0
FAILED=0

for module_spec in "${MODULES[@]}"; do
    IFS=':' read -r module output <<< "$module_spec"
    if docompile_module "$module" "$output"; then
        ((COMPILED++))
    else
        ((FAILED++))
    fi
done

echo ""
echo "=== Build Summary ==="
echo "Compiled: $COMPILED modules"
echo "Failed: $FAILED modules"
echo ""

# Create library bundle if we have compiled modules
if [ $COMPILED -gt 0 ]; then
    echo "=== Creating Library Bundle ==="
    
    # Create a combined runner that dispatches to all modules
    cat > "$BUILD_DIR/wm_koka_dispatcher.kk" << 'DISPATCHER'
module wm_koka_dispatcher

import std/core
import std/text/json

// Dispatch table for all compiled modules
val dispatch-table = [
  ("prat", "prat_effects"),
  ("resonance", "prat_resonance"),
  ("gan_ying", "gan_ying"),
  ("gana", "gana_base"),
  ("circuit", "circuit_breaker"),
  ("retry", "retry_logic")
]

fun dispatch(module: string, operation: string, args: json-value): json-value
  // Route to appropriate module
  json-object([
    ("module", json-string(module)),
    ("operation", json-string(operation)),
    ("status", json-string("not_yet_implemented"))
  ])

fun main() : io ()
  val input = readline()
  match parse-json(input)
    Ok(req) ->
      val module = req.field("module").default(json-string("unknown")).string
      val operation = req.field("operation").default(json-string("unknown")).string
      val args = req.field("args").default(json-null())
      val result = dispatch(module, operation, args)
      println(result.show)
    Error(e) ->
      println(json-object([("error", json-string(e))]).show)
DISPATCHER
    
    if $KOKA_BIN -o "$BUILD_DIR/wm_koka_dispatcher" "$BUILD_DIR/wm_koka_dispatcher.kk" 2>&1; then
        echo "  ✓ Dispatcher compiled: $BUILD_DIR/wm_koka_dispatcher"
    else
        echo "  ✗ Dispatcher compilation failed"
    fi
fi

echo ""
echo "=== Build Complete ==="
echo "Binaries in: $BUILD_DIR"
echo ""
ls -la "$BUILD_DIR"/*.kk 2>/dev/null || true
echo ""
echo "To use:"
echo "  echo '{\"module\":\"prat\",\"operation\":\"route\",\"args\":{}}' | $BUILD_DIR/wm_koka_dispatcher"
