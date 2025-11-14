# WhiteMagic 🧠✨

**Tiered Memory Management for AI Agents with Native MCP + REST Support**

[![Version](https://img.shields.io/badge/version-2.1.5-blue.svg)](https://github.com/lbailey94/whitemagic/releases)
[![npm](https://img.shields.io/badge/npm-2.1.3-red.svg)](https://www.npmjs.com/package/whitemagic-mcp)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-223%20passing-brightgreen.svg)](#testing)
[![Grade](https://img.shields.io/badge/grade-A%2B%20(99%2F100)-success.svg)](docs/reviews/v2.1.3/PRODUCTION_TEST_RESULTS.md)

[![CodeQL](https://github.com/lbailey94/whitemagic/workflows/CodeQL%20Security%20Scan/badge.svg)](https://github.com/lbailey94/whitemagic/actions/workflows/codeql.yml)
[![Docker Security](https://github.com/lbailey94/whitemagic/workflows/Docker%20Security%20Scan/badge.svg)](https://github.com/lbailey94/whitemagic/actions/workflows/docker-security.yml)
[![Security Grade](https://img.shields.io/badge/security-A%2B-success.svg)](SECURITY.md)
[![Security Policy](https://img.shields.io/badge/security-policy-blue.svg)](SECURITY.md)
[![Dependabot](https://img.shields.io/badge/dependabot-enabled-success.svg)](https://github.com/lbailey94/whitemagic/network/updates)

WhiteMagic is a production-ready memory OS for AI agents. **Free to use locally** with full features, or upgrade to cloud-hosted for team collaboration and sync. Includes Python SDK + CLI, FastAPI backend, and native MCP integration for Cursor/Windsurf/Claude.

## 🎁 Free Forever (Local)
- ✅ Full feature set
- ✅ No signup required
- ✅ Local SQLite storage
- ✅ MCP server included
- ✅ Perfect for individuals

## ☁️ Cloud Tiers (Coming Soon)
- **Starter** ($10/month): 10k requests, 100 memories, cloud sync
- **Pro** ($30/month): Unlimited requests, unlimited memories, priority support

*Cloud integration powered by Stripe - Simple, secure signup*

---

## 🚦 Getting Started (3 Steps)

1. **Install**: `pip install whitemagic` or `git clone https://github.com/lbailey94/whitemagic`
2. **Try CLI**: `whitemagic create "My first memory" --content "Hello WhiteMagic!"`
3. **Connect to IDE**: `npx whitemagic-mcp-setup` (auto-configures Cursor, Windsurf, Claude Desktop, VS Code)

→ **Full guides**: [User Guide](docs/USER_GUIDE.md) | [Quickstart](docs/guides/QUICKSTART.md) | [Cheat Sheet](docs/CHEATSHEET.md)

---

## ✨ Features

- **Tiered Memory**: Short-term, long-term, and archive storage
- **MCP Integration**: 7 tools + 4 resources for Cursor/Windsurf/Claude
- **Smart Search**: Full-text search with tag filtering
- **Context Generation**: 3-tier context system
- **Type-Safe**: 100% type hints with Pydantic V2
- **CLI + API**: Command-line and Python library
- **Automated Tests**: 223 passing tests (196 Python + 27 MCP)
- **Production Grade**: A+ (99/100) - All security vulnerabilities patched

## 🚀 Quick Start

### Official SDKs (New in v2.1.4!) 📦

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
- 🌐 **API**: https://api.whitemagic.dev (Railway)
- 📊 **Dashboard**: https://app.whitemagic.dev (Vercel)

**Stack:**
- **Backend**: Railway (FastAPI + PostgreSQL + Redis)
- **Frontend**: Vercel (Static dashboard)
- **Payments**: Stripe (Coming soon)

For deployment guides, see `docs/archive/deployment/` or contact for enterprise setup.

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

### Core Docs
- [INSTALL.md](INSTALL.md) - Installation guide
- [whitemagic-mcp/README.md](whitemagic-mcp/README.md) - MCP setup for Cursor/Windsurf/Claude
- [ROADMAP.md](ROADMAP.md) - Development roadmap
- [CHANGELOG.md](CHANGELOG.md) - Version history

### Reference
- [docs/reviews/v2.1.3/](docs/reviews/v2.1.3/) - Quality assurance reports
- [docs/production/](docs/production/) - Production deployment guides
- [docs/archive/](docs/archive/) - Historical documentation

## 🧪 Testing

**196 Python + 27 MCP automated tests** - See [docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md](docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md)

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

WhiteMagic v2.1.3 underwent extensive security and stability reviews:

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

📁 **Full review documentation**: [docs/reviews/v2.1.3/](docs/reviews/v2.1.3/)  
📄 **Production test results**: [PRODUCTION_TEST_RESULTS.md](docs/reviews/v2.1.3/PRODUCTION_TEST_RESULTS.md)

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
- ✅ v2.1.4: SDKs (TypeScript + Python clients)
- ✅ v2.1.5: Infrastructure (Railway + Vercel deployment)
- 🚧 v2.2: Stripe Integration (Cloud tiers, subscriptions)
- 📅 v2.3: Semantic Search (Vector embeddings, AI-powered search)
- 📅 v3.0: Team Features (Shared memories, collaboration)

See [ROADMAP.md](ROADMAP.md) for detailed plans.

## 📄 License

MIT - See [LICENSE](LICENSE)

## 🔗 Links

- Issues: https://github.com/lbailey94/whitemagic/issues
- Discussions: https://github.com/lbailey94/whitemagic/discussions
