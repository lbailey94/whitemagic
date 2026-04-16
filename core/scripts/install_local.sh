#!/usr/bin/env bash
# WhiteMagic Local Installer (for testing before GitHub push)
# =============================================================
# This installs WhiteMagic v18 from local source files
#
# Usage:
#   bash scripts/install_local.sh
#   bash scripts/install_local.sh --wasm-only
#   bash scripts/install_local.sh --python-only

set -euo pipefail

VERSION="18.1.0"
INSTALL_DIR="$HOME/.whitemagic"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}WhiteMagic v${VERSION} - Local Installer${NC}"
echo ""

# Parse arguments
WASM_ONLY=false
PYTHON_ONLY=false

for arg in "$@"; do
    case $arg in
        --wasm-only) WASM_ONLY=true; shift ;;
        --python-only) PYTHON_ONLY=true; shift ;;
    esac
done

# Install WASM
install_wasm() {
    echo "Installing WASM components..."
    mkdir -p "$INSTALL_DIR/wasm"
    cp "$PROJECT_DIR/whitemagic-rust/pkg/web/"* "$INSTALL_DIR/wasm/"
    echo -e "${GREEN}✓ WASM installed to $INSTALL_DIR/wasm/${NC}"
    echo ""
    echo "To test:"
    echo "  cd $INSTALL_DIR/wasm"
    echo "  python3 -m http.server 8080"
    echo "  # Open http://localhost:8080/demo.html"
}

# Install Python
install_python() {
    echo "Installing Python package..."
    
    # Create venv
    mkdir -p "$INSTALL_DIR"
    if [ ! -d "$INSTALL_DIR/.venv" ]; then
        python3 -m venv "$INSTALL_DIR/.venv"
    fi
    
    # Activate and install
    source "$INSTALL_DIR/.venv/bin/activate"
    pip install --upgrade pip
    
    # Install from local source
    cd "$PROJECT_DIR"
    pip install -e . 2>/dev/null || {
        echo "Installing without setup.py..."
        pip install "$PROJECT_DIR"
    }
    
    echo -e "${GREEN}✓ Python package installed${NC}"
    echo ""
    echo "To use:"
    echo "  source $INSTALL_DIR/.venv/bin/activate"
    echo "  python -c \"from whitemagic import bootstrap; bootstrap()\""
    echo "  python -c \"from whitemagic import memory; print(memory)\""
}

# Main
main() {
    if [ "$WASM_ONLY" = true ]; then
        install_wasm
    elif [ "$PYTHON_ONLY" = true ]; then
        install_python
    else
        install_wasm
        install_python
    fi
    
    echo ""
    echo -e "${GREEN}Installation complete!${NC}"
}

main
