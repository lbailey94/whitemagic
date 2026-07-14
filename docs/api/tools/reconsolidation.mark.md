# reconsolidation.mark

**Category**: memory | **Safety**: write
**Gana**: `gana_abundance`

## Description

Mark a retrieved memory as labile (modifiable). Within the 5-minute window, it can be updated with new context.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "memory_id": {
      "type": "string",
      "description": "Memory ID to mark labile"
    },
    "content": {
      "type": "string",
      "description": "Current memory content"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Current tags"
    },
    "query": {
      "type": "string",
      "description": "Query that triggered retrieval"
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
    "memory_id",
    "content"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "reconsolidation.mark",
    {"memory_id": "Memory ID to mark labile", "content": "Current memory content", "tags": [], "query": "Query that triggered retrieval", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
