#!/bin/bash
# WhiteMagic Math WASM Build & Optimization Script

set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
MATH_CRATE="$SCRIPT_DIR"
TARGET="wasm32-unknown-unknown"
OUT_DIR="$PROJECT_ROOT/dist/wasm"

echo "🚀 Building whitemagic-math for $TARGET..."

cd "$MATH_CRATE"

# Build with release profile and wasm feature
cargo build --target "$TARGET" --release --features wasm

echo "✅ Build complete."

# Optimization phase
WASM_PATH="target/$TARGET/release/whitemagic_math.wasm"

mkdir -p "$OUT_DIR"
cp "$WASM_PATH" "$OUT_DIR/whitemagic-math.wasm"

echo "📦 Initial size: $(du -h "$OUT_DIR/whitemagic-math.wasm" | cut -f1)"

# Check for wasm-opt (part of binaryen)
if command -v wasm-opt &> /dev/null
then
    echo "✨ Optimizing with wasm-opt..."
    wasm-opt -Oz "$OUT_DIR/whitemagic-math.wasm" -o "$OUT_DIR/whitemagic-math.opt.wasm"
    mv "$OUT_DIR/whitemagic-math.opt.wasm" "$OUT_DIR/whitemagic-math.wasm"
    echo "📉 Optimized size: $(du -h "$OUT_DIR/whitemagic-math.wasm" | cut -f1)"
else
    echo "⚠️  wasm-opt not found. Skipping advanced optimization."
    echo "💡 Install binaryen (apt install binaryen) for <200KB binary sizes."
fi

# Check for wasm-strip (part of wabt)
if command -v wasm-strip &> /dev/null
then
    echo "🧹 Stripping debug symbols with wasm-strip..."
    wasm-strip "$OUT_DIR/whitemagic-math.wasm"
    echo "📉 Final size: $(du -h "$OUT_DIR/whitemagic-math.wasm" | cut -f1)"
else
    echo "⚠️  wasm-strip not found. Skipping symbol stripping."
    echo "💡 Install wabt (apt install wabt) for smaller binaries."
fi

echo "🏁 WASM artifact ready at: $OUT_DIR/whitemagic-math.wasm"
