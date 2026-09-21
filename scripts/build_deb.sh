#!/bin/sh
# Build a .deb from a released wm binary (no compilation, no maintainer
# scripts, no dependencies — the binary is the fully static musl build).
#
# Usage: sh scripts/build_deb.sh <binary> <amd64|arm64> <version> <outdir>
#
# Produces <outdir>/wm-linux-<arch>.deb plus a .sha256 beside it.
# Requires dpkg-deb (Ubuntu runners and release workflows only).

set -eu

BIN="${1:?usage: build_deb.sh <binary> <amd64|arm64> <version> <outdir>}"
ARCH="${2:?arch required (amd64|arm64)}"
VERSION="${3:?version required}"
OUTDIR="${4:?outdir required}"

[ -f "$BIN" ] || { echo "binary not found: $BIN" >&2; exit 1; }
case "$ARCH" in
    amd64|arm64) ;;
    *) echo "unsupported deb architecture: $ARCH" >&2; exit 1 ;;
esac

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/pkg/DEBIAN" "$WORK/pkg/usr/bin"
install -m 0755 "$BIN" "$WORK/pkg/usr/bin/wm"
SIZE="$(du -sk "$WORK/pkg" | awk '{print $1}')"

cat > "$WORK/pkg/DEBIAN/control" <<EOF
Package: whitemagic
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: WhiteMagic AI <lbailey94@protonmail.com>
Installed-Size: ${SIZE}
Section: utils
Priority: optional
Homepage: https://www.whitemagic.dev
Description: Local-first memory layer for AI agents (static single binary)
 WhiteMagic gives an MCP-capable agent durable project memory, session
 continuity, and governed audit — with no hosted service, no off-device
 telemetry, and no runtime network requirement. This package installs the
 fully static musl build of the wm binary to /usr/bin/wm.
EOF

mkdir -p "$OUTDIR"
dpkg-deb --build --root-owner-group "$WORK/pkg" "$OUTDIR/wm-linux-${ARCH}.deb"
sha256sum "$OUTDIR/wm-linux-${ARCH}.deb" > "$OUTDIR/wm-linux-${ARCH}.deb.sha256"
echo "built $OUTDIR/wm-linux-${ARCH}.deb"
