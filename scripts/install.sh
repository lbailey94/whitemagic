#!/bin/sh
# WhiteMagic install script — downloads a release binary and verifies its checksum.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.sh | sh
#   curl -fsSL ... | sh -s -- --version v7.0.0-alpha.4
#
# After install, the `wm` binary is at ~/.local/bin/wm.
# Add ~/.local/bin to your PATH if it isn't already.
#
# Supported platform (private alpha): Linux x86-64 only.
# On Linux x86-64 the fully static (musl) build is preferred when the target
# release provides it; the dynamically linked glibc build requires glibc 2.39+.

set -eu

VERSION=""
TARGET=""
INSTALL_DIR="${HOME}/.local/bin"
REPO="lbailey94/whitemagic"

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
    # Fetch the most recent release INCLUDING prereleases.
    # (releases/latest skips prereleases, which would silently install an
    # older stable during the alpha phase. Revisit at public beta.)
    VERSION="$(curl -fsSL "https://api.github.com/repos/${REPO}/releases?per_page=1" \
        | grep '"tag_name"' | head -1 | sed -E 's/.*"([^"]+)".*/\1/')"
    if [ -z "$VERSION" ]; then
        echo "Could not determine latest release version." >&2
        echo "Specify --version explicitly, e.g.: $0 --version v7.0.0-alpha.1" >&2
        exit 1
    fi
fi

echo "Installing WhiteMagic ${VERSION} for ${TARGET}..."

# Map target to artifact name. Only Linux x86-64 has passed an install gate;
# other targets are refused rather than pointed at artifacts that do not exist.
# On Linux x86-64 the static musl build wins when present; otherwise fall back
# to the glibc build after verifying the local glibc meets its minimum.
glibc_at_least() {
    # $1 = major, $2 = minor
    _v="$(getconf GNU_LIBC_VERSION 2>/dev/null || true)"
    [ -n "$_v" ] || return 1
    _maj="$(echo "$_v" | sed -E 's/[^0-9]*([0-9]+)\.([0-9]+).*/\1/')"
    _min="$(echo "$_v" | sed -E 's/[^0-9]*([0-9]+)\.([0-9]+).*/\2/')"
    [ -n "$_maj" ] && [ -n "$_min" ] || return 1
    [ "$_maj" -gt "$1" ] || { [ "$_maj" -eq "$1" ] && [ "$_min" -ge "$2" ]; }
}

artifact_available() {
    code="$(curl -fsIL -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || echo 000)"
    [ "$code" = "200" ]
}

BASE_URL="https://github.com/${REPO}/releases/download/${VERSION}"
STATIC_BUILD=0

case "$TARGET" in
    x86_64-unknown-linux-musl)
        ARTIFACT="wm-linux-x86_64-musl"
        STATIC_BUILD=1
        ;;
    x86_64-unknown-linux-gnu)
        if artifact_available "${BASE_URL}/wm-linux-x86_64-musl.sha256"; then
            ARTIFACT="wm-linux-x86_64-musl"
            STATIC_BUILD=1
        else
            # Older releases ship only the dynamically linked build.
            ARTIFACT="wm-linux-x86_64"
            if ! glibc_at_least 2 39; then
                echo "This release provides no static build for your platform," >&2
                echo "and the dynamic build requires glibc 2.39+ (found: $(getconf GNU_LIBC_VERSION 2>/dev/null || echo 'unknown'))." >&2
                echo "Upgrade your distribution's glibc, or install a newer WhiteMagic release." >&2
                exit 1
            fi
        fi
        ;;
    *)
        echo "Unsupported target for this release: ${TARGET}" >&2
        echo "The private alpha supports Linux x86-64 only." >&2
        exit 1
        ;;
esac

BINARY_URL="${BASE_URL}/${ARTIFACT}"
CHECKSUM_URL="${BASE_URL}/${ARTIFACT}.sha256"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "Downloading binary..."
curl -fsSL "$BINARY_URL" -o "${TMPDIR}/${ARTIFACT}"
curl -fsSL "$CHECKSUM_URL" -o "${TMPDIR}/checksum.sha256"

echo "Verifying checksum..."
# Release checksum lines may reference the pre-rename build name ("wm") rather
# than the distributed artifact name. Honor whatever name the manifest uses.
BINARY_PATH="${TMPDIR}/${ARTIFACT}"
expected="$(sed -E 's/^[0-9a-fA-F]{64}[[:space:]]+\*?(.+)$/\1/' "${TMPDIR}/checksum.sha256" | head -1)"
if [ -n "$expected" ] && [ "$expected" != "$ARTIFACT" ]; then
    mv "${TMPDIR}/${ARTIFACT}" "${TMPDIR}/${expected}"
    BINARY_PATH="${TMPDIR}/${expected}"
fi
# sha256sum on Linux, shasum on macOS
if command -v sha256sum >/dev/null 2>&1; then
    (cd "$TMPDIR" && sha256sum -c checksum.sha256)
else
    (cd "$TMPDIR" && shasum -a 256 -c checksum.sha256)
fi

echo "Installing to ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
mv "${BINARY_PATH}" "${INSTALL_DIR}/wm"
chmod +x "${INSTALL_DIR}/wm"

echo ""
echo "WhiteMagic ${VERSION} installed to ${INSTALL_DIR}/wm"
if [ "$STATIC_BUILD" = "1" ]; then
    echo "Build: fully static (musl) — no glibc requirement."
else
    echo "Build: dynamically linked (glibc 2.39+ required)."
fi
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
