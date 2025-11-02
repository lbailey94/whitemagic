# WhiteMagic 🧠✨

**Tiered Memory Management for AI Agents with Native MCP Support**

[![Version](https://img.shields.io/badge/version-0.1.0--beta-blue.svg)](https://github.com/your-org/whitemagic)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-23%2F23%20passing-brightgreen.svg)](#testing)

WhiteMagic is a production-ready memory management system for AI agents with native integration for Cursor, Windsurf, and Claude Desktop via MCP.

## ✨ Features

- **Tiered Memory**: Short-term, long-term, and archive storage
- **MCP Integration**: 7 tools + 4 resources for Cursor/Windsurf/Claude
- **Smart Search**: Full-text search with tag filtering
- **Context Generation**: 3-tier context system
- **Type-Safe**: 100% type hints with Pydantic
- **CLI + API**: Command-line and Python library

## 🚀 Quick Start

```bash
# Install
git clone https://github.com/your-org/whitemagic.git
cd whitemagic && pip install pydantic

# Use Python API
python3 -c "from whitemagic import MemoryManager; print('Ready!')"

# Use CLI
python3 cli.py create --title "Test" --content "Hello" --type short_term
```

## 📦 MCP Server (Windsurf/Cursor)

```bash
cd whitemagic-mcp && npm install && npm run build
```

Add to `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "node",
      "args": ["/path/to/whitemagic-mcp/dist/index.js"],
      "env": {"WM_BASE_PATH": "/path/to/whitemagic"}
    }
  }
}
```

## 📚 Documentation

- [INSTALL.md](INSTALL.md) - Installation guide
- [RELEASE_NOTES_v0.1.0.md](RELEASE_NOTES_v0.1.0.md) - Release notes
- [whitemagic-mcp/README.md](whitemagic-mcp/README.md) - MCP setup
- [ROADMAP.md](ROADMAP.md) - Development roadmap

## 🧪 Testing

```bash
python3 -m unittest discover tests -v  # 23/23 tests passing
```

## 📊 Stats

- **2,158** lines Python
- **772** lines TypeScript  
- **23** tests (100% passing)
- **1** dependency (pydantic)

## 🗺️ Roadmap

- ✅ Phase 1A: Python API
- ✅ Phase 1B: MCP Integration
- 🚧 Phase 2A: Whop + REST API (next)
- 📅 Phase 2B: Semantic search
- 📅 Phase 3: Extensions

## 📄 License

MIT - See [LICENSE](LICENSE)

## 🔗 Links

- Issues: https://github.com/your-org/whitemagic/issues
- Discussions: https://github.com/your-org/whitemagic/discussions
