=== MESSAGE 0 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 1 - User ===
good evening! let's look over the codebase perfection doc together, see if there's anything we can improve in the plan (we should probably conduct extensive internal codebase and external online research first to inform our conclusions) and then we'll get started!

=== MESSAGE 2 - Assistant ===
Good evening! Let me start by reading the strategy doc, then we'll dig into the codebase and external research.

=== MESSAGE 3 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 4 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 5 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 6 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 7 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 8 - Assistant ===
Good, I've read the full document. Now let me conduct parallel research — internal codebase state and external best practices — to inform our review.

=== MESSAGE 9 - Tool ===
[CORTEX_STEP_TYPE_FIND_CODE_CONTEXT]

=== MESSAGE 10 - Tool ===
[CORTEX_STEP_TYPE_FIND_CODE_CONTEXT]

=== MESSAGE 11 - Tool ===
[CORTEX_STEP_TYPE_FIND_CODE_CONTEXT]

=== MESSAGE 12 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 13 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 14 - Assistant ===
Let me do a few more targeted searches — both internal and external.

=== MESSAGE 15 - Tool ===
[CORTEX_STEP_TYPE_FIND_CODE_CONTEXT]

=== MESSAGE 16 - Tool ===
[CORTEX_STEP_TYPE_FIND_CODE_CONTEXT]

=== MESSAGE 17 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 18 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 19 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 20 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 21 - Assistant ===
I've now completed extensive internal and external research. Let me synthesize my findings into a structured review.

---

# Strategy Document Review — Findings & Recommendations

## Research Summary

I examined the codebase internals (tool registry, dispatch table, conftest, config systems, architectural boundaries, background workers) and researched external best practices (MCP conformance standards, tool contract testing, dependency locking, test determinism, spec-driven contracts). Here's what I found and where the plan can be strengthened.

---

## A. Internal Codebase Findings (Validating the Plan's Diagnoses)

### 1. The Fallback READ Problem is Real and Located

`tool_catalog.py:227-235` still defaults unauthored tools to `ToolSafety.READ`:

```@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/tools/tool_catalog.py:227-235
    # Default to READ safety for dispatch-only tools without authored definitions.
    inferred_safety = (
        ToolSafety.WRITE if name in WRITE_TOOLS else ToolSafety.READ
    )
```

The `WRITE_TOOLS` set in `dispatch_core.py:20-54` is **manually maintained** — only 24 entries. With 832 dispatch entries and 476 authored definitions, ~356 tools get synthesized with default `READ` safety. The plan correctly identifies this as the highest-risk release blocker.

### 2. Architectural Boundary Violations Are Concrete

I found multiple core→tools imports the plan should explicitly inventory:

- **`fusions.py`** (core) → imports `whitemagic.tools.prat_mappings`, `whitemagic.tools.prat_resonance`
- **`researcher.py`** (core intelligence) → imports `whitemagic.tools.handlers.llama_tools`
- **`narrative_compressor.py`** (core dreaming) → imports `whitemagic.tools.handlers.llama_tools`
- **`galaxy_sync.py`** (core memory) → imports `whitemagic.tools.handlers.broker`
- **`recursive_loop.py`** (core evolution) → imports `whitemagic.tools.handlers.tool_bandit`
- **`lifecycle.py`** (core consciousness) → imports `whitemagic.tools.unified_api`
- **`apotheosis_engine.py`** (core consciousness) → imports `whitemagic.tools.dispatch_table`

These are the exact "port" candidates P4.1 needs — inference port, event port, broker port, dispatch port.

### 3. Two Competing Config Systems

There are **two configuration systems** with different env var prefixes:
- **`daemon_config.py`**: Dataclass-based, uses `WM_*` prefix, covers ~10 vars
- **`manager.py`**: Pydantic-based, uses `WHITEMAGIC_*` prefix, covers ~8 vars

Meanwhile, ~220 `WM_*` symbols are accessed via direct `os.getenv()` across the codebase. P4.4 should explicitly call out this dual-system conflict.

### 4. Test Isolation is Fragile but Improving

