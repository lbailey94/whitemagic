# topological.decode

**Category**: metrics | **Safety**: read
**Gana**: `gana_three_stars`

## Description

Decode topologically encoded data with error correction. Recovers original data from redundant encoding.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "encoded": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "description": "Topologically encoded data"
    },
    "original_length": {
      "type": "integer",
      "description": "Length of original data"
    },
    "n_redundant": {
      "type": "integer",
      "default": 3,
      "description": "Number of redundant copies used in encoding"
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
    "encoded",
    "original_length"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "topological.decode",
    {"encoded": [], "original_length": 10, "n_redundant": 3, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
