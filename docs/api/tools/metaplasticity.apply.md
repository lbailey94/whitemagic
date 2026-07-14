# metaplasticity.apply

**Category**: memory | **Safety**: write
**Gana**: `gana_extended_net`

## Description

Apply a strength modification to a memory, gated by its metaplasticity threshold.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "memory_id": {
      "type": "string",
      "description": "Memory ID to modify"
    },
    "delta": {
      "type": "number",
      "description": "Strength change to apply",
      "default": 0.0
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
    "metaplasticity.apply",
    {"memory_id": "Memory ID to modify", "delta": 0.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
