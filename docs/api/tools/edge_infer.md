# edge_infer

**Category**: edge | **Safety**: read
**Gana**: `gana_turtle_beak`

## Description

Rule-based edge inference (no API calls)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Query to process locally"
    },
    "mode": {
      "type": "string",
      "enum": [
        "auto",
        "fast",
        "explore",
        "deep",
        "memory_augmented"
      ],
      "default": "auto"
    },
    "ground_in_memory": {
      "type": "boolean",
      "description": "Use memory for RAG-style context",
      "default": false
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
    "query"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "edge_infer",
    {"query": "Query to process locally", "mode": "example", "ground_in_memory": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
