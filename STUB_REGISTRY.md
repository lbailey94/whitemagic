# STUB_REGISTRY.md — Technical Debt Tracker

Tracks every `NotImplementedError`, placeholder, and structural stub in the codebase.
Each entry makes technical debt visible and trackable, rather than hidden in code.

This file is the **single source of truth** for stub allowlisting. The
`core/scripts/stub_allowlist.json` file is auto-generated from the Active Stubs
table below — do not edit it directly.

## Active Stubs

| Module | Location | Reason | Planned Date | Added |
|--------|----------|--------|--------------|-------|
| `inference/unified_embedder.py` | `:154:_encode_mojo_gpu` | Mojo compiler unavailable (removed v23.2.0) | When Mojo compiler ships | 2026-04-16 |
| `tools/handlers/misc.py` | `:10:_stub` | Intentional test stub handler | Never (test fixture) | 2026-04-16 |
| `run_mcp.py` | `:32:startup` | MCP startup hook — deferred to lean server | v24.0.1 | 2026-04-16 |
| `run_mcp.py` | `:37:shutdown` | MCP shutdown hook — deferred to lean server | v24.0.1 | 2026-04-16 |
| `core/memory/akashic.py` | `:112:_save_field` | Legacy method — seeds now persisted individually | Never (legacy) | 2026-06-28 |
| `core/memory/backends/base.py` | `:73:find_by_content_hash` | Abstract base — optional override, returns None by default | Never (interface) | 2026-07-07 |
| `core/memory/backends/base.py` | `:77:store_coords` | Abstract base — optional override, no-op by default | Never (interface) | 2026-07-07 |
| `core/plugin/base.py` | `:31:deactivate` | Plugin base — intentional empty override | Never (interface) | 2026-06-28 |
| `core/plugin/base.py` | `:34:configure` | Plugin base — intentional empty override | Never (interface) | 2026-06-28 |
| `embeddings/__init__.py` | `:32:get_embedding_provider` | Local provider not yet available, OpenAI provider works | When local models ship | 2026-07-03 |
| `interfaces/chat.py` | `:1050:stop_server` | Ollama manages its own lifecycle — no-op is correct | Never (design) | 2026-07-07 |
| `interfaces/terminal/__init__.py` | `:23:__getattr__` | Lazy import — stub docstring | Never (lazy import pattern) | 2026-06-28 |
| `mesh/proto/mesh_pb2_grpc.py` | `:59:BroadcastSignal` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `mesh/proto/mesh_pb2_grpc.py` | `:65:BroadcastHologram` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `mesh/proto/mesh_pb2_grpc.py` | `:71:DiscoverPeers` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `mesh/proto/mesh_pb2_grpc.py` | `:258:CallTool` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `mesh/proto/mesh_pb2_grpc.py` | `:265:CittaStream` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `mesh/proto/mesh_pb2_grpc.py` | `:272:CreateSession` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `mesh/proto/mesh_pb2_grpc.py` | `:279:ResumeSession` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `mesh/proto/mesh_pb2_grpc.py` | `:285:DreamEvents` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `mesh/proto/mesh_pb2_grpc.py` | `:292:Telemetry` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `mesh/proto/mesh_pb2_grpc.py` | `:299:DaemonStatus` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `mesh/proto/mesh_pb2_grpc.py` | `:306:DaemonShutdown` | Auto-generated gRPC stub | Never (generated) | 2026-07-07 |
| `plugins/base.py` | `:48:on_load` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `plugins/base.py` | `:57:on_unload` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `plugins/base.py` | `:118:on_memory_created` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `plugins/base.py` | `:126:on_memory_updated` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `plugins/base.py` | `:134:on_memory_deleted` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `plugins/base.py` | `:151:set_config` | Plugin hook — intentional empty override | Never (interface) | 2026-06-28 |
| `root_modules/comprehensive_review.py` | `:26:__init__` | Constructor — stub docstring (fast mode) | Never (cosmetic) | 2026-06-28 |

## Resolved Stubs

| Module | Location | Resolution | Resolved |
|--------|----------|------------|----------|
| `core/consciousness/continuous_audit.py` | `:258:_fix_issue` | Implemented — handles empty dirs, missing __init__, stub fixes | 2026-07-03 |
| `core/evolution/adaptive_system.py` | `:161:_optimize_pathway` | Implemented — audit trail in rollback_history, approval-gated | 2026-07-07 |
| `core/evolution/adaptive_system.py` | `:167:_strengthen_pathway` | Implemented — audit trail in rollback_history, approval-gated | 2026-07-07 |
| `core/intelligence/synthesis/kaizen_engine.py` | `:200:_analyze_codebase` | Implemented — runs STRATA analysis on codebase | 2026-07-03 |
| `core/intelligence/synthesis/title_generator.py` | `:62:_generate_evocative_name` | Intentional no-op — LLM bridge not re-wired (v22.2.0), falls through to deterministic strategies | 2026-07-03 |
| `codex/__init__.py` | `:99:embed` | Implemented — uses EmbeddingEngine with pseudo-embed fallback | 2026-07-07 |
| `codex/__init__.py` | `:112:index` | Implemented — cosine similarity graph + Louvain clustering | 2026-07-07 |
| `codex/__init__.py` | `:125:export` | Implemented — writes sphere-nodes.json, manifest.json, search-index.json | 2026-07-07 |
| `cli/lazy_groups.py` | `:92:_create_missing_dep_command` | Fixed — docstring no longer triggers stub checker | 2026-07-07 |
| `inference/router.py` | `:572:_cloud_handler` | Fixed — docstring no longer triggers stub checker, intentional fallback | 2026-07-07 |
| `tools/gana_forge.py` | `:124:_compute_manifest_signature` | Already implemented — HMAC-SHA256 with vault key, stale registry entry | 2026-07-07 |
| `tools/handlers/anomaly.py` | `:20:handle_anomaly_check` | Already implemented — docstring fixed to remove stub keyword | 2026-07-07 |
| `tools/strata/checkers/stubs.py` | `:213:_is_stub_body` | Fixed — docstring no longer triggers stub checker | 2026-07-07 |

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