The `conftest.py` manually resets **~40+ singletons** in `_reset_singletons()`. The GanYingBus global worker thread explicitly **cannot be nulled** (comment at line 100-104 explains why). Some tests (e.g., `test_consciousness_loop.py:225`) override `WM_STATE_ROOT` locally without using the `fresh_state_root` fixture. The `test_galactic.py:233-248` `substrate_path` fixture reads from the **real production DB**.

### 5. Blanket `noqa: BLE001` Suppressions

Multiple core files have blanket broad-catch suppressions: `_consolidated.py`, `dream_cycle.py`, `dispatch_core.py`, `daemon_config.py`, `boot.py`. P7.2 should specifically target these.

---

## B. External Research Findings (Informing Plan Improvements)

### 1. MCP Conformance is Now a Real Standard

The MCP ecosystem now has:
- **`mcp-conform`**: Author-side conformance linter that checks tool annotations, schema hygiene, tool-poisoning patterns. Missing annotations are the **#1 cause of rejection** from ChatGPT/Claude app directories.
- **MCP spec rule**: Clients **must assume worst case** (destructive, open-world) when tool hints are missing — this directly validates P1.2's fail-closed approach.
- **MCP Tool Cards**: Per-tool safety profiles with `side_effect_class`, `reversibility`, `PII/secret exposure` — more granular than WM's READ/WR
<truncated 3493 bytes>
del.

10. **Call out the conftest singleton list**: P3.1 should explicitly reference the ~40-entry manual singleton reset in `conftest.py:160-241` as a primary target for replacement with the centralized `reset_all_singletons()` registry.

11. **Call out `substrate_path` fixture**: P3.2 should reference `test_galactic.py:233-248` as an example of tests reading from the real production DB — this is a determinism violation.

12. **Call out local WM_STATE_ROOT overrides**: P3.2 should reference tests like `test_consciousness_loop.py:225` that override `WM_STATE_ROOT` without using the `fresh_state_root` fixture.

### Phase 4 Improvements

13. **Inventory the specific boundary violations**: P4.1 should list the 7 concrete core→tools imports I found above as the baseline violation set, grouped by needed port (inference, event, broker, dispatch).

14. **Call out the dual config system**: P4.4 should explicitly name `daemon_config.py` (WM_* prefix) vs `manager.py` (WHITEMAGIC_* prefix) as a consolidation target.

### Phase 5 Improvements

15. **Reference the raw sqlite3.connect() issue**: P5.2 should reference the known 113 raw `sqlite3.connect()` calls (from prior audit) as a backend-boundary target. The `safe_connect()` helper exists but migration is incomplete.

### Phase 7 Improvements

16. **Target blanket noqa suppressions**: P7.2 should specifically call out the `# ruff: noqa: BLE001` blanket suppressions in `_consolidated.py`, `dream_cycle.py`, `dispatch_core.py`, `daemon_config.py`, `boot.py` as high-priority broad-catch targets.

17. **Add the config-system duplicate to P7.5**: The two config systems with different env var prefixes are a duplicate group that should be classified and consolidated.

### Phase 8 Improvements

18. **Add uv to CI lanes**: Lane A should use `uv sync --frozen --no-dev` for fast install. Lane C should use `uv sync --frozen` for full install. The `astral-sh/setup-uv` GitHub Action should be referenced.

19. **Add MCP conformance to Lane A**: Run the MCP annotation/schema conformance check as a fast-gate item.

20. **Add leak detection to Lane A**: `pytest --hygiene-strict` should be in the fast gate.

### Phase 9 Improvements

21. **Add MCP registry publishing checklist**: P9.3 should include `server.json` manifest, reverse-DNS namespace, tool annotations, and `mcp-conform` compliance as release requirements.

22. **Add rebuild test concept**: P9.1 should mention the "rebuild test" as a documentation quality metric — can a fresh agent session regenerate the tool contract from docs?

### Structural Improvements

23. **Add a DAG, not just linear sequence**: Section 11 shows a linear sequence, but some phases can overlap. P7's ruff ratchet can start during P1. P2's version repair can start during P0. Consider expressing dependencies as a DAG.

