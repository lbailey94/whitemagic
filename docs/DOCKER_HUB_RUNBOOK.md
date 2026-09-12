# Docker — packaging the `wm` binary and keeping Docker Hub current

**Created:** 2026-09-08. Owner: Lucas Bailey (hub: `lbailey94/whitemagic`).

## Current state (honest)

The Hub holds 13 tags pushed Nov 11–19, 2025 — the **2.x-era Python MCP
stack** (npm-2.x days), last push `2.3.1` + `latest` + `buildcache`.
1,441 cumulative pulls. These images are history, not the v9 Rust
product. The Hub README is currently bare.

## The v9 image (this repo's Dockerfile)

`Dockerfile` here **packages the released binary** rather than compiling
the workspace — tiny builds, and the checksum verification ships inside
the image build:

```bash
docker build --build-arg WM_VERSION=v9 -t lbailey94/whitemagic:9 . 
docker run --rm lbailey94/whitemagic:9 --version   # wm 9.1.3
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
3. Update the Hub README version line (below).

## Hub README maintenance (the part that rots)

The README lives only on the Hub (Manage Repository → Description), so
the source of truth for its text is the block below — paste it, bump
the version line on each release:

> **WhiteMagic** — local-first memory and session continuity for AI
> coding agents, over MCP. Single static Rust binary, no telemetry, no
> cloud service. MIT.
>
> - Docs & installer: https://whitemagic.dev
> - Source: https://github.com/lbailey94/whitemagic
> - Image `9.x`/`latest`: v9 Rust binary (`wm`) — run
>   `docker run -i lbailey94/whitemagic:9 serve --profile curated`
> - Tags `2.x` (2.1.0–2.3.1, Nov 2025): the historical Python MCP
>   stack, kept for provenance — not the current product.
>
> Store your data in a mounted volume; memory never leaves the machine.

**API alternative** (no web UI): with a Hub access token,
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
