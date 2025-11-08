# WhiteMagic 🧠✨

**Tiered Memory Management for AI Agents with Native MCP + REST Support**

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/lbailey94/whitemagic/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-40%2B%20passing-brightgreen.svg)](#testing)

WhiteMagic ships a production-ready memory OS for AI agents: a Python SDK + CLI, FastAPI backend with Whop-based auth/monetization, and native MCP integration for Cursor/Windsurf/Claude.

## ✨ Features

- **Tiered Memory**: Short-term, long-term, and archive storage
- **MCP Integration**: 7 tools + 4 resources for Cursor/Windsurf/Claude
- **Smart Search**: Full-text search with tag filtering
- **Context Generation**: 3-tier context system
- **Type-Safe**: 100% type hints with Pydantic
- **CLI + API**: Command-line and Python library

## 🚀 Quick Start

```bash
# Install from source
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic && pip install -e ".[api,dev]"

# Or install the SDK directly
pip install whitemagic==2.1.0

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
Follow the step-by-step instructions in [`NEXT_STEPS.md`](NEXT_STEPS.md) and [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md).

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
- [NEXT_STEPS.md](NEXT_STEPS.md) - One-day launch checklist (npm + MCP registry + Vercel/Railway) ⭐
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Comprehensive production deployment
- [DEPLOY_NOW.md](DEPLOY_NOW.md) - Quick 45-minute deploy

### Reference
- [TEST_COVERAGE_SUMMARY.md](TEST_COVERAGE_SUMMARY.md) - 65+ tests, 85% coverage
- [COMPREHENSIVE_REVIEW_ASSESSMENT.md](COMPREHENSIVE_REVIEW_ASSESSMENT.md) - Latest project review
- [docs/production/OPTIONAL_INTEGRATIONS.md](docs/production/OPTIONAL_INTEGRATIONS.md) - Optional add-ons (Sentry, metrics)
- [requirements-plugins.txt](requirements-plugins.txt) - Install optional integrations

## 🧪 Testing

**65+ automated tests, 85% coverage** - See [TEST_COVERAGE_SUMMARY.md](TEST_COVERAGE_SUMMARY.md)

```bash
# Python tests (40+ tests)
python3 -m pytest -v

# MCP tests (25+ tests)
cd whitemagic-mcp && npm test

# With coverage
python3 -m pytest --cov=whitemagic --cov-report=html
```

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
