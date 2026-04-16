#!/usr/bin/env bash
# WhiteMagic One-Click Installer
# ==============================
# Install WhiteMagic WASM + Python in one command
#
# Usage:
#   curl -sSL https://whitemagic.ai/install | bash
#   curl -sSL https://whitemagic.ai/install | bash -s -- --wasm-only
#
# Options:
#   --wasm-only     Install only WASM components (no Python)
#   --python-only   Install only Python components (no WASM)
#   --dev           Install development dependencies
#   --no-docker     Skip Docker installation even if available
#   --help          Show this help message

set -euo pipefail

VERSION="18.1.0"
REPO_URL="https://github.com/whitemagic-ai/whitemagic.git"
NPM_PKG="@whitemagic/wasm"
PIP_PKG="whitemagic"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
WASM_ONLY=false
PYTHON_ONLY=false
DEV_MODE=false
NO_DOCKER=false

for arg in "$@"; do
    case $arg in
        --wasm-only)     WASM_ONLY=true; shift ;;
        --python-only)   PYTHON_ONLY=true; shift ;;
        --dev)           DEV_MODE=true; shift ;;
        --no-docker)     NO_DOCKER=true; shift ;;
        --help)          grep '^#' "$0" | sed 's/^# //'; exit 0 ;;
        *)               echo "Unknown option: $arg"; exit 1 ;;
    esac
done

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           WhiteMagic v${VERSION} - One-Click Installer            ║"
echo "║              The Polyglot Memory Ecosystem                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)  echo "linux" ;;
        Darwin*) echo "macos" ;;
        CYGWIN*) echo "windows" ;;
        MINGW*)  echo "windows" ;;
        *)       echo "unknown" ;;
    esac
}

OS=$(detect_os)
echo -e "${GREEN}✓ Detected OS: ${OS}${NC}"

# Check if command exists
has() {
    command -v "$1" &> /dev/null
}

