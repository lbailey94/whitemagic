# whitemagic-mcp

Persistent memory and session continuity for AI coding agents, over MCP.
[WhiteMagic](https://whitemagic.dev) is one Rust binary — local-first,
no telemetry by default, MIT — and every handoff can be signed as a
verifiable [continuity receipt](https://www.whitemagic.dev/trust).

Works with Claude Code, Claude Desktop, Cursor, Codex, VS Code, opencode,
Antigravity, and Devin Desktop — per-client configs:
https://www.whitemagic.dev/whitemagic/guide

This package installs and runs the official `wm` binary from the
[GitHub releases](https://github.com/lbailey94/whitemagic/releases)
(checksum-verified at install time) so an MCP client can launch it
without a manual download step.

## Quick start (no install step)

The local, full-write path straight from npm — the package downloads and
checksum-verifies the official `wm` binary on first run. Pin an exact published
package and inspect its matching release assets. This source checkout's
version is not installable until its package and native release are published.
The `latest` and `next` dist-tags are independent selectors controlled by
release health; neither is a permanent alias for a generation.

```bash
npx -y whitemagic-mcp@11.2.1 serve --profile cyberbrain
```

MCP client config:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "npx",
      "args": ["-y", "whitemagic-mcp@11.2.1", "serve", "--profile", "cyberbrain"]
    }
  }
}
```

Or try the binary directly:

```bash
npx -y whitemagic-mcp@11.2.1 selftest   # invariant self-test + host diagnostics
npx -y whitemagic-mcp@11.2.1 --version  # wm 11.2.1
npx -y whitemagic-mcp@11.2.1 grimoire --plan  # preview detected client config targets
```

The binary is cached under `~/.cache/whitemagic/bin/<release-tag>/`
(respects `XDG_CACHE_HOME`). Pin the exact published
release with `whitemagic-mcp@11.2.1`, or override the release
tag with `WHITEMAGIC_RELEASE`.

## Try it without installing (hosted read-only lane)

The evaluation lane runs at `https://mcp.whitemagic.dev/mcp`
(streamable-http; no SLA). Free paths, no account needed:

- keyless discovery (`initialize` / `tools/list`) for directory probes;
- an anonymous free tier — 3 calls/day per client IP, no key and no header;
- instant evaluation keys at https://mcp.whitemagic.dev/keys
  (50 recalls/day, email optional);
- OAuth 2.1 for MCP clients that speak it.

```bash
claude mcp add whitemagic-mcp --transport http https://mcp.whitemagic.dev/mcp
```

Beyond the free paths, metered calls settle per call via x402 (USDC on
Base), keyless — no account, no invoice. The npm package remains the
local, full-write path.

## Platforms

The Gen3 native matrix covers Linux x86-64 and arm64 requiring glibc 2.39+,
plus macOS arm64. Consult the exact signed manifest and completed release
health record for its actual assets and installer certification. Windows x64
and Intel macOS are absent from this matrix; do not infer a fallback artifact
from an npm selector.
Downloads prefer the compressed `.gz`
distributable when the release ships one (~58% smaller) and fall back to the
raw binary otherwise. No asset for your platform? Build from source:
https://github.com/lbailey94/whitemagic#install

## MCPB bundle

Build the dynamic MCPB bundle with `mcpb/build.sh` from this package directory.
It includes the complete launcher and lets the client select `cyberbrain` or
`full` through actual server arguments. Live `tools/list` owns discovery.

The old static Smithery catalog is retained as historical source and is not
emitted as a release variant. It needs qualification against an exact runtime
version and selected profile before it can describe this Gen3 bundle.

## Privacy

Your memory store lives on your machine. `wm` does not phone home; this
installer contacts GitHub releases only to download the binary and its
checksum. See [PRIVACY_POLICY.md](https://github.com/lbailey94/whitemagic/blob/main/PRIVACY_POLICY.md).

mcp-name: io.github.lbailey94/whitemagic-mcp
