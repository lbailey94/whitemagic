# WhiteMagic Prologue

This document is the **canonical first stop** for both humans and AI runtimes entering WhiteMagic.

It does not try to replace the rest of the documentation. Its job is simpler:

- define what WhiteMagic is
- define which surfaces are canonical
- define where to go next depending on your task
- keep the rest of the documentation tree organized around a single center

---

## What WhiteMagic Is

WhiteMagic is a tool and memory substrate for agentic systems.

At its core, it provides:

- persistent memory with retrieval and lifecycle management (5D holographic coordinates, Galactic Map)
- a unified tool dispatch layer with governance and middleware (412 MCP tools, 8-stage pipeline)
- MCP-facing interfaces, especially PRAT mode through the 28 Ganas (28 meta-tools)
- optional polyglot accelerators for high-value hot paths (9 languages)
- ethical governance: Dharma Rules Engine, Karma Ledger, Harmony Vector
- LoCoMo benchmark: 78.3% recall accuracy (beats Letta 74%, Mem0 68.5%, OpenAI 63.8%)

The project contains both a **public contract** and a **research body**.
The public contract should stay smaller, clearer, and more stable than the experimental surface area around it.

---

## The Canonical Centers

Use the documentation in this order.

### 1. Prologue

Start here when you need orientation.

- file: `whitemagic/grimoire/00_PROLOGUE.md`
- role: canonical introduction and document router

### 2. AI Primary

Read this when you are an AI runtime or when you need the operational contract.

- file: `AI_PRIMARY.md`
- role: AI-facing contract, integration posture, canonical runtime surfaces

### 3. System Map

Read this when you need the repo layout, subsystem map, and architecture navigation.

- file: `SYSTEM_MAP.md`
- role: architecture and repository map

### 4. README

Read this when you want the human-facing project overview and install path.

- file: `README.md`
- role: human-facing entry page

### 5. Grimoire Index

Read this when you want the 28-chapter navigation model.

- file: `whitemagic/grimoire/00_INDEX.md`
- role: chapter navigation and grimoire traversal

---

## Canonical Runtime Surfaces

These are the surfaces that currently matter most.

- `python -m whitemagic.run_mcp_lean`
- `WM_MCP_PRAT=1 python -m whitemagic.run_mcp`
- `python -m whitemagic.run_mcp`
- `from whitemagic.tools.unified_api import call_tool`
- `wm ...`

Everything else should be treated as one of the following until proven otherwise:

- supporting infrastructure
- optional accelerator path
- experimental interface
- archived or historical material

---

## How To Use The Docs

### If you are an AI runtime

Read in this order:

1. `whitemagic://orientation/prologue`
2. `whitemagic://orientation/ai-primary`
3. `whitemagic://orientation/system-map`
4. `whitemagic://grimoire/index`

### If you are a human developer

Read in this order:

1. `README.md`
2. `whitemagic/grimoire/00_PROLOGUE.md`
3. `docs/QUICKSTART.md`
4. `AI_PRIMARY.md`
5. `SYSTEM_MAP.md`

### If you are debugging or refactoring

Start here:

1. `SYSTEM_MAP.md`
2. `docs/ARCHITECTURE.md`
3. `whitemagic/tools/dispatch_table.py`
4. `whitemagic/tools/prat_router.py`
5. `whitemagic/core/memory/unified.py`
6. `whitemagic/core/memory/sqlite_backend.py`

---

## Phase Structure For The Current Audit

The current improvement program is organized into five phases.

### Phase 0 — Canonical Center

Create one true documentation center and route all first-contact surfaces through it.

### Phase 1 — Drift Reconciliation

Reconcile versioning, tool counts, interface claims, stale paths, and docs-to-code mismatches.

### Phase 2 — High-Coupling Refactor

Break monolithic routing and memory control-plane zones into clearer modules with polyglot-friendly boundaries.

### Phase 3 — Debuggability And Degraded-Mode Clarity

Add explicit debug flags, degraded-mode signaling, routing clarity, and failure resolution surfaces.

### Phase 4 — Proof

Strengthen tests, benchmarks, and reproducible evidence for the supported system surface.

---

## Current Rule Of Interpretation

If two documents disagree:

- treat this prologue as the canonical router
- treat `AI_PRIMARY.md` as the contract for AI-facing integration
- treat `SYSTEM_MAP.md` as the repo map
- treat live code as the final authority when docs drift

The next audit phases are intended to reduce how often this rule is needed.