# Install WASM components
install_wasm() {
    echo -e "\n${BLUE}▸ Installing WASM components...${NC}"
    
    # Check for Node.js
    if ! has node; then
        echo -e "${YELLOW}⚠ Node.js not found. Installing via nvm...${NC}"
        if ! has nvm; then
            curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
            export NVM_DIR="$HOME/.nvm"
            [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
        fi
        nvm install --lts
    fi
    
    echo -e "${GREEN}✓ Node.js $(node --version)${NC}"
    
    # Install WASM package
    if has npm; then
        echo -e "${BLUE}  Installing ${NPM_PKG}...${NC}"
        npm install -g ${NPM_PKG}@${VERSION} 2>/dev/null || {
            echo -e "${YELLOW}⚠ npm package not yet published, using direct download${NC}"
            mkdir -p "$HOME/.whitemagic/wasm"
            curl -sSL "https://github.com/whitemagic-ai/whitemagic/releases/download/v${VERSION}/whitemagic-wasm.tar.gz" | \
                tar -xzf - -C "$HOME/.whitemagic/wasm" 2>/dev/null || {
                echo -e "${YELLOW}⚠ Release not found, cloning from source${NC}"
                git clone --depth 1 "$REPO_URL" /tmp/whitemagic 2>/dev/null
                cp -r /tmp/whitemagic/whitemagic-rust/pkg/web/* "$HOME/.whitemagic/wasm/"
            }
        }
    fi
    
    # Verify installation
    if [ -f "$HOME/.whitemagic/wasm/whitemagic_rust.js" ]; then
        echo -e "${GREEN}✓ WASM installed to ~/.whitemagic/wasm/${NC}"
        echo -e "${GREEN}✓ Size: $(du -sh "$HOME/.whitemagic/wasm" | cut -f1)${NC}"
    fi
}

# Install Python components
install_python() {
    echo -e "\n${BLUE}▸ Installing Python components...${NC}"
    
    # Check for Python
    if ! has python3; then
        echo -e "${YELLOW}⚠ Python 3 not found. Please install Python 3.11+${NC}"
        echo -e "  Ubuntu/Debian: sudo apt install python3 python3-pip"
        echo -e "  macOS: brew install python3"
        echo -e "  Windows: choco install python"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION}${NC}"
    
    # Create virtual environment
    INSTALL_DIR="$HOME/.whitemagic"
    mkdir -p "$INSTALL_DIR"
    
    if [ ! -d "$INSTALL_DIR/.venv" ]; then
        echo -e "${BLUE}  Creating virtual environment...${NC}"
        python3 -m venv "$INSTALL_DIR/.venv"
    fi
    
    source "$INSTALL_DIR/.venv/bin/activate"
    
    # Install package
    echo -e "${BLUE}  Installing ${PIP_PKG}...${NC}"
    pip install --upgrade pip
    pip install "${PIP_PKG}==${VERSION}" 2>/dev/null || {
        echo -e "${YELLOW}⚠ pip package not yet published, installing from source${NC}"
        pip install git+"$REPO_URL"@v${VERSION}
    }
    
    echo -e "${GREEN}✓ Python package installed${NC}"
}

# Install development dependencies
install_dev() {
    echo -e "\n${BLUE}▸ Installing development dependencies...${NC}"
    
    # Rust
    if ! has rustc; then
        echo -e "${BLUE}  Installing Rust...${NC}"
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
    fi
    echo -e "${GREEN}✓ Rust $(rustc --version)${NC}"
    
    # wasm-pack
    if ! has wasm-pack; then
        echo -e "${BLUE}  Installing wasm-pack...${NC}"
        cargo install wasm-pack
    fi
    echo -e "${GREEN}✓ wasm-pack installed${NC}"
    
    # Clone repo
    if [ ! -d "$HOME/whitemagic" ]; then
        echo -e "${BLUE}  Cloning repository...${NC}"
        git clone "$REPO_URL" "$HOME/whitemagic"
    fi
    echo -e "${GREEN}✓ Repository cloned to ~/whitemagic${NC}"
}

# Setup Docker
setup_docker() {
    if [ "$NO_DOCKER" = true ]; then
        return
    fi
    
    if has docker; then
        echo -e "\n${BLUE}▸ Setting up Docker...${NC}"
        docker pull whitemagic/wasm:${VERSION} 2>/dev/null || {
            echo -e "${YELLOW}⚠ Docker image not yet published${NC}"
        }
        echo -e "${GREEN}✓ Docker ready${NC}"
    fi
}

# Print success message
print_success() {
    echo -e "\n${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    Installation Complete!                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo "WhiteMagic v${VERSION} is ready!"
    echo ""
    echo "Quick Start:"
    echo ""
    if [ "$WASM_ONLY" = true ] || [ "$PYTHON_ONLY" = false ]; then
        echo "  # Browser (WASM)"
        echo "  open ~/.whitemagic/wasm/demo.html"
        echo ""
        echo "  # Node.js"
        echo "  const wm = require('@whitemagic/wasm');"
        echo "  console.log(wm.wasm_version());"
        echo ""
    fi
    if [ "$PYTHON_ONLY" = true ] || [ "$WASM_ONLY" = false ]; then
        echo "  # Python"
        echo "  source ~/.whitemagic/.venv/bin/activate"
        echo "  python -c \"from whitemagic import WhiteMagic; wm = WhiteMagic()\""
        echo ""
    fi
    echo "Documentation: https://whitemagic.ai/docs"
    echo "GitHub:        https://github.com/whitemagic-ai/whitemagic"
    echo ""
}

# Main installation flow
main() {
    echo -e "${BLUE}Starting installation...${NC}"
    
    # Install components based on flags
    if [ "$WASM_ONLY" = true ]; then
        install_wasm
    elif [ "$PYTHON_ONLY" = true ]; then
        install_python
    else
        install_wasm
        install_python
    fi
    
    # Dev mode
    if [ "$DEV_MODE" = true ]; then
        install_dev
    fi
    
    # Docker
    setup_docker
    
    # Success
    print_success
}

# Run main
main
