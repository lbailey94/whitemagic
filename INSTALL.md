# Installation Guide - WhiteMagic v0.1.0

## Quick Install

### Method 1: Clone and Run (Recommended for v0.1.0)

```bash
# Clone the repository
git clone https://github.com/your-org/whitemagic.git
cd whitemagic

# Install dependencies
pip install pydantic

# Add to your Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verify installation
python3 -c "from whitemagic import MemoryManager; print('✓ WhiteMagic installed')"
```

### Method 2: Direct Python Path

```bash
# Clone the repository
git clone https://github.com/your-org/whitemagic.git

# Use in your Python code
import sys
sys.path.insert(0, '/path/to/whitemagic')
from whitemagic import MemoryManager
```

### Method 3: Pip Install (Coming Soon)

```bash
# Will be available on PyPI soon
pip install whitemagic
```

---

## Requirements

- **Python**: 3.10 or higher
- **Dependencies**: 
  - `pydantic >= 2.0.0` (required)
- **Optional**:
  - `Node.js 18+` (for MCP server)

---

## Installation for Different Use Cases

### For CLI Usage Only

```bash
git clone https://github.com/your-org/whitemagic.git
cd whitemagic

# Install dependencies
pip install pydantic

# Use the CLI
python3 cli.py --help
python3 cli.py create --title "Test" --content "Hello"
```

### For Python Library

```python
# After cloning and adding to PYTHONPATH
from whitemagic import MemoryManager

manager = MemoryManager(base_dir="/path/to/project")
manager.create_memory(
    title="My Memory",
    content="Content here",
    memory_type="short_term",
    tags=["example"]
)
```

### For MCP Server (Windsurf/Cursor/Claude Desktop)

```bash
# 1. Install WhiteMagic (as above)

# 2. Build MCP server
cd whitemagic-mcp
npm install
npm run build

# 3. Configure your IDE
# See whitemagic-mcp/README.md for detailed instructions

# For Windsurf:
nano ~/.codeium/windsurf/mcp_config.json

# Add:
{
  "mcpServers": {
    "whitemagic": {
      "command": "node",
      "args": ["/path/to/whitemagic/whitemagic-mcp/dist/index.js"],
      "env": {
        "WM_BASE_PATH": "/path/to/your/project"
      }
    }
  }
}

# 4. Restart your IDE
```

---

## Verification

### Test Python Package

```bash
python3 -c "from whitemagic import MemoryManager, __version__; print(f'WhiteMagic v{__version__}')"
```

### Test CLI

```bash
python3 cli.py list
```

### Test MCP Server

```bash
cd whitemagic-mcp
WM_BASE_PATH=/path/to/project node dist/index.js
# Should see: "Connected to WhiteMagic" and "MCP Server ready"
```

### Run Tests

```bash
# Unit tests
python3 -m unittest discover tests -v

# MCP integration tests
python3 -m unittest tests.test_mcp_integration -v
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'whitemagic'"

**Solution**: Add WhiteMagic to your Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/whitemagic"
```

Or in Python:
```python
import sys
sys.path.insert(0, '/path/to/whitemagic')
```

### "ModuleNotFoundError: No module named 'pydantic'"

**Solution**: Install pydantic:
```bash
pip install pydantic
```

### MCP Server: "Python stderr: ModuleNotFoundError"

**Solution**: Ensure `WM_BASE_PATH` points to the WhiteMagic directory:
```json
{
  "env": {
    "WM_BASE_PATH": "/absolute/path/to/whitemagic"
  }
}
```

### CLI Not Working

**Solution**: Use Python explicitly:
```bash
python3 cli.py [command]
```

---

## Uninstallation

```bash
# If installed via pip (future)
pip uninstall whitemagic

# If cloned
rm -rf /path/to/whitemagic
# Remove from PYTHONPATH if added
```

---

## Next Steps

- Read [README.md](README.md) for feature overview
- Check [whitemagic-mcp/README.md](whitemagic-mcp/README.md) for MCP setup
- See [ROADMAP.md](ROADMAP.md) for upcoming features
- Run tests to verify everything works

---

## Support

- **Issues**: https://github.com/your-org/whitemagic/issues
- **Discussions**: https://github.com/your-org/whitemagic/discussions
- **Email**: support@whitemagic.dev (coming soon)

---

**Version**: 0.1.0  
**Last Updated**: November 2, 2025
