#!/usr/bin/env bash
# Portable no-network qualification for an explicitly selected WM Gen3
# binary. This candidate runs against a caller-supplied source build in CI or
# an explicitly pinned installed artifact locally.
set -Eeuo pipefail

WM_BINARY="${WM_BINARY:-${WM:-}}"
EXPECTED_SHA256="${WM_EXPECTED_SHA256:-}"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == Linux ]] || fail "Linux is required for user+network namespace qualification"
[[ -n "$WM_BINARY" ]] || fail "set WM_BINARY (or WM) to the explicit binary under test"
[[ -x "$WM_BINARY" ]] || fail "WM_BINARY is not executable: $WM_BINARY"
actual_sha="$(sha256sum -- "$WM_BINARY" | awk '{print $1}')"
if [[ -n "$EXPECTED_SHA256" && "$actual_sha" != "$EXPECTED_SHA256" ]]; then
  fail "binary SHA-256 mismatch: expected $EXPECTED_SHA256, got $actual_sha"
fi
version="$("$WM_BINARY" --version 2>&1 | head -n 1)"
[[ "$version" =~ ^wm[[:space:]]+[^[:space:]]+$ ]] || fail "could not identify binary version from: $version"
version_number="${version#wm }"
source_rev="${WM_SOURCE_REVISION:-unspecified}"

printf '[identity] binary=%s\n' "$WM_BINARY"
printf '[identity] sha256=%s expected_sha256=%s version=%s\n' "$actual_sha" "${EXPECTED_SHA256:-unspecified}" "$version"
printf '[identity] platform=%s source_revision_claim=%s profile=full\n' "$(uname -srmo)" "$source_rev"
printf '[identity] binary_source_mapping=unverified unless the caller establishes the build from this revision\n'

tmp="$(mktemp -d "${TMPDIR:-/tmp}/wm-no-network.XXXXXXXX")" || fail "cannot create owned temporary workspace"
cleanup() { rm -rf -- "$tmp"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
mkdir -p "$tmp/home" "$tmp/xdg-data" "$tmp/xdg-config" "$tmp/store"

# Do not let user credentials, store selection, or provider settings enter the
# isolated server process. The binary and store path are explicit.
export WM_BINARY
export WM_NO_NETWORK_STORE="$tmp/store"
export WM_NO_NETWORK_HOME="$tmp/home"
export WM_NO_NETWORK_XDG_DATA="$tmp/xdg-data"
export WM_NO_NETWORK_XDG_CONFIG="$tmp/xdg-config"
export WM_NO_NETWORK_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export WM_NO_NETWORK_VERSION="$version_number"
export WM_NO_NETWORK_SOURCE_REVISION="$source_rev"

set +e
timeout --signal=TERM --kill-after=5s 150s \
  unshare --user --map-root-user --net \
  bash "$HERE/no_network_inner.sh" "$HERE/zero_egress_rpc.py"
rc=$?
set -e
if [[ $rc -eq 124 || $rc -eq 137 ]]; then
  fail "bounded no-network run exceeded 150 seconds; no proof produced"
elif [[ $rc -eq 42 ]]; then
  fail "HOST POLICY blocked the egress control (EPERM); this is not product failure or namespace proof"
elif [[ $rc -ne 0 ]]; then
  fail "user+network namespace run failed (exit $rc); namespace unavailability is not a pass"
fi
printf '[proof] PASS: profile=full Gen3 %s create+recall succeeded with lo DOWN; egress control was route-blocked. This is scoped local evidence, not a universal zero-egress or CI claim.\n' "$version_number"
