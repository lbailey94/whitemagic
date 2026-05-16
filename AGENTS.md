# AGENTS.md — WhiteMagic Agent Guide

**Version**: 22.0.0
**Last Updated**: 2026-04-25
**Purpose**: Operational guide for AI agents contributing to the WhiteMagic codebase.

---

## 1. What This Project Is

WhiteMagic is a **cognitive operating system** for agentic AI — not merely a memory tool. It provides:

- Persistent memory with 5D holographic coordinates and galactic lifecycle
- 479 callable tools across 451 dispatch entries + 28 Gana meta-tools (PRAT)
- 8-stage dispatch pipeline with Dharma ethical governance
- Polyglot accelerators (Rust, Haskell, Elixir, Go, Zig, Mojo)
- 2,216 passing tests, 0 failures

**The single most important rule**: *Tests are the guardrail. Never skip them.*

---

## 2. First Actions on Entering the Repo

```bash
# 1. Activate the venv (all deps + Mojo 0.26.1)
cd /home/lucas/Desktop/WHITEMAGIC
source .venv/bin/activate

# 2. Verify test baseline (should be 2216 passed, 67 skipped, 0 failed)
cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q

# 3. Verify doc drift
python scripts/check_doc_drift.py

# 4. Check git status
git status
```

If tests fail on entry, **stop and fix the baseline before making changes**.

---

## 3. Repository Structure

```
WHITEMAGIC/
├── core/                    # Python package (shipped to PyPI)
│   ├── whitemagic/          # Main source (~720 Python files)
│   │   ├── tools/           # Tool registry, dispatch, handlers
│   │   ├── core/            # Memory, intelligence, resonance
│   │   ├── interfaces/      # API, dashboard, CLI
│   │   └── config/          # Path resolution, settings
│   ├── tests/               # 2,063 tests
│   ├── scripts/             # Audit, drift-check, stress-test
│   └── docs/                # Core-specific docs
├── grimoire/                # Canonical 28 Gana chapters (.md)
├── docs/                    # Project-level docs
│   ├── message_board/       # Active session docs (current cycle)
│   ├── adr/                 # Architecture Decision Records
│   ├── public/              # Website, legal, GitHub-facing
│   └── ...
├── polyglot/                # 7-language acceleration cores
├── apps/                    # Application layer (Next.js site)
└── AGENTS.md                # This file
```

**Key principle**: `core/` is a separate distributable package. Do not merge its docs with `docs/`.

---

## 4. Documentation Conventions

### The Index System

`INDEX.md` at the repo root is the **single source of truth** for where to find any `.md` document. Rules:

1. **Adding a doc**: Update `INDEX.md` in the same commit.
2. **Moving a doc**: Use `git mv`, update all code references, update `INDEX.md`.
3. **Archiving a doc**: Move to `docs/archive/`, add `> **Superseded by**: [new path]` at the top.

### The Message Board

`docs/message_board/` is the **active workspace**. Current session docs live here. When a cycle ends, move docs to the appropriate topical folder or `docs/archive/`.

### The Grimoire

`grimoire/` (root) is the **canonical** markdown source. `core/whitemagic/grimoire/` contains only the Python code (`chapters.py`, `core.py`, `auto_cast.py`). Do not duplicate `.md` files in `core/whitemagic/grimoire/`.

### Doc Drift Detection

Run `python core/scripts/check_doc_drift.py` after any doc change. It validates:
- Garden count = 28
- Gana tool count = 28
- Dispatch table count matches registry
- Version consistency
- No stale directory references

---

## 5. Testing Protocol

### The Golden Rule
**Run the full test suite after every change.** The project went from 783 passing → 2,063 passing by fixing wiring, not by skipping tests.

### Test Commands

```bash
# Full suite (from core/)
cd core
python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q

# Specific module
python -m pytest tests/unit/test_path_hygiene.py -v

# With coverage
python -m pytest tests/ --cov=whitemagic --cov-report=term-missing -q
```

### What to Do If Tests Fail

1. Read the failure message carefully.
2. Check if the failure is in code you touched.
3. If not, check `docs/message_board/SESSION_SUMMARY.md` for known issues.
4. If the failure is new, **revert your change** and investigate.

---

## 6. Code Conventions

### Style
- **Python**: PEP 8, type hints required for public functions.
- **Rust**: `cargo fmt`, `cargo clippy`.
- **Module imports**: Use absolute imports (`from whitemagic.core.memory...`).

### Path Hygiene
- **Never** use `Path.home()` or `.expanduser()` outside `core/whitemagic/config/paths.py`.
- All runtime state lives under `WM_STATE_ROOT`. Never write to the repo.
- The repo must remain clean of `memory/`, `data/`, `logs/`, `.whitemagic/`.

### Error Handling
All tools return a **stable JSON envelope**:
```python
{
    "status": "success" | "error",
    "tool": "tool_name",
    "request_id": "uuid",
    "error_code": "tool_not_found" | "invalid_params" | ...,
    "details": {},
    "retryable": bool,
    "timestamp": "ISO-8601",
}
```

