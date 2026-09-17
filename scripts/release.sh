#!/usr/bin/env bash
# WhiteMagic release script — orchestration + verification (F4, 9.1.9).
#
# Usage:
#   scripts/release.sh <version> [--dry-run] [--skip-ci-wait]
#
# Example:
#   scripts/release.sh 9.1.9
#   scripts/release.sh 9.1.9 --dry-run
#
# Division of labor (9.1.8 lesson): the tag-triggered `release.yml` workflow
# owns the five channels — it builds the 5-platform binaries, signs the
# manifest, generates SBOMs, and publishes crates.io → npm → Docker Hub →
# MCP registry (its `registries` job). This script orchestrates the release
# and then VERIFIES every channel:
#
#   bump → release commit → push → CI gate → signed tag → [release.yml] →
#   assets + checksum + registries + release-health verification.
#
# The pre-9.1.9 script also built binaries and published registries locally;
# that duplicated the workflow (double-publish risk) and was retired. The
# manual fallback is re-running the workflow itself — never a hand-upload
# (provenance lesson, 2026-09-15: local assets desynced the signed manifest).
#
# Ordering: the release commit is pushed first, CI on that commit is watched
# to green, and only then is the signed tag created and pushed — release.yml
# publishes on tag push, so tagging before the gate would make a red CI
# unable to prevent publication. --skip-ci-wait overrides the gate loudly.
#
# Conventions kept:
#   - workspace version = npm package version = server.json version
#   - image tags: vX.Y.Z + major tag (X) flipped to latest (by the workflow)
#   - registry identifier: docker.io/lbailey94/whitemagic:X (major)
set -euo pipefail

VERSION="${1:?usage: scripts/release.sh <version> [--dry-run] [--skip-ci-wait]}"
DRY_RUN=false; SKIP_CI_WAIT=false
for arg in "${@:2}"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --skip-ci-wait) SKIP_CI_WAIT=true ;;
    *) echo "unknown flag: $arg"; exit 1 ;;
  esac
done
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
UA="whitemagic-release/1.0 (lbailey94@protonmail.com)"

banner() { echo; echo "━━━━ $* ━━━"; }

# ── preflight ────────────────────────────────────────────────────────────
banner "PREFLIGHT"
[ -z "$(git status --porcelain)" ] || { echo "ERROR: dirty tree — commit or stash first"; exit 1; }
[ "$(git branch --show-current)" = "main" ] || { echo "ERROR: run from main"; exit 1; }
git fetch origin main --quiet
[ -z "$(git rev-list HEAD..origin/main)" ] || { echo "ERROR: local main is behind origin — pull first"; exit 1; }
CUR=$(grep -m1 '^version = ' Cargo.toml | sed 's/version = "\(.*\)"/\1/')
echo "workspace: $CUR → $VERSION"
python3 scripts/version_truth.py --check \
  || { echo "ERROR: version-truth drift — every surface must agree before a release"; exit 1; }
for tool in gh cargo python3 jq curl; do command -v "$tool" >/dev/null || { echo "ERROR: $tool missing"; exit 1; }; done
if ! $DRY_RUN; then
  gh auth status >/dev/null 2>&1 || { echo "ERROR: gh not authed"; exit 1; }
fi
echo "preflight ok"

# ── version bump ─────────────────────────────────────────────────────────
banner "VERSION BUMP → $VERSION"
if $DRY_RUN; then
  echo "[dry-run] python3 scripts/version_truth.py --set $VERSION (all listed"
  echo "[dry-run]   surfaces: Cargo.toml pins, npm package/server/MCPB, Dockerfile"
  echo "[dry-run]   labels, CITATION, docs, skill.md, README, PRIVACY_POLICY.md,"
  echo "[dry-run]   install examples, rust-toolchain.toml; CHANGELOG ceremony is"
  echo "[dry-run]   checked separately)"
  echo "[dry-run] cargo check (refresh Cargo.lock); commit + push; tag v$VERSION"
