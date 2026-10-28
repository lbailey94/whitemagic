#!/usr/bin/env bash
# WhiteMagic release script — orchestration + verification (F4, 9.1.9).
#
# Usage:
#   scripts/release.sh <version> [--dry-run] [--skip-ci-wait] [--tail-only] [--skip-site]
#
# Example:
#   scripts/release.sh 9.1.9
#   scripts/release.sh 9.1.9 --dry-run
#   scripts/release.sh 9.1.9 --tail-only   # live post-release reconciliation
#   scripts/release.sh 9.1.9 --tail-only --dry-run   # local preview, no network/writes
#
# Division of labor (9.1.8 lesson): the tag-triggered `release.yml` workflow
# owns the five channels — it builds the 5-platform binaries, signs the
# manifest, generates SBOMs, and publishes crates.io → npm → Docker Hub →
# MCP registry (its `registries` job). This script orchestrates the release
# and then VERIFIES every channel:
#
#   bump → release commit → push → CI gate → signed tag → [release.yml] →
#   assets + checksum + registries + release-health verification
#   → generation-specific contract manifest → applicable site path → Hub README.
#
# The tail stages (contract, site, Hub) are live reconciliation steps.
# `--tail-only` can commit/push generated docs, sync the applicable site, and
# dispatch the Hub description workflow. Combine it with `--dry-run` for a
# local preview that does not fetch, query, launch, write, commit, push, or dispatch.
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

VERSION="${1:?usage: scripts/release.sh <version> [--dry-run] [--skip-ci-wait] [--tail-only] [--skip-site]}"
DRY_RUN=false; SKIP_CI_WAIT=false; TAIL_ONLY=false; SKIP_SITE=false
for arg in "${@:2}"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --skip-ci-wait) SKIP_CI_WAIT=true ;;
    --tail-only) TAIL_ONLY=true ;;
    --skip-site) SKIP_SITE=true ;;
    *) echo "unknown flag: $arg"; exit 1 ;;
  esac
done
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
UA="whitemagic-release/1.0 (lbailey94@protonmail.com)"
RELEASE_FAMILY="$(python3 scripts/release_tail.py family "$VERSION")" \
  || { echo "ERROR: unsupported release family for $VERSION" >&2; exit 1; }
TAG_COMMIT=""

banner() { echo; echo "━━━━ $* ━━━"; }

runtime_manifest() { # <output-file> — read RELEASED_BIN's capability manifest
  local out="$1" port="" store="" pid="" i rc=0 p
  for p in $(seq 19140 19260); do
    if ! ss -tln 2>/dev/null | grep -q ":$p "; then port="$p"; break; fi
  done
  [ -n "$port" ] || { echo "no free port for the runtime manifest" >&2; return 1; }
  store="$(mktemp -d)"
  RUST_LOG=error "$RELEASED_BIN" serve --profile curated --store "$store" \
    --transport sse --bind "127.0.0.1:$port" >/dev/null 2>&1 &
  pid=$!
  for i in $(seq 1 30); do
    if ss -tln 2>/dev/null | grep -q ":$port "; then break; fi
    sleep 0.5
  done
  if ! "$RELEASED_BIN" manifest --endpoint "http://127.0.0.1:$port" > "$out" 2>/dev/null; then
    rc=1
  fi
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  rm -rf "$store"
  return $rc
}

# ── preflight ────────────────────────────────────────────────────────────
banner "PREFLIGHT"
[ -z "$(git status --porcelain)" ] || { echo "ERROR: dirty tree — commit or stash first"; exit 1; }
[ "$(git branch --show-current)" = "main" ] || { echo "ERROR: run from main"; exit 1; }
if $DRY_RUN; then
  echo "dry-run: skipping git fetch (using only cached origin/main refs)"
else
  git fetch origin main --quiet
fi
[ -z "$(git rev-list HEAD..origin/main)" ] || { echo "ERROR: local main is behind origin — pull first"; exit 1; }
CUR=$(grep -m1 '^version = ' Cargo.toml | sed 's/version = "\(.*\)"/\1/')
echo "workspace: $CUR → $VERSION"
if $TAIL_ONLY; then
  python3 scripts/version_truth.py --check --version "$VERSION" \
    || { echo "ERROR: version-truth drift for $VERSION"; exit 1; }