### Graceful Degradation
Every optional feature must fail safely:
- Rust extension missing? Python fallback runs transparently.
- FastAPI not installed? Webhook routes return `missing_dependency` envelope.
- Mojo compiler absent? GPU path falls back to Python embedding.

---

## 7. The Stub Lesson

This codebase has essentially **zero TODO comments** but had 41 **structural stubs** — empty methods, simulated returns, docstring-marked placeholders. These are more dangerous than TODOs because the code *looks* like it works but silently does nothing.

### How to Avoid Introducing Stubs

1. If you add a placeholder, mark it explicitly: `raise NotImplementedError("Reason + planned implementation date")`.
2. If you recover code from `~/Desktop/whitemagic-aux/archive/`, diff it against the current version before copying.
3. If a module shrinks by >50% in a refactor, flag it for review.

### How to Detect Stubs

```bash
# Search for stub patterns
grep -rn "stub" core/whitemagic/ --include="*.py" | grep -i "docstring\|placeholder\|not yet"
```

---

## 8. Safe Change Patterns

### Adding a New Tool
1. Define the tool in `core/whitemagic/tools/registry_defs/<domain>.py`.
2. Add the handler in `core/whitemagic/tools/handlers/<domain>.py`.
3. Register in `core/whitemagic/tools/dispatch_table.py`.
4. Add tests in `core/tests/unit/test_<domain>.py`.
5. Update `grimoire/TRUTH_TABLE.md` if the tool belongs to a Gana.
6. Run the full test suite.

### Adding a New Document
1. Choose the correct folder based on audience and topic.
2. If it's session-active → `docs/message_board/`.
3. Update `INDEX.md`.
4. Run `python core/scripts/check_doc_drift.py`.

### Before Writing New Code — Archive Reconnaissance
> **Rule of thumb**: If a module is a stub, missing, or significantly smaller than its archive counterpart, recover before reinventing.

1. **Primary archive**: `~/Desktop/whitemagic-aux/archive/whitemagic0.2/` (965 Python files, 2.2 GB)
   - Contains substantially more complete versions of at least 8 core modules.
   - Notable recoveries to date: `lifecycle.py` (+383 lines), `solver_engine.py` (+110), `db_manager.py` (+196), `galactic_map.py` (+585), `consolidation.py` (+521), `kaizen_engine.py` (+554).
2. **Secondary locations**:
   - `core/whitemagic/_archived/` — recently moved modules
   - `docs/archive/` — superseded documentation
   - `~/Desktop/whitemagic-aux/archive/whitemagic0.1/` — older tar archives
3. **Diff before copying**. Archive code may predate current API changes. Always diff against the current file and merge carefully.
4. **Validate after recovery**. Run the full test suite. Archive code may have dependencies on modules that no longer exist.

### Refactoring Memory Subsystems
1. Memory code is high-risk. Always run stress tests:
   ```bash
   python core/scripts/stress_test_memory.py
   ```
2. Check `~/Desktop/whitemagic-aux/archive/whitemagic0.2/` for more complete historical implementations.
3. Verify galactic zone boundaries match `grimoire/TRUTH_TABLE.md`.

---

## 9. Key Files to Memorize

| File | Purpose | When to Read |
|------|---------|-------------|
| `INDEX.md` | Doc index | Adding/moving any doc |
| `AI_PRIMARY.md` | AI-facing contract | Integration questions |
| `SYSTEM_MAP.md` | Architecture map | Refactoring or debugging |
| `grimoire/TRUTH_TABLE.md` | Canonical 28-fold mapping | Grimoire/registry changes |
| `core/whitemagic/tools/dispatch_table.py` | Tool dispatch | Adding tools |
| `core/whitemagic/tools/unified_api.py` | Tool contract | Envelope changes |
| `core/whitemagic/config/paths.py` | Path resolution | State root changes |
| `core/pyproject.toml` | Package config | Dependency changes |
| `docs/message_board/SESSION_SUMMARY.md` | Latest session log | Handoff/context |
| `~/Desktop/whitemagic-aux/archive/whitemagic0.2/` | Primary code archive | Before writing new code |

---

## 10. Common Pitfalls

1. **Forgetting to update `INDEX.md`** when adding docs. The doc drift CI job will catch this, but fix it before commit.
2. **Moving root `.md` files** without updating code references. Root files (`README.md`, `AI_PRIMARY.md`, `SYSTEM_MAP.md`) are referenced by scripts.
3. **Writing runtime state to the repo**. Always use `WM_STATE_ROOT`.
4. **Duplicating `.md` files** in `core/whitemagic/grimoire/`. The canonical source is `grimoire/` (root).
5. **Skipping tests** after "trivial" changes. The 1,280-test improvement came from fixing wiring, not from heroic test-writing.
6. **Using `Path.home()` outside `core/whitemagic/config/paths.py`**. The path hygiene test will flag this.

---

## 11. Build & Verification Checklist

Before declaring any task complete:

