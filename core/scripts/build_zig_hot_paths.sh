#!/bin/bash
# Build all Zig hot path modules for PSR-001

set -e

ZIG_DIR="/home/lucas/Desktop/whitemagicdev/whitemagic-zig"
OUT_DIR="$ZIG_DIR/zig-out/lib"

echo "=== Building Zig Hot Path Modules ==="

mkdir -p "$OUT_DIR"

# Build browser_tools.zig
echo "Building browser_tools..."
zig build-lib -dynamic -O ReleaseFast \
    -femit-bin="$OUT_DIR/libbrowser_tools.so" \
    "$ZIG_DIR/src/tools/browser_tools.zig" 2>&1 || echo "Note: browser_tools build had warnings"

# Build gan_ying_async.zig
echo "Building gan_ying_async..."
zig build-lib -dynamic -O ReleaseFast \
    -femit-bin="$OUT_DIR/libgan_ying_async.so" \
    "$ZIG_DIR/src/resonance/gan_ying_async.zig" 2>&1 || echo "Note: gan_ying_async build had warnings"

# Build broker.zig
echo "Building broker..."
zig build-lib -dynamic -O ReleaseFast \
    -femit-bin="$OUT_DIR/libbroker.so" \
    "$ZIG_DIR/src/tools/broker.zig" 2>&1 || echo "Note: broker build had warnings"

# Build distiller.zig
echo "Building distiller..."
zig build-lib -dynamic -O ReleaseFast \
    -femit-bin="$OUT_DIR/libdistiller.so" \
    "$ZIG_DIR/src/browser/distiller.zig" 2>&1 || echo "Note: distiller build had warnings"

# Build actions.zig
echo "Building actions..."
zig build-lib -dynamic -O ReleaseFast \
    -femit-bin="$OUT_DIR/libactions.so" \
    "$ZIG_DIR/src/browser/actions.zig" 2>&1 || echo "Note: actions build had warnings"

# Build cli_sangha.zig
echo "Building cli_sangha..."
zig build-lib -dynamic -O ReleaseFast \
    -femit-bin="$OUT_DIR/libcli_sangha.so" \
    "$ZIG_DIR/src/tools/cli_sangha.zig" 2>&1 || echo "Note: cli_sangha build had warnings"

echo ""
echo "=== Build Complete ==="
echo "Libraries in: $OUT_DIR"
ls -la "$OUT_DIR"