24. **Add a "quick wins" section**: Identify packets that can be done in <1 hour to build momentum: (a) adopt uv, (b) add pytest-hygiene, (c) add pytest-randomly, (d) fix the `substrate_path` fixture, (e) merge the two config env var prefixes.

25. **Date the audit baseline**: The audit numbers (860 tools, 9,429 tests, etc.) should have a date and git commit hash. They're already marked as needing recalculation, but anchoring them to a specific point in time makes the recalculation verifiable.

---

## D. What the Plan Gets Right

The plan is genuinely excellent in several areas that shouldn't be changed:

- **The central diagnosis** ("competing sources of truth") is exactly right and confirmed by the codebase
- **The change discipline rules** (Section 3) are best-in-class for solo+model development
- **The smaller-model session protocol** (Section 12) is well-designed for delegation
- **The "what not to do" section** (Section 16) prevents the most likely failure modes
- **The feature freeze through Phase 3** is the right call
- **The closing guidance** about not making WM smaller for conventionality is important

---

## E. Recommended Next Steps

Shall I:

=== MESSAGE 22 - Tool ===
[CORTEX_STEP_TYPE_ASK_USER_QUESTION]

=== MESSAGE 23 - Assistant ===
Let me re-read the strategy document to get exact text for the edits.

=== MESSAGE 24 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 25 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 26 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 27 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 28 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 29 - Assistant ===
Now I'll apply all 25 recommendations. I'll break this into multiple edit batches to keep each manageable.

=== MESSAGE 30 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 31 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 32 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 33 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 34 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 35 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 36 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 37 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 38 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 39 - Assistant ===
Now apply P4.1 and P4.4 edits:

=== MESSAGE 40 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 41 - Assistant ===
Now apply P5.2, P7.2, P7.5 edits:

=== MESSAGE 42 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 43 - Assistant ===
Now apply P8 (CI lanes) and P9 edits:

=== MESSAGE 44 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 45 - Assistant ===
Now apply the structural improvements — DAG note, quick wins section, and freezegun mention:

=== MESSAGE 46 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 47 - Assistant ===
Now add the quick wins section. Let me find the right insertion point — after the closing guidance section:

=== MESSAGE 48 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 49 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 50 - Assistant ===
All 25 recommendations have been applied. Let me verify the final state of the document:

=== MESSAGE 51 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 52 - Assistant ===
All 25 recommendations applied. The document grew from 1,049 to 1,134 lines. Here's a summary of what changed:

**Phase 0:**
- Dated the audit baseline (2026-07-17)
- Added dual-config-system and MCP annotation gaps to P0.2 known issues
- Added leak detection, test randomization, and MCP conformance to P0.3 baseline gates

**Section 4 (Architecture):**
- Added MCP spec annotations, Tool Card fields, and evidence requirements to canonical tool contract

**Phase 1:**
- Called out `tool_catalog.py:227-235` as the specific fallback READ location
- Added structured negative contract tests (permission, timeout, duplicate, schema version, tenant mismatch, missing approval)

**Phase 2:**
- Replaced "Decide whether uv is canonical" with decisive adoption of `uv` with rationale

**Phase 3:**
- Named `pytest-hygiene`, `pytest-randomly`, `freezegun` as specific tools
- Called out conftest ~40-entry singleton reset list, `substrate_path` fixture, and local `WM_STATE_ROOT` overrides

**Phase 4:**
- Inventoried 7 concrete core→tools boundary violations grouped by port type
- Called out dual config system (`daemon_config.py` vs `manager.py`) with consolidation recommendation

**Phase 5:**
- Referenced 113 raw `sqlite3.connect()` calls as primary backend-boundary target

**Phase 7:**
- Listed 5 specific blanket `noqa: BLE001` suppression files
- Added config-system duplicate group to P7.5

**Phase 8:**
- Added `uv sync` commands, MCP conformance, and leak detection to CI lanes
- Added `astral-sh/setup-uv` GitHub Action reference

**Phase 9:**
- Added rebuild test concept to P9.1
- Added MCP registry publishing checklist to P9.3

**Section 11:**
- Added parallelization opportunities (DAG note) for P7/P1, P2/P0, P3.2/P3.1, P9.1/P0

**New Section 18:**
- Quick wins list (6 items, each < 1 hour)