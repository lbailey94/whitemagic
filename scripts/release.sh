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
  echo "[dry-run] sed workspace Cargo.toml version; update Cargo.lock (cargo check);"
  echo "[dry-run] sed $NPM_DIR/package.json + server.json versions; commit + tag v$VERSION + push"
else
  python3 - "$VERSION" <<'EOF'
import json, pathlib, re, sys
v = sys.argv[1]
root = pathlib.Path("Cargo.toml")
t = root.read_text()
t2 = re.sub(r'^version = "[^"]*"', f'verison = "{v}"'.replace("verison", "version"), t, count=1, flags=re.M)
assert t2 != t, "workspace version bump failed"
root.write_text(t2)
pkg = pathlib.Path("npm/whitemagic-mcp/package.json")
d = json.loads(pkg.read_text()); d["version"] = v
pkg.write_text(json.dumps(d, indent=2) + "\n")
srv = pathlib.Path("npm/whitemagic-mcp/server.json")
j = json.loads(srv.read_text()); j["version"] = v
for p in j.get("packages", []):
    if p.get("registryType") == "npm":
        p["version"] = v
srv.write_text(json.dumps(j, indent=2) + "\n")
print(f"bumped Cargo.toml, package.json, server.json → {v}")
EOF
  cargo check --workspace --quiet 2>/dev/null || cargo check -p wm-core --quiet   # refresh Cargo.lock
  git add -A
  git -c user.name="WhiteMagic AI" -c user.email="lbailey94@protonmail.com" commit -m "release: v$VERSION"
  git push origin main
fi

# ── tag + CI ─────────────────────────────────────────────────────────────
banner "TAG + CI"
if $DRY_RUN; then
  echo "[dry-run] git tag v$VERSION; git push origin v$VERSION; wait for CI"
else
  git tag "v$VERSION"
  git push origin "v$VERSION"
fi
if ! $SKIP_CI_WAIT && ! $DRY_RUN; then
  echo "waiting for CI on tag push (gh run watch — Ctrl-C to skip waiting and continue)"
  sleep 15
  RUN_ID=$(gh run list --workflow CI --limit 1 --json databaseId --jq '.[0].databaseId')
  gh run watch "$RUN_ID" --exit-status || { echo "CI FAILED — aborting release"; exit 1; }
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
CRATES="wm-core wm-conformal wm-memory wm-substrate wm-simulation wm-workspace wm-polyglot wm-sangha wm-selfmodel wm-governance wm-bicameral wm-dispatch wm-cognitive wm-tools whitemagic"
for c in $CRATES; do
  published=""
  lag=0
  while [ -z "$published" ]; do
    if $DRY_RUN; then echo "[dry-run] cargo publish -p $c"; published=1; break; fi
    if cargo publish -p "$c" > "/tmp/pub-$c.log" 2>&1; then echo "PUBLISHED: $c"; published=1; sleep 20; break; fi
    if grep -aq "already exists" "/tmp/pub-$c.log"; then echo "SKIP (already live): $c"; published=1; break; fi
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
