# rust_similarity

**Category**: system | **Safety**: read
**Gana**: `gana_root`

## Description

Calculate text similarity using Rust SIMD (50x faster)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "text1": {
      "type": "string"
    },
    "text2": {
      "type": "string"
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
    "text1",
    "text2"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "rust_similarity",
    {"text1": "example", "text2": "example", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
