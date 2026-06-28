# STUB_REGISTRY.md — Technical Debt Tracker

Tracks every `NotImplementedError`, placeholder, and structural stub in the codebase.
Each entry makes technical debt visible and trackable, rather than hidden in code.

This file is the **single source of truth** for stub allowlisting. The
`core/scripts/stub_allowlist.json` file is auto-generated from the Active Stubs
table below — do not edit it directly.

## Active Stubs

| Module | Location | Reason | Planned Date | Added |
|--------|----------|--------|--------------|-------|
| `cli/lazy_groups.py` | `:92:_create_missing_dep_command` | CLI lazy group — missing dep handler is intentionally a stub | v24.0.0 | 2026-04-20 |
| `inference/unified_embedder.py` | `:154:_encode_mojo_gpu` | Mojo compiler unavailable (removed v23.2.0) | When Mojo compiler ships | 2026-04-16 |
| `tools/gana_forge.py` | `:124:_compute_manifest_signature` | Manifest signature hashing not yet wired | v23.4.0 | 2026-04-16 |
| `tools/handlers/misc.py` | `:9:_stub` | Intentional test stub handler | Never (test fixture) | 2026-04-16 |
| `run_mcp.py` | `:31:startup` | MCP startup hook — deferred to lean server | v24.0.0 | 2026-04-16 |
| `run_mcp.py` | `:36:shutdown` | MCP shutdown hook — deferred to lean server | v24.0.0 | 2026-04-16 |
| `codex/__init__.py` | `:99:embed` | CODEX embed — not yet implemented | v23.4.0 | 2026-06-28 |
| `codex/__init__.py` | `:112:index` | CODEX index — not yet implemented | v23.4.0 | 2026-06-28 |
| `codex/__init__.py` | `:125:export` | CODEX export — not yet implemented | v23.4.0 | 2026-06-28 |
| `core/consciousness/continuous_audit.py` | `:258:_fix_issue` | Issue fixer dispatcher not yet implemented | v23.4.0 | 2026-06-28 |
| `core/evolution/adaptive_system.py` | `:161:_optimize_pathway` | Adaptive pathway optimization — stub docstring | v23.4.0 | 2026-06-28 |
| `core/evolution/adaptive_system.py` | `:167:_strengthen_pathway` | Adaptive pathway strengthening — stub docstring | v23.4.0 | 2026-06-28 |
| `core/intelligence/synthesis/kaizen_engine.py` | `:200:_analyze_codebase` | Codebase analysis — stub docstring | v23.4.0 | 2026-06-28 |
| `core/intelligence/synthesis/title_generator.py` | `:62:_generate_evocative_name` | Evocative name generation — stub docstring | v23.4.0 | 2026-06-28 |
| `core/memory/akashic.py` | `:113:_save_field` | Legacy method — seeds now persisted individually | Never (legacy) | 2026-06-28 |
| `core/plugin/base.py` | `:31:deactivate` | Plugin base — intentional empty override | Never (interface) | 2026-06-28 |
| `core/plugin/base.py` | `:34:configure` | Plugin base — intentional empty override | Never (interface) | 2026-06-28 |
| `embeddings/__init__.py` | `:32:get_embedding_provider` | Provider factory — stub docstring | v23.4.0 | 2026-06-28 |
| `inference/router.py` | `:572:_cloud_handler` | Cloud inference handler — stub docstring | v23.4.0 | 2026-06-28 |
| `interfaces/terminal/__init__.py` | `:23:__getattr__` | Lazy import — stub docstring | Never (lazy import pattern) | 2026-06-28 |
| `plugins/base.py` | `:48:on_load` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `plugins/base.py` | `:57:on_unload` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `plugins/base.py` | `:118:on_memory_created` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `plugins/base.py` | `:126:on_memory_updated` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `plugins/base.py` | `:134:on_memory_deleted` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `plugins/base.py` | `:151:set_config` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `root_modules/comprehensive_review.py` | `:26:__init__` | Constructor — stub docstring (fast mode) | Never (cosmetic) | 2026-06-28 |
| `tools/handlers/anomaly.py` | `:20:handle_anomaly_check` | Handler — stub docstring | v23.4.0 | 2026-06-28 |
| `tools/strata/checkers/stubs.py` | `:213:_is_stub_body` | The checker itself — stub docstring (meta) | Never (self-referential) | 2026-06-28 |

## Resolved Stubs

| Module | Location | Resolution | Resolved |
|--------|----------|------------|----------|
| _(none yet)_ | | | |

---

## How to Use

1. **Adding a stub**: When you add `raise NotImplementedError(...)` or a placeholder return,
   add an entry to the "Active Stubs" table with the module, reason, and planned implementation date.
   Then run `python core/scripts/sync_stub_registry.py` to regenerate `stub_allowlist.json`.
2. **Resolving a stub**: When you implement the placeholder, move the entry to "Resolved Stubs"
   with the resolution description and date. Then run `python core/scripts/sync_stub_registry.py`.
3. **Reviewing stubs**: During session planning, check this file for stubs with past-due planned dates.
4. **Detecting untracked stubs**: Run `python core/scripts/check_stubs.py` — it will flag any
   `NotImplementedError` or empty body not listed in `stub_allowlist.json`.
5. **CI enforcement**: The `core-ci` GitHub Actions workflow runs `check_stubs.py` on every PR.
   Untracked stubs will fail CI.
