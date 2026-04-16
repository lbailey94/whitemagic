#!/bin/bash
# WhiteMagic One-Click Setup (WASM-First)
# This script initializes the environment, builds native extensions, and prepares the WASM server.

set -e

echo "🔮 Initializing WhiteMagic Environment..."

# 1. Environment Check
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# 2. Virtual Environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# 4. Native Acceleration (Rust)
if command -v cargo &> /dev/null; then
    echo "🦀 Building Rust accelerators..."
    cd whitemagic_rs && cargo build --release && cp target/release/libwhitemagic_rs.so ../whitemagic_rs.so && cd ..
else
    echo "⚠️  Cargo not found, skipping Rust acceleration build."
fi

# 5. WASM Preparation
if [ -f "Dockerfile.wasm" ]; then
    echo "🕸️  Preparing WASM environment..."
    # Placeholder for WASM build steps if toolchain present
fi

# 6. Database Initialization
echo "🗄️  Initializing holographic galaxy..."
python -m whitemagic.cli.cli_app setup

echo "✅ WhiteMagic Setup Complete!"
echo "Run 'docker-compose up' to start the MCP server and WASM dashboard."
