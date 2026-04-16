#!/bin/bash
# Koka Installation Script for WhiteMagic (S023)
# Installs Koka v3.2.2 compiler to ~/.local/bin

set -e

KOKA_VERSION="v3.2.2"
INSTALL_DIR="$HOME/.local/bin"
KOKA_URL="https://github.com/koka-lang/koka/releases/download/${KOKA_VERSION}/koka-${KOKA_VERSION}-linux-x64.tar.gz"

echo "=== Koka Installation for WhiteMagic ==="
echo "Version: $KOKA_VERSION"
echo "Install directory: $INSTALL_DIR"
echo ""

# Create install directory
mkdir -p "$INSTALL_DIR"

# Download Koka
echo "Downloading Koka $KOKA_VERSION..."
cd /tmp
wget -q --show-progress "$KOKA_URL" -O koka.tar.gz 2>&1 || curl -L "$KOKA_URL" -o koka.tar.gz

# Extract
echo "Extracting..."
tar -xzf koka.tar.gz

# Find extracted directory (should be koka-v3.2.2 or similar)
KOKA_DIR=$(ls -d koka-* 2>/dev/null | head -1)

if [ -z "$KOKA_DIR" ]; then
    echo "ERROR: Could not find extracted Koka directory"
    exit 1
fi

echo "Found Koka directory: $KOKA_DIR"

# Copy binary
cp "$KOKA_DIR/bin/koka" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/koka"

# Cleanup
cd /tmp
rm -rf koka.tar.gz "$KOKA_DIR"

# Verify installation
echo ""
echo "Verifying installation..."
if "$INSTALL_DIR/koka" --version; then
    echo ""
    echo "=== Installation Successful ==="
    echo "Koka installed to: $INSTALL_DIR/koka"
    echo ""
    echo "Add to PATH if not already:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
    echo ""
    echo "Or for this session only:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
    echo "  source .venv/bin/activate"
else
    echo "ERROR: Koka installation verification failed"
    exit 1
fi
