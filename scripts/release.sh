#!/usr/bin/env bash
# WhiteMagic release script — one command, five channels.
#
# Usage:
#   scripts/release.sh <version> [--dry-run] [--skip-ci-wait]
#
# Example:
#   scripts/release.sh 9.1.0
#   scripts/release.sh 9.1.0 --dry-run
#
# Channels: git tag + GitHub release (with binaries) → crates.io (ordered
# publish) → npm → Docker Hub (tag + latest) → official MCP registry.
# Site + Hub README get printed reminders (site is a separate repo; Hub
# README via API needs HUB_TOKEN in the environment).
#
# Ordering: the release commit is pushed first, CI on that commit is watched
# to green, and only then is the signed tag created and pushed — release.yml
# publishes on tag push, so tagging before the gate would make a red CI
# unable to prevent publication. --skip-ci-wait overrides the gate loudly.
#
# Conventions kept:
#   - workspace version = npm package version = server.json version
#   - image tags: vX.Y.Z + major tag (X) flipped to latest
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
MAJOR="${VERSION%%.*}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
NPM_DIR="npm/whitemagic-mcp"
UA="whitemagic-release/1.0 (lbailey94@protonmail.com)"

banner() { echo; echo "━━━━ $* ━━━"; }
run() { if $DRY_RUN; then echo "[dry-run] $*"; else "$@"; fi; }

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
for tool in gh cargo npm docker; do command -v "$tool" >/dev/null || { echo "ERROR: $tool missing"; exit 1; }; done
if ! $DRY_RUN; then
  npm whoami >/dev/null 2>&1 || { echo "ERROR: npm not logged in (npm login)"; exit 1; }
  [ -f ~/.cargo/credentials.toml ] || { echo "ERROR: cargo not logged in (cargo login)"; exit 1; }
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
  git push origin "v$VERSION"
fi

# ── build assets + GitHub release ────────────────────────────────────────
banner "ASSETS + GITHUB RELEASE"
if $DRY_RUN; then
  echo "[dry-run] build linux gnu+musl, sha256 each; include prebuilt mac/win from release-assets/ if present"
  echo "[dry-run] gh release create v$VERSION --title 'WhiteMagic v$VERSION' --generate-notes + assets"
else
  mkdir -p release-assets
  for target in x86_64-unknown-linux-gnu x86_64-unknown-linux-musl; do
    rustup target add "$target" 2>/dev/null || true
    cargo build --release --target "$target" -p whitemagic --bin wm
    ext=""; [ "$target" = "x86_64-unknown-linux-musl" ] && ext="-musl"
    cp "target/$target/release/wm" "release-assets/wm-linux-x86_64$ext"
  done
  for f in release-assets/wm-linux-*; do sha256sum "$f" | awk '{print $1}' > "$f.sha256"; done
  # include pre-built mac/win assets if the operator dropped them here
  for f in release-assets/wm-macos-* release-assets/wm-windows-*.exe; do
    [ -f "$f" ] || continue
    case "$f" in *.sha256) continue ;; esac
    sha256sum "$f" | awk '{print $1}' > "$f.sha256"
  done
  # The repo's release.yml workflow auto-creates the release from the tag and
  # builds all 5 binaries (linux gnu+musl, macos x2, windows). Only create
  # here if the workflow hasn't (draft/manual runs); upload extra assets if
  # the operator dropped mac/win builds in release-assets/.
  if gh release view "v$VERSION" >/dev/null 2>&1; then
    echo "release v$VERSION already exists (release.yml) — uploading extras only"
    ls release-assets/wm-* >/dev/null 2>&1 && gh release upload "v$VERSION" release-assets/wm-* --clobber
  else
    gh release create "v$VERSION" --title "WhiteMagic v$VERSION" --generate-notes
    gh release upload "v$VERSION" release-assets/wm-* --clobber
  fi
  echo "release v$VERSION published with $(ls release-assets/wm-* | grep -vc sha256) binaries"
fi

# ── crates.io (ordered; rides 429 windows if any) ────────────────────────
banner "CRATES.IO"
# Derived from cargo metadata (same source as release.yml) so the order can
# never drift from the actual dependency graph.
CRATES="$(python3 scripts/crates_publish_order.py)"
for c in $CRATES; do
  published=""
  lag=0
  while [ -z "$published" ]; do
    if $DRY_RUN; then echo "[dry-run] cargo publish -p $c"; published=1; break; fi
    if cargo publish -p "$c" > "/tmp/pub-$c.log" 2>&1; then echo "PUBLISHED: $c"; published=1; sleep 20; break; fi
    if grep -aqE "already exists|already uploaded" "/tmp/pub-$c.log"; then echo "SKIP (already live): $c"; published=1; break; fi
    if grep -aq "429 Too Many" "/tmp/pub-$c.log"; then
      after=$(grep -aoP "try again after \K.*?GMT" "/tmp/pub-$c.log" | head -n 1)
      wait=$(( $(date -d "$after" +%s 2>/dev/null || echo 0) - $(date +%s) + 15 ))
      [ "$wait" -lt 15 ] && wait=300
      echo "rate-limited on $c — sleeping ${wait}s"; sleep "$wait"; continue
    fi
    if grep -aqE "no matching package|failed to select" "/tmp/pub-$c.log"; then
      lag=$((lag+1)); [ "$lag" -gt 6 ] && { echo "FAILED (index lag): $c"; exit 1; }
      echo "index lag on $c — retry $lag"; sleep 30; continue
    fi
    echo "FAILED: $c"; grep -a -m1 "^error" "/tmp/pub-$c.log"; exit 1
  done
done

# ── npm ──────────────────────────────────────────────────────────────────
banner "NPM"
if $DRY_RUN; then echo "[dry-run] (cd npm/whitemagic-mcp && npm publish --access public)"; else
  ( cd "$NPM_DIR" && npm publish --access public )
fi

# ── docker ───────────────────────────────────────────────────────────────
banner "DOCKER"
if $DRY_RUN; then
  echo "[dry-run] docker build --build-arg WM_VERSION=v$VERSION -t lbailey94/whitemagic:$MAJOR ."
  echo "[dry-run] push :$MAJOR + :$VERSION + flip :latest"
else
  docker build --build-arg "WM_VERSION=v$VERSION" -t "lbailey94/whitemagic:$MAJOR" -t "lbailey94/whitemagic:$VERSION" .
  docker push "lbailey94/whitemagic:$VERSION"
  docker push "lbailey94/whitemagic:$MAJOR"
  docker tag "lbailey94/whitemagic:$MAJOR" "lbailey94/whitemagic:latest"
  docker push "lbailey94/whitemagic:latest"
fi

# ── official MCP registry ────────────────────────────────────────────────
banner "MCP REGISTRY"
if $DRY_RUN; then
  echo "[dry-run] mcp-publisher publish $NPM_DIR/server.json (login token must be fresh — mcp-publisher login github)"
else
  ( cd "$NPM_DIR" && mcp-publisher publish server.json ) \
    || { echo "publish failed — if 401, run: mcp-publisher login github, then rerun this stage"; exit 1; }
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

# ── manual tail ──────────────────────────────────────────────────────────
banner "MANUAL TAIL (not automatable tonight)"
cat <<'EOF'
 1. site: bump lib/facts.ts version + verifiedDate, regenerate manifests if the tool surface changed, push master
 2. CHANGELOG.md entry (if not covered by --generate-notes)
 3. llms.txt / agent surfaces: version references if they hardcode a version
 4. announce: repo-as-funnel surfaces auto-picked-up; consider a changelog note on whitemagic.dev
EOF
banner "DONE — v$VERSION on all channels"