else
  python3 scripts/version_truth.py --set "$VERSION"
  cargo check --workspace --quiet 2>/dev/null || cargo check -p wm-core --quiet   # refresh Cargo.lock
  git add -A
  git -c user.name="WhiteMagic AI" -c user.email="lbailey94@protonmail.com" commit -m "release: v$VERSION"
  git push origin main
fi

# ── tag + CI ─────────────────────────────────────────────────────────────
banner "TAG + CI"
# Source provenance: sign the tag when a signing key is configured; fall
# back to an annotated (unsigned) tag with a loud warning otherwise.
if git config --get user.signingkey >/dev/null 2>&1 \
  || git config --get gpg.format >/dev/null 2>&1; then
  SIGNED_TAG=1
else
  SIGNED_TAG=0
fi
if $DRY_RUN; then
  echo "[dry-run] wait for CI on the release commit (gh run watch); abort before tagging if red"
  if [ "$SIGNED_TAG" = "1" ]; then
    echo "[dry-run] git tag -s v$VERSION -m 'WhiteMagic v$VERSION' (signed)"
  else
    echo "[dry-run] git tag -a v$VERSION -m 'WhiteMagic v$VERSION' (UNSIGNED —"
    echo "[dry-run]   configure user.signingkey for source provenance)"
  fi
  echo "[dry-run] git push origin v$VERSION (release.yml builds + publishes)"
else
  # Pre-tag CI gate. CI runs on the main push from the bump stage; watch that
  # run BEFORE the tag exists. release.yml publishes on tag push, so a red CI
  # discovered after tagging cannot prevent publication (the v9.1.5 incident:
  # release.sh aborted at its post-tag CI gate while the release was already
  # out). Nothing is tagged until this commit is green.
  if $SKIP_CI_WAIT; then
    echo "WARN: --skip-ci-wait — tagging $(git rev-parse --short HEAD) without a CI gate."
  else
    RELEASE_SHA=$(git rev-parse HEAD)
    echo "waiting for CI on $RELEASE_SHA before tagging (nothing tagged yet)..."
    RUN_ID=""
    for _ in $(seq 1 20); do
      RUN_ID=$(gh run list --workflow CI --commit "$RELEASE_SHA" --limit 1 \
        --json databaseId --jq '.[0].databaseId // empty' 2>/dev/null || true)
      [ -n "$RUN_ID" ] && break
      sleep 6
    done
    if [ -z "$RUN_ID" ]; then
      echo "ERROR: no CI run found for $RELEASE_SHA after 120s — aborting before the tag."
      echo "       (commit not pushed? Actions outage? override with --skip-ci-wait)"
      exit 1
    fi
    gh run watch "$RUN_ID" --exit-status \
      || { echo "CI FAILED on $RELEASE_SHA — aborting before the tag; nothing published"; exit 1; }
    echo "CI green on $RELEASE_SHA."
  fi

  # `git tag -s` can exit 0 while silently creating an UNSIGNED tag when the
  # signer fails (observed 2026-09-14: agent refused operation). Verify a
  # signature block actually landed; fall back loudly if not.
  tag_ok=0
  if [ "$SIGNED_TAG" = "1" ]; then
    git tag -s "v$VERSION" -m "WhiteMagic v$VERSION" || true
    if git cat-file -p "v$VERSION" 2>/dev/null | grep -qE 'BEGIN (SSH|PGP|X509) SIGNATURE'; then
      echo "tag v$VERSION signed."
      tag_ok=1
    else
      echo "WARN: tag signing failed (key or agent unavailable) — removing the"
      echo "      unsigned tag and falling back to an annotated tag."
      git tag -d "v$VERSION" >/dev/null
    fi
  else
    echo "WARN: no signing key configured — creating an annotated but UNSIGNED tag."
    echo "      Set user.signingkey (and gpg.format for SSH signing) before the next release."
  fi
  if [ "$tag_ok" = "0" ]; then
    git tag -a "v$VERSION" -m "WhiteMagic v$VERSION"
  fi
  TAG_PUSH_AT=$(date +%s)
  git push origin "v$VERSION"
