# Installation Guide · WhiteMagic v2.1.2

Whether you want to kick the tires locally or deploy the full stack, use the flow that matches your goal.

---

## 1. Install from PyPI (CLI + SDK)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "whitemagic[api]"  # CLI + API extras

# sanity check
whitemagic --help
```

What you get:
- `whitemagic` CLI (create/list/search/context/consolidate/etc.)
- `from whitemagic import MemoryManager` for scripting
- Optional FastAPI extras (enabled via `[api]`)

---

## 2. Install for Development

**Important**: If you have `whitemagic` installed globally or in another environment, uninstall it first to avoid import conflicts:

```bash
pip uninstall whitemagic -y
```

Then install from source in editable mode:

```bash
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[api,dev]"  # dev extra now includes test-only deps like openai
```

Useful extras:
- `pip install -r requirements-plugins.txt` to pull optional integrations (Sentry, Prometheus, etc.)
- `pre-commit install` to match repository linting

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

## 5. Run the MCP Server (Cursor/Windsurf/Claude)

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

## 6. Verification Checklist

| Task | Command |
| --- | --- |
| CLI works | `whitemagic list` |
| Python SDK import | `python -c "from whitemagic import MemoryManager; print('Ready')" ` |
| API smoke test | `curl http://localhost:8000/health` |
| Tests (Python) | `pytest tests -q` |
| Tests (MCP) | `cd whitemagic-mcp && npm test` |

---

## 7. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `whitemagic: command not found` | Activate your virtualenv or reinstall with `pip install .`. |
| `ModuleNotFoundError: whitemagic` | Ensure the package is installed (`pip install "whitemagic[api]"`) or add the repo root to `PYTHONPATH`. |
| Rate-limit headers missing | Set `REDIS_URL` and restart the API. Without Redis the limiter is a no-op. |
| MCP server can’t find Python | Double-check `WM_BASE_PATH` and that the Python environment you installed into is on `PATH`. |
| `/api/v1/exec` missing | It’s disabled by default for safety. Set `WM_ENABLE_EXEC_API=true` **only** inside a locked-down environment. |

Need help beyond this guide? Open an issue on GitHub or ping the discussion board. Happy hacking!
