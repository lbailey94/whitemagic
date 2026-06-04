# WhiteMagic Architecture Manifest — June 4, 2026

**Status**: Post-extraction, post-pivot architectural clarity document
**Scope**: What this repo is, what the sibling repos are, and how they relate

---

## The Three-Repo Reality

After May 15–June 4, WhiteMagic split from a monorepo into a **core library + satellite repos** model.

| Repo | Path | Role | Status |
|------|------|------|--------|
| **whitemagic** (this repo) | `/home/lucas/Desktop/WHITEMAGIC` | Core Python library + documentation + polyglot accelerators | Active |
| **whitemagic-site** | `~/Desktop/whitemagic-site/` | Public website (Next.js, essays, evidence map, librarian) | Extracted May 2026 |
| **whitemagic-codex** | `~/Desktop/whitemagic-codex/` | Rust CODEX extraction pipeline | Extracted May 2026 |

The desktop application (`whitemagic-app/`) currently lives **inside this repo** but may eventually move to its own repo.

---

## What This Repo Is

### Core Identity

This repo is the **canonical source library** for WhiteMagic's cognitive operating system primitives:

- **28 PRAT Gana meta-tools** — consciousness lenses for MCP routing
- **5D holographic memory** — XYZWV coordinate system with galactic lifecycle
- **Karma Ledger** — declared-vs-actual side-effect audit substrate
- **Voice Audit** — deterministic enforcement of tool-call governance
- **Dharma Rules** — ethical constraint system with runtime evaluation
- **Polyglot accelerators** — Rust, Zig, Koka, Haskell, Elixir, Go, Mojo, Julia

### What This Repo Is NOT

| Misconception | Reality |
|--------------|---------|
| A public website | Website extracted to `whitemagic-site` |
| A document extraction pipeline | CODEX extracted to `whitemagic-codex` |
| A product with users | Research/lab artifact; no public beta |
| A hosted SaaS | Local-first, MIT-licensed, self-hosted |

---

## Directory Map (Current)

```
WHITEMAGIC/
├── core/                    # Python package (shipped to PyPI)
│   ├── whitemagic/          # Main source (~720 Python files)
│   │   ├── tools/           # Tool registry, dispatch, handlers
│   │   ├── core/            # Memory, intelligence, resonance
│   │   ├── interfaces/      # API, dashboard, CLI
│   │   ├── config/          # Path resolution, settings
│   │   └── hermes/          # Telemetry/context hooks (NEW Jun 4)
│   ├── tests/               # 2,379 tests
│   ├── scripts/             # Audit, drift-check, stress-test
│   └── docs/                # Package docs (46 tracked Markdown files)
├── docs/                    # Project-level docs
│   ├── message_board/       # Active workspace (41 tracked files)
│   ├── public/              # Public-facing docs (19 files)
│   ├── private/             # Ignored local-only docs
│   ├── archive/             # Historical docs
│   ├── strategy_manifestos/ # Strategic planning
│   └── ...                  # ADRs, reports, specs, etc.
├── grimoire/                # Canonical 28 Gana chapters (38 files)
├── polyglot/                # 7-language acceleration (minus CODEX)
├── whitemagic-app/          # NEW: Tauri desktop app (157 files)
│   ├── nexus/               # Tauri + React desktop shell
│   ├── hub/                 # Shared components, build scripts
│   ├── shell/               # Vite/React UI shell
│   └── sdk/                 # Desktop app SDK
├── apps/site/               # EMPTIED (extracted to whitemagic-site)
└── ...                      # Root docs, CI, deployment, etc.
```

---

## Sibling Repo Relationships

### whitemagic-site

- **Contains**: Next.js 15 app, essays, evidence map, librarian UI, PWA infrastructure
- **Depends on**: This repo (for facts, API contracts, content)
- **Status**: Extracted but may need re-sync with core library changes
- **Deployment target**: `whitemagic.dev` (not yet live)

### whitemagic-codex

- **Contains**: Rust CODEX pipeline (7 crates: extract, chunk, embed, index, export, consolidate)
- **Depends on**: This repo (for content, LIBRARY integration)
- **Status**: Extracted; needs independent build verification
- **Use case**: Document extraction, embedding, clustering for the memory system

### whitemagic-app (future extraction candidate)

- **Contains**: Tauri desktop app with React/Vite shell
- **Depends on**: This repo (core library via MCP or direct import)
- **Status**: Currently nested inside this repo; may move to sibling repo
- **Use case**: Local-first desktop interface for WhiteMagic primitives

---

## Why This Structure

The extraction was driven by three forces:

1. **Rate of change divergence**: The website and CODEX pipeline were evolving on different cadences than the core library.
2. **Build system conflicts**: Next.js, Rust, and Python have incompatible build/toolchain requirements.
3. **Local-first philosophy**: The desktop app (`whitemagic-app`) aligns with WhiteMagic's governance-over-cloud stance.

---

## What Belongs in This Repo

### Should stay

- Core Python library (`core/whitemagic/`)
- Tests and verification infrastructure (`core/tests/`, `core/scripts/`)
- Grimoire canonical source (`grimoire/`)
- Documentation about the library (`docs/public/`, `docs/adr/`, `docs/reports/`)
- Polyglot accelerators that ship with the core (`polyglot/` minus CODEX)

### Should move out

- `whitemagic-app/` → eventual sibling repo (when stable)
- `apps/site/` → already extracted; remove residual files

### Should be archived or pruned

- Stale docs in `docs/message_board/` that reference old architectures
- Grant strategy docs with expired deadlines (May 17, May 31)
- Pre-extraction references to `polyglot/codex/` and `apps/site/` in docs

---

## The One-Sentence Identity

> **WhiteMagic is a locally-runnable, MIT-licensed Python library providing 28 consciousness-lens meta-tools, 5D holographic memory, and runtime governance (Karma Ledger, Voice Audit, Dharma Rules) for agentic AI systems.**

The website explains it. The desktop app interfaces with it. CODEX feeds it. But this repo **is** the library.

---

## Verification

- Tracked Markdown files: 287 (down from 3,652 when auxiliary corpora included)
- Tests passing: 2,379
- Doc drift: check passing
- Version: 22.2.0

---

*Generated during June 4, 2026 architectural clarity session.*