fi

# ── release workflow (assets + registries) ───────────────────────────────
banner "RELEASE WORKFLOW (assets + registries)"
if $DRY_RUN; then
  echo "[dry-run] gh run watch the tag-triggered Release workflow: 5-platform"
  echo "[dry-run]   binaries + cosign bundles + SBOMs + signed manifest, then its"
  echo "[dry-run]   registries job: crates.io → npm → Docker Hub → MCP registry"
else
  RUN_ID=""
  for _ in $(seq 1 30); do
    RUN_ID=$(gh run list --workflow Release --limit 10 \
      --json databaseId,headBranch \
      --jq ".[] | select(.headBranch == \"v$VERSION\") | .databaseId" | head -n1)
    [ -n "$RUN_ID" ] && break
    sleep 10
  done
  if [ -z "$RUN_ID" ]; then
    echo "ERROR: no Release workflow run found for v$VERSION after 5 minutes."
    echo "       (tag pushed? Actions outage?) Inspect: gh run list --workflow Release"
    exit 1
  fi
  echo "watching Release run $RUN_ID ..."
  gh run watch "$RUN_ID" --exit-status \
    || { echo "ERROR: Release workflow FAILED ($RUN_ID) — assets/registries may be partial."; \
         echo "       Inspect: gh run view $RUN_ID --log-failed"; exit 1; }
  echo "Release workflow green — assets + registries published by the workflow."
fi

# ── release assets verification ──────────────────────────────────────────
banner "RELEASE ASSETS"
if $DRY_RUN; then
  echo "[dry-run] gh release view v$VERSION --json assets (expect >= 28: 5 binaries,"
  echo "[dry-run]   5 sha256, 5 cosign bundles, 15 SBOMs, manifest + .sig)"
  echo "[dry-run] download wm-linux-x86_64 + .sha256; sha256sum -c"
else
  ASSET_COUNT=$(gh release view "v$VERSION" --json assets --jq '.assets | length')
  echo "assets: $ASSET_COUNT"
  if [ "$ASSET_COUNT" -lt 28 ]; then
    echo "ERROR: release assets look incomplete (<28) — inspect the Release workflow."; exit 1
  fi
  # Checksum spot check in the exact format the Dockerfile consumes
  # (`sha256sum -c`; bare-hash files broke Docker on 2026-09-15).
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  gh release download "v$VERSION" -p 'wm-linux-x86_64' -p 'wm-linux-x86_64.sha256' -D "$TMP" >/dev/null
  if ( cd "$TMP" && sha256sum -c wm-linux-x86_64.sha256 >/dev/null ); then
    echo "checksum: wm-linux-x86_64 OK (sha256sum -c format)"
  else
    echo "ERROR: checksum verification failed for wm-linux-x86_64"; exit 1
  fi
fi

# ── registries verification (published by the workflow) ──────────────────
banner "REGISTRIES"
probe_version() { # <label> <url> <jq-expr> [tries]
  local label="$1" url="$2" expr="$3" tries="${4:-40}" got="" i
  for i in $(seq 1 "$tries"); do
    got=$(curl -fsS -m 20 -A "$UA" "$url" 2>/dev/null | jq -r "$expr" 2>/dev/null || true)
    if [ "$got" = "$VERSION" ]; then echo "  $label: $got"; return 0; fi
    if [ "$i" -lt "$tries" ]; then sleep 15; fi
  done
  echo "ERROR: $label reports '${got:-nothing}' (want $VERSION)"; return 1
}
if $DRY_RUN; then
  echo "[dry-run] probe crates.io / npm / Docker Hub until they report $VERSION"
