"""MCP Tool Annotations — derivation policy and aggregation (P9.3).

Single source of truth for MCP ``ToolAnnotations`` across WhiteMagic.

The MCP spec (2025-03-26+) defines five annotation fields. Absent fields
default to worst-case client assumptions (non-read-only, destructive,
non-idempotent, open-world), causing confirmation prompts on every call.
WhiteMagic's canonical contract already knows each tool's safety
(READ/WRITE/DELETE, P1) and karmic effects (PURE/LOCAL_WRITE/NETWORK/
DESTRUCTIVE/OBSERVATION, MandalaOS), so annotations are **generated from
ground truth** here rather than hand-maintained.

Policy:
    title           = humanized tool name (explicit override wins)
    readOnlyHint    = safety READ and effects ⊆ {PURE, OBSERVATION}
    destructiveHint = safety DELETE or DESTRUCTIVE effect present
    idempotentHint  = read-only tools; plus CURATED_IDEMPOTENT write tools
                      (content-hash dedup creates, by-ID overwrites)
    openWorldHint   = NETWORK effect present

Per-tool explicit ``ToolDefinition.annotations`` fields always win over
derived values (partial overrides merge field-by-field).
"""
from __future__ import annotations

from whitemagic.tools.tool_types import McpAnnotations, ToolDefinition, ToolSafety

# Write tools whose repeated invocation with identical arguments has no
# additional effect. Inclusion criteria (conservative — when in doubt, leave out):
#   - content-hash dedup (retry returns the existing record)
#   - by-ID full overwrite (retry writes identical state)
#   - set-by-key/upsert (retry sets the same value)
#   - reload-from-disk (retry loads the same files)
#   - reset-to-baseline (retry resets to the same state)
#   - clear/flush (retry finds nothing to clear)
#   - guard-flag start/stop (retry is a no-op due to running/stopped guard)
# Each entry must name the mechanism in a comment.
CURATED_IDEMPOTENT: frozenset[str] = frozenset(
    {
        # ── Content-hash dedup (retry returns existing record) ──
        "create_memory",  # content-hash dedup in UnifiedMemory.store()
        "remember",  # delegates to create_memory, same dedup
        "import_memories",  # merge_strategy="skip" default, skips existing
        "galaxy.ingest",  # file ingestion via remember(), content-hash dedup
        "galaxy.import",  # Arrow/JSON import via remember(), content-hash dedup
        # ── By-ID overwrite (retry writes identical state) ──
        "update_memory",  # by-ID field overwrite
        "memory_update",  # alias of update_memory, same handler
        "reconsolidation.update",  # by-ID reconsolidated field overwrite
        "state.update",  # current-state snapshot overwrite: identical state
        # ── Set-by-key / upsert (retry sets same value) ──
        "set_dharma_profile",  # sets _active_profile, retry sets same
        "tx_firewall.set_policy",  # dict overwrite by agent_id
        "sandbox.set_limits",  # dict overwrite by tool_name
        "ilp.configure",  # sets config fields, retry sets same
        "cognitive.set",  # sets _manual_override, retry sets same
        "governor_set_goal",  # sets current_goal + clears action_history
        "state.context",  # set-by-key: tracker.set_context(key, value)
        "galaxy.switch",  # sets active galaxy, retry sets same
        # ── Reload-from-disk (retry loads same files) ──
        "prompt.reload",  # reloads templates from disk
        "dharma.reload",  # reloads rules from disk
        "forge.reload",  # reloads extensions from disk
        # ── Reset-to-baseline (retry resets to same state) ──
        "neuro.reset",  # resets neuromodulator levels to baseline
        # ── Clear/flush (retry finds nothing to clear) ──
        "cache.flush",  # flushes stale entries, retry finds nothing
        "web_cache_clear",  # clears web cache, retry finds nothing
        # ── Backfill (retry finds nothing to update) ──
        "session.backfill",  # fills missing sequence numbers, no-op when done
        # ── Sleep consolidation (content-hash dedup on promoted memories) ──
        "session.consolidate",  # promotes turns via remember(), dedup
        "memory.consolidate",  # same mechanism
        "consolidation.run",  # runs consolidation cycle, dedup on promote
        # ── Pattern ingestion (dict overwrite by deterministic ID) ──
        "vuln.ingest_report",  # pattern_id from section index, dict overwrite
        # ── Start/stop (guard flag, retry is no-op) ──
        "autoswarm.stop",  # stops loop, no-op when already stopped
        "autoswarm.start",  # guards on _running flag, no-op if running
        "watcher_start",  # sets active=True, retry sets same
        "embedding.daemon_start",  # guards on _running flag, no-op if running
        "dream_start",  # guards on _running flag, no-op if running
        # ── Delete-by-ID (retry finds nothing to delete) ──
        "delete_memory",  # delete by memory_id, error if already gone
        "memory_delete",  # alias of delete_memory, same handler
        "dream.expire",  # soft delete by dream_id, not_found if expired
        "watcher_remove",  # dict delete by watcher_id, not_found if gone
        # ── File overwrite (retry writes identical content) ──
        "fast_write.write",  # p.write_text(content), full overwrite
        "fast_write.batch",  # delegates to fast_write.write per file
        # ── Upsert by key (retry sets same value) ──
        "wiki.update",  # _upsert_entry by entry_id, force=True
        "dilo_co.init",  # sets coordinator params (h, k_ratio, lr, lr_outer)
        "dharma.resolve_review",  # set review status by review_id, error if done
        # ── Get-or-create (retry returns existing) ──
        "garden_activate",  # get_garden(name) returns existing or creates
        # ── Content-hash dedup via remember() ──
        "scratchpad_finalize",  # converts scratchpad to memory via remember()
        # ── Pure reads misclassified as WRITE ──
        "karma.anchor_status",  # returns anchor_status(), pure read
        "karma.verify_anchor",  # blockchain read/verify, no state change
        "model.optimize_status",  # returns get_status(), pure read
        "network_state.status",  # returns get_status(), pure read
        "salience.spotlight",  # returns current spotlight, pure read
        "pattern.resolve",  # looks up proven resolution, pure read
        "starter_packs",  # routes to list/get/suggest, all pure reads
        "starter_packs.get",  # get_pack(), pure read
        "starter_packs.list",  # list_packs(), pure read
        "starter_packs.suggest",  # suggest_pack(), pure read
        "garden_list_files",  # lists garden files, pure read
        "garden_list_functions",  # lists garden functions, pure read
        "wiki.scan",  # scans for doc drift, pure read
        "export_memories",  # exports data to JSON/CSV/MD, pure read
        "windsurf.export_all",  # exports sessions, pure read
        "emergence.scan",  # scans for emergent patterns, pure read
        "narrative.compress",  # pure computation, no state change
        "entity_resolve",  # resolves mentions to canonical entities, pure read
        # ── Upsert by ID (retry sets same status) ──
        "task.complete",  # sets task.status by task_id, retry sets same
        "swarm.complete",  # sets subtask status by plan_id+task_id, retry sets same
        "reconsolidation.mark",  # marks labile by memory_id, upsert in _labile dict
        # ── Content-hash dedup via remember() ──
        "windsurf.ingest",  # ingests sessions via remember(), dedup
        "windsurf.sync",  # incremental sync via remember(), dedup
        # ── Process unprocessed (retry finds nothing) ──
        "embedding.daemon_process",  # processes pending embeddings, no-op when done
        # ── Deterministic computation (retry produces same result) ──
        "cache.tune",  # auto_tune_ttls(), deterministic
        # ── Pure reads misclassified as WRITE (batch 4) ──
        "hermit.assess",  # assesses privacy exposure, pure read
        "garden_resolve",  # resolves virtual path to physical, pure read
        "satkona.fuse",  # fuses perspectives, pure computation
        # ── Upsert by ID (batch 4) ──
        "hermit.withdraw",  # sets privacy level, retry sets same
        "hermit.resolve",  # resolves conflict by conflict_id, upsert
        "network_state.resolve",  # resolves proposal by proposal_id, upsert
        # ── Index rebuild (retry overwrites with same content) ──
        "fragment.index",  # builds/updates Fragment index, overwrites existing
    }
)


