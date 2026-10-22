#!/usr/bin/env bash
# Invoked only by zero_egress_test.sh inside a fresh user+network namespace.
set -Eeuo pipefail

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
[[ -n "${WM_BINARY:-}" && -x "$WM_BINARY" ]] || fail "explicit test binary unavailable in namespace"
[[ -d "${WM_NO_NETWORK_STORE:-}" ]] || fail "owned temporary store missing"

links="$(ip -o link show | awk -F': ' '{print $2}' | sed 's/@.*//')"
count="$(ip -o link show | wc -l | tr -d ' ')"
[[ "$count" == 1 && "$links" == lo ]] || {
  ip -o link show >&2
  fail "namespace must contain only loopback; found $count link(s): $links"
}
ip link set lo down || fail "could not bring namespace loopback down"
if ip -o link show lo | grep -qE '<[^>]*UP'; then
  fail "loopback remains UP after request to lower it"
fi
v4routes="$(ip -4 route show)"
v6routes="$(ip -6 route show)"
[[ -z "$v4routes" && -z "$v6routes" ]] || fail "namespace has routes despite isolated link set: v4='$v4routes' v6='$v6routes'"
printf '[namespace] user+network namespace; only lo present and DOWN; IPv4/IPv6 route tables empty\n'

python3 "$1" --check-egress

env -i PATH="$WM_NO_NETWORK_PATH" HOME="$WM_NO_NETWORK_HOME" \
  XDG_DATA_HOME="$WM_NO_NETWORK_XDG_DATA" \
  XDG_CONFIG_HOME="$WM_NO_NETWORK_XDG_CONFIG" \
  WM_HOMEOSTASIS_FROZEN=1 \
  WM_BINARY="$WM_BINARY" WM_VERSION="$WM_NO_NETWORK_VERSION" \
  WM_SOURCE_REVISION="$WM_NO_NETWORK_SOURCE_REVISION" STORE="$WM_NO_NETWORK_STORE" \
  python3 "$1"
