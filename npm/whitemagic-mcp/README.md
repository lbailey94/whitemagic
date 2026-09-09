# whitemagic-mcp

[WhiteMagic](https://whitemagic.dev) — local-first memory and session
continuity for AI coding agents, over MCP. One static Rust binary, no
telemetry, no cloud service. MIT.

This package installs and runs the official `wm` binary from the
[GitHub releases](https://github.com/lbailey94/whitemagic/releases)
(checksum-verified at install time) so an MCP client can launch it
without a manual download step.

## Use

Point any MCP client (Claude Desktop, Cursor, Codex, Gemini CLI,
opencode) at:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "whitemagic-mcp",
      "args": ["serve", "--profile", "curated"]
    }
  }
}
```

Or try it directly:

```bash
npx whitemagic-mcp --version   # wm 9.0.0
npx whitemagic-mcp doctor      # environment health check
```

The binary is cached under `~/.cache/whitemagic/bin/<release-tag>/`
(respects `XDG_CACHE_HOME`); the package version's major tracks the
release tag (9.0.0 → `v9`). Pin a different release with
`WHITEMAGIC_RELEASE`.

## Platforms

Linux x86-64 (static musl), macOS arm64/x64, Windows x64. No asset for
your platform? Build from source:
https://github.com/lbailey94/whitemagic#install

## Privacy

Your memory store lives on your machine. `wm` does not phone home; this
installer contacts GitHub releases only to download the binary and its
checksum. See [PRIVACY_POLICY.md](https://github.com/lbailey94/whitemagic/blob/main/PRIVACY_POLICY.md).
