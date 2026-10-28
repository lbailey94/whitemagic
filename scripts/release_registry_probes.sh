#!/usr/bin/env bash
# Verify exact package versions and channel selectors for the release family.
set -euo pipefail

VERSION="${1:?usage: release_registry_probes.sh <version> [--dry-run]}"
DRY_RUN=false
if [ "${2:-}" = "--dry-run" ]; then DRY_RUN=true; fi
UA="whitemagic-release/1.0 (lbailey94@protonmail.com)"
TRIES="${WM_RELEASE_PROBE_TRIES:-40}"
DELAY="${WM_RELEASE_PROBE_DELAY:-15}"

if $DRY_RUN; then
  echo "[dry-run] verify release-family crate versions, npm selectors, and Docker Hub tag $VERSION"
  exit 0
fi

probe_exact() { # <label> <url> <jq-expression>
  local label="$1" url="$2" expr="$3" got="" i
  for i in $(seq 1 "$TRIES"); do
    got=$(curl -fsS -m 20 -A "$UA" "$url" 2>/dev/null | jq -r "$expr" 2>/dev/null || true)
    if [ "$got" = "$VERSION" ]; then echo "  $label: $got"; return 0; fi
    if [ "$i" -lt "$TRIES" ]; then sleep "$DELAY"; fi
  done
  echo "ERROR: $label reports '${got:-nothing}' (want exact release $VERSION)" >&2
  return 1
}

npm_json=$(curl -fsS -m 20 -A "$UA" "https://registry.npmjs.org/whitemagic-mcp")
npm_latest=$(printf '%s' "$npm_json" | jq -r '.["dist-tags"].latest // ""')
if [[ "$VERSION" =~ ^9\.[0-9]+\.[0-9]+$ ]]; then
  # Gen2 uses the legacy root crate and owns npm latest. An already newer
  # stable selector is accepted without a downgrade.
  probe_exact "crates.io (whitemagic)" \
    "https://crates.io/api/v1/crates/whitemagic/$VERSION" '.version.num'
  if ! [[ "$npm_latest" =~ ^9\.[0-9]+\.[0-9]+$ ]]; then
    echo "ERROR: npm latest is '${npm_latest:-missing}'; expected a stable Gen2 9.x.y version" >&2
    exit 1
  fi
  latest_policy=$(python3 scripts/release_channels.py "$VERSION" false "$npm_latest")
  if [ "$latest_policy" = "skip" ]; then
    echo "  npm (whitemagic-mcp latest): $npm_latest (newer stable; no downgrade)"
  else
    probe_exact "npm (whitemagic-mcp latest)" \
      "https://registry.npmjs.org/whitemagic-mcp" '.["dist-tags"].latest'
  fi
else
  # Gen3 publishes six packages and stays on npm next. The stable selector
  # must remain a stable Gen2 version; next may be ahead but never moves back.
  for crate in wm-gen3-core wm-gen3-shm wm-gen3-vault wm-gen3-systemone \
    wm-gen3-zeropointfive wm-gen3-harness; do
    probe_exact "crates.io ($crate)" \
      "https://crates.io/api/v1/crates/$crate/$VERSION" '.version.num'
  done
  if ! [[ "$npm_latest" =~ ^9\.[0-9]+\.[0-9]+$ ]]; then
    echo "ERROR: npm latest is '${npm_latest:-missing}'; expected a stable Gen2 9.x.y version" >&2
    exit 1
  fi
  echo "  npm (whitemagic-mcp latest): $npm_latest (stable Gen2 preserved)"

  npm_next=$(printf '%s' "$npm_json" | jq -r '.["dist-tags"].next // ""')
  if [ -z "$npm_next" ]; then
    echo "ERROR: npm next selector is missing" >&2
    exit 1
  fi
  next_policy=$(python3 scripts/release_channels.py "$VERSION" false "$npm_next")
  if [ "$next_policy" = "skip" ]; then
    echo "  npm (whitemagic-mcp next): $npm_next (newer than release; no downgrade)"
  else
    probe_exact "npm (whitemagic-mcp next)" \
      "https://registry.npmjs.org/whitemagic-mcp" '.["dist-tags"].next'
  fi
fi

probe_exact "Docker Hub (tag $VERSION)" \
  "https://hub.docker.com/v2/repositories/lbailey94/whitemagic/tags/$VERSION" '.name'
