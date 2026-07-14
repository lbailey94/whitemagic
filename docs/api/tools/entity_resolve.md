# entity_resolve

**Category**: memory | **Safety**: write
**Gana**: `gana_abundance`

## Description

Run embedding-based entity resolution (dedup) on the memory store. Finds near-duplicate memories and merges them by reinforcing the canonical and pushing duplicates to FAR_EDGE.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "similarity_threshold": {
      "type": "number",
      "description": "Cosine similarity threshold (default: 0.92)",
      "default": 0.92
    },
    "batch_limit": {
      "type": "integer",
      "description": "Max pairs to evaluate (default: 500)",
      "default": 500
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
  }
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "entity_resolve",
    {"similarity_threshold": 0.92, "batch_limit": 500, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
