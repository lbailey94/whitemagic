# AGENTS.md — WhiteMagic Agent Guide

**Version**: 24.0.0 (AGENTS.md revision 24.0)
**Last Updated**: 2026-07-03
**Purpose**: Operational guide for AI agents contributing to the WhiteMagic codebase.

---

## 1. What This Project Is

WhiteMagic is a **cognitive operating system** for agentic AI — not merely a memory tool. It provides:

- Persistent memory with 5D holographic coordinates and galactic lifecycle
- 518 callable tools across 490 dispatch entries + 28 Gana meta-tools (PRAT)
- 8-stage dispatch pipeline with Dharma ethical governance
- Polyglot accelerators (Rust, Haskell, Elixir, Go, Zig)
- v22.2.0 release baseline: 2,216 passing tests, 0 failures
- v23.0.0: test suite optimized from 823s → 119s (6.9x); integration suite from 642s → 23s (27.7x); 3 flaky tests fixed by mocking heavy engines; AGENTS.md process refinements (test purity, hot path review, ruff linting, flaky test ban)
- v23.1.0: integration test hangs fixed (stale GanYingBus singleton root cause); full suite 2,526 passed, 0 failed, ~105s; 4 compiled binaries removed from git; gitignore cleanup
- v23.2.0: Mojo removed (8→7 polyglot languages); multi-user galaxy isolation (per-user SQLite namespaces, local profiles, X-User-Id header); real-time sync via Redis (galaxy lifecycle events on user-scoped channels, REDIS_URL env var support); Rust SIMD expansion (batch Euclidean distance, batch dot product, batch top-k) + RustCascadeBackend wired into GanYingBus; browser-first PWA substrate (MemoryStore, DharmaEngine, KarmaLedger, GnosisSnapshot in WASM, LocalTransport in TypeScript SDK, PWA shell with service worker); full suite 2,589 passed, 0 failed, ~110s
- v23.3.2: Token economy wiring + budget enforcement; prediction calibration feedback loop; module consolidation (DepthGauge, TokenOptimizer shims); subprocess bridge timeout fixes (WM_SKIP_POLYGLOT); STRATA 10 new checkers + 5-phase auto-fix (3,008+ findings); SkillForge (43 skills); Citta P0 (Smarana, Presence, coherence auto-measure); de-slop pass; 3,337 unit tests passing
- v23.3.1: Memory system overhaul — 10-galaxy taxonomy (aria, citta, codex, journals, dreams, research, sessions, substrate, tutorial, universal); CITTA memory type for consciousness-stream memories; citta bridge auto-persists significant moments; HNSW index with disk persistence (16,219 embeddings, 0.26ms search); galaxy-aware search (semantic + FTS5); `galaxy.canonical_taxonomy` + `galaxy.export_tutorial` tools; oracle readings auto-persist to dreams galaxy; content_hash backfilled for all 12,737 memories; holographic coords for all memories; 2,853 cross-galaxy associations; FTS5 phrase-first search + join bug fix; 3,206 unit + 259 integration tests passing
- v23.3.3: Neuro PyO3 cleanup — removed ThalamicGate + MomentumDynamics from Rust (PyO3 FFI overhead > dict-lookup compute; only PredictiveCoder remains at 19x speedup); Session Memory system — `SessionRecorder` with chronological sequence numbers, progressive recall (token-budgeted), selective replay (importance-filtered), FTS5 session search, backfill for existing memories; 9 MCP tools (`session.record/recall/replay/search/memory_stats/backfill/continuity/consolidate`) mapped to `gana_heart`; auto-recording middleware in dispatch pipeline; cross-session continuity (previous session recall on reconnect); sleep consolidation (important turns → codex galaxy); emotional auto-tagging (citta cycle → valence mapping); polyglot test hang fix (WM_SKIP_POLYGLOT guard); 51 session tests + 506 total passing across affected suites
- v24.0.1: Meta-strategy execution — 49,413 memories across 10 galaxies (3,715 documents ingested from WHITEMAGIC, archives, public, WindsurfRips, ~/.whitemagic, ~/.codeium); Phase 0 session mining (76 decisions, 19 breakthroughs, 540 user turns analyzed, 7+1 directive taxonomy, 3 proto-emotional turns discovered); FTS5 search bug fix (column-name escaping); agent registry heartbeat reset fix; 55 ruff fixes; STUB_REGISTRY updated (7 stubs resolved); Goal Graph (`goal_graph.py`) for cross-session intention tracking; Emotional Steering Signals (`emotional_steering.py`) — frustration, curiosity, satisfaction; Self-Directed Attention prototype (`self_directed_attention.py`) — 7+1 action types generated internally; 22 new consciousness tests; 4,190+ passing, 0 failing, 19 skipped