else
  python3 scripts/version_truth.py --check \
    || { echo "ERROR: version-truth drift — every surface must agree before a release"; exit 1; }
fi
for tool in gh cargo python3 jq curl; do command -v "$tool" >/dev/null || { echo "ERROR: $tool missing"; exit 1; }; done
if ! $DRY_RUN; then
  gh auth status >/dev/null 2>&1 || { echo "ERROR: gh not authed"; exit 1; }
fi
echo "preflight ok"

if $TAIL_ONLY; then
  banner "TAIL-ONLY — post-release stages for an already-published v$VERSION"
  echo "skipping: version bump, CI gate, signed tag, Release workflow."
  echo "running live reconciliation: assets, registries, exact-source health,"
  echo "  generation-specific contract, applicable site path, and Hub README."
  if $DRY_RUN; then
    echo "dry-run: no tag/run lookup, network request, binary launch, file write, commit, push, or workflow dispatch."
  else
    TAG_COMMIT="$(git rev-parse "refs/tags/v$VERSION^{commit}" 2>/dev/null || true)"
    [ -n "$TAG_COMMIT" ] || {
      echo "ERROR: local tag v$VERSION is required to bind tail checks to its source commit." >&2
      echo "       Fetch the exact tag without retagging it, then rerun." >&2
      exit 1
    }
  fi
else

# ── version bump ─────────────────────────────────────────────────────────
banner "VERSION BUMP → $VERSION"
if $DRY_RUN; then
  echo "[dry-run] python3 scripts/version_truth.py --open-changelog $VERSION"
  echo "[dry-run] python3 scripts/version_truth.py --set $VERSION (all listed"
  echo "[dry-run]   surfaces: Cargo.toml pins, npm package/server/MCPB, Dockerfile"
  echo "[dry-run]   labels, CITATION, docs, skill.md, README, PRIVACY_POLICY.md,"
  echo "[dry-run]   install examples, rust-toolchain.toml; CHANGELOG ceremony is"
  echo "[dry-run]   checked separately)"
  echo "[dry-run] cargo check (refresh Cargo.lock); commit + push; tag v$VERSION"
else
  python3 scripts/version_truth.py --open-changelog "$VERSION"
  python3 scripts/version_truth.py --set "$VERSION"
  cargo check --workspace --quiet 2>/dev/null || cargo check -p wm-core --quiet   # refresh Cargo.lock
  # Resume-safe: if a prior run aborted before the tag (red CI), the bump commit
  # already exists and this produces no diff — commit only when there is
  # something to commit, but always push, because the CI gate below watches
  # HEAD and HEAD must be on origin for a run to exist.
  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git -c user.name="WhiteMagic AI" -c user.email="lbailey94@protonmail.com" commit -m "release: v$VERSION"
  else
    echo "bump produced no changes (already at $VERSION) — resuming the ceremony"
  fi
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

# ── release workflow (assets + registries) ───────────────────────────────
banner "RELEASE WORKFLOW (assets + registries)"
if $DRY_RUN; then
  echo "[dry-run] gh run watch the tag-triggered Release workflow: 5-platform"
  echo "[dry-run]   binaries + cosign bundles + SBOMs + signed manifest, then its"
  echo "[dry-run]   registries job: crates.io → npm → Docker Hub → MCP registry"
else
  TAG_COMMIT="$(git rev-parse "refs/tags/v$VERSION^{commit}")"
  RUN_ID=""
  for _ in $(seq 1 30); do
    RUNS=$(gh run list --workflow Release --commit "$TAG_COMMIT" --limit 20 \
      --json databaseId,headBranch,headSha,event,status,conclusion,createdAt 2>/dev/null || echo '[]')
    RUN_ID=$(printf '%s' "$RUNS" | python3 scripts/release_tail.py select-release \
      --version "$VERSION" --source-sha "$TAG_COMMIT" 2>/dev/null || true)
    [ -n "$RUN_ID" ] && break
    sleep 10
  done
  if [ -z "$RUN_ID" ]; then
    echo "ERROR: no Release run matches tag v$VERSION at $TAG_COMMIT after 5 minutes."
    echo "       Inspect: gh run list --workflow Release --commit $TAG_COMMIT"
    exit 1
  fi
  echo "watching Release run $RUN_ID ..."
  gh run watch "$RUN_ID" --exit-status \
    || { echo "ERROR: Release workflow FAILED ($RUN_ID) — assets/registries may be partial."; \
         echo "       Inspect: gh run view $RUN_ID --log-failed"; exit 1; }
  echo "Release workflow green — assets + registries published by the workflow."
