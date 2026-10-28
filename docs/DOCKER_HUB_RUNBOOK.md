# Docker Hub description source

The quoted block below is the source for Docker Hub's public `full_description`.
The `hub-description.yml` workflow extracts this block, replaces the Gen3
current-release date from the signed release manifest, patches Docker Hub, and
verifies the public result. Keep release channels and volume paths explicit.

> **WhiteMagic** — local-first memory and session continuity for AI coding agents, over MCP. MIT licensed. No usage telemetry is sent off-device by default. Optional read-only hosted evaluation: https://mcp.whitemagic.dev/mcp — evaluation keys, receipts, and verifier: https://www.whitemagic.dev/trust.
>
> - Docs and installer: https://whitemagic.dev
> - Host installer, pinned to stable Gen2 v9.3.4: `curl -fsSL 'https://www.whitemagic.dev/install.sh?ref=dockerhub' | sh -s -- --version v9.3.4`
> - Source: https://github.com/lbailey94/whitemagic
> - Stable Gen2 image: tags `9` and `latest` resolve to v9.3.4 for Linux amd64 and arm64. Run with persistent storage: `docker run -i --rm -e WM_STORE_PATH=/workspace/.whitemagic -v whitemagic-gen2-data:/workspace lbailey94/whitemagic:9 serve --profile curated`.
> - Experimental Gen3 image: tag `10.6.1` is the open-alpha release for Linux amd64 and arm64; it is separate from stable aliases. Run with persistent storage: `docker run -i --rm -e WM_STORE=/workspace/gen3-store -v whitemagic-gen3-data:/workspace lbailey94/whitemagic:10.6.1 serve`.
> - Current release: v10.6.1 — https://github.com/lbailey94/whitemagic/releases/tag/v10.6.1
> - Stable Gen2 release: v9.3.4 (published 2026-10-01) — https://github.com/lbailey94/whitemagic/releases/tag/v9.3.4
>
> Store your data in the mounted generation-specific volume. The optional hosted evaluation lane is separate from the local container store.

## Verified channel and storage facts

- Docker Hub tags `latest`, `9`, and `9.3.4` resolve to one OCI index, `sha256:6a1f79378e20d55bea97b0fe11031fbb33fdbf7ee4e0ec413a9449bbfd376788`, with Linux amd64 and arm64 images. They remain the stable Gen2 v9.3.4 channel.
- Docker Hub tag `10.6.1` is the separately published Gen3 open-alpha multi-architecture image; it does not replace stable aliases.
- Gen2's Dockerfile uses the stable binary and `wm` supports `WM_STORE_PATH`; its explicit volume path is `/workspace/.whitemagic`.
- Gen3's Dockerfile sets `HOME=/home/wm`, uses `/workspace` as its working directory, and gives that directory to user `wm`. The binary accepts `WM_STORE`; the command pins storage to `/workspace/gen3-store` on a separate named volume.
