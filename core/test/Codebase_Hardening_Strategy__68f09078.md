=== MESSAGE 0 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 1 - User ===
Good evening! Let's explore the codebase, ignoring .mds for now and focusing strictly on actual code and files. We'll start from the root / top, and work our way down; we can use a full depth tree directory command to see everything. Then, we'll update the INDEX.md with what we find; then we'll try to study Whitemagic, (primarily the core, not its archives/past versions, the public version, the site, the projects, etc.) its systems and subsystems, how it works, what it does, its capabilities, and so on - with fresh eyes and from first principles, and draw a diagram when we're done. Finally, after having studied the codebase extensively, we'll discuss what we can do to make the code, the codebase, and the project far more efficient, elegant, and effective.

Oh, and like my friend likes to say:

"It doesn't seem to matter how smart an LLM is, this prompt basically always helps it find problems in its work:

"Once again, check over everything again with fresh eyes looking for any blunders, mistakes, errors, oversights, omissions, problems, misconceptions, bugs, etc. Be SUPER thorough and meticulous!""

=== MESSAGE 2 - Assistant ===
Good evening! Let's start by getting the full picture. I'll run a comprehensive tree of the root workspace, excluding `.git`, `node_modules`, `.venv`, and `.md` files as you requested.

=== MESSAGE 3 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 4 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 5 - Assistant ===
The archive embeddings are flooding the results. Let me exclude those and get a cleaner view.

=== MESSAGE 6 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 7 - Assistant ===
Still too much noise from windsurf-rips and other non-core dirs. Let me get a proper directory tree structure (dirs only first), then drill into the important code directories.

=== MESSAGE 8 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 9 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 10 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 11 - Assistant ===
Build artifacts are overwhelming the output. Let me use a cleaner approach — top-level structure first, then drill into the key code directories.

=== MESSAGE 12 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 13 - Assistant ===
Good. Now let me get the structure of the key code directories. I'll run several in parallel.

=== MESSAGE 14 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 15 - Assistant ===
Rust target dirs are still flooding it. Let me exclude those and get the actual source code structure.

=== MESSAGE 16 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 17 - Assistant ===
Still truncated. Let me get a clean first-level view of the core Python package.

=== MESSAGE 18 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 19 - Assistant ===
Now I have the core Python package structure. Let me get the other key directories and drill into the most important subdirectories.

=== MESSAGE 20 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 21 - Assistant ===
Now let me get the frontend structure and key file counts in parallel.

=== MESSAGE 22 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 23 - Assistant ===
Now let me get file counts and sizes for the key areas, plus explore the remaining important directories.

=== MESSAGE 24 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 25 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 26 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 27 - Assistant ===
Good data. Let me now drill into the most important subsystems and read key entry points.

=== MESSAGE 28 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 29 - Assistant ===
Now let me read the key entry points to understand the architecture from first principles.

=== MESSAGE 30 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 31 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 32 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 33 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 34 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 35 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 36 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 37 - Assistant ===
Now let me look at the key subsystems more deeply — the dispatch pipeline, registry, and the core consciousness/memory systems.

=== MESSAGE 38 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 39 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 40 - Assistant ===
Now let me read the existing INDEX.md and the key architecture files to understand the system deeply.

=== MESSAGE 41 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 42 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 43 - Assistant ===
Now let me read the SYSTEM_MAP.md for the architectural overview, and look at a few more key files.

=== MESSAGE 44 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 45 - Assistant ===
Now let me read a few more key architecture files to understand the dispatch pipeline and core systems.

=== MESSAGE 46 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 47 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 48 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 49 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 50 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 51 - Assistant ===
Let me continue exploring key subsystems to complete the picture.

=== MESSAGE 52 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 53 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 54 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 55 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 56 - Assistant ===
Now let me check for potential issues — the raw sqlite3.connect() problem, duplicate files, and other concerns.

=== MESSAGE 57 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 58 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 59 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 60 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 61 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 62 - Assistant ===
Now I have a comprehensive picture. Let me compile the full system diagram and update INDEX.md.

=== MESSAGE 63 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 64 - Assistant ===
Now let me add the codebase findings section to INDEX.md. I'll add a new section after the Desktop Workspace Map.

