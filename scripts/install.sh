#!/bin/sh
# WhiteMagic install script — downloads a release binary and verifies its checksum.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.sh | sh
#   curl -fsSL ... | sh -s -- --version v9.2.1
#   curl -fsSL ... | sh -s -- --ref hero      # install attribution (local marker)
#
# --ref (or WM_INSTALL_REF) is recorded locally in
# <store-root>/install_channel so `wm status` / `wm telemetry status` can show
# how this install arrived. It is sanitized (lowercase, [a-z0-9_-], 24 chars),
# never transmitted, and never fails the install.
#
# After install, the `wm` binary is at ~/.local/bin/wm.
# Add ~/.local/bin to your PATH if it isn't already.
#
# Install gate (alpha): Linux x86-64 and macOS (x86_64/aarch64). macOS
# binaries are checksum-verified like Linux; the site copy stays
# "published, not install-gated" until a real-Mac smoke test passes.
# Windows binaries are published in every release but have no installer
# yet — this script refuses them rather than guessing.
# On Linux x86-64 the fully static (musl) build is preferred when the target
# release provides it; the dynamically linked glibc build requires glibc 2.39+.

set -eu

VERSION=""
TARGET=""
INSTALL_DIR="${HOME}/.local/bin"
REPO="lbailey94/whitemagic"
REF="${WM_INSTALL_REF:-}"

# Site middleware sanitization for install refs: lowercase, [a-z0-9_-],
# capped at 24 chars (whitemagic-site/middleware.ts). Empty means no ref.
sanitize_ref() {
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-' | cut -c1-24
}

# Record the arrival channel locally (best effort; never fails the install,
# never creates lmdb/). Content: install_sh[:ref], atomically renamed into
# place so a reinstall updates it in one step.
write_install_marker() {
    _store_root="${XDG_DATA_HOME:-${HOME}/.local/share}/whitemagic"
    _marker="${_store_root}/install_channel"
    _tmp="${_store_root}/.install_channel.tmp"
    if ! mkdir -p "${_store_root}" 2>/dev/null; then
        return 0
    fi
    if [ -n "${REF}" ]; then
        _value="install_sh:${REF}"
    else
        _value="install_sh"
    fi
    if printf '%s\n' "${_value}" > "${_tmp}" 2>/dev/null \
        && mv "${_tmp}" "${_marker}" 2>/dev/null; then
        return 0
    fi
    rm -f "${_tmp}" 2>/dev/null || true
    return 0
}

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
        --ref) REF="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

REF="$(sanitize_ref "${REF}")"

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
        echo "Specify --version explicitly, e.g.: $0 --version v9.2.1" >&2
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
PLATFORM_LABEL=""

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
    aarch64-apple-darwin)
        ARTIFACT="wm-macos-aarch64"
        PLATFORM_LABEL="macOS arm64"
        ;;
    x86_64-apple-darwin)
        ARTIFACT="wm-macos-x86_64"
        PLATFORM_LABEL="macOS x86_64"
        ;;
    *)
        echo "Unsupported target for this release: ${TARGET}" >&2
        echo "Install-gated targets are Linux x86-64 and macOS (x86_64/aarch64)." >&2
        echo "Windows binaries are published in every release: https://github.com/${REPO}/releases" >&2
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

# Local arrival marker (best effort; never fails the install).
write_install_marker

echo ""
echo "WhiteMagic ${VERSION} installed to ${INSTALL_DIR}/wm"
if [ "$STATIC_BUILD" = "1" ]; then
    echo "Build: fully static (musl) — no glibc requirement."
elif [ -n "$PLATFORM_LABEL" ]; then
    echo "Build: ${PLATFORM_LABEL} — ad-hoc signed by the macOS linker."
else
    echo "Build: dynamically linked (glibc 2.39+ required)."
fi
echo ""
echo "Verify installation:"
echo "  wm --version"
echo ""
echo "Get started:"
echo "  wm grimoire"
echo ""
echo "Fallbacks:"
echo "  wm quickstart                 # 30-second continuity demo (throwaway store)"
echo "  wm serve --profile curated    # dispatch-only MCP server"
echo "  wm doctor                     # diagnostics when something is wrong"
echo ""
if ! echo "$PATH" | grep -q "$INSTALL_DIR"; then
    # Self-wire the shell profile so `wm` works in new terminals — a fresh
    # stranger should never see "wm: not found" right after installing.
    path_line="export PATH=\"${INSTALL_DIR}:\$PATH\""
    path_fixed=0
    profile_found=0
    for rc in "$HOME/.profile" "$HOME/.bashrc" "$HOME/.zshrc"; do
        [ -f "$rc" ] || continue
        profile_found=1
        # Whole-line match only: a commented or stale mention of the path
        # must not count as "already wired" (2026-09-15 review).
        if ! grep -qsxF "$path_line" "$rc"; then
            if printf '\n# Added by the WhiteMagic installer\n%s\n' "$path_line" >> "$rc"; then
                path_fixed=1
            else
                echo "warning: could not write the PATH line to $rc" >&2
            fi
        fi
    done
    if [ "$path_fixed" = "1" ]; then
        echo "PATH wired into your shell profile — open a new terminal, or run now:"
    elif [ "$profile_found" = "1" ]; then
        # A profile exists and already exports the path: never rewrite it.
        # (Reinstall case — the old logic overwrote ~/.profile with `>` here,
        # destroying every unrelated line.)
        echo "PATH already wired in your shell profile — open a new terminal, or run now:"
    else
        # No profile file existed (minimal containers/boxes) — create ~/.profile,
        # which POSIX login shells read.
        printf '# Added by the WhiteMagic installer\n%s\n' "$path_line" > "$HOME/.profile"
        echo "PATH wired into ~/.profile (created) — open a new terminal, or run now:"
    fi
fi