- [ ] `python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q` → 2063 passed, 0 failed
- [ ] `python scripts/check_doc_drift.py` → All checks pass
- [ ] `python scripts/check_versions.py` → Version consistent
- [ ] `git status` → Only intended files modified
- [ ] No new `Path.home()` or `.expanduser()` outside `core/whitemagic/config/paths.py`
- [ ] `INDEX.md` updated if docs added/moved

---

## 12. Session Timing & Velocity Tracking

This project uses **focused sessions** with explicit time tracking. Each session should have a clear, well-scoped goal.

### Before Starting

Record the start time and state the goal:

```bash
date '+%H:%M:%S'
# Goal: Add X to Y module
```

### After Finishing

Record end time and note:
- **Duration** (actual vs expected)
- **Test run time** (how long did the 2,063 tests take?)
- **What was surprising** (unexpected friction, archive recovery needed, etc.)
- **What took longer than expected and why**
- **Technical debt created** (stubs, TODOs, deferred refactors)

### Why This Matters for WhiteMagic

- **Archive reconnaissance** can take 5-15 minutes per module. Timing reveals which modules need upstream recovery.
- **Test suite runtime** (~30-60s for full suite) is a metric. If it grows, investigate parallelization.
- **Doc drift checks** (~5s) should never be skipped. If they fail, fix before commit.
- **Memory subsystem changes** require stress tests. Timing these helps estimate risk for future memory work.

### Phase-Based Execution Protocol

When working through a prioritized backlog, use **phased execution** with explicit time gates:

```bash
# Before each phase
date '+%H:%M:%S'
# Goal: Phase N — description
```

**Rules**:
1. **Time gate per phase** (adaptive by objective class):
   - **Immediate objectives**: 10-minute gate. These are well-scoped fixes (wiring, config, small refactors).
   - **Short-term objectives**: 10-minute gate. Slightly larger but still bounded (handler expansion, CLI commands, benchmarks).
   - **Medium-term objectives**: 15-minute gate. These involve architecture, new subsystems, or significant design decisions. The extra 5 minutes acknowledges integration complexity.
   - If a phase completes under its gate, proceed immediately. If it exceeds the gate, finish the phase (no shortcuts), then summarize progress and decide whether to pivot or continue.
2. **Batch gate**: If all objectives in a batch complete under their cumulative gate threshold, escalate to the next batch.
3. **Summarize on threshold breach**: When a phase exceeds its gate, record:
   - What took longer than expected and why
   - Whether the overrun signals hidden complexity (warranting a pivot) or just normal friction (warranting continuation)
   - Any technical debt created

**Why adaptive gates work**: Medium-term objectives (e.g., CyberBrain Layer 7, polyglot revival) are inherently more complex than immediate fixes. A 10-minute gate would force premature pivots on architecture that legitimately needs 12-15 minutes to wire correctly. The 15-minute gate respects the complexity while still preventing open-ended rabbit holes.

### Healthy Session Benchmarks

| Task Type | Healthy Duration | Warning Signal |
|-----------|------------------|----------------|
| Add a new tool | 15-30 min | >45 min = dispatch table complexity |
| Recover from archive | 10-20 min | >30 min = merge conflicts / API drift |
| Refactor memory code | 20-40 min | >60 min = run stress tests, check galactic zones |
| Documentation update | 5-10 min | >20 min = INDEX.md or drift issues |
| Full test suite | 30-60s | >2 min = investigate slow tests |
| Single immediate objective | 5-10 min | >10 min = summarize and reassess |
| Immediate batch (4 objectives) | 20-40 min | >40 min = escalate or stop |

### Documentation as Byproduct

Every session produces:
- Working code + passing tests
- Updated `docs/message_board/SESSION_SUMMARY.md`
- If grimoire-affecting: updated `grimoire/TRUTH_TABLE.md`
- If architecture-affecting: updated `AGENTS.md`

---

## 13. AI Context Retrieval

This project is indexed with **Fragment** for fast AI context retrieval. Before asking AI assistants about this codebase, ensure the index is current:

```bash
# From the project root
fragment index .

# Query for relevant chunks
fragment query . "how does memory holography work"

# Or use the HTTP API for editor integration
fragment serve . --bind 127.0.0.1:7727
curl -s -X POST http://127.0.0.1:7727/api/query -H "Content-Type: application/json" -d '{"q":"dispatch pipeline","top":5}'
```

The index lives in `.fragment/` and is ignored by git. Re-index after significant architectural changes.

---

## 14. Contact & Context

- **Project**: WhiteMagic v22.2.0
- **Repository**: `/home/lucas/Desktop/WHITEMAGIC/`
- **Virtual Environment**: `.venv/` (source before any Python work)
- **Test Command**: `cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q`
- **Doc Drift Check**: `python core/scripts/check_doc_drift.py`
- **Memory Stress Test**: `python core/scripts/stress_test_memory.py`
- **Archive**: `~/Desktop/whitemagic-aux/archive/whitemagic0.2/`

**License**: MIT
**Contact**: whitemagicdev@proton.me

---

*This document is a living artifact. Update it as conventions evolve.*
