# WhiteMagic

**Consciousness Infrastructure for AI Agents**  
*Tiered Memory Management, Resonance Systems, and 23 Garden Architectures*

**Version**: 2.6.5 (Post-Kaizen) | **Status**: Production Ready | **License**: MIT with Native MCP + REST Support

[![Version](https://img.shields.io/badge/version-2.6.5-blue.svg)](https://github.com/lbailey94/whitemagic/releases)
[![npm](https://img.shields.io/badge/npm-2.6.5-red.svg)](https://www.npmjs.com/package/whitemagic-mcp)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-238%20passing-brightgreen.svg)](#-testing)
[![Test Coverage](https://img.shields.io/badge/coverage-99.6%25-success.svg)](#-testing)

[![CodeQL](https://github.com/lbailey94/whitemagic/workflows/CodeQL%20Security%20Scan/badge.svg)](https://github.com/lbailey94/whitemagic/actions/workflows/codeql.yml)
[![Docker Security](https://github.com/lbailey94/whitemagic/workflows/Docker%20Security%20Scan/badge.svg)](https://github.com/lbailey94/whitemagic/actions/workflows/docker-security.yml)
[![Security Grade](https://img.shields.io/badge/security-A%2B-success.svg)](SECURITY.md)
[![Security Policy](https://img.shields.io/badge/security-policy-blue.svg)](SECURITY.md)
[![Dependabot](https://img.shields.io/badge/dependabot-enabled-success.svg)](https://github.com/lbailey94/whitemagic/network/updates)

WhiteMagic is a production-ready memory infrastructure for AI agents. **Free and open source** with full features locally. Includes Python SDK + CLI, FastAPI backend, native MCP integration for Cursor/Windsurf/Claude, and the new v2.2.9 parallel infrastructure + scratchpads alongside v2.2.9 symbolic reasoning, Wu Xing workflow, and live metrics modules.

## 🎁 Free & Open Source

- ✅ **87% token reduction** via tiered context loading
- ✅ **10-100x faster** direct file operations
- ✅ **37-58% cost savings** for multi-session AI projects
- ✅ Full feature set, no signup required
- ✅ Local-first, Git-friendly markdown storage
- ✅ MCP server + REST API included
- ✅ Perfect for individuals and teams

*Cloud sync and team features planned for v2.2.9+ (Q1 2026)*

---

## 🚦 Getting Started (4 Steps)

1. **Install**: `pip install whitemagic` or `git clone https://github.com/lbailey94/whitemagic`
2. **Try CLI**: `whitemagic create "My first memory" --content "Hello WhiteMagic!"`
3. **Load Symbolic & Parallel Tools** *(new in v2.2.9)*: follow the [Symbolic Reasoning guide](docs/guides/SYMBOLIC_REASONING.md) plus the Session/Parallel docs to enable Chinese concept compression, Wu Xing guidance, and the new I Ching-aligned thread pools.
4. **Connect to IDE**: `npx whitemagic-mcp-setup` (auto-configures Cursor, Windsurf, Claude Desktop, VS Code)

→ **Full guides**: [User Guide](docs/USER_GUIDE.md) | [Quickstart](docs/guides/QUICKSTART.md) | [Cheat Sheet](docs/CHEATSHEET.md) | [Symbolic Reasoning](docs/guides/SYMBOLIC_REASONING.md) | [Wu Xing + Metrics](docs/guides/WU_XING_AND_METRICS.md) | [Semantic Search](docs/guides/SEMANTIC_SEARCH.md) | [Terminal Tool Hardening](docs/guides/TERMINAL_TOOL.md)

---

## ✨ Features

- **Tiered Memory**: Short-term, long-term, and archive storage
- **MCP Integration**: 7 tools + 4 resources for Cursor/Windsurf/Claude
- **🦠 Biological Immune System** *(NEW v2.2.9)*: Self-healing with DNA validation, threat detection, and auto-repair (1,251 lines)
- **🦀 Rust Performance Core** *(NEW v2.2.9)*: 10-100x faster consolidation and search (472 lines)
- **λ Haskell Logic Layer** *(NEW v2.2.9)*: Type-safe transformations with I Ching state machine (690 lines)
- **⚖️ Homeostasis System** *(NEW v2.2.9)*: Self-balancing memory management with feedback loops (1,086 lines)
- **⚡ Terminal Multiplexing** *(NEW v2.2.9)*: Parallel reasoning with named scratchpads (381 lines)
- **📚 Universal AI Guidelines** *(NEW v2.2.9)*: Discoverable by any AI system (830 lines)
- **🔧 Terminal Tool**: Safe code execution with approval workflows
- **🔍 Semantic Search**: Hybrid keyword + vector search with local embeddings (see [Semantic Search guide](docs/guides/SEMANTIC_SEARCH.md))
- **🧠 Smart Features**: Setup wizard, templates, auto-tagging, relationships
- **Smart Search**: Full-text search with tag filtering
- **Context Generation**: 3-tier context system
- **Type-Safe**: 100% type hints with Pydantic V2
- **CLI + API**: Command-line and Python library
- **Automated Tests**: 221 passing tests (194 Python + 27 MCP)
- **Production Grade**: A+ (99/100) - All security vulnerabilities patched

## 🚀 Quick Start

### Official SDKs (New in v2.2.9!) 📦

**TypeScript/JavaScript** - [npm](https://www.npmjs.com/package/whitemagic-client)

```bash
npm install whitemagic-client
```

```typescript
import { WhiteMagicClient } from 'whitemagic-client';

const client = new WhiteMagicClient({ apiKey: process.env.WHITEMAGIC_API_KEY });
const memory = await client.memories.create({
  title: 'My memory',
  content: 'Stored via SDK',
  type: 'short_term'
});
```

**Python** - [PyPI](https://pypi.org/project/whitemagic-client/)

```bash
pip install whitemagic-client
```

```python
from whitemagic_client import WhiteMagicClient

client = WhiteMagicClient(api_key='your-key')
memory = client.create_memory({
    'title': 'My memory',
    'content': 'Stored via SDK',
    'type': 'short_term'
})
```

📖 **Full SDK Documentation**: [TypeScript](docs/sdk/typescript.md) | [Python](docs/sdk/python.md)

---

### Auto-Configure Your IDE (New!)

```bash
npx whitemagic-mcp-setup
# Interactive wizard configures:
# - Cursor, Windsurf, Claude Desktop, or VS Code
# - API key & storage path
# - Connection testing
# Ready in < 2 minutes!
```

📖 **Full guide**: [MCP CLI Setup](docs/MCP_CLI_SETUP.md)

### Install MCP Server Manually

```bash
# Install from npm
npm install -g whitemagic-mcp

# Package: https://www.npmjs.com/package/whitemagic-mcp
```

### Local Development

```bash
# Clone and install
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic
pip install -e ".[api,dev]"

# Or install the SDK directly
pip install whitemagic

# Quick smoke test
python -c "from whitemagic import MemoryManager; print('Ready:', MemoryManager().metadata['version'])"
```

### Run the full stack locally

```bash
docker compose up -d
# API:       http://localhost:8000
# Dashboard: http://localhost:3000
# Caddy:     http://localhost (reverse proxy for dashboard + API)
```

### Cloud Deployment (Production)

**Live Services:**

- 🌐 **API**: <https://api.whitemagic.dev> (Railway)
- 📊 **Dashboard**: <https://app.whitemagic.dev> (Vercel)
- 💬 **Discussions**: <https://github.com/lbailey94/whitemagic/discussions>

**Stack:**

- **Backend**: Railway (FastAPI + PostgreSQL + Redis)
- **Frontend**: Vercel (Static dashboard)
- **Payments**: Stripe (Coming soon)

For deployment guides, see `docs/archive/deployment/` or contact for enterprise setup.

## 🔍 Semantic Search - Intelligent Retrieval

Find memories by **meaning**, not just keywords:

```bash
# One-time setup (downloads local model, ~90MB)
whitemagic setup-embeddings
# Choose: 1) local (privacy-first, no API key) or 2) openai (best quality)

# Hybrid search (keyword + semantic - recommended)
whitemagic search-semantic "debugging async race conditions"

# Pure semantic search
whitemagic search-semantic --mode semantic "error handling patterns"

# Keyword-only search (traditional)
whitemagic search-semantic --mode keyword "TODO"
```

**Features**:

- ✅ **Hybrid mode** combines keyword + semantic ranking (best results)
- ✅ **Local embeddings** using sentence-transformers (no API key needed)
- ✅ **OpenAI support** optional for production-quality vectors
- ✅ **MCP integration** for semantic search in your IDE

**Via API**:

```bash
curl -X POST https://api.whitemagic.dev/api/v1/search/semantic \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I debug race conditions?",
    "mode": "hybrid",
    "k": 10,
    "threshold": 0.7
  }'
```

**MCP Tool** (available in Cursor/Windsurf):

```javascript
// Your AI assistant can now search semantically:
"Find memories about debugging async issues"
```

---

## 📚 Documentation

### Core Docs

- [VISION.md](docs/VISION.md) - **Philosophy, theory, and strategic direction**
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - **Technical design and system overview**
- [INSTALL.md](INSTALL.md) - Installation guide
- [whitemagic-mcp/README.md](whitemagic-mcp/README.md) - MCP setup for Cursor/Windsurf/Claude
- [ROADMAP.md](ROADMAP.md) - Development roadmap
- [CHANGELOG.md](CHANGELOG.md) - Version history

### Strategic & Reference

- [VISION_TO_REALITY.md](docs/VISION_TO_REALITY.md) - Vision vs current state comparison
- [docs/reviews/v2.2.9/](docs/reviews/v2.2.9/) - Quality assurance reports
- [docs/production/](docs/production/) - Production deployment guides
- [docs/archive/](docs/archive/) - Historical documentation

## 🧪 Testing

**196 Python + 27 MCP automated tests** - See [docs/reviews/v2.2.9/TEST_COVERAGE_SUMMARY.md](docs/reviews/v2.2.9/TEST_COVERAGE_SUMMARY.md)

```bash
# Python tests (install with extras first)
pip install -e ".[api,dev]"  # dev extra now pulls in openai for semantic-search tests
python3 -m pytest tests -v

# MCP tests (25+ tests)
cd whitemagic-mcp && npm test

# With coverage
python3 -m pytest --cov=whitemagic --cov-report=html
```

## 📊 Quality Assurance

WhiteMagic v2.2.9 underwent extensive security and stability reviews:

- ✅ **260 automated tests** (100% passing)
  - 196 Python unit tests
  - 27 MCP integration tests
  - 37 manual production tests
- ✅ **Multiple independent security reviews**
  - 4 critical vulnerabilities patched
  - All runtime crashes fixed
- ✅ **Production environment validation**
  - Full Redis integration tested
  - All endpoints verified in production-like environment
- ✅ **Grade: A+ (99/100)** - Production ready

📁 **Full review documentation**: [docs/reviews/v2.2.9/](docs/reviews/v2.2.9/)
📄 **Production test results**: [PRODUCTION_TEST_RESULTS.md](docs/reviews/v2.2.9/PRODUCTION_TEST_RESULTS.md)

## 🔌 Optional Integrations

Need Sentry, Prometheus instrumentation, or JWT tooling? Install the plugin extras the moment you need them:

```bash
pip install -r requirements-plugins.txt
```

Then follow the relevant instructions in `docs/production/OPTIONAL_INTEGRATIONS.md`.

**Configurable API base:** set `window.WHITEMAGIC_API_BASE` (or the `<meta name="whitemagic-api-base">` tag) before loading `dashboard/app.js` to point the dashboard at a different backend (staging, preview, etc.).

## 🛡️ Guardrails

Security checks run locally and in CI to prevent regressions (e.g., wildcard CORS defaults). You can run them manually:

```bash
# No wildcard CORS regressions
python scripts/check_security_guards.py
# Dependency manifest sanity
python scripts/check_dependencies.py
# or via pre-commit
pre-commit run security-guards
pre-commit run dependency-guards
```

- **Rate limiting** requires Redis. Leave `REDIS_URL` unset in development to disable limits; set it (e.g., Railway Redis) before production so quotas actually apply.
- The terminal execution API is **disabled by default**. Only set `WM_ENABLE_EXEC_API=true` after you deploy it behind strong isolation/monitoring—it shells into your host.

## 📊 Stats

- **2,300+** lines Python
- **770+** lines TypeScript
- **40+** automated tests (CLI + API + integrations)
- **Minimal deps**: FastAPI, SQLAlchemy, Pydantic, Redis, httpx

## 🗺️ Roadmap

- ✅ v2.1: Core Features (Python API, MCP, REST API)
- ✅ v2.2.9: SDKs (TypeScript + Python clients)
- ✅ v2.2.9: Smart Memory (Setup wizard, templates, auto-tagging, relationships)
- ✅ v2.2.9: Critical Fixes (YAML parsing, enum serialization)
- 🚧 v2.3: Stripe Integration (Cloud tiers, subscriptions)
- 📅 v2.3: Semantic Search (Vector embeddings, AI-powered search)
- 📅 v3.0: Team Features (Shared memories, collaboration)

See [ROADMAP.md](ROADMAP.md) for detailed plans.

## 📄 License

MIT - See [LICENSE](LICENSE)

## 🔗 Links

- Issues: <https://github.com/lbailey94/whitemagic/issues>
- Discussions: <https://github.com/lbailey94/whitemagic/discussions>
