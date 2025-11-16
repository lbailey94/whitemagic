# Installation Guide · WhiteMagic v2.2.1

**WhiteMagic is modular by design.** Start minimal (~50MB), add features as needed.

## 🎯 Choose Your Installation

### Quick Comparison

| Installation | Size | Use Case | Command |
|-------------|------|----------|----------|
| **Minimal** | ~50MB | Core memory management | `pip install whitemagic` |
| **+ Local AI** | ~2.5GB | Privacy-first semantic search | `pip install whitemagic[embeddings]` |
| **+ Terminal** | +5MB | Safe command execution | `pip install whitemagic[terminal]` |
| **Full Offline** | ~2.5GB | Everything local, zero cloud | `pip install whitemagic[offline]` |
| **Development** | ~2.5GB | Local features + dev tools | `pip install -r requirements.txt` |

---

## 1. Minimal Installation (Recommended Start)

**Perfect for**: First-time users, cloud deployments (Railway/Vercel), minimal footprint

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install whitemagic

# Verify it works
whitemagic --version
whitemagic list
```

**What you get** (~50MB):
- ✅ Core memory management (create, list, search, update, delete)
- ✅ File-based storage (`~/.whitemagic/memory/`)
- ✅ Configuration system (`~/.whitemagic/config.yaml`)
- ✅ Terminal Tool (safe command execution)
- ✅ Rich CLI formatting (tables, colors, progress bars)
- ✅ MCP server support
- ✅ REST API server
- ✅ OpenAI embeddings support (API key required)

**What you don't get**:
- ❌ Local embeddings (sentence-transformers, torch)
- ❌ Offline semantic search

---

## 2. Add Local AI (Privacy-First)

**Perfect for**: Users who want semantic search without API keys, 100% offline

```bash
pip install whitemagic[embeddings]

# Or combine with other extras
pip install whitemagic[embeddings,terminal]
```

**Adds** (+2.5GB):
- ✅ Local embedding models (sentence-transformers)
- ✅ Offline semantic search (no API keys needed)
- ✅ Privacy-first: all data stays on your machine
- ✅ Model: `all-MiniLM-L6-v2` (88MB compressed, 384 dimensions)

**Install your first model**:
```bash
whitemagic embeddings-install
# Downloads ~88MB model, expands to ~230MB
# Cached at ~/.cache/huggingface/hub/
```

**Try semantic search**:
```bash
whitemagic search-semantic "terminal tool architecture"
```

---

## 3. Full Offline Suite

**Perfect for**: Maximum privacy, air-gapped systems, offline development

```bash
pip install whitemagic[offline]
```

Same as `[embeddings]` but explicitly labeled for offline use.

---

## 4. Development Setup

**Perfect for**: Contributors, testing, building features

```bash
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic
python3 -m venv .venv
source .venv/bin/activate

# Install everything: core + embeddings + dev tools
pip install -r requirements.txt

# Or explicitly
pip install -e ".[embeddings,dev]"

# Optional: pre-commit hooks
pre-commit install
```

**What you get**:
- ✅ Everything from `[offline]`
- ✅ Testing tools (pytest, coverage)
- ✅ Code quality (black, mypy, ruff)
- ✅ Editable install (`-e`) for live code changes

---

## 3. Run the CLI

```bash
# create a short-term memory
whitemagic create --title "First memory" --content "It works!" --type short_term --tag demo

# list memories
whitemagic list

# search with tag filters
whitemagic search --query "works" --tag demo

# generate tiered context
whitemagic context --tier 1
```

All CLI subcommands accept `--help` for detailed options.

---

## 4. Run the API (FastAPI + SQLite)

```bash
cp .env.example .env
uvicorn whitemagic.api.app:app --reload
```

Default endpoints:
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Remember: rate limiting is **disabled** unless you set `REDIS_URL`. Point it at Redis (Railway, Docker, etc.) before production.

---

## 5. Security Considerations

### ⚠️ Terminal Execution API (DISABLED BY DEFAULT)

WhiteMagic includes a **Terminal Execution API** (`/api/v1/exec`) that allows AI agents to run commands. This feature is **disabled by default** for security reasons.

**Threat Model**:
- If enabled with weak authentication, attackers could execute arbitrary commands
- Combined with compromised API keys = Remote Code Execution (RCE)
- Even read-only mode exposes filesystem and environment information

**When to Enable**:
- ✅ **Local development** with trusted AI agents only
- ✅ **Controlled environments** (isolated VMs, sandboxed containers)
- ✅ **Research** with understanding of risks
- ❌ **NOT in production** without additional safeguards
- ❌ **NOT on public APIs** without strong authentication

**How to Enable**:
```bash
# Only set this if you understand the risks!
export WM_ENABLE_EXEC_API=true
uvicorn whitemagic.api.app:app --host 0.0.0.0 --port 8000
```

**Safer Alternatives**:
- Use CLI: `whitemagic exec <command>` (interactive approval for writes)
- Use MCP server: Built-in safety with Windsurf/Cursor's approval workflows
- Use Python SDK: Direct MemoryManager calls (no command execution)

See [SECURITY.md](SECURITY.md#terminal-execution-api-security) for full threat model and mitigation strategies.

### 🔐 API Key Security

**Best Practices**:
- Generate keys via CLI: `whitemagic create-api-key --email user@example.com`
- Rotate keys regularly (30-90 days for production)
- Use environment variables, never hardcode keys
- Enable rate limiting with Redis (`REDIS_URL`) before production
- Monitor `/health` endpoint for anomalies

**Key Storage**:
- Keys are hashed with SHA-256 (never stored in plaintext)
- Stored in SQLite (local) or PostgreSQL (production)
- Database should be secured with filesystem permissions

---

## 6. Run the MCP Server (Cursor/Windsurf/Claude)

```bash
cd whitemagic-mcp
npm install
npm run build
```

Example Cursor config (`~/.codeium/windsurf/mcp_config.json`):

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "node",
      "args": ["/absolute/path/to/whitemagic-mcp/dist/index.js"],
      "env": {
        "WM_BASE_PATH": "/absolute/path/to/whitemagic"
      }
    }
  }
}
```

Set `WM_API_URL` + `WM_API_KEY` if you prefer the REST API over local file mode.

---

## 7. Verification Checklist

| Task | Command |
| --- | --- |
| CLI works | `whitemagic list` |
| Python SDK import | `python -c "from whitemagic import MemoryManager; print('Ready')" ` |
| API smoke test | `curl http://localhost:8000/health` |
| Tests (Python) | `pytest tests -q` |
| Tests (MCP) | `cd whitemagic-mcp && npm test` |

---

## 8. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `whitemagic: command not found` | Activate your virtualenv or reinstall with `pip install .`. |
| `ModuleNotFoundError: whitemagic` | Ensure the package is installed (`pip install "whitemagic[api]"`) or add the repo root to `PYTHONPATH`. |
| Rate-limit headers missing | Set `REDIS_URL` and restart the API. Without Redis the limiter is a no-op. |
| MCP server can’t find Python | Double-check `WM_BASE_PATH` and that the Python environment you installed into is on `PATH`. |
| `/api/v1/exec` missing | It’s disabled by default for safety. Set `WM_ENABLE_EXEC_API=true` **only** inside a locked-down environment. |

Need help beyond this guide? Open an issue on GitHub or ping the discussion board. Happy hacking!
