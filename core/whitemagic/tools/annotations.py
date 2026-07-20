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
#   - content-hash dedup (retry returns the existing record), or
#   - by-ID full overwrite (retry writes identical state).
# Each entry must name the mechanism in a comment.
CURATED_IDEMPOTENT: frozenset[str] = frozenset(
    {
        "create_memory",  # content-hash dedup: retry returns existing memory
        "update_memory",  # by-ID field overwrite: retry writes identical state
        "state.update",  # current-state snapshot overwrite: identical state
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
