# MCP Client Configuration Guide

**Version**: 7.0.0-alpha.3

The release binary is a single executable: `wm` (dynamically linked; requires
glibc 2.39+). The MCP server is the `serve` subcommand. The curated profile
is the supported surface.

## Native (recommended)

Install the release binary:

```bash
curl -fsSL https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.sh | sh
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

## One store per project (recommended for multi-project users)

If you work across several projects, give each project its own store and
scope label instead of sharing one global store — otherwise `session.continuity`
returns whichever project ran last and memories cross-contaminate. Per
client, scope the config to the project directory and set `WM_PROJECT`:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "~/.local/bin/wm",
      "args": ["serve", "--profile", "curated", "--store",
               "~/.local/share/whitemagic-<project>"],
      "env": {
        "RUST_LOG": "warn",
        "WM_PROJECT": "<project>"
      }
    }
  }
}
```

The server discloses mode, project, and store path in the MCP handshake and
`tools/list`, so agents can confirm which memory slice they are bound to
before writing. Layout details, hygiene conventions (`project:<name>` tags),
and a worked example: [`MULTI_PROJECT_MEMORY.md`](MULTI_PROJECT_MEMORY.md).

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
mode; mutations are refused with an error that states the mode and how to
fix the configuration. The server also announces read-only mode in its MCP
handshake and `tools/list` so agents do not waste attempts on writes.

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
| `WM_PROJECT` | unset | Project scope label disclosed in the MCP handshake and `tools/list` |
| `WM_PROJECT_ROOT` | unset | Repository root — `session.checkpoint` auto-captures git state; `session.verify` reports drift against it |
| `WM_EMBEDDER_ENDPOINT` | unset | Optional embedding backend for semantic routing (e.g. llama-server `/v1/embeddings`) |
| `WM_FRICTION_AUTOLOG` | off | Opt-in (`1`): auto-write friction/anomaly memories to the store on dispatch errors and latency/karma anomalies. Default off — failures remain visible in tool errors and (in `--readonly` mode) the `friction_ro.jsonl` sidecar |

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
