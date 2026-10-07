# whitemagic-mcp

Persistent memory and session continuity for AI coding agents, over MCP.
[WhiteMagic](https://whitemagic.dev) is one static Rust binary — local-first,
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
checksum-verifies the official `wm` binary on first run. Use the `@next`
dist-tag: npm `@latest` still resolves the stable v9 line.

```bash
npx -y whitemagic-mcp@next serve --profile curated
```

MCP client config:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "npx",
      "args": ["-y", "whitemagic-mcp@next", "serve", "--profile", "curated"]
    }
  }
}
```

Or try the binary directly:

```bash
npx -y whitemagic-mcp@next selftest   # invariant self-test + host diagnostics
npx -y whitemagic-mcp@next --version  # wm 10.2.0-alpha.4
npx -y whitemagic-mcp@next doctor     # environment health check
```

The binary is cached under `~/.cache/whitemagic/bin/<release-tag>/`
(respects `XDG_CACHE_HOME`). `@next` tracks the v10 alpha line; unpinned
`@latest` installs fetch the stable v9 line instead. Pin the exact
prerelease with `whitemagic-mcp@10.2.0-alpha.4`, or override the release
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

Linux x86-64 (static musl), Linux arm64 (static musl), macOS arm64 + x64,
and Windows x64 are install-gated (CI certifies each installer against the
published release). Downloads prefer the compressed `.gz`
distributable when the release ships one (~58% smaller) and fall back to the
raw binary otherwise. No asset for your platform? Build from source:
https://github.com/lbailey94/whitemagic#install

## Privacy

Your memory store lives on your machine. `wm` does not phone home; this
installer contacts GitHub releases only to download the binary and its
checksum. See [PRIVACY_POLICY.md](https://github.com/lbailey94/whitemagic/blob/main/PRIVACY_POLICY.md).

mcp-name: io.github.lbailey94/whitemagic-mcp