fi
fi

# ── release assets verification ──────────────────────────────────────────
banner "RELEASE ASSETS"
TMP=""
RELEASED_BIN=""
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
  if [ "$(uname -s)" = "Linux" ] && [ "$(uname -m)" = "x86_64" ]; then
    RELEASED_BIN="$TMP/wm-linux-x86_64"
    chmod +x "$RELEASED_BIN"
    echo "released binary: $RELEASED_BIN (kept for the tail stages)"
  else
    echo "WARN: host is $(uname -s)/$(uname -m) — the released Linux binary cannot run here"
  fi
fi

# ── registries verification (published by the workflow) ──────────────────
banner "REGISTRIES"
if $DRY_RUN; then
  bash scripts/release_registry_probes.sh "$VERSION" --dry-run
else
  bash scripts/release_registry_probes.sh "$VERSION"
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
    echo "        gh run view ${RUN_ID:-<release run>} --log | grep -A2 -i 'mcp registry'"
  fi
fi

# ── release health (canonical channel reconciliation) ────────────────────
banner "RELEASE HEALTH"
if $DRY_RUN; then
  echo "[dry-run] select newest matching workflow_run health for source $TAG_COMMIT, then require success"
  echo "[dry-run] verify the v$VERSION record against its exact signed manifest and install certifications"
else
  HRUN=""
  for _ in $(seq 1 30); do
    RUNS=$(gh run list --workflow release-health.yml --commit "$TAG_COMMIT" --limit 20 \
      --json databaseId,headSha,event,status,conclusion,createdAt 2>/dev/null || echo '[]')
    HRUN=$(printf '%s' "$RUNS" | python3 scripts/release_tail.py select-health \
      --version "$VERSION" --source-sha "$TAG_COMMIT" 2>/dev/null || true)
    [ -n "$HRUN" ] && break
    sleep 10
  done
  [ -n "$HRUN" ] || {
    echo "ERROR: no workflow_run health event matches v$VERSION source $TAG_COMMIT." >&2
    echo "       Scheduled/manual checks are not accepted for this release hook." >&2
    exit 1
  }
  echo "watching release-health run $HRUN ..."
  gh run watch "$HRUN" --exit-status \
    || { echo "ERROR: release-health workflow FAILED ($HRUN)." >&2; \
         echo "       Inspect: gh run view $HRUN --log-failed" >&2; exit 1; }
  mkdir -p "$TMP/health"
  gh run download "$HRUN" --name release-health --dir "$TMP/health" >/dev/null
  MANIFEST="$TMP/release-manifest.json"
  gh release download "v$VERSION" -p 'release-manifest.json' -D "$TMP" >/dev/null
  MANIFEST_SHA="$(sha256sum "$MANIFEST" | cut -d' ' -f1)"
  jq -e --arg version "$VERSION" \
    '.schema == 1 and .version == $version and (.targets | type == "object" and length > 0)' \
    "$MANIFEST" >/dev/null || {
    echo "ERROR: downloaded signed manifest kind/schema/version/targets do not match v$VERSION" >&2; exit 1;
  }
  python3 scripts/release_tail.py verify-health --version "$VERSION" \
    --manifest-sha256 "$MANIFEST_SHA" --record "$TMP/health/release-health.json"
  echo "release-health: healthy ($HRUN), bound to v$VERSION manifest $MANIFEST_SHA and source $TAG_COMMIT"
fi

# ── contract manifest (regenerated from the released binary) ─────────────
banner "CONTRACT MANIFEST"
if $DRY_RUN; then
  python3 scripts/release_tail.py contract --version "$VERSION" \
    --repo-root "$REPO_ROOT" --dry-run
