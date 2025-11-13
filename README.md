# WhiteMagic 🧠✨

**Tiered Memory Management for AI Agents with Native MCP + REST Support**

[![Version](https://img.shields.io/badge/version-2.1.3-blue.svg)](https://github.com/lbailey94/whitemagic/releases)
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

WhiteMagic ships a production-ready memory OS for AI agents: a Python SDK + CLI, FastAPI backend with Whop-based auth/monetization, and native MCP integration for Cursor/Windsurf/Claude.

---

## 🚦 Getting Started (3 Steps)

1. **Install**: `pip install whitemagic==2.1.3`
2. **Try CLI**: `whitemagic create "My first memory" --content "Hello WhiteMagic!"`
3. **Connect to IDE**: See [MCP Quick Setup](docs/guides/QUICK_SETUP_MCP.md)

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

### Official SDKs (New in v2.1.4!)

**TypeScript/JavaScript**
```bash
npm install @whitemagic/client
```
```typescript
import { WhiteMagicClient } from '@whitemagic/client';

const client = new WhiteMagicClient({ apiKey: process.env.WHITEMAGIC_API_KEY });
const memory = await client.memories.create({
  title: 'My memory',
  content: 'Stored via SDK',
  type: 'short_term'
});
```

**Python**
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

### Install MCP Server (Published!)
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
pip install whitemagic==2.1.3

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

### Recommended production hosting

- **Frontend (dashboard + landing)**: Deploy the `dashboard/` directory to Vercel (static build). Set `NEXT_PUBLIC_API_URL` (or `meta[name="whitemagic-api-base"]`) to your Railway API URL.
- **Backend (API + Postgres + Redis)**: Deploy `compose.yaml` services to Railway—one service for FastAPI, managed Postgres + Redis, and Caddy if you want TLS out of the box.  
Follow the step-by-step instructions in [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md).

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

**New here?** Start with [DOCUMENTATION_MAP.md](DOCUMENTATION_MAP.md) - your navigation guide

### Core Docs
- [docs/INDEX.md](docs/INDEX.md) - Complete documentation index
- [INSTALL.md](INSTALL.md) - Installation guide
- [whitemagic-mcp/README.md](whitemagic-mcp/README.md) - MCP setup for Cursor/Windsurf/Claude
- [ROADMAP.md](ROADMAP.md) - Development roadmap

### Deployment
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Comprehensive production deployment
- [INSTALL.md](INSTALL.md) - Local development setup

### Reference
- [docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md](docs/reviews/v2.1.3/TEST_COVERAGE_SUMMARY.md) - 196 Python + 27 MCP tests
- [docs/reviews/v2.1.3/COMPREHENSIVE_REVIEW_ASSESSMENT.md](docs/reviews/v2.1.3/COMPREHENSIVE_REVIEW_ASSESSMENT.md) - Latest project review
- [docs/production/OPTIONAL_INTEGRATIONS.md](docs/production/OPTIONAL_INTEGRATIONS.md) - Optional add-ons (Sentry, metrics)
- [requirements-plugins.txt](requirements-plugins.txt) - Install optional integrations

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

- ✅ Phase 1A: Python API
- ✅ Phase 1B: MCP Integration
- ✅ Phase 2A: Whop + REST API
- 📅 Phase 2B: Semantic search
- 📅 Phase 3: Extensions

## 📄 License

MIT - See [LICENSE](LICENSE)

## 🔗 Links

- Issues: https://github.com/lbailey94/whitemagic/issues
- Discussions: https://github.com/lbailey94/whitemagic/discussions
