# Quickstart · Build Your First Memory in 5 Minutes

This guide assumes Python 3.10+ and a POSIX shell. Windows PowerShell works with equivalent commands.

---

## 1. Install & Set Up

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "whitemagic[api]"
```

Verify the CLI:

```bash
whitemagic --help
```

---

## 2. Create Your First Memory

```bash
whitemagic create \
  --title "Debugging tip" \
  --content "Reproduce the bug with logging before guessing." \
  --type short_term \
  --tag debugging --tag habit
```

Memories are stored under `memory/short_term` by default. Each file is Markdown with YAML frontmatter—open them in any editor.

---

## 3. Browse & Search

```bash
# list memories grouped by tier
whitemagic list

# search by keyword + tag filter
whitemagic search --query "logging" --tag debugging
```

Add `--json` to either command for machine-readable output.

---

## 4. Generate Context for Your Agent

```bash
whitemagic context --tier 1
```

Tier presets:
- `0` – tiny (2 short-term memories)
- `1` – balanced (5 short-term + 2 long-term)
- `2` – full (10 short-term + 5 long-term)

Pipe the output directly into your IDE’s custom instructions or an MCP tool.

---

## 5. Run the API (Optional)

```bash
cp .env.example .env
uvicorn whitemagic.api.app:app --reload
```

### Create an API key

The repo ships a helper script that bootstraps a demo user and prints a key:

```bash
python scripts/create_demo_user.py
```

Copy the key that’s printed and paste it wherever you need authentication.  
Use the key with `curl`:

```bash
curl -H "Authorization: Bearer wm_dev_xxx" http://localhost:8000/api/v1/memories
```

> **Note:** The hosted dashboard login is paused while we redesign the experience. Stick to CLI/API provisioning (or your MCP IDE) for now.

Remember to set `REDIS_URL` if you want rate limiting.

---

## 6. Connect an IDE via MCP

```bash
cd whitemagic-mcp
npm install
npm run build
```

Point Cursor/Windsurf/Claude Desktop at `dist/index.js`, exporting `WM_BASE_PATH` (and optionally `WM_API_URL`/`WM_API_KEY`).

---

## 7. Clean Up Short-Term Noise

```bash
# preview what would move to archive
whitemagic consolidate --dry-run

# actually archive & auto-promote tagged insights
whitemagic consolidate
```

---

## Troubleshooting

| Issue | Fix |
| --- | --- |
| CLI can’t find config | Run commands inside the directory that contains the `memory/` folder, or set `WM_BASE_PATH`. |
| API refuses to start | Ensure SQLite file is writable (`whitemagic_dev.db` by default) and Redis is reachable if you set `REDIS_URL`. |
| MCP server exits immediately | Check that Node ≥18 is installed and that the Python virtualenv is active when launching the MCP server. |

Need more depth? See `docs/guides/MEMORY_SYSTEM_README.md` for architecture details or `docs/production/DEPLOYMENT_GUIDE.md` to ship the full stack.