else
  probe_version "crates.io (whitemagic)" "https://crates.io/api/v1/crates/whitemagic" '.crate.max_version' 40
  probe_version "npm (whitemagic-mcp)" "https://registry.npmjs.org/whitemagic-mcp/latest" '.version' 24
  probe_version "Docker Hub (tag ${VERSION})" "https://hub.docker.com/v2/repositories/lbailey94/whitemagic/tags/${VERSION}" '.name' 20
fi

# The MCP registry search index lags the publish; the publish itself is in the
# workflow log. Probe briefly, then report honestly (advisory, not a gate).
banner "MCP REGISTRY (advisory)"
if $DRY_RUN; then
  echo "[dry-run] advisory probe: registry.modelcontextprotocol.io search for $VERSION"
else
  found=""
  for _ in $(seq 1 10); do
    if curl -fsS -m 20 "https://registry.modelcontextprotocol.io/v0/servers?search=whitemagic" 2>/dev/null \
      | jq -r '.servers[].server.version' 2>/dev/null | grep -qx "$VERSION"; then
      found=1; break
    fi
    sleep 15
  done
  if [ -n "$found" ]; then
    echo "  MCP registry: $VERSION visible"
  else
    echo "  WARN: MCP registry index did not show $VERSION within the probe window."
    echo "        The workflow reported the publish; confirm with:"
    echo "        gh run view $RUN_ID --log | grep -A2 -i 'mcp registry'"
  fi
fi

# ── release health (canonical channel reconciliation) ────────────────────
banner "RELEASE HEALTH"
if $DRY_RUN; then
  echo "[dry-run] wait for the tag-triggered Release health run; fail loudly if red"
else
  HRUN=""
  for _ in $(seq 1 30); do
    HRUN=$(gh run list --workflow release-health.yml --limit 5 \
      --json databaseId,createdAt \
      --jq "[.[] | select((.createdAt | fromdateiso8601) >= ($TAG_PUSH_AT - 120))] | .[0].databaseId // empty" \
      2>/dev/null || true)
    [ -n "$HRUN" ] && break
    sleep 10
  done
  if [ -n "$HRUN" ]; then
    gh run watch "$HRUN" --exit-status \
      && echo "release-health: green ($HRUN)" \
      || { echo "ERROR: release-health failed ($HRUN) — inspect gh run view $HRUN"; exit 1; }
  else
    echo "WARN: no release-health run appeared for v$VERSION yet — the scheduled run will reconcile."
  fi
fi

# ── hub README (optional: needs HUB_TOKEN) ───────────────────────────────
banner "HUB README"
if [ -n "${HUB_TOKEN:-}" ]; then
  if $DRY_RUN; then echo "[dry-run] PATCH full_description with version line $VERSION"
  else
    JWT=$(curl -s -H "Content-Type: application/json" -d "{\"username\":\"lbailey94\",\"password\":\"$HUB_TOKEN\"}" https://hub.docker.com/v2/users/login | jq -r '.token // empty')
    [ -n "$JWT" ] && echo "HUB_TOKEN accepted — update the version line in the Hub description manually or extend this stage with the runbook block"
  fi
else
  echo "HUB_TOKEN not set — remember to bump the version line in the Hub README (docs/DOCKER_HUB_RUNBOOK.md block)"
fi

# ── manual tail (separate lanes) ─────────────────────────────────────────
banner "MANUAL TAIL (separate lanes)"
cat <<'EOF'
 1. site: npm run sync-facts:refresh → check-facts/check-surfaces → push master
    (regenerate the capability manifest counts when the tool surface moved)
 2. contract manifest: run `wm contract --json --out docs/contract/route-schema-manifest.json`
    from the released binary and commit (standing post-release item)
 3. announce: repo-as-funnel surfaces auto-pick-up; consider a site changelog note
EOF
banner "DONE — v$VERSION verified on all channels"
