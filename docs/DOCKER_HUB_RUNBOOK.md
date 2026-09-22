# Docker — packaging the `wm` binary and keeping Docker Hub current

**Created:** 2026-09-08. Owner: Lucas Bailey (hub: `lbailey94/whitemagic`).

## Current state (honest)

The Hub carries the **v9 line only** (one tag per release through the
current version, plus `9` and `latest`). The 13 tags from Nov 2025 — the
**2.x-era Python MCP stack** (1,441 cumulative pulls) — were retired
2026-09-19 (S12): digests were archived first
(`planning/private/S12_DOCKERHUB_TAG_RECEIPTS_2026-09-19.md`) and the
allowlisted cleanup ran through `.github/workflows/hub-tag-cleanup.yml`
(dispatch-only, exact-confirm input). Use that workflow for future stale
tags; it cannot delete anything outside its hardcoded allowlist.

## The v9 image (this repo's Dockerfile)

`Dockerfile` here **packages the released binary** rather than compiling
the workspace — tiny builds, and the checksum verification ships inside
the image build:

```bash
docker build --build-arg WM_VERSION=v9 -t lbailey94/whitemagic:9 . 
docker run --rm lbailey94/whitemagic:9 --version   # wm 9.2.3
```

- Uses `wm-linux-x86_64-musl` (fully static) + its `.sha256` from the
  GitHub release; build fails loudly on checksum mismatch.
- `WM_VERSION` build-arg selects the tag (default `v9`).
- Runtime is `alpine:3.21`; entrypoint is `wm` so
  `docker run ... serve --profile curated` is the MCP-server pattern.

## Release-day ritual (add to the release checklist)

1. Tag + publish the release with binaries (existing flow).
2. Rebuild + push the image:
   ```bash
   docker build --build-arg WM_VERSION=vX -t lbailey94/whitemagic:X .
   docker push lbailey94/whitemagic:X
   docker tag  lbailey94/whitemagic:X lbailey94/whitemagic:latest
   docker push lbailey94/whitemagic:latest
   ```
   (musl build first if the release didn't ship it — see
   `scripts/` release tooling.)
3. Sync the Hub README: `gh workflow run hub-description.yml` (or update
   manually — the block below is the source of truth).

## Hub README maintenance (the part that rots)

The README lives only on the Hub (Manage Repository → Description), so
the source of truth for its text is the block below — paste it, bump
the `Current release:` line on each release:

> **WhiteMagic** — local-first memory and session continuity for AI
> coding agents, over MCP. Single static Rust binary, no telemetry, no
> cloud service. MIT.
>
> - Docs & installer: https://whitemagic.dev
> - Host installer (Linux x86-64, static): `curl -fsSL https://www.whitemagic.dev/install.sh?ref=dockerhub | sh`
> - Source: https://github.com/lbailey94/whitemagic
> - Image `9.x`/`latest`: v9 Rust binary (`wm`) — run
>   `docker run -i lbailey94/whitemagic:9 serve --profile curated`
> - Current release: v9.2.3 (2026-09-18) —
>   https://github.com/lbailey94/whitemagic/releases/tag/v9.2.3
> - Tags `2.x` (2.1.0–2.3.1, Nov 2025): the historical Python MCP
>   stack — retired 2026-09-19; digests archived in the lab's process
>   archive.
>
> Store your data in a mounted volume; memory never leaves the machine.

**Automated (verified 2026-09-18):** `.github/workflows/hub-description.yml`
extracts the block above from this file and PATCHes `full_description` with
the `DOCKERHUB_TOKEN` Actions secret, then verifies the public description:

```bash
gh workflow run hub-description.yml
```

The secret must be a PAT with **Read + Write + Delete** permissions: the
`docker login` credential in `~/.docker/config.json` and a registry-only PAT
both log in but return 403 `insufficient scope` on the description API
(re-verified against both on 2026-09-18); the scoped PAT replaced the CI
secret that day. The workflow dates the `Current release:` line from the
signed manifest's `published` timestamp at run time, so the hand-typed date
in the block only matters for manual pastes (the version comes from the
block, which `scripts/release.sh` auto-bumps and hands to the workflow
after the release workflow completes).

**API alternative** (no web UI): with a Hub **PAT scoped read/write/delete**
(the token stored by `docker login` is registry-scoped only and returns
403 `insufficient scope` on the description API — verified 2026-09-15),
```bash
JWT=$(curl -s -H "Content-Type: application/json" \
  -d '{"username":"lbailey94","password":"<HUB_PAT>"}' \
  https://hub.docker.com/v2/users/login | jq -r .token)
curl -X PATCH -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"full_description":"<README markdown>"}' \
  https://hub.docker.com/v2/repositories/lbailey94/whitemagic/
```

## `latest` contract decision (recorded 2026-09-08)

`latest` moves to v9 with the first v9 push. The 2.x images stay under
their own tags; the README block above tells that story explicitly so
nobody's 2.x workflow breaks silently.
