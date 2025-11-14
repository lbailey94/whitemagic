# WhiteMagic MCP Server

Model Context Protocol server for WhiteMagic memory system, enabling AI agents in Cursor, Windsurf, and Claude Desktop to access tiered memory and context.

## Features

- **Resources**: Access short-term and long-term memories as MCP resources
- **Tools**: Create, search, update, and manage memories
- **Context Generation**: Tier-based context injection (Tier 0/1/2)
- **Consolidation**: Automatic archiving of old memories
- **Native Integration**: Works with Cursor, Windsurf, Claude Desktop

## Installation

### Prerequisites

- Node.js 18+ (for MCP server)
- Python 3.10+ with `whitemagic` package installed
- Cursor, Windsurf, or Claude Desktop

### Setup

1. **Install dependencies**:
   ```bash
   cd whitemagic-mcp
   npm install
   ```

2. **Build the server**:
   ```bash
   npm run build
   ```

3. **Test locally**:
   ```bash
   npm run dev
   ```

## Configuration

### For Cursor

Add to Cursor settings (`settings.json` > MCP Servers):

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "node",
      "args": ["/path/to/whitemagic-mcp/dist/index.js"],
      "env": {
        "WM_BASE_PATH": "/path/to/your/project"
      }
    }
  }
}
```

### For Windsurf

Add to Windsurf config (`~/.windsurf/mcp.json`):

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "node",
      "args": ["/path/to/whitemagic-mcp/dist/index.js"],
      "env": {
        "WM_BASE_PATH": "/path/to/your/project"
      }
    }
  }
}
```

### For Claude Desktop

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "node",
      "args": ["/path/to/whitemagic-mcp/dist/index.js"],
      "env": {
        "WM_BASE_PATH": "/path/to/your/project"
      }
    }
  }
}
```

### Environment Variables

- `WM_BASE_PATH`: Base directory for memory storage (required)
- `WM_API_URL`: WhiteMagic API URL (optional, for REST API mode)
- `WM_API_KEY`: API key for authentication (optional, for REST API mode)

## Resources

The MCP server exposes these resources:

### `memory://short_term`
Recent session-level memories (temporary insights, current context)

### `memory://long_term`
Persistent knowledge (proven patterns, heuristics, decisions)

### `memory://stats`
System statistics (memory counts, tags, storage)

### `memory://tags`
Tag directory with usage statistics

## Tools

### `create_memory`
Create a new memory entry.

**Parameters**:
- `title` (required): Memory title
- `content` (required): Memory content (markdown)
- `type`: `"short_term"` or `"long_term"` (default: `"short_term"`)
- `tags`: Array of tags for categorization

**Example**:
```typescript
create_memory({
  title: "Debugging Async Race Condition",
  content: "Use Promise.all() instead of awaiting in loop to prevent race conditions...",
  type: "long_term",
  tags: ["debugging", "async", "heuristic"]
})
```

### `search_memories`
Search memories by query, type, and tags.

**Parameters**:
- `query`: Search query (searches title, content, tags)
- `type`: Filter by `"short_term"` or `"long_term"`
- `tags`: Array of tags (AND logic)
- `include_archived`: Include archived memories (default: `false`)

**Example**:
```typescript
search_memories({
  query: "async debugging",
  tags: ["heuristic"],
  type: "long_term"
})
```

### `get_context`
Generate tier-appropriate context for AI prompts.

**Parameters**:
- `tier` (required): Context tier
  - `0`: Minimal (2 short-term, summary mode)
  - `1`: Balanced (5 short-term + 2 long-term)
  - `2`: Full (10 short-term + 5 long-term)

**Example**:
```typescript
get_context({ tier: 1 })
```

### `consolidate`
Consolidate and archive old short-term memories.

**Parameters**:
- `dry_run`: If `true`, show what would happen without executing (default: `true`)

**Example**:
```typescript
consolidate({ dry_run: false })
```

### `update_memory`
Update an existing memory's content, title, or tags.

**Parameters**:
- `filename` (required): Memory filename
- `title`: New title (optional)
- `content`: New content (optional)
- `tags`: Replace all tags (optional)
- `add_tags`: Add these tags (optional)
- `remove_tags`: Remove these tags (optional)

### `delete_memory`
Delete or archive a memory.

**Parameters**:
- `filename` (required): Memory filename
- `permanent`: If `true`, permanently delete; otherwise archive (default: `false`)

### `restore_memory`
Restore an archived memory.

**Parameters**:
- `filename` (required): Archived memory filename
- `type`: Target type (`"short_term"` or `"long_term"`, default: `"short_term"`)

## Usage Examples

### In Cursor/Windsurf

Once installed, AI agents can access your memories:

```
Agent: "Show me my recent memories about React hooks"
> Uses: search_memories({ query: "React hooks", type: "short_term" })

Agent: "Create a memory about the bug fix I just did"
> Uses: create_memory({
    title: "Fixed useState closure issue",
    content: "...",
    type: "long_term",
    tags: ["bug-fix", "react", "hooks"]
  })

Agent: "Give me full context for this task"
> Uses: get_context({ tier: 2 })
```

### Testing

Test the MCP server with the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector dist/index.js
```

## Architecture

```
┌─────────────────┐
│  Cursor/        │
│  Windsurf/      │  MCP Protocol
│  Claude Desktop │◄────────────┐
└─────────────────┘             │
                                │
                    ┌───────────▼──────────┐
                    │  WhiteMagic MCP      │
                    │  Server (Node.js)    │
                    └───────────┬──────────┘
                                │
                                │ JSON-RPC
                                │
                    ┌───────────▼──────────┐
                    │  Python Wrapper      │
                    │  (subprocess)        │
                    └───────────┬──────────┘
                                │
                                │ Direct Import
                                │
                    ┌───────────▼──────────┐
                    │  WhiteMagic Library  │
                    │  (Python Package)    │
                    └──────────────────────┘
```

## Development

### Build
```bash
npm run build
```

### Dev Mode (with auto-reload)
```bash
npm run dev
```

### Testing
```bash
# Run tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage
```

### Lint
```bash
npm run lint
```

## Troubleshooting

### "Python process failed to start"
- Ensure Python 3.10+ is installed
- Verify `whitemagic` package is installed: `python3 -c "import whitemagic"`
- Check `WM_BASE_PATH` points to a valid directory

### "Unknown method" errors
- Rebuild the server: `npm run build`
- Restart your IDE
- Check MCP server logs in IDE console

### Memory not persisting
- Verify `WM_BASE_PATH` is set correctly
- Check file permissions on the memory directory
- Ensure `memory/metadata.json` is writable

## License

MIT

## See Also

- [WhiteMagic Documentation](../README.md)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Cursor MCP Docs](https://docs.cursor.com/context/model-context-protocol)
- [Claude Desktop MCP Docs](https://docs.anthropic.com/claude/docs/model-context-protocol)
