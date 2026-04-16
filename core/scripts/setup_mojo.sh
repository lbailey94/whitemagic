#!/bin/bash
# Mojo CLI Setup Script
# Installs magic CLI from get.modular.com

set -e

echo "🔥 Setting up Mojo infrastructure..."

# Check if magic CLI is already installed
if command -v magic &> /dev/null; then
    MAGIC_VERSION=$(magic --version 2>/dev/null || echo "unknown")
    echo "✅ Magic CLI already installed: $MAGIC_VERSION"
    
    # Check if Mojo is available
    if magic list 2>/dev/null | grep -q "mojo"; then
        echo "✅ Mojo runtime found"
        exit 0
    fi
fi

# Install magic CLI
echo "📦 Installing Magic CLI from get.modular.com..."
curl -ssL https://get.modular.com | sh -s --

# Source the environment if it exists
if [ -f "$HOME/.modular/bin/env" ]; then
    source "$HOME/.modular/bin/env"
fi

# Add to PATH if needed
export PATH="$HOME/.modular/bin:$PATH"

# Verify installation
if ! command -v magic &> /dev/null; then
    echo "⚠️ Magic CLI not in PATH after installation"
    echo "   Add to your shell profile:"
    echo '   export PATH="$HOME/.modular/bin:$PATH"'
    exit 1
fi

MAGIC_VERSION=$(magic --version)
echo "✅ Magic CLI installed: $MAGIC_VERSION"

# Install Mojo runtime
echo "🔥 Installing Mojo runtime..."
magic install mojo || echo "⚠️ Mojo install command failed, may already be installed"

# Verify Mojo
if magic list | grep -q "mojo"; then
    echo "✅ Mojo runtime ready"
    MOJO_PATH=$(magic list 2>/dev/null | grep mojo | head -1 | awk '{print $2}')
    echo "   Mojo location: $MOJO_PATH"
else
    echo "⚠️ Mojo runtime not detected"
fi

echo ""
echo "🔥 Mojo setup complete!"
echo ""
echo "Add to your shell profile (.bashrc, .zshrc):"
echo '  export PATH="$HOME/.modular/bin:$PATH"'
echo ""
echo "Compile Mojo files:"
echo "  cd whitemagic-mojo && magic build"
