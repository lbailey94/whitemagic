#!/usr/bin/env bash
# WhiteMagic Rust Bridge Builder
# Compiles whitemagic_rust and installs it for both .venv and system Python.
#
# Usage:
#   bash scripts/build_rust_bridge.sh          # Build + install into .venv
#   bash scripts/build_rust_bridge.sh --global  # Also install system-wide
#
# Called automatically by session_startup.py when WM_AUTO_BUILD_RUST_BRIDGE=1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUST_DIR="$PROJECT_ROOT/whitemagic-rust"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[rust-bridge]${NC} $*"; }
warn()  { echo -e "${YELLOW}[rust-bridge]${NC} $*"; }
error() { echo -e "${RED}[rust-bridge]${NC} $*" >&2; }

# ── Pre-flight checks ────────────────────────────────────────────
check_prerequisites() {
    if ! command -v rustc &>/dev/null; then
        error "rustc not found. Install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
        exit 1
    fi
    if ! command -v cargo &>/dev/null; then
        error "cargo not found."
        exit 1
    fi
    if ! command -v maturin &>/dev/null; then
        # Try .venv maturin
        if [ -x "$PROJECT_ROOT/.venv/bin/maturin" ]; then
            MATURIN="$PROJECT_ROOT/.venv/bin/maturin"
        else
            warn "maturin not found. Installing..."
            pip install maturin 2>/dev/null || "$VENV_PYTHON" -m pip install maturin
            MATURIN="maturin"
        fi
    else
        MATURIN="maturin"
    fi
    if [ ! -d "$RUST_DIR" ]; then
        error "Rust source directory not found: $RUST_DIR"
        exit 1
    fi
    info "Prerequisites OK (rustc $(rustc --version | awk '{print $2}'), maturin)"
}

# ── Check if already compiled and up-to-date ─────────────────────
check_existing() {
    if "$VENV_PYTHON" -c "import whitemagic_rust; print(f'whitemagic_rust OK: {len([f for f in dir(whitemagic_rust) if not f.startswith(\"_\")])} functions')" 2>/dev/null; then
        # Check if source is newer than the .so
        SO_FILE=$("$VENV_PYTHON" -c "import whitemagic_rust, pathlib; print(pathlib.Path(whitemagic_rust.__file__).parent)" 2>/dev/null)
        if [ -n "$SO_FILE" ]; then
            NEWEST_SRC=$(find "$RUST_DIR/src" -name "*.rs" -newer "$SO_FILE/whitemagic_rust.cpython-"*.so 2>/dev/null | head -1)
            if [ -z "$NEWEST_SRC" ]; then
                info "Rust bridge is up-to-date (no source changes)"
                return 0
            else
                info "Source changed: $NEWEST_SRC — rebuilding"
                return 1
            fi
        fi
    fi
    return 1
}

# ── Build ─────────────────────────────────────────────────────────
build_rust() {
    info "Building whitemagic_rust (release mode)..."
    cd "$RUST_DIR"

    # Use maturin develop for .venv install
    if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
        VIRTUAL_ENV="$PROJECT_ROOT/.venv" "$MATURIN" develop --release 2>&1 | tail -5
    else
        "$MATURIN" develop --release 2>&1 | tail -5
    fi

    # Verify
    if "$VENV_PYTHON" -c "import whitemagic_rust" 2>/dev/null; then
        FUNC_COUNT=$("$VENV_PYTHON" -c "import whitemagic_rust; print(len([f for f in dir(whitemagic_rust) if not f.startswith('_')]))")
        info "✅ Build successful: $FUNC_COUNT functions available"
    else
        error "Build appeared to succeed but import failed"
        exit 1
    fi
}

# ── System-wide install (optional) ───────────────────────────────
install_global() {
    info "Installing system-wide..."
    cd "$RUST_DIR"

    # Build a wheel
    "$MATURIN" build --release 2>&1 | tail -3

    # Find the wheel
    WHEEL=$(ls -t "$RUST_DIR/target/wheels/"whitemagic_rust-*.whl 2>/dev/null | head -1)
    if [ -z "$WHEEL" ]; then
        warn "No wheel found, trying pip install"
        pip install --user "$RUST_DIR" 2>/dev/null || true
    else
        pip install --user --force-reinstall "$WHEEL" 2>/dev/null || \
            pip install --user --force-reinstall --break-system-packages "$WHEEL" 2>/dev/null || \
            warn "System-wide install failed (PEP 668). Use .venv/bin/python instead."
    fi
}

# ── Main ──────────────────────────────────────────────────────────
main() {
    info "WhiteMagic Rust Bridge Builder"
    check_prerequisites

    if check_existing; then
        # Already up-to-date, skip unless --force
        if [[ "${1:-}" != "--force" ]]; then
            return 0
        fi
    fi

    build_rust

    if [[ "${1:-}" == "--global" ]]; then
        install_global
    fi

    info "Done."
}

main "$@"
