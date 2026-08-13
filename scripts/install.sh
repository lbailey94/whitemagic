#!/bin/sh
# WhiteMagic v5 install script — downloads a release binary and verifies its checksum.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/lucas/whitemagic/main/scripts/install.sh | sh
#   curl -fsSL ... | sh -s -- --version v5.8.0 --target x86_64-unknown-linux-gnu
#
# After install, the `wm` binary is at ~/.local/bin/wm.
# Add ~/.local/bin to your PATH if it isn't already.

set -eu

VERSION=""
TARGET=""
INSTALL_DIR="${HOME}/.local/bin"
REPO="lucas/whitemagic"

# Detect platform if not specified
detect_target() {
    os="$(uname -s)"
    arch="$(uname -m)"
    case "$os" in
        Linux) os="unknown-linux-gnu" ;;
        Darwin) os="apple-darwin" ;;
        *) echo "Unsupported OS: $os" >&2; exit 1 ;;
    esac
    case "$arch" in
        x86_64|amd64) arch="x86_64" ;;
        arm64|aarch64) arch="aarch64" ;;
        *) echo "Unsupported arch: $arch" >&2; exit 1 ;;
    esac
    echo "${arch}-${os}"
}

# Parse args
while [ $# -gt 0 ]; do
    case "$1" in
        --version) VERSION="$2"; shift 2 ;;
        --target) TARGET="$2"; shift 2 ;;
        --dir) INSTALL_DIR="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$TARGET" ]; then
    TARGET="$(detect_target)"
fi

if [ -z "$VERSION" ]; then
    # Fetch latest release tag
    VERSION="$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
        | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')"
    if [ -z "$VERSION" ]; then
        echo "Could not determine latest release version." >&2
        echo "Specify --version v5.8.0 explicitly." >&2
        exit 1
    fi
fi

echo "Installing WhiteMagic ${VERSION} for ${TARGET}..."

# Map target to artifact name
case "$TARGET" in
    *linux*) ARTIFACT="wm-linux-x86_64" ;;
    *darwin*x86_64*) ARTIFACT="wm-macos-x86_64" ;;
    *darwin*aarch64*) ARTIFACT="wm-macos-aarch64" ;;
    *windows*) ARTIFACT="wm-windows-x86_64.exe" ;;
    *) echo "Unsupported target: $TARGET" >&2; exit 1 ;;
esac

BASE_URL="https://github.com/${REPO}/releases/download/${VERSION}"
BINARY_URL="${BASE_URL}/${ARTIFACT}"
CHECKSUM_URL="${BASE_URL}/${ARTIFACT}.sha256"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "Downloading binary..."
curl -fsSL "$BINARY_URL" -o "${TMPDIR}/wm"
curl -fsSL "$CHECKSUM_URL" -o "${TMPDIR}/wm.sha256"

echo "Verifying checksum..."
# sha256sum on Linux, shasum on macOS
if command -v sha256sum >/dev/null 2>&1; then
    (cd "$TMPDIR" && sha256sum -c wm.sha256)
else
    (cd "$TMPDIR" && shasum -a 256 -c wm.sha256)
fi

echo "Installing to ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
chmod +x "${TMPDIR}/wm"
mv "${TMPDIR}/wm" "${INSTALL_DIR}/wm"

echo ""
echo "WhiteMagic ${VERSION} installed to ${INSTALL_DIR}/wm"
echo ""
echo "Verify installation:"
echo "  wm --version"
echo ""
echo "Quick start:"
echo "  wm quickstart"
echo "  wm serve --profile curated"
echo ""
echo "Health check:"
echo "  wm doctor"
echo ""
if ! echo "$PATH" | grep -q "$INSTALL_DIR"; then
    echo "NOTE: ${INSTALL_DIR} is not in your PATH."
    echo "Add it with: export PATH=\"${INSTALL_DIR}:\$PATH\""
fi