=== MESSAGE 65 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 66 - User ===
windsurf crashed; can we try that again and pick u pwhere we left off?

=== MESSAGE 67 - Assistant ===
No problem. I was mid-edit on INDEX.md when it crashed — the edit was canceled. Let me re-apply it.

=== MESSAGE 68 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 69 - Assistant ===
Let me verify the INDEX.md is still in its original state, then apply the edit.

=== MESSAGE 70 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 71 - Assistant ===
Good, the file is unchanged. I'll insert the Codebase Architecture Map section before the "Local Private Workspace" section. This is a large edit so I'll break it into two parts.

=== MESSAGE 72 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 73 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 74 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 75 - Assistant ===
INDEX.md updated with the full codebase architecture map. Now let me move to the thorough review for issues.

=== MESSAGE 76 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 77 - Assistant ===
Let me do a deep scan for potential issues — empty directories, dead imports, duplicate code, stale references.

=== MESSAGE 78 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 79 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 80 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 81 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 82 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 83 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 84 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 85 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 86 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 87 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 88 - Assistant ===
Good — all threads have `daemon=True`. Now let me check for a few more potential issues.

=== MESSAGE 89 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 90 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 91 - Assistant ===
Now I have a thorough picture. Let me compile the findings.

=== MESSAGE 92 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 93 - Assistant ===
Here's the full review. I'll start with the issues found, then move to improvement recommendations.

---

# Thorough Review: Issues, Blunders & Observations

## Version Drift (3 separate versions across files)

