#!/bin/sh
# wm-seed installer — curl | sh
# Downloads the latest wm-seed binary from GitHub Releases
# Usage: curl https://whitemagic.dev/install.sh | sh

set -e

GITHUB_OWNER="lbailey94"
GITHUB_REPO="whitemagic"
BINARY_NAME="wm-seed"
INSTALL_DIR="/usr/local/bin"

# Detect OS and architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Linux*)  OS="linux";;
    Darwin*) OS="macos";;
    *) echo "❌ Unsupported OS: $OS"; exit 1;;
esac

case "$ARCH" in
    x86_64|amd64)  ARCH="x86_64";;
    aarch64|arm64) ARCH="aarch64";;
    *) echo "❌ Unsupported architecture: $ARCH"; exit 1;;
esac

ASSET_NAME="${BINARY_NAME}-${OS}-${ARCH}"
RELEASES_URL="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest"

echo "🔍 Detecting latest release..."
LATEST_URL="$(curl -sL -o /dev/null -w '%{url_effective}' "${RELEASES_URL}")"
LATEST_TAG="$(basename "${LATEST_URL}")"

if [ -z "${LATEST_TAG}" ] || [ "${LATEST_TAG}" = "releases" ]; then
    echo "❌ Could not determine latest release. Please check https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases"
    exit 1
fi

DOWNLOAD_URL="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases/download/${LATEST_TAG}/${ASSET_NAME}"

echo "📦 Downloading wm-seed ${LATEST_TAG} for ${OS}/${ARCH}..."
TMP_FILE="$(mktemp)"
curl -sL -o "${TMP_FILE}" "${DOWNLOAD_URL}"

# Download checksum file
CHECKSUM_URL="${DOWNLOAD_URL}.sha256"
CHECKSUM_TMP="$(mktemp)"
if curl -sLf -o "${CHECKSUM_TMP}" "${CHECKSUM_URL}" 2>/dev/null; then
    echo "🔐 Verifying checksum..."
    EXPECTED_HASH="$(cut -d' ' -f1 < "${CHECKSUM_TMP}")"
    ACTUAL_HASH="$(sha256sum "${TMP_FILE}" | cut -d' ' -f1)"
    if [ "${EXPECTED_HASH}" != "${ACTUAL_HASH}" ]; then
        echo "❌ Checksum verification failed!"
        echo "   Expected: ${EXPECTED_HASH}"
        echo "   Actual:   ${ACTUAL_HASH}"
        rm -f "${TMP_FILE}" "${CHECKSUM_TMP}"
        exit 1
    fi
    echo "✅ Checksum verified."
    rm -f "${CHECKSUM_TMP}"
else
    echo "⚠️  No checksum file found — skipping verification."
fi

# Make executable and install
chmod +x "${TMP_FILE}"

echo "📥 Installing to ${INSTALL_DIR}/${BINARY_NAME}..."
if [ -w "${INSTALL_DIR}" ]; then
    mv "${TMP_FILE}" "${INSTALL_DIR}/${BINARY_NAME}"
else
    echo "🔐 sudo required to install to ${INSTALL_DIR}:"
    sudo mv "${TMP_FILE}" "${INSTALL_DIR}/${BINARY_NAME}"
fi

rm -f "${TMP_FILE}"

echo ""
echo "✅ wm-seed ${LATEST_TAG} installed successfully!"
echo ""
echo "Quick start:"
echo "  wm-seed serve          # Launch MCP stdio server (30 tools)"
echo "  wm-seed init           # Initialize state directory with seed memories"
echo "  wm-seed --help         # Show all commands"
echo ""
echo "Claude Desktop config:"
echo '  {"mcpServers":{"whitemagic":{"command":"wm-seed","args":["serve"]}}}'
