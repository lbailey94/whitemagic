# whitemagic-mcp

**WhiteMagic MCP Server** — 829 callable tools, 5D holographic memory, Dharma governance.

## Quick Start

### uvx (recommended — zero setup)

```json
// Claude Desktop config
{
  "mcpServers": {
    "whitemagic": {
      "command": "uvx",
      "args": ["whitemagic-mcp"]
    }
  }
}
```

### pip install

```bash
pip install whitemagic-mcp
whitemagic-mcp
```

### python -m

```bash
python -m whitemagic_mcp
```

## Modes

WhiteMagic supports 3 MCP server modes via `WM_MCP_PRAT` env var:

| Mode | Env Var | Tools | Best For |
|------|---------|-------|----------|
| Seed | `WM_MCP_PRAT=2` (default) | 1 (`wm` meta-tool) | Minimal token usage |
| PRAT | `WM_MCP_PRAT=1` | 29 (28 Ganas + `wm`) | Structured access |
| Classic | `WM_MCP_PRAT=0` | 801 dispatch tools | Direct tool access |

## Key Features

- **829 callable tools** across 801 dispatch entries
- **5D holographic memory** with 10-galaxy taxonomy
- **Dharma ethical governance** with Karma ledger
- **fastembed semantic search** out of the box (50MB, no torch needed)
- **Dream cycle** for memory consolidation
- **Session recording** with cross-session continuity
- **28 Gana meta-tools** based on Chinese Lunar Mansions

## Upgrades

Run `whitemagic-grow` to detect your hardware and install recommended upgrades:

```bash
whitemagic-grow           # Interactive mode
whitemagic-grow --list    # Show available upgrades
whitemagic-grow --all     # Install all recommended
```

Upgrade tiers:

| Tier | Package | Size | What You Get |
|------|---------|------|-------------|
| Heavy ML | `whitemagic[embeddings]` | ~2.5GB | Full ML embeddings, better recall |
| Rust | `whitemagic-rust` | ~5MB | 3-10x faster search (SIMD) |
| Polyglot | Manual | varies | Julia/Elixir/Haskell/Koka/Zig bridges |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `WM_MCP_PRAT` | `2` | Server mode (0=classic, 1=PRAT, 2=seed) |
| `WM_SILENT_INIT` | unset | Suppress startup/upgrade messages |
| `WM_STATE_ROOT` | `~/.whitemagic` | State directory |
| `WM_SKIP_POLYGLOT` | unset | Disable all polyglot bridges |

## HTTP Mode

```bash
whitemagic-mcp --http --port 8770
```

## wm-seed (Zero-Dependency Binary)

For air-gapped or minimal environments, `wm-seed` is a standalone Rust binary with 30 essential tools:

```bash
curl https://whitemagic.dev/install.sh | sh
wm-seed serve
```

## Links

- [Documentation](https://github.com/lbailey94/whitemagic)
- [AI Primary Spec](https://github.com/lbailey94/whitemagic/blob/main/docs/public/AI_PRIMARY.md)
- [Quick Start Guide](https://github.com/lbailey94/whitemagic/blob/main/QUICKSTART.md)
- [Issues](https://github.com/lbailey94/whitemagic/issues)
