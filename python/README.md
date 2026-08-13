# WhiteMagic v5 - Python MCP Shell

## Overview

The Python MCP shell is a thin wrapper around the Rust core. It provides:
- MCP protocol I/O over stdio (JSON-RPC)
- Optional ONNX embedding fallback (via `fastembed`)
- Optional HuggingFace tokenizer integration
- Environment variable configuration

All business logic stays in Rust. Python is only for I/O and ecosystem access.
The native `wm` binary is the primary release path; use this shell only when a
Python extension is required.

## Build

### 1. Build the Rust extension module

```bash
cargo build --release --features python -p wm-mcp
```

This produces a shared library (`libwhitemagic_v5.so` on Linux) in
`target/release/`. Copy or symlink it to your Python path:

```bash
cp target/release/libwhitemagic_v5.so target/release/whitemagic_v5.so
export PYTHONPATH="$PWD/target/release:$PYTHONPATH"
```

### 2. Install optional Python dependencies

```bash
pip install -r python/requirements.txt
```

### 3. Run the server

```bash
python python/whitemagic_v5_server.py --store ~/.local/share/whitemagic/lmdb
```

## MCP Client Configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "whitemagic-v5": {
      "command": "python",
      "args": [
        "/path/to/whitemagic-v5/python/whitemagic_v5_server.py",
        "--store",
        "/path/to/whitemagic-v5/.whitemagic/lmdb"
      ]
    }
  }
}
```

### Cursor / Windsurf

See `python/mcp_config_cursor.json` and `python/mcp_config_windsurf.json`
for templates.

### Pure Rust (no Python)

```json
{
  "mcpServers": {
    "whitemagic-v5": {
      "command": "/path/to/whitemagic-v5/target/release/wm",
      "args": ["serve", "--profile", "curated", "--store", "/path/to/whitemagic-v5/.whitemagic/lmdb"]
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WM_STORE_PATH` | `~/.local/share/whitemagic/lmdb` | Path to LMDB store |
| `WM_LOG_LEVEL` | `info` | Log level: trace, debug, info, warn, error |

## Python API

```python
import whitemagic_v5

# Create server
server = whitemagic_v5.Server("/path/to/lmdb")

# Handle JSON-RPC request
response = server.handle_request('{"jsonrpc":"2.0","id":1,"method":"tools/list"}')

# Get status
print(server.status())
print(server.brain_wave())     # "Gamma", "Beta", "Alpha", "Theta", "Delta"
print(server.tool_count())     # number of registered tools
print(server.coherence())      # citta coherence (0.0-1.0)
print(server.galaxy_counts())  # JSON string of memory counts per galaxy
```
