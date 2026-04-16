#!/bin/bash
# WhiteMagic WASM Build Script
# Builds WebAssembly packages for web and Node.js targets

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUST_DIR="$PROJECT_ROOT/whitemagic-rust"
PKG_DIR="$RUST_DIR/pkg"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v rustc &> /dev/null; then
        log_error "Rust not found. Please install Rust: https://rustup.rs/"
        exit 1
    fi
    
    if ! rustup target list | grep -q "wasm32-unknown-unknown (installed)"; then
        log_info "Installing wasm32-unknown-unknown target..."
        rustup target add wasm32-unknown-unknown
    fi
    
    if ! command -v wasm-pack &> /dev/null; then
        log_info "Installing wasm-pack..."
        curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh
    fi
    
    log_success "Prerequisites satisfied"
}

# Build WASM for web target
build_web() {
    log_info "Building WASM for web target..."
    cd "$RUST_DIR"
    
    # Clean previous build
    rm -rf "$PKG_DIR/web"
    
    # Build with wasm-pack
    wasm-pack build \
        --target web \
        --out-dir pkg/web \
        --no-default-features \
        --features wasm
    
    log_success "Web WASM build complete: $PKG_DIR/web/"
}

# Build WASM for Node.js target
build_nodejs() {
    log_info "Building WASM for Node.js target..."
    cd "$RUST_DIR"
    
    # Clean previous build
    rm -rf "$PKG_DIR/nodejs"
    
    # Build with wasm-pack
    wasm-pack build \
        --target nodejs \
        --out-dir pkg/nodejs \
        --no-default-features \
        --features wasm
    
    log_success "Node.js WASM build complete: $PKG_DIR/nodejs/"
}

# Update package.json versions
update_versions() {
    log_info "Updating package versions..."
    
    VERSION=$(cat "$PROJECT_ROOT/VERSION" | tr -d '[:space:]')
    
    # Update web package.json
    if [ -f "$PKG_DIR/web/package.json" ]; then
        sed -i "s/\"version\": \"[0-9.]*\"/\"version\": \"$VERSION\"/" "$PKG_DIR/web/package.json"
        log_success "Updated web package.json to v$VERSION"
    fi
    
    # Update nodejs package.json
    if [ -f "$PKG_DIR/nodejs/package.json" ]; then
        sed -i "s/\"version\": \"[0-9.]*\"/\"version\": \"$VERSION\"/" "$PKG_DIR/nodejs/package.json"
        log_success "Updated nodejs package.json to v$VERSION"
    fi
}

# Copy WASM files to Python SDK
copy_to_python_sdk() {
    log_info "Copying WASM files to Python SDK..."
    
    PYTHON_WASM_DIR="$PROJECT_ROOT/sdk/python-wasm/whitemagic_wasm/wasm"
    mkdir -p "$PYTHON_WASM_DIR"
    
    cp "$PKG_DIR/web/whitemagic_rust_bg.wasm" "$PYTHON_WASM_DIR/"
    cp "$PKG_DIR/web/whitemagic_rust.js" "$PYTHON_WASM_DIR/"
    
    log_success "WASM files copied to Python SDK"
}

# Print usage
print_usage() {
    echo "WhiteMagic WASM Build Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --web       Build web target only"
    echo "  --nodejs    Build Node.js target only"
    echo "  --all       Build all targets (default)"
    echo "  --sdk       Copy WASM files to Python SDK after build"
    echo "  --publish   Publish to npm after build (requires auth)"
    echo "  --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0              # Build all targets"
    echo "  $0 --web        # Build web target only"
    echo "  $0 --all --sdk  # Build all and copy to Python SDK"
}

# Main
main() {
    local build_web=false
    local build_nodejs=false
    local copy_sdk=false
    local publish=false
    
    # Parse arguments
    if [ $# -eq 0 ]; then
        build_web=true
        build_nodejs=true
    fi
    
    while [ $# -gt 0 ]; do
        case $1 in
            --web)
                build_web=true
                shift
                ;;
            --nodejs)
                build_nodejs=true
                shift
                ;;
            --all)
                build_web=true
                build_nodejs=true
                shift
                ;;
            --sdk)
                copy_sdk=true
                shift
                ;;
            --publish)
                publish=true
                shift
                ;;
            --help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
    
    # Execute builds
    check_prerequisites
    
    if [ "$build_web" = true ]; then
        build_web
    fi
    
    if [ "$build_nodejs" = true ]; then
        build_nodejs
    fi
    
    update_versions
    
    if [ "$copy_sdk" = true ]; then
        copy_to_python_sdk
    fi
    
    if [ "$publish" = true ]; then
        log_info "Publishing to npm..."
        cd "$PKG_DIR/web"
        npm publish --access public
        log_success "Published to npm"
    fi
    
    log_success "WASM build complete!"
    echo ""
    echo "Outputs:"
    [ "$build_web" = true ] && echo "  - Web:     $PKG_DIR/web/"
    [ "$build_nodejs" = true ] && echo "  - Node.js: $PKG_DIR/nodejs/"
    [ "$copy_sdk" = true ] && echo "  - Python:  $PROJECT_ROOT/sdk/python-wasm/whitemagic_wasm/wasm/"
}

main "$@"
