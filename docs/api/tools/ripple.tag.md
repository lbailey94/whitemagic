# ripple.tag

**Category**: memory | **Safety**: write
**Gana**: `gana_abundance`

## Description

Tag memories that co-activate within a ripple window for consolidation during sleep.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "memory_ids": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Memory IDs to tag as co-activated"
    },
    "emotional_weight": {
      "type": "number",
      "description": "Emotional salience weight 0-1 (default 1.0)",
      "default": 1.0
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
    "memory_ids"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "ripple.tag",
    {"memory_ids": [], "emotional_weight": 1.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