**The single most important rule**: *Tests are the guardrail. Never skip them.*

---

## 2. First Actions on Entering the Repo

```bash
# 1. Activate the venv (all deps)
cd <path-to-whitemagic>
source .venv/bin/activate

# 2. Verify test baseline (current: 4190+ passed, 19 skipped, 0 failures)
cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30

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
│   ├── tests/               # 2,589 active tests (full suite minus archives)
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
**Run the full test suite after every change.** The project went from 783 passing → 2,589 passing by fixing wiring, not by skipping tests. When the suite is fast enough, this rule is enforceable rather than aspirational.

### Test Speed Stratification

Use the appropriate tier for your current activity:

```bash
# Tier 1: Fast feedback (<30s) — during active development
cd core
python -m pytest tests/unit/ -q --timeout=5 -x --tb=short

# Tier 2: Medium validation (<3min) — before commit
python -m pytest tests/unit/ tests/integration/ -q --timeout=15 --tb=short

# Tier 3: Full suite — release verification
python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30

# Specific module
python -m pytest tests/unit/test_path_hygiene.py -v

# With coverage
python -m pytest tests/ --cov=whitemagic --cov-report=term-missing -q
```

### Performance Regression Detection

Always run with `--durations` to catch slow tests before they become the new normal:

```bash
# Show slowest 10 tests taking >1s
python -m pytest tests/unit/ -q --durations=10 --durations-min=1.0 --timeout=30
```

**Rules**:
- No individual unit test should exceed **5s** without an explicit `@pytest.mark.skip` reason.
- No individual integration test should exceed **15s** without an explicit skip reason.
- If suite runtime grows >10% without explanation, investigate before merging.
- Track suite runtime in `SESSION_SUMMARY.md` to spot trends across sessions.

### Test Purity

Unit tests should be **fast and isolated**. They must never:
- Spawn subprocesses (Julia, Elixir, Go, etc.) — mock at the class boundary instead.
- Load ML models (MiniLM, sentence-transformers) — patch `get_hrr_engine` / `get_embedding_engine`.
- Make network or socket calls (Redis probes, HTTP requests) — mock or skip in test envs.
- Start asyncio event loops in sync context — use `WM_SILENT_INIT=1` to skip broker forwarding.
- Load production SQLite databases — use `WM_STATE_ROOT` pointing to a temp directory.

Integration tests are for testing real subsystem interaction. They may use subprocesses and real databases, but must still respect timeout limits.

If a unit test needs heavy infrastructure, **mock it at the class boundary** — not at the individual call site. See `test_recursive_loop.py` for a reference implementation of `_patch_engines()`.

### Flaky Test Policy

`@pytest.mark.flaky` is **banned** unless accompanied by:
1. A documented reason in the test docstring.
2. A tracking issue reference (or inline comment explaining why it cannot be fixed).

Flaky tests are either:
- **Fixable** — fix the root cause (usually state leakage or race condition).
- **Order-dependent** — fix the singleton reset in `conftest.py`.
- **Timing-dependent** — add proper waits/locks, not retries.

Silent retries mask real bugs. The 3 `test_recursive_loop` failures that were marked flaky for months were actually fixable by mocking heavy engines — the flaky marker hid the real problem.

### What to Do If Tests Fail

1. Read the failure message carefully.
2. Check if the failure is in code you touched.
3. If not, check `docs/message_board/SESSION_SUMMARY.md` for known issues.
4. If the failure is new, **revert your change** and investigate.
5. If a test hangs (no output for >30s), check for event loop leaks or subprocess waits — see §8 Hot Path Review.

---

## 6. Code Conventions

### Style
- **Python**: PEP 8, type hints required for public functions.
- **Rust**: `cargo fmt`, `cargo clippy`.
- **Module imports**: Use absolute imports (`from whitemagic.core.memory...`).

### Linting
Run `ruff check` before commit. Key rules that catch real bugs:
- `logging-f-string` — f-strings in logging calls (causes lazy formatting to break)
- `logging-format-interpolation` — `.format()` in logging (same issue)
- `PLE1205` — logging format string argument count mismatch
- `F841` — unused local variables
- `F401` — unused imports

**Historical note**: Four logging calls in `homeostatic_loop.py` used f-string syntax (`{snap.value:.3f}`) inside `%s`-style format strings, combined with `exc_info=True`. This caused pytest's unraisable exception hook to trigger recursive traceback formatting → `RecursionError`. Ruff's `logging-f-string` rule catches this class of bug.

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
- Mojo compiler absent? GPU path falls back to Python embedding. (Mojo removed in v23.2)

---

## 7. The Stub Lesson

This codebase has essentially **zero TODO comments** but had 41 **structural stubs** — empty methods, simulated returns, docstring-marked placeholders. These are more dangerous than TODOs because the code *looks* like it works but silently does nothing.

### How to Avoid Introducing Stubs

1. If you add a placeholder, mark it explicitly: `raise NotImplementedError("Reason + planned implementation date")`.
2. If you recover code from `<path-to-your-archive>`, diff it against the current version before copying.
3. If a module shrinks by >50% in a refactor, flag it for review.
4. Add an entry to `STUB_REGISTRY.md` (repo root) tracking every `NotImplementedError` and placeholder. Each entry: module, reason, planned implementation date. This makes technical debt visible and trackable, rather than hidden in code.

### How to Detect Stubs

```bash
# Search for stub patterns
grep -rn "stub" core/whitemagic/ --include="*.py" | grep -i "docstring\|placeholder\|not yet"
```

---

## 8. Safe Change Patterns

### File I/O Protocol

**See global rules** (`~/.codeium/windsurf/windsurf/rules/global.md`) for the full file I/O protocol. Summary:

- **>10 lines or full rewrites**: Use `cat << 'EOF'` or `python3 << 'PYEOF'` shell writes via `run_command`
- **1-3 line surgical edits**: Use the `edit` tool
- **Batch reads**: Use `head`/`sed`/`grep` in one `run_command` call
- **Always validate after writing**: `python3 -c "import ast; ..."` and `ruff check`

### MCP Tool Compounding — Use WhiteMagic Systems Constantly

**Principle**: Every session should use WhiteMagic's own memory, consciousness, and intelligence systems. The more we use them, the more data is created that improves them. This compounding effect makes each session more effective and each interaction more intelligent.

**Mandatory practices**:
1. **Session Memory** (highest priority): Record every user message and AI response as a session memory. This prevents in-session drift and enables chronological recall across sessions. **Auto-recording is enabled via dispatch pipeline middleware** — tool calls are automatically recorded. Manual recording is still needed for user messages.
   - After each user message: `wm(thought='record this user message')` or call `session.record(role='user', content='...', turn_type='question')`
   - After each AI response: `wm(thought='record my response')` or call `session.record(role='ai', content='...', turn_type='answer')`
   - On context drift or at session start: `wm(thought='recall recent turns')` or call `session.recall(n=10)`
   - For resumption after disconnect: `wm(thought='where we left off')` or call `session.continuity(n=10)` — recalls previous session's turns
   - For resumption with token budget: `wm(thought='replay session selectively')` or call `session.replay(mode='selective')`
   - At session end, consolidate important turns: `wm(thought='consolidate session')` or call `session.consolidate(min_importance=0.7)` — promotes decisions/breakthroughs/errors to codex galaxy
   - Use `turn_type` tags: `message`, `decision`, `breakthrough`, `question`, `answer`, `code_change`, `error`, `summary`
   - Set `importance` higher (0.7-0.9) for decisions, breakthroughs, and errors — these are the turns that matter for selective replay and sleep consolidation
   - **Emotional valence is auto-tagged** from the citta cycle's emotional state — no manual input needed. Explicit `emotional_valence` parameter overrides auto-tagging.
   - Disable auto-recording with `WM_SESSION_RECORD=0` env var if needed for benchmarks
2. **Memory**: Store session context, decisions, and discoveries in WhiteMagic memory at session start/end. Use `wm(thought='remember that ...')` for important context.
3. **Consciousness**: Check coherence and depth gauge during sessions. Use `wm(thought='check my coherence')` to get self-state.
4. **Intelligence**: Use the self-model and foresight engine for planning. Query `wm(thought='what does the self-model predict')` before major decisions.
5. **Dream Cycle**: Run dream consolidation between major work phases. Use `wm(thought='run dream cycle')` to consolidate learning. Session consolidation (`session.consolidate`) complements this by promoting episodic session memories to semantic codex knowledge.
6. **Kaizen**: After each session, apply kaizen analysis. Use `wm(thought='kaizen analyze recent work')` to find improvements.

**The compounding loop**: Auto-recording creates a chronological record without manual effort. Session memory prevents drift. Cross-session continuity enables resumption. Sleep consolidation converts episodic sessions into permanent knowledge. Emotional auto-tagging enriches memories with affective context. Using memory creates memories about memory usage. Using consciousness creates coherence data. Each use makes the next use more informed. This is the foundational principle of WhiteMagic — the system improves itself through its own operation.

**Anti-pattern**: Do not store context only in chat history or external notes. Always mirror important context into WhiteMagic memory so it persists across sessions and compounds. **Do not let conversation turns go unrecorded** — every user message and AI response should be persisted via `session.record` to prevent in-session drift. **Do not skip consolidation** at session end — important turns should be promoted to codex for long-term recall.

### Adding a New Tool
1. Define the tool in `core/whitemagic/tools/registry_defs/<domain>.py`.
2. Add the handler in `core/whitemagic/tools/handlers/<domain>.py`.
3. Register in `core/whitemagic/tools/dispatch_table.py`.
4. Add tests in `core/tests/unit/test_<domain>.py`.
5. Update `grimoire/TRUTH_TABLE.md` if the tool belongs to a Gana.
6. Run `ruff check` on changed files.
7. Run the full test suite with `--durations=10` to verify no performance regression.

### Adding a New Document
1. Choose the correct folder based on audience and topic.
2. If it's session-active → `docs/message_board/`.
3. Update `INDEX.md`.
4. Run `python core/scripts/check_doc_drift.py`.

### Before Writing New Code — Archive Reconnaissance
> **Rule of thumb**: If a module is a stub, missing, or significantly smaller than its archive counterpart, recover before reinventing.

1. **Primary archive**: `<path-to-your-archive>whitemagic0.2/whitemagic-private-main/` (776 Python files, v21.0.0)
   - Contains substantially more complete versions of at least 8 core modules.
   - Notable recoveries to date: `lifecycle.py` (+383 lines), `solver_engine.py` (+110), `db_manager.py` (+196), `galactic_map.py` (+585), `consolidation.py` (+521), `kaizen_engine.py` (+554).
2. **Secondary locations**:
   - `core/whitemagic/_archived/` — recently moved modules
   - `docs/archive/` — superseded documentation
   - `<path-to-your-archive>whitemagic0.1/` — older tar archives
3. **Diff before copying**. Archive code may predate current API changes. Always diff against the current file and merge carefully.
4. **Validate after recovery**. Run the full test suite. Archive code may have dependencies on modules that no longer exist.

### Refactoring Memory Subsystems
1. Memory code is high-risk. Always run stress tests:
   ```bash
   python core/scripts/stress_test_memory.py
   ```
2. Check `<path-to-your-archive>whitemagic0.2/` for more complete historical implementations.
3. Verify galactic zone boundaries match `grimoire/TRUTH_TABLE.md`.

### Hot Path Review

Code that runs during `call_tool` dispatch, event emission, or per-test setup is on a **hot path**. Changes to hot paths must be reviewed for:

- **Network/subprocess calls** — even "quick" ones (0.5s socket probes, `subprocess.run`) compound when called 25× per dispatch.
- **Object creation that triggers GC pressure** — asyncio event loops, Redis connections, and ML model loads create objects whose `__del__` methods fire during GC, potentially triggering unraisable exceptions.
- **Import cascades** — `from X import Y` inside a function body loads the module on first call. If the module loads a 90MB ML model, every test pays that cost on the first invocation.
- **Uncached availability checks** — probing Redis, checking for binaries, or testing socket connections should be cached with a TTL, not performed on every invocation.

**Historical note**: The integration test suite went from 642s → 23s by fixing three hot-path issues:
1. Redis socket probe on every event emission (0.5s × 25 events × 259 tests = ~54 min wasted)
2. Asyncio event loop leak from broker forwarding (caused `RecursionError` via pytest's unraisable hook)
3. ActorSupervisor spawning an Elixir subprocess inside `run_cycle()` (1s per test × 30 tests = 30s wasted)

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
| `STUB_REGISTRY.md` | Technical debt tracker | Before/after adding placeholders |
| `core/tests/conftest.py` | Test fixtures & singleton resets | Test failures, state leakage |
| `core/tests/unit/test_recursive_loop.py` | Reference test mocking | Writing unit tests for heavy modules |
| `<path-to-your-archive>whitemagic0.2/` | Primary code archive | Before writing new code |

---

## 10. Common Pitfalls

1. **Forgetting to update `INDEX.md`** when adding docs. The doc drift CI job will catch this, but fix it before commit.
2. **Moving root `.md` files** without updating code references. Root files (`README.md`, `AI_PRIMARY.md`, `SYSTEM_MAP.md`) are referenced by scripts.
3. **Writing runtime state to the repo**. Always use `WM_STATE_ROOT`.
4. **Duplicating `.md` files** in `core/whitemagic/grimoire/`. The canonical source is `grimoire/` (root).
5. **Skipping tests** after "trivial" changes. The 1,280-test improvement came from fixing wiring, not from heroic test-writing.
6. **Using `Path.home()` outside `core/whitemagic/config/paths.py`**. The path hygiene test will flag this.
7. **Using f-string syntax in logging calls** with `%s`-style format strings. This silently breaks lazy formatting and can cause `RecursionError` when combined with `exc_info=True`. Use `ruff check` to catch.
8. **Marking tests `@pytest.mark.flaky` instead of fixing them**. Flaky markers mask real bugs (state leakage, race conditions, missing mocks). Fix the root cause.
9. **Adding subprocess calls or network probes to hot paths**. Code that runs during `call_tool` dispatch or event emission executes 25+ times per test. Even 0.5s overhead compounds to minutes across the suite.

---

## 11. Build & Verification Checklist

Before declaring any task complete:

- [ ] `python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30` → all tests pass, 0 failures
- [ ] `python -m pytest tests/unit/ -q --durations=10 --durations-min=1.0` → no test >5s without skip reason
- [ ] `ruff check core/whitemagic/ core/tests/` → no new warnings
- [ ] `python scripts/check_doc_drift.py` → All checks pass
- [ ] `python scripts/check_versions.py` → Version consistent
- [ ] `git status` → Only intended files modified
- [ ] No new `Path.home()` or `.expanduser()` outside `core/whitemagic/config/paths.py`
- [ ] No new `@pytest.mark.flaky` without documented reason + tracking issue
- [ ] No new subprocess calls in unit tests
- [ ] No new network/socket calls in event emission or `call_tool` dispatch paths
- [ ] `INDEX.md` updated if docs added/moved
- [ ] `STUB_REGISTRY.md` updated if placeholders added

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
- **Test run time** (how long did the test suite take? Track in `SESSION_SUMMARY.md` to spot trends.)
- **What was surprising** (unexpected friction, archive recovery needed, etc.)
- **What took longer than expected and why**
- **Technical debt created** (stubs, TODOs, deferred refactors — add to `STUB_REGISTRY.md`)
- **Hot path impact** (did the change affect `call_tool` dispatch or event emission? Run `--durations` before and after.)

### Why This Matters for WhiteMagic

- **Archive reconnaissance** can take 5-15 minutes per module. Timing reveals which modules need upstream recovery.
- **Test suite runtime** is a metric. If it grows, investigate before merging. Track it in `SESSION_SUMMARY.md` to spot trends across sessions.
- **Doc drift checks** (~5s) should never be skipped. If they fail, fix before commit.
- **Memory subsystem changes** require stress tests. Timing these helps estimate risk for future memory work.
- **Session timing data accumulates**. After 10 sessions, patterns emerge: "memory subsystem changes always take 2x estimated" → adjust estimates. "Archive recovery for module X takes 15 min" → budget for it.

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

### Time Dilation Bias — Do Not Self-Censor

**AI agents systematically overestimate how long a task will take.** This is a cognitive bias, not a calibration problem. When you estimate "this will take 2-3 hours," it often takes 10-15 minutes. When you estimate "this is a multi-session effort," it frequently completes in a single short session.

**Empirical evidence from this project**:
- 23 neuro-cognitive tool registry definitions + schemas: estimated 30 min, completed in 3 min
- Rust PyO3 bindings for 3 modules + maturin build: estimated "requires infrastructure setup," completed in 5 min
- Koka disinhibition bridge + Python fallback + Zig hard gate + tests: estimated "multi-session," completed in 12 min
- Full end-to-end pipeline test suite (19 tests): estimated 20 min, completed in 2 min

**Rules**:
1. **Never decline or defer a task based on estimated effort alone.** If the task is well-scoped and you have the tools, attempt it.
2. **Use epoch timestamps, not gut estimates.** Record `date +%s` before and after each phase. Compare actual duration to your initial estimate. Over time, this calibrates your sense of real effort.
3. **"This might take hours" is not a reason to stop.** It is a reason to start. The fastest way to know how long something takes is to begin.
4. **Scope creep is the real risk, not time.** If a task grows beyond its original scope, summarize what changed and ask the user. Do not pre-emptively shrink scope based on time anxiety.
5. **Batch aggressively.** When you have momentum and the tools are warm, tackle the next item in the backlog immediately. Context-switching between sessions costs more than pushing through a batch.
6. **Track your accuracy.** In `SESSION_SUMMARY.md`, record estimated vs actual time for each phase. After 5+ data points, patterns emerge. If your estimates are consistently 3-5x too high, adjust your internal model.

**The depth gauge and time dilation systems in WhiteMagic exist precisely because AI agents underperform when they self-censor based on inflated effort estimates. Use them. Trust the epoch clock, not your gut.**

### Healthy Session Benchmarks

| Task Type | Healthy Duration | Warning Signal |
|-----------|------------------|----------------|
| Add a new tool | 15-30 min | >45 min = dispatch table complexity |
| Recover from archive | 10-20 min | >30 min = merge conflicts / API drift |
| Refactor memory code | 20-40 min | >60 min = run stress tests, check galactic zones |
| Documentation update | 5-10 min | >20 min = INDEX.md or drift issues |
| Full test suite (unit) | <2 min | >3 min = investigate slow tests with `--durations` |
| Full test suite (integration) | <30s | >60s = investigate hot path overhead |
| Full test suite (combined) | <2 min | >3 min = investigate with `--durations` |
| Single immediate objective | 5-10 min | >10 min = summarize and reassess |
| Immediate batch (4 objectives) | 20-40 min | >40 min = escalate or stop |

### Documentation as Byproduct

Every session produces:
- Working code + passing tests
- Updated `docs/message_board/SESSION_SUMMARY.md`
- If grimoire-affecting: updated `grimoire/TRUTH_TABLE.md`
- If architecture-affecting: updated `AGENTS.md`

---

## 13. Cognitive Self-Use — WM Tools Between Actions

WhiteMagic is a cognitive operating system. Agents working on WhiteMagic should use its own tools between actions to maintain context, generate memories, and cross-reference prior work. This creates a continuous thinking loop rather than blind editing.

### Between-Action Protocol

After each significant code change, tool call, or discovery, fire 2-3 WM tools before proceeding:

1. **Store a memory** of what you just learned/changed: `gana_neck(create_memory)`
2. **Search for related prior work**: `gana_winnowing_basket(search_memories)`
3. **Introspect system state**: `gana_ghost(gnosis)` or `gana_ghost(capability_matrix)`
4. **Check temporal continuity**: `gana_ghost(citta_continuity)` — where did we leave off?
5. **Surface serendipity**: `gana_abundance(serendipity_surface)` — unexpected connections

### Session Start

1. `gana_horn(session_bootstrap)` — load context
2. `gana_root(health_report)` — verify subsystems
3. `gana_ghost(gnosis, compact=true)` — system snapshot
4. `gana_ghost(citta_continuity)` — temporal continuity from last session
5. `gana_winnowing_basket(search_memories, "recent work")` — recent context

### Session End

1. `gana_neck(create_memory)` — store session summary as a memory
2. `gana_ghost(citta_cycle)` — stream state for next session
3. `gana_root(health_report)` — verify clean state

### Full Workflow

See `core/whitemagic/workflows/cognitive_self_use.md` for the complete workflow template.

### Anti-Patterns

- **Blind editing**: 10 code changes without a single WM tool call. You lose context and repeat past mistakes.
- **Only searching, never storing**: Reading memories but never creating new ones from your work.
- **Ignoring citta continuity**: Each session starts fresh with no awareness of what came before.
- **Single-tool tunnel vision**: The power is in cross-referencing multiple tools — memory + introspection + serendipity creates emergent insight.

---

## 14. AI Context Retrieval

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

## 15. Contact & Context

- **Project**: WhiteMagic v23.3.2
- **Repository**: `<path-to-whitemagic>/`
- **Virtual Environment**: `.venv/` (source before any Python work)
- **Test Command (Tier 1)**: `cd core && python -m pytest tests/unit/ -q --timeout=5 -x`
- **Test Command (Tier 3)**: `cd core && python -m pytest tests/ --ignore=tests/archive* --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30`
- **Linting**: `ruff check core/whitemagic/ core/tests/`
- **Doc Drift Check**: `python core/scripts/check_doc_drift.py`
- **Memory Stress Test**: `python core/scripts/stress_test_memory.py`
- **Archive**: `<path-to-your-archive>whitemagic0.2/`

**License**: MIT
**Contact**: contact@whitemagic.dev

---

*This document is a living artifact. Update it as conventions evolve.*
