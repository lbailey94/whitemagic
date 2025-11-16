# Start Here: WhiteMagic Quick Orientation

**Welcome!** WhiteMagic is a memory OS for AI agents—think of it as "git for AI memory."

---

## What is WhiteMagic?

WhiteMagic gives AI **durable, structured memory** across sessions, devices, and tools.

**The Problem**: Most AI forgets everything between conversations.  
**The Solution**: Local-first memory that any AI can read and write.

---

## Core Features

- **Tiered Memory**: Short-term (working notes) + Long-term (permanent knowledge)
- **Human-Readable**: Markdown files you can edit directly
- **Multi-Interface**: CLI, Python SDK, REST API, MCP (IDE integration)
- **Local-First**: Your data lives on your machine (cloud optional)
- **AI-Friendly**: Works with ChatGPT, Claude, local LLMs, and agents

---

## Quick Start (Pick Your Path)

### 🚀 I Want to Try It Now (5 minutes)

```bash
# Install
pip install whitemagic

# Create your first memory
whitemagic create "My first memory" --content "Hello WhiteMagic!" --type short_term

# Search
whitemagic search "first"

# Generate context for AI
whitemagic context --tier 1
```

**Next**: [QUICKSTART.md](docs/guides/QUICKSTART.md)

---

### 💻 I Want to Use It in My IDE (10 minutes)

```bash
# Auto-configure Cursor/Windsurf/Claude Desktop
npx whitemagic-mcp-setup
```

Your AI assistant can now create, search, and recall memories!

**Next**: [MCP_CLI_SETUP.md](docs/MCP_CLI_SETUP.md)

---

### 🔧 I Want to Build with It (Python SDK)

```python
from whitemagic import MemoryManager

manager = MemoryManager()

# Create
manager.create_memory(
    title="Project Notes",
    content="Architecture decisions...",
    memory_type="long_term",
    tags=["project", "architecture"]
)

# Search
results = manager.search_memories(query="architecture")

# Context
context = manager.get_context(tier=1)
```

**Next**: [USER_GUIDE.md](docs/USER_GUIDE.md)

---

### 🌐 I Want to Run the API

```bash
# Local development
uvicorn whitemagic.api.app:app --reload

# Docker Compose (full stack)
docker compose up -d
```

API runs at `http://localhost:8000`, docs at `/docs`.

**Next**: [INSTALL.md](INSTALL.md)

---

## Understanding WhiteMagic

### 📖 Philosophy & Theory
Read [VISION.md](docs/VISION.md) to understand:
- Why memory ≈ intelligence
- The "white magic" name
- Memory hygiene principles
- Strategic direction

### 🏗️ Architecture
Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) for:
- System design
- Component structure
- API patterns
- Security model

### 🗺️ Roadmap
Check [ROADMAP.md](ROADMAP.md) for:
- Current version status
- Upcoming features
- Release timeline
- Success metrics

---

## Common Questions

**Q: Is my data private?**  
A: Yes! By default, everything is local. Cloud sync is optional and encrypted.

**Q: What AI tools work with it?**  
A: Any! CLI for command-line, MCP for IDEs (Cursor/Windsurf/Claude), API for custom apps.

**Q: Do I need to code?**  
A: No! The CLI is beginner-friendly. Coding gives you more power.

**Q: Is it production-ready?**  
A: Yes! 223 passing tests, A+ security grade, deployed at api.whitemagic.dev.

**Q: How much does it cost?**  
A: Free locally forever. Cloud features (sync, semantic search) coming soon at ~$12/mo.

---

## Key Links

- **Documentation Index**: [docs/INDEX.md](docs/INDEX.md)
- **User Guide**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- **Cheat Sheet**: [docs/CHEATSHEET.md](docs/CHEATSHEET.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **GitHub**: https://github.com/lbailey94/whitemagic
- **Issues**: https://github.com/lbailey94/whitemagic/issues
- **Security**: [SECURITY.md](SECURITY.md)

---

## Get Help

- 📖 Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) first
- 🐛 Found a bug? [Open an issue](https://github.com/lbailey94/whitemagic/issues)
- 💬 Have questions? [Start a discussion](https://github.com/lbailey94/whitemagic/discussions)
- 🔒 Security issue? See [SECURITY.md](SECURITY.md)

---

## The Big Idea

> **"If git is version control for code, WhiteMagic is version control for thought."**

Traditional AI: Smart but forgetful.  
WhiteMagic AI: Smart **and** remembers.

That changes everything.

---

**Ready?** Pick a quick start path above and dive in! 🚀

**Version**: 2.2.1  
**License**: MIT  
**Last Updated**: November 14, 2025
