# WhiteMagic MCP - Quick Setup Guide

**5-minute setup for Windsurf, Cursor, and Claude Desktop**

---

## What You Need

- ✅ Windsurf, Cursor, or Claude Desktop installed
- ✅ Python 3.10+ installed
- ✅ Node.js 18+ installed
- ⏱️ 5 minutes

---

## Step 1: Install WhiteMagic MCP

### Option A: Install from npm (Recommended - Easiest!)

```bash
npm install -g whitemagic-mcp
```

### Option B: From Source (For Development)

```bash
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic/whitemagic-mcp
npm install
npm run build
```

---

## Step 2: Add to Your IDE

### For Windsurf or Cursor

1. **Open Settings**
   - Press `Cmd+,` (Mac) or `Ctrl+,` (Windows/Linux)

2. **Search for "MCP"**
   - Type "MCP" in the search box

3. **Click "Add Server"**

4. **Enter Server Details**:
   - **Name**: `WhiteMagic`
   - **Command**: `node`
   - **Args** (choose based on your install):
     - **Global install**:

       ```
       /usr/local/lib/node_modules/whitemagic-mcp/dist/index.js
       ```

     - **Local install (macOS/Linux)**:

       ```
       /Users/YOUR_USERNAME/path/to/whitemagic/whitemagic-mcp/dist/index.js
       ```

     - **Local install (Windows)**:

       ```
       C:\Users\YOUR_USERNAME\path\to\whitemagic\whitemagic-mcp\dist\index.js
       ```

   - **Environment Variables**:

     ```
     WM_BASE_PATH=/path/to/your/memory/folder
     ```

     Example: `/Users/yourname/whitemagic-memory`

5. **Save** and **Connect**
   - Click "Save"
   - Find WhiteMagic in the MCP panel
   - Click "Connect"

### For Claude Desktop

1. **Edit Configuration File**:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add WhiteMagic Server**:

   ```json
   {
     "mcpServers": {
       "whitemagic": {
         "command": "node",
         "args": [
           "/usr/local/lib/node_modules/whitemagic-mcp/dist/index.js"
         ],
         "env": {
           "WM_BASE_PATH": "/path/to/your/memory/folder"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop**

---

## Step 3: Test It Works

Ask your AI assistant:

```
Show me my memories
```

Or:

```
Create a test memory with title "My First Memory" and content "Testing WhiteMagic!"
```

You should see WhiteMagic tools appear and execute! 🎉

---

## Available Commands

Once connected, ask your AI to:

### Memory Management

- `"Create a short-term memory about this project"`
- `"List all my memories"`
- `"Search my memories for Python"`
- `"Update the memory about XYZ"`
- `"Delete the memory about ABC"`

### Context & Search

- `"Give me tier 1 context from my memories"`
- `"Search for memories tagged with 'important'"`
- `"Get memory statistics"`
- `"Show me all my tags"`

### Advanced

- `"Consolidate old memories (dry run)"`
- `"Get all my archived memories"`

---

## Troubleshooting

### "Command not found" or "node: not found"

**Solution**: Find your node path and use the full path:

```bash
# Find node path
which node

# On macOS/Linux, might be:
/usr/local/bin/node

# On Windows with nvm:
C:\Program Files\nodejs\node.exe
```

Use this full path in the "Command" field.

---

### "Connection failed" or "Server not responding"

**Checklist**:

1. ✅ Verify `WM_BASE_PATH` points to an existing directory
2. ✅ Check the directory is writable
3. ✅ Verify the path to `index.js` is correct
4. ✅ Check IDE logs/MCP panel for error details

**Create the directory if it doesn't exist**:

```bash
mkdir -p /path/to/your/memory/folder
```

---

### "No memories found" when asking to list

This is normal on first run! Create your first memory:

```
Create a test memory
```

Then verify:

```
List my memories
```

---

### Permission denied errors

**Solution**: Ensure the memory folder is writable:

```bash
chmod 755 /path/to/your/memory/folder
```

---

### Server keeps disconnecting

**Check**:

1. No other WhiteMagic instance running
2. Port 8000 not already in use (if running API)
3. Node.js version is 18+: `node --version`

---

## Next Steps

### Level 1: CLI User (Beginner)

→ See [User Guide - CLI Basics](../USER_GUIDE.md#cli-basics)

### Level 2: API User (Intermediate)

→ See [User Guide - API Setup](../USER_GUIDE.md#api-setup)

### Level 3: Developer (Advanced)

→ See [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

## Finding Your Node Path

### macOS/Linux

```bash
# Standard locations
which node
# Output examples:
# /usr/local/bin/node
# /opt/homebrew/bin/node
# ~/.nvm/versions/node/v20.0.0/bin/node

# For global npm packages
npm root -g
# Then append: /whitemagic-mcp/dist/index.js
```

### Windows

```cmd
# Find node
where node
# Output example: C:\Program Files\nodejs\node.exe

# For global npm packages
npm root -g
# Then append: \whitemagic-mcp\dist\index.js
```

---

## Configuration Reference

### Minimum Configuration

```json
{
  "command": "node",
  "args": ["/path/to/whitemagic-mcp/dist/index.js"],
  "env": {
    "WM_BASE_PATH": "/path/to/memory"
  }
}
```

### Full Configuration (with API)

```json
{
  "command": "node",
  "args": ["/path/to/whitemagic-mcp/dist/index.js"],
  "env": {
    "WM_BASE_PATH": "/path/to/memory",
    "WM_API_URL": "http://localhost:8000",
    "WM_API_KEY": "your-api-key-here"
  }
}
```

---

## Support

- 📖 **Full Documentation**: [USER_GUIDE.md](../USER_GUIDE.md)
- 🐛 **Issues**: <https://github.com/lbailey94/whitemagic/issues>
- 💬 **Discussions**: <https://github.com/lbailey94/whitemagic/discussions>
- 📝 **Cheat Sheet**: [CHEATSHEET.md](../CHEATSHEET.md)

---

## Quick Reference Card

| Task | Command Example |
|------|----------------|
| Create memory | "Create a memory titled 'Meeting Notes' with content '...'" |
| List memories | "Show me all my memories" |
| Search | "Search for memories about Python" |
| Delete | "Delete the memory about XYZ" |
| Get context | "Give me context tier 1" |
| Stats | "Show memory statistics" |

---

**Setup Time**: ~5 minutes
**Skill Level**: Beginner
**Support**: Available via GitHub issues

Happy memory managing! 🧠✨