def humanize(tool_name: str) -> str:
    """'create_memory' -> 'Create Memory'; 'galaxy.search' -> 'Galaxy Search'."""
    return tool_name.replace(".", " ").replace("_", " ").title()


def derive_annotations(
    tool_name: str, safety: ToolSafety, effect_names: set[str]
) -> McpAnnotations:
    """Derive annotations from safety classification and karmic effect names.

    Pure policy function — no I/O, no registry access. ``effect_names`` are
    EffectType member names (e.g. {"PURE"}, {"NETWORK", "LOCAL_WRITE"}).
    """
    read_only = safety == ToolSafety.READ and effect_names <= {"PURE", "OBSERVATION"}
    destructive = safety == ToolSafety.DELETE or "DESTRUCTIVE" in effect_names
    idempotent = read_only or tool_name in CURATED_IDEMPOTENT
    open_world = "NETWORK" in effect_names
    return McpAnnotations(
        title=humanize(tool_name),
        read_only=read_only,
        destructive=destructive,
        idempotent=idempotent,
        open_world=open_world,
    )


def resolve_annotations(tool_def: ToolDefinition) -> McpAnnotations:
    """Resolve the effective annotations for a tool definition.

    Explicit ``tool_def.annotations`` fields win; unset fields fall back to
    the derivation policy (safety + effect registry).
    """
    try:
        from whitemagic.dharma.effect_registry import get_declared_effects

        effect_names = {e.effect_type.name for e in get_declared_effects(tool_def.name)}
    except Exception:  # noqa: BLE001 — derivation must never break schema emission
        effect_names = set()

    derived = derive_annotations(tool_def.name, tool_def.safety, effect_names)
    explicit = tool_def.annotations
    if explicit is None:
        return derived
    return McpAnnotations(
        title=explicit.title if explicit.title is not None else derived.title,
        read_only=(
            explicit.read_only if explicit.read_only is not None else derived.read_only
        ),
        destructive=(
            explicit.destructive
            if explicit.destructive is not None
            else derived.destructive
        ),
        idempotent=(
            explicit.idempotent
            if explicit.idempotent is not None
            else derived.idempotent
        ),
        open_world=(
            explicit.open_world
            if explicit.open_world is not None
            else derived.open_world
        ),
    )


def aggregate_annotations(
    name: str, children: list[McpAnnotations]
) -> McpAnnotations:
    """Aggregate child tool annotations for a router tool (Gana meta-tool).

    A router is only as safe as its most permissive child:
    - readOnlyHint: ALL children read-only
    - destructiveHint: ANY child destructive
    - idempotentHint: ALL children idempotent
    - openWorldHint: ANY child open-world
    Empty child list -> conservative worst case (all False).
    """
    if not children:
        return McpAnnotations(
            title=humanize(name),
            read_only=False,
            destructive=False,
            idempotent=False,
            open_world=False,
        )
    return McpAnnotations(
        title=humanize(name),
        read_only=all(c.read_only for c in children),
        destructive=any(c.destructive for c in children),
        idempotent=all(c.idempotent for c in children),
        open_world=any(c.open_world for c in children),
    )
