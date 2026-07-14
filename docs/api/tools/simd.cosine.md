# simd.cosine

**Category**: metrics | **Safety**: read
**Gana**: `gana_tail`

## Description

Compute cosine similarity between two vectors using Zig SIMD acceleration (Python fallback available)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "a": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "description": "First vector"
    },
    "b": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "description": "Second vector"
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
    "a",
    "b"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "simd.cosine",
    {"a": [], "b": [], "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