elif [ -n "$RELEASED_BIN" ] && [ -x "$RELEASED_BIN" ]; then
  CONTRACT_PATH="$(python3 scripts/release_tail.py contract --version "$VERSION" \
    --binary "$RELEASED_BIN" --repo-root "$REPO_ROOT" \
    | sed -n 's/^.*manifest written: //p')"
  if [ -n "$CONTRACT_PATH" ]; then
    if [ -n "$(git status --porcelain -- "$CONTRACT_PATH")" ]; then
      git add -- "$CONTRACT_PATH"
      git commit -m "chore(contract): regenerate route schema manifest at $VERSION"
      git push origin main
      echo "contract manifest: regenerated and pushed"
    else
      echo "contract manifest: unchanged"
    fi
  else
    echo "WARN: contract regeneration failed — validate the released binary output manually"
  fi
else
  echo "WARN: released binary unavailable on this host — regenerate the contract manifest manually"
fi

# ── site sync (facts, gates, push master) ────────────────────────────────
banner "SITE SYNC"
SITE_DIR="${WM_SITE_DIR:-$HOME/Desktop/front burner/WHITEMAGIC/whitemagic-site}"
if $SKIP_SITE; then
  echo "site sync skipped (--skip-site); defer until the rendered site preview is reviewed"
elif [ "$RELEASE_FAMILY" = "gen3" ]; then
  echo "Gen3 site sync skipped: this tail's runtime-count and autopush checks are Gen2-specific."
  echo "Current site checkout: $SITE_DIR"
  echo "Manual refresh: cd \"$SITE_DIR\" && npm run sync-facts:refresh && npm run check-facts"
  echo "  && npm run check-build-truth && npm run check-surfaces && npx tsc --noEmit && npm run build"
  echo "Review the site diff and rendered preview before its normal deployment."
elif $DRY_RUN; then
  echo "[dry-run] in $SITE_DIR: verify capability counts vs the released binary,"
  echo "[dry-run]   verify the public installer copy matches scripts/install.sh,"
  echo "[dry-run]   verify guide commands/flags vs the released binary,"
  echo "[dry-run]   npm run sync-facts:refresh → check-* / tsc / build → commit + push master"
elif [ ! -d "$SITE_DIR/.git" ]; then
  echo "WARN: site repo not found at $SITE_DIR — sync the site manually"
elif [ ! -d "$SITE_DIR/node_modules" ]; then
  echo "WARN: site dependencies missing (run npm install) — sync the site manually"
else
  (
    cd "$SITE_DIR" || exit 0
    if [ -n "$(git status --porcelain)" ]; then
      echo "WARN: site tree is dirty — sync the site manually after resolving"
      exit 0
    fi
    if [ "$(git branch --show-current)" != "master" ]; then
      echo "WARN: site repo is on '$(git branch --show-current)', not master — sync manually"
      exit 0
    fi
    git fetch origin master --quiet || { echo "WARN: site fetch failed"; exit 0; }
    git pull --ff-only origin master --quiet || { echo "WARN: site pull failed"; exit 0; }

    # The public installer is a manual copy of scripts/install.sh and drifted
    # behind it once (2026-09-21 reviewer finding: no arm64 mapping, stale
    # PATH logic). Byte-compare before syncing facts.
    INSTALLER_OK=1
    if ! cmp -s "$REPO_ROOT/scripts/install.sh" public/install.sh; then
      echo "ERROR: public/install.sh is not in sync with scripts/install.sh" >&2
      echo "  fix: cp $REPO_ROOT/scripts/install.sh public/install.sh" >&2
      INSTALLER_OK=0
    fi

    COUNTS_OK=1
    if [ -n "$RELEASED_BIN" ] && [ -x "$RELEASED_BIN" ]; then
      RUNTIME_JSON="$(mktemp)"
      if runtime_manifest "$RUNTIME_JSON"; then
        python3 "$REPO_ROOT/scripts/check_site_counts.py" \
          --runtime-manifest "$RUNTIME_JSON" \
          --site-manifest public/api/manifest.json || COUNTS_OK=0
      else
        echo "WARN: could not read the released binary's runtime manifest — counts not verified"
        COUNTS_OK=0
      fi
      rm -f "$RUNTIME_JSON"
    else
      echo "WARN: released binary unavailable — counts not verified"
      COUNTS_OK=0
    fi
    if [ "$COUNTS_OK" = "0" ] || [ "$INSTALLER_OK" = "0" ]; then
      echo "site NOT synced: fix the issue(s) above, then:"
      echo "  cd $SITE_DIR && npm run sync-facts:refresh && npm run check-facts \\"
      echo "    && git add -A && git commit -m 'release(site): sync facts to v$VERSION' && git push origin master"
      exit 0
    fi

    RELEASE_COMMIT="$(git -C "$REPO_ROOT" rev-list -n1 "v$VERSION" | cut -c1-7)"
    export WM_SITE_GENERATOR_NOTE="capability counts verified via \`wm manifest\` against the v$VERSION release binary ($RELEASE_COMMIT)"
    npm run sync-facts:refresh || { echo "WARN: site fact refresh failed"; exit 0; }
    # Guide copy must not advertise commands or flags the released binary
    # stopped printing. Uses the same verified $RELEASED_BIN the counts check
    # used; check_guide_commands.py exits 2 only when no binary is available.
    GUIDE_OK=1
    WM_BIN="$RELEASED_BIN" python3 scripts/check_guide_commands.py || GUIDE_OK=0
    if [ "$GUIDE_OK" = "0" ] || ! { npm run check-facts && npm run check-build-truth && npm run check-surfaces && npx tsc --noEmit; }; then
      echo "WARN: site gates failed (facts, counts, prose, guide commands, or types) — site NOT pushed; inspect $SITE_DIR"
      exit 0
    fi
    SITE_LOG="$(mktemp)"
    if ! npm run build >"$SITE_LOG" 2>&1; then
      echo "WARN: site build failed — site NOT pushed; see $SITE_LOG"
      tail -20 "$SITE_LOG"
      exit 0
    fi
    rm -f "$SITE_LOG"
    if [ -n "$(git status --porcelain)" ]; then
      git add -A
      git commit -m "release(site): sync facts to v$VERSION"
      git push origin master
      echo "site: facts synced and pushed (Vercel deploys on push)"
    else
      echo "site: already current — nothing to push"
    fi
  ) || echo "WARN: site sync subshell exited non-zero — inspect $SITE_DIR"
