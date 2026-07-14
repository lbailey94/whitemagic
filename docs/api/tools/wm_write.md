# wm_write

**Category**: memory | **Safety**: write
**Gana**: `gana_neck`

## Description

Unified write interface — auto-selects best strategy or uses explicit mode. Modes: auto, memory (full enrichment), scratchpad (ephemeral), file (atomic), neural (neural store), dream (artifact), oms (.mem package). Memory mode enables: surprise gate, holographic coords, embeddings, entity extraction — unlike handle_create_memory which disables them.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "content": {
      "type": "string",
      "description": "Content to write (required)"
    },
    "title": {
      "type": "string",
      "description": "Title for the content"
    },
    "mode": {
      "type": "string",
      "enum": [
        "auto",
        "memory",
        "scratchpad",
        "file",
        "neural",
        "dream",
        "oms"
      ],
      "default": "auto",
      "description": "Write strategy. 'auto' detects from args."
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Tags for memory mode"
    },
    "memory_type": {
      "type": "string",
      "enum": [
        "short_term",
        "long_term",
        "emotional",
        "narrative",
        "symbolic",
        "collective",
        "immune",
        "pattern"
      ],
      "default": "short_term",
      "description": "Memory type for memory mode"
    },
    "importance": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "default": 0.5,
      "description": "Importance score"
    },
    "emotional_valence": {
      "type": "number",
      "minimum": -1.0,
      "maximum": 1.0,
      "default": 0.0,
      "description": "Emotional valence (-1 negative, +1 positive)"
    },
    "metadata": {
      "type": "object",
      "description": "Additional metadata"
    },
    "auto_embed": {
      "type": "boolean",
      "default": true,
      "description": "Auto-generate embedding for memory mode"
    },
    "enable_surprise_gate": {
      "type": "boolean",
      "default": true,
      "description": "Enable surprise-gated ingestion for memory mode"
    },
    "enable_entity_extraction": {
      "type": "boolean",
      "default": true,
      "description": "Auto-extract entities for memory mode"
    },
    "enable_holographic_index": {
      "type": "boolean",
      "default": true,
      "description": "Auto-compute 5D holographic coords for memory mode"
    },
    "is_private": {
      "type": "boolean",
      "default": false,
      "description": "Mark as private (excluded from MCP responses)"
    },
    "model_exclude": {
      "type": "boolean",
      "default": false,
      "description": "Exclude from AI model context windows"
    },
    "path": {
      "type": "string",
      "description": "File path for file mode"
    },
    "scratchpad_id": {
      "type": "string",
      "description": "Scratchpad ID for scratchpad mode"
    },
    "dream_type": {
      "type": "string",
      "description": "Dream artifact type for dream mode (e.g. 'bridge')"
    },
    "request_id": {
      "type": "string",
      "description": "Optional caller-provided request id for tracing. If omitted, a UUID is generated."
    },
    "idempotency_key": {
      "type": "string",
      "description": "Optional idempotency key. For write tools, retries with the same key will replay prior results."
    },
    "dry_run": {
      "type": "boolean",
      "description": "If true, do not perform writes; return an execution preview when possible.",
      "default": false
    },
    "now": {
      "type": "string",
      "description": "Optional ISO timestamp override for deterministic evaluation/replay (best-effort)."
    }
  },
  "required": [
    "content"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "wm_write",
    {"content": "Content to write (required)", "title": "Title for the content", "mode": "Write strategy. 'auto' detects from args.", "tags": [], "memory_type": "Memory type for memory mode", "importance": 0.5, "emotional_valence": 0.0, "auto_embed": true, "enable_surprise_gate": true, "enable_entity_extraction": true, "enable_holographic_index": true, "is_private": false, "model_exclude": false, "path": "File path for file mode", "scratchpad_id": "Scratchpad ID for scratchpad mode", "dream_type": "Dream artifact type for dream mode (e.g. 'bridge')", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
