# MCP Client Configuration Guide

**Version**: 5.8.0

The release binary is a single static executable: `wm`. The MCP server is the
`serve` subcommand. The curated profile is the supported surface.

## Native (recommended)

Install the release binary:

```bash
curl -fsSL https://raw.githubusercontent.com/lucas/whitemagic/main/scripts/install.sh | sh
```

This installs `wm` to `~/.local/bin/wm` with SHA-256 checksum verification.
Then use `~/.local/bin/wm` as the command in your MCP client config:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "~/.local/bin/wm",
      "args": ["serve", "--profile", "curated"],
      "env": {
        "RUST_LOG": "warn"
      }
    }
  }
}
```

Store location defaults to `~/.local/share/whitemagic`. Point `--store` at a
different location to use a specific store:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "~/.local/bin/wm",
      "args": ["serve", "--profile", "curated", "--store", "/path/to/store"]
    }
  }
}
```

## Read-only access to a shared store

When another process (e.g. `wm daemon`) owns the store, add `--readonly`:

```json
{
  "mcpServers": {
    "whitemagic-readonly": {
      "command": "~/.local/bin/wm",
      "args": ["serve", "--profile", "curated", "--readonly", "--store", "/path/to/store"]
    }
  }
}
```

Reads, search, session replay, and claims calibration all work in read-only
mode; mutations are refused with a clear error.

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows) with the native
block above.

## Cursor / Windsurf

Cursor: `.cursor/mcp.json` in the project or the Cursor settings MCP panel.
Windsurf: `~/.codeium/windsurf/mcp_config.json`. Both accept the same
`mcpServers` block.

## Other MCP clients

WhiteMagic speaks plain JSON-RPC 2.0 over stdio (MCP `2024-11-05`). Clients
that only expose limited MCP support can call the single `wm` meta-tool with
explicit routes:

- `wm(route="memory.create", args={"content": "...", "galaxy": "codex"})`
- `wm(route="memory.search", args={"query": "..."})`
- `wm(route="session.continuity", args={"n": 5})`
- `wm(route="tools.list")` — discover the full curated surface, including
  argument schemas and safety annotations (readOnlyHint/destructiveHint)

## Environment knobs

| Variable | Default | Purpose |
|---|---|---|
| `RUST_LOG` | error | Log verbosity (stderr) |
| `WM_DISPATCH_TOOL_RPM` | 60 | Per-tool dispatch rate limit |
| `WM_DISPATCH_GLOBAL_RPM` | 300 | Global dispatch limit |
| `WM_DISPATCH_BURST` | 10 | Burst allowance per tool |
| `WM_EMBEDDER_ENDPOINT` | unset | Optional embedding backend for semantic routing (e.g. llama-server `/v1/embeddings`) |

## Troubleshooting

- **"failed to get tools" / tools never load**: the server answers MCP `ping`
  and ignores notifications (fixed in 5.8.0). Update the binary and restart
  the client.
- **LockBusy on startup**: another process owns the store's search index.
  Use `--readonly`, or stop the daemon.
- **Unknown tool errors**: the curated profile only exposes the memory/session
  surface. Use `wm(route="tools.list")` to see what is available.
- **Verify the install**: run `wm doctor --store <path>` and
  `python3 scripts/curated_smoke_test.py`.
