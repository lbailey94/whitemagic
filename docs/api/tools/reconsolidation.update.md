# reconsolidation.update

**Category**: memory | **Safety**: write
**Gana**: `gana_abundance`

## Description

Update a labile memory with new context before reconsolidation.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "memory_id": {
      "type": "string",
      "description": "Memory ID to update"
    },
    "new_context": {
      "type": "string",
      "description": "Additional context to append"
    },
    "new_tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "New tags to merge"
    },
    "annotation": {
      "type": "string",
      "description": "Note about why the update happened"
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
    "memory_id"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "reconsolidation.update",
    {"memory_id": "Memory ID to update", "new_context": "Additional context to append", "new_tags": [], "annotation": "Note about why the update happened", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
