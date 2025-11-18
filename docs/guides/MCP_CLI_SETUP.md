# MCP CLI Auto-Setup

One-command setup for WhiteMagic in any MCP-compatible IDE.

## Quick Start

```bash
npx whitemagic-mcp-setup
```

That's it! The wizard will:

1. ✅ Detect your IDE (Cursor, Windsurf, Claude Desktop, VS Code)
2. ✅ Prompt for your API key
3. ✅ Configure base path
4. ✅ Test the connection
5. ✅ Write the config
6. ✅ Backup existing config

---

## Supported IDEs

| IDE | Config Path | Status |
|-----|-------------|--------|
| **Cursor** | `~/.cursor/mcp.json` | ✅ Supported |
| **Windsurf** | `~/.windsurf/mcp_server_config.json` | ✅ Supported |
| **Claude Desktop** | Platform-specific | ✅ Supported |
| **VS Code (Cline)** | `~/.vscode/mcp/settings.json` | ✅ Supported |

### Platform-Specific Paths

**Claude Desktop**:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

---

## Usage

### Interactive Mode (Recommended)

```bash
npx whitemagic-mcp-setup
```

The wizard will guide you through:

1. **IDE Detection**

   ```
   🔍 Detected MCP-Compatible IDEs:
     ✅ Config found - Windsurf
       Path: /home/user/.windsurf/mcp_server_config.json
   ```

2. **API Key Input**

   ```
   🔑 API Key Configuration
   Enter your WhiteMagic API key: wm_****
   ```

3. **Storage Configuration**

   ```
   📁 Storage Configuration
   Base path for memories [~/whitemagic]:
   ```

4. **API Configuration**

   ```
   🌐 API Configuration
   API URL [https://api.whitemagic.dev]:
   ```

5. **Connection Test**

   ```
   🔌 Testing connection...
   ✅ Connection successful!
   📦 API Version: 2.2.7
   ```

6. **Config Writing**

   ```
   💾 Creating backup...
   📦 Backup created: /home/user/.windsurf/mcp_server_config.json.backup-2025-11-12

   📝 Writing configuration...
   ✅ Config written: /home/user/.windsurf/mcp_server_config.json
   ```

7. **Success!**

   ```
   ✅ Setup complete!
   🎉 WhiteMagic is now configured for your IDE.

   Next steps:
     1. Restart your IDE
     2. WhiteMagic MCP server will start automatically
     3. Try: "Create a new memory called 'test'"
   ```

---

## Configuration Generated

The setup creates this config structure:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "npx",
      "args": ["-y", "whitemagic-mcp"],
      "env": {
        "WHITEMAGIC_API_KEY": "your-api-key",
        "WM_BASE_PATH": "~/whitemagic",
        "WM_API_BASE_URL": "https://api.whitemagic.dev"
      }
    }
  }
}
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WHITEMAGIC_API_KEY` | ✅ Yes | - | Your WhiteMagic API key |
| `WM_BASE_PATH` | No | `~/whitemagic` | Local storage path |
| `WM_API_BASE_URL` | No | `https://api.whitemagic.dev` | API endpoint |

---

## Features

### Auto-Detection

- Scans for all MCP-compatible IDEs
- Prioritizes existing configurations
- Shows which IDEs are already configured

### Safe Merging

- Backs up existing config before changes
- Merges WhiteMagic into existing MCP configs
- Doesn't overwrite other MCP servers

### Connection Testing

- Validates API key format
- Tests connection to WhiteMagic API
- Verifies authentication
- Shows API version

### Error Handling

- Clear error messages
- Rollback capability
- Retry on validation failures
- Option to continue on connection errors

---

## Troubleshooting

### No IDE Detected

```
❌ No MCP-compatible IDE detected.
```

**Solution**: Install one of the supported IDEs:

- [Cursor](https://cursor.sh/)
- [Windsurf](https://codeium.com/windsurf)
- [Claude Desktop](https://claude.ai/download)
- [VS Code](https://code.visualstudio.com/) + [Cline extension](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev)

### Invalid API Key

```
❌ Invalid API key format.
```

**Solution**:

1. Get your API key from the WhiteMagic dashboard
2. Ensure you copied the entire key (starts with `wm_` or similar)
3. No spaces or newlines

### Connection Failed

```
❌ Could not connect to API (connection refused)
```

**Causes**:

- API is down (check status page)
- Network connectivity issues
- Firewall blocking requests
- Wrong API URL for self-hosted

**Solution**:

- Verify you can reach <https://api.whitemagic.dev>
- For self-hosted, use correct URL
- You can continue setup anyway (connection tested on IDE restart)

### Permission Denied

```
❌ Failed to write config: EACCES: permission denied
```

**Solution**:

- Check file permissions on config directory
- Ensure you have write access
- Try running without sudo (should work for user configs)

---

## Advanced Usage

### Self-Hosted WhiteMagic

If you're running WhiteMagic locally or on your own server:

```bash
npx whitemagic-mcp-setup
# When prompted for API URL, enter your server:
API URL: http://localhost:8000
```

### Custom Base Path

```bash
# When prompted:
Base path for memories: /custom/path/to/memories
```

### Manual Configuration

If you prefer to configure manually, create/edit your IDE's config file:

**Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "npx",
      "args": ["-y", "whitemagic-mcp"],
      "env": {
        "WHITEMAGIC_API_KEY": "your-key-here",
        "WM_BASE_PATH": "~/whitemagic"
      }
    }
  }
}
```

**Windsurf** (`~/.windsurf/mcp_server_config.json`):

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "npx",
      "args": ["-y", "whitemagic-mcp"],
      "env": {
        "WHITEMAGIC_API_KEY": "your-key-here",
        "WM_BASE_PATH": "~/whitemagic"
      }
    }
  }
}
```

---

## Testing

Test IDE detection without making changes:

```bash
# Clone the repo
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic/whitemagic-mcp

# Build
npm install
npm run build

# Test detection
node dist/cli/detect-test.js
```

---

## Development

### Project Structure

```
whitemagic-mcp/src/cli/
├── setup.ts       # Main setup wizard
├── detect.ts      # IDE detection
├── config.ts      # Config read/write/merge
├── validate.ts    # API key & connection validation
└── detect-test.ts # Detection testing tool
```

### Running Locally

```bash
cd whitemagic-mcp
npm run setup
```

### Building

```bash
npm run build
# Output: dist/cli/setup.js (executable)
```

---

## Next Steps

After setup:

1. **Restart IDE** - Close and reopen your IDE
2. **Test Connection** - Try: "List my memories"
3. **Create Memory** - Try: "Create a memory called 'test'"
4. **Explore Tools** - See what WhiteMagic can do

---

## Support

- **Documentation**: <https://github.com/lbailey94/whitemagic#readme>
- **Issues**: <https://github.com/lbailey94/whitemagic/issues>
- **Discord**: Coming soon!

---

**Last Updated**: November 12, 2025
**Version**: 2.1.4
**Status**: ✅ Ready to use