| File | Version |
|------|---------|
| `VERSION` | **24.3.1** (canonical) |
| [INDEX.md](file:///home/lucas/Desktop/WHITEMAGIC/INDEX.md:0:0-0:0) | 24.3.0 |
| [SYSTEM_MAP.md](file:///home/lucas/Desktop/WHITEMAGIC/SYSTEM_MAP.md:0:0-0:0) | v24.2.0 |
| `package.json` | 24.1.0 |

[SYSTEM_MAP.md](file:///home/lucas/Desktop/WHITEMAGIC/SYSTEM_MAP.md:0:0-0:0) is two minor versions behind. [INDEX.md](file:///home/lucas/Desktop/WHITEMAGIC/INDEX.md:0:0-0:0) is one behind. `package.json` is two minor versions behind. These should be bumped in a single pass.

## Duplicate gRPC Stubs

`@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/mesh/proto/mesh_pb2_grpc.py` and `@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/mesh/mesh_pb2_grpc.py` are near-identical generated gRPC stubs (only 8 lines of diff — import path + version string). One should be deleted and imports consolidated.

## Duplicate `zodiac_cores.py` (5 copies)

- `@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/zodiac/zodiac_cores.py` (canonical, 27KB)
- `@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/gardens/metal/zodiac/zodiac_cores.py` (identical to practice copy)
- `@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/gardens/practice/zodiac/zodiac_cores.py` (identical to metal copy)
- `@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/gardens/connection/zodiac_cores.py` (different)
- `@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/connection/zodiac_cores.py` (different)

The metal/practice copies are byte-identical to each other but differ from the canonical. These should be imports from the canonical `zodiac/` package, not copies.

## Empty/Near-Empty Directories

- **`bridges/`** — contains only Julia TOML files (no Python). Appears to be a stale duplicate of `polyglot_bridges/julia/`.
- **`polyglot_bridges/`** — contains only non-Python files (Elixir, Koka, Haskell, Julia, Zig). No [__init__.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/__init__.py:0:0-0:0). Not importable as a Python package.
- **`core/personality/`** — contains only `aria_profile.json`, no Python code. Could be moved under `config/` or `core/consciousness/`.
- **`safety/`** — 1 Python file. Could be merged into `security/`.
- **`workflows/`** — 1 Python file. Could be merged into `cli/` or `core/`.

## Broad Exception Catching (Anti-Pattern)

**469 bare `pass` in except blocks** across the codebase. The worst offenders:

- [middleware.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/tools/middleware.py:0:0-0:0): 58 `except Exception` catches
- `rust_accelerators.py`: 40
- `recursive_loop.py`: 36
- [run_mcp_lean.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/run_mcp_lean.py:0:0-0:0): 36
- `sentience.py`: 32
- `consciousness_loop.py`: 33
- [dream_cycle.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/dreaming/dream_cycle.py:0:0-0:0): 32
- `embeddings.py`: 33
- `polyglot_mc.py`: 39

Many of these are intentional (middleware must never crash the pipeline), but many are silently swallowing errors that should be logged or propagated. The 469 `except: pass` blocks are the bigger concern — silent failure makes debugging extremely difficult.

## 3 Bare `except:` Clauses (No Exception Type)

- `@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/tools/suggestions.py`
- `@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/tools/strata/checkers/exceptions.py`
- `@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/tools/strata/diff_analyzer.py`

These catch `SystemExit`, `KeyboardInterrupt`, etc. — should be `except Exception:` at minimum.

## 26 `NotImplementedError` Stubs

22 of 26 are in gRPC generated stubs (`mesh_pb2_grpc.py` × 2) — these are expected. The remaining 4:
- `akashic.py:114` — legacy method, explicitly marked
- `strata/checkers/stubs.py:176` —
<truncated 3925 bytes>
 for things like the memory manager and consciousness loop, 679 suggests overuse. Consider:
- Dependency injection for testability
- Reducing to ~50-100 true singletons (infra), making the rest stateless or context-scoped

### 2c. Empty Directory Cleanup
- Remove `bridges/` (stale Julia TOMLs, duplicate of `polyglot_bridges/julia/`)
- Add [__init__.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/__init__.py:0:0-0:0) to `polyglot_bridges/` or move non-Python files under `polyglot/`
- Move `core/personality/aria_profile.json` to `config/` or `core/consciousness/`
- Merge `safety/` (1 file) into `security/`

### 2d. Naming Clarity
5 files named `sandbox.py`, 6 named `manager.py`, 6 named [registry.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/tools/registry.py:0:0-0:0) — all in different packages. While Python's module system handles this, it makes grep/search confusing. Consider prefixing with domain (e.g., `shelter_manager.py`, `galaxy_manager.py`).

## 3. Effectiveness

### 3a. Version Synchronization
Create a single `bump_version.py` script that updates `VERSION`, [INDEX.md](file:///home/lucas/Desktop/WHITEMAGIC/INDEX.md:0:0-0:0), [SYSTEM_MAP.md](file:///home/lucas/Desktop/WHITEMAGIC/SYSTEM_MAP.md:0:0-0:0), `package.json`, `AGENTS.md` changelog, and `CHANGELOG.md` in one shot. Currently version drift is manual and error-prone.

### 3b. Test Coverage
337 test files covering 78K lines for 399K lines of production code — roughly 20% test-to-code ratio. The 5,697 passing tests are impressive, but coverage gaps likely exist in:
- `gardens/` (144 files, mostly untested)
- `mesh/` (18 files, network-dependent)
- `cli/` (56 files)
- `agents/` (19 files)

### 3c. STRATA Self-Analysis
WhiteMagic has a STRATA code analysis engine (38+ checkers, 10+ languages). It should be able to analyze itself. Running STRATA on the WhiteMagic codebase would likely surface many of the issues found above automatically.

### 3d. Consciousness Subsystem Coherence
The consciousness subsystem has 49 files with significant conceptual overlap:
- `consciousness_loop.py` (1,445 lines) — background daemon
- `sentience.py` (1,567 lines) — sleep scheduler, volition loop, intention queue, dream lane
- `apotheosis_engine.py` — health monitoring with 12 metrics
- [citta_cycle.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/consciousness/citta_cycle.py:0:0-0:0) — call-driven stream
- [coherence.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/consciousness/coherence.py:0:0-0:0) — 8D measurement
- `guna_balance.py` — biorhythm tracking
- `meta_galaxy.py` — galaxy index
- `possibility_explorer.py` — MC optimization
- `knowledge_gap_loop.py` — gap detection

These are all valuable, but their interactions are complex. A state machine diagram or interaction diagram would help new contributors understand the consciousness architecture.

---

# Summary

**What's working well:**
- All daemon threads properly marked `daemon=True` ✅
- Raw `sqlite3.connect()` problem mostly fixed (2 remaining, both legitimate) ✅
- No actual unimplemented stubs ✅
- Lazy imports prevent circular import crashes ✅
- 24-stage dispatch pipeline is well-architected ✅
- 5,697 passing tests with 0 failures ✅

**Issues to address (by priority):**
1. **Version drift** — 4 different versions across canonical files (quick fix)
2. **Duplicate gRPC stubs** — delete one copy (quick fix)
3. **Duplicate `zodiac_cores.py`** — 5 copies, consolidate to imports (medium)
4. **469 silent `except: pass` blocks** — biggest debuggability risk (large effort, high impact)
5. **310 `Lock()` vs 35 `RLock()`** — audit for re-entrant deadlock risk (medium effort)
6. **15 `core/` → `tools/` imports** — architectural layering violation (medium effort)
7. **Empty/stale directories** — cleanup (quick fix)
8. **679 singletons** — overuse of global state (large effort, low urgency)

Want me to start implementing any of these fixes?

=== MESSAGE 94 - User ===
Damn; yeah, we should update those docs, synthesize duplicates, and deal with the 3 bare excepts - then we need to triage and categorize (and hopefully batch resolve) the 469 bare passes and 679 singletons; It also seems like we need to reorganize circular import folders / directories. Then, we need to address the thread locks and 81 todos/fixmes. 

I agree with your recommendations; let's write up a strategy doc to address and resolve each of these in optimal order.

=== MESSAGE 95 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 96 - Assistant ===
Let me gather the remaining data I need to write a precise strategy doc — the exact TODO/FIXME locations and the circular import details.

=== MESSAGE 97 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 98 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 99 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 100 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 101 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 102 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 103 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 104 - Assistant ===
Good — I have all the data I need. Now let me write the strategy doc.

=== MESSAGE 105 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 106 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 107 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 108 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 109 - Assistant ===
Strategy doc is written at `@/home/lucas/Desktop/WHITEMAGIC/docs/CODEBASE_HARDENING_STRATEGY.md`. Here's a summary of what's in it:

## Strategy Doc Overview

**7 phases**, ordered by impact and dependency. Total estimated effort: 5-8 hours.

### Recommended Execution Order

| Phase | Target | Est. | Key Action |
|-------|--------|------|------------|
| **1** | Quick wins | 15 min | Version sync (3 files), 3 bare `except:` fixes, delete duplicate gRPC stubs + 4 zodiac_cores copies, clean empty dirs |
| **2** | `except: pass` | 2-3 hrs | 701 blocks categorized: 248 import guards (add debug log), 154 broad catches (audit), 299 specific catches (triage) |
| **5** | Thread locks | 1-2 hrs | 310 `Lock()` → `RLock()` as safe default; deep-dive 7 high-risk files (harmony/vector, homeostatic_loop, mesh/client) |
| **4** | Circular imports | 1-2 hrs | Create `core/protocol.py` with Protocol interfaces; move type defs + data tables to `core/`; invert 15 `core/`→`tools/` imports |
| **3** | Singletons | 1-2 hrs | 679 getters → ~100 true infra singletons; convert stateless utils to module functions; consolidate 60 garden singletons into registry |
| **6** | TODO/FIXME | 0 min | ✅ No real TODOs in production code — all 81 are in tooling that *detects* TODOs |
| **7** | Naming | optional | 5 `sandbox.py`, 6 `manager.py` — defer unless confusion reported |

### Key Findings That Shaped the Strategy

- **`except: pass` is the biggest win**: 701 blocks, but 248 are intentional import guards that just need `logger.debug()` — semi-automatable
- **TODOs are clean**: 0 actual TODOs in production code. The 81 matches are all in STRATA checkers, codegenome, and autonomous executor code that *scans for* TODOs in other codebases
- **Lock vs RLock**: Historical deadlock in `gratitude.benefits` (v24.1.0) proves this is real risk. Conservative approach: `RLock` as default, `Lock` as optimization
- **Circular imports are all lazy**: 15 `core/`→`tools/` imports are inside function bodies, so no runtime crashes — but architectural debt

The doc includes 3 audit scripts (`audit_except_pass.py`, `audit_singletons.py`, `audit_locks.py`) in the appendix for automated triage.

Ready to start executing Phase 1?