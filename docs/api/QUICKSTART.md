# WhiteMagic API Quick Start

## From Python

```python
from whitemagic.tools.unified_api import call_tool

# Create a memory
result = call_tool("create_memory", content="Hello, WhiteMagic!", galaxy="universal")

# Search memories
results = call_tool("search_memories", query="hello", limit=5)

# Check system health
health = call_tool("health")
```

## From MCP Client (Claude Desktop)

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "uvx",
      "args": ["whitemagic-mcp"]
    }
  }
}
```

## From HTTP

```bash
# Start HTTP server
whitemagic-mcp --http --port 8770

# Call a tool
curl -X POST http://localhost:8770/tools/search_memories \
  -H "Content-Type: application/json" \
  -d '{"query": "hello", "limit": 5}'
```

## Tool Modes

| Mode | Env Var | Tools | Description |
|------|---------|-------|-------------|
| Seed | `WM_MCP_PRAT=2` | 1 (`wm`) | Single meta-tool, minimal tokens |
| PRAT | `WM_MCP_PRAT=1` | 29 | 28 Ganas + `wm` |
| Classic | `WM_MCP_PRAT=0` | 801 | Direct tool access |

## Categories

Browse tools by category in `categories/` or by Gana in `gana/`.