fi

# ── hub README (dispatch the description workflow; advisory) ─────────────
banner "HUB README"
if $DRY_RUN; then
  echo "[dry-run] gh workflow run hub-description.yml: extracts the runbook block,"
  echo "[dry-run]   dates the Current release line from the signed manifest, PATCHes"
  echo "[dry-run]   full_description with the DOCKERHUB_TOKEN secret; advisory."
else
  PREV_RUN=$(gh run list --workflow hub-description.yml --limit 1 \
    --json databaseId --jq '.[0].databaseId // empty' 2>/dev/null || true)
  if gh workflow run hub-description.yml >/dev/null 2>&1; then
    HUB_RUN=""
    for _ in $(seq 1 24); do
      CUR_RUN=$(gh run list --workflow hub-description.yml --limit 1 \
        --json databaseId --jq '.[0].databaseId // empty' 2>/dev/null || true)
      if [ -n "$CUR_RUN" ] && [ "$CUR_RUN" != "$PREV_RUN" ]; then HUB_RUN="$CUR_RUN"; break; fi
      sleep 5
    done
    if [ -n "$HUB_RUN" ]; then
      gh run watch "$HUB_RUN" --exit-status >/dev/null 2>&1 \
        && echo "hub-description: green ($HUB_RUN) — Hub README synced from the runbook block" \
        || echo "WARN: hub-description run $HUB_RUN failed — sync the Hub README manually (docs/DOCKER_HUB_RUNBOOK.md)"
    else
      echo "WARN: hub-description.yml dispatched but no run appeared — check gh run list"
    fi
  else
    echo "WARN: could not dispatch hub-description.yml — sync the Hub README manually"
    echo "      (source of truth: docs/DOCKER_HUB_RUNBOOK.md block)"
  fi
fi

# ── manual tail (separate lanes) ─────────────────────────────────────────
banner "MANUAL TAIL"
cat <<'EOF'
 1. announce: repo-as-funnel surfaces auto-pick-up; consider a site changelog note
 2. if any WARN above fired (site counts moved, binary unavailable, Hub dispatch
    failed), resolve it before the next release
EOF
if $DRY_RUN; then
  banner "DRY RUN COMPLETE — v$VERSION ceremony rehearsed; no channels verified"
else
  banner "RELEASE CEREMONY COMPLETE — v$VERSION release checks finished"
fi
