# WhiteMagic · Plain-Language Primer

## What it is

WhiteMagic is a personal knowledge base for AI agents. Think “second brain” tooling that lives on your filesystem or behind a simple API. You capture insights as Markdown files, the tool keeps them tidy, and your agent requests tiered context whenever it needs to reason about prior work.

## Why it matters

- **Better conversations** – your agent remembers preferences, gotchas, and recent fixes.
- **Searchable history** – every note is just Markdown, so you can grep, sync, or diff it like code.
- **Drop-in integrations** – CLI, Python SDK, FastAPI backend, and an MCP server for Cursor/Windsurf/Claude Desktop.

## Pricing / tiers (recommended)

| Tier | Deploy | Suggested Price | Includes |
| --- | --- | --- | --- |
| Hobby | Self-host (Docker/CLI) | Free | Unlimited local memories, MCP integration |
| Pro | Managed (Railway + Vercel) | $29/mo | 10k API calls/day, Redis rate limiting, email support |
| Team | Custom | $99+/mo | Multi-user workspaces, SSO, priority support |

## 60‑second setup

```bash
pip install "whitemagic[api]"
whitemagic create --title "Onboarding" --content "It works!" --type short_term
whitemagic list
```

Need it in your IDE? Build the MCP server (`whitemagic-mcp`) and point Cursor/Windsurf/Claude at it with `WM_BASE_PATH=/path/to/whitemagic`.

## Architecture snapshot

```
memory/
├── short_term/   # rolling notes (auto-archived after ~7 days)
├── long_term/    # curated heuristics + SOPs
├── archive/      # soft-deleted short-term files for provenance
└── metadata.json # index + consolidation log
```

## Key features (non-technical)

- **Tiered context**: ask for a light, balanced, or deep summary depending on task complexity.
- **Auto-consolidation**: archive stale short-term notes and auto-promote tagged insights.
- **Safe defaults**: CORS locked down, rate limiting available (requires Redis), `/api/v1/exec` disabled unless you intentionally turn it on.
- **Bring-your-own prompts**: the system outputs clean Markdown so you can inject it anywhere.

## How it integrates

- **CLI / SDK**: developers run `whitemagic ...` or import `MemoryManager`.
- **REST API**: FastAPI service with API keys, quotas, dashboards.
- **MCP Server**: registers as a Model Context Protocol source—perfect for AI copilots.

## Ready to explore?

1. Follow `INSTALL.md` for the flow you need (CLI, API, or full stack).
2. Skim `docs/guides/QUICKSTART.md` to capture your first memory.
3. Read `COMPREHENSIVE_REVIEW_ASSESSMENT.md` if you want the latest state-of-the-project view.

Questions? Open a GitHub issue or say hi in the discussions tab. Happy shipping! 😄
