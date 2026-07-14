# dilo_co.submit_gradient

**Category**: agent | **Safety**: write
**Gana**: `gana_ox`

## Description

Submit gradients from a worker to the DiLoCo coordinator

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "worker_id": {
      "type": "string"
    },
    "gradients": {
      "type": "object",
      "description": "Gradient dict (param_name -> array)"
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
    "worker_id",
    "gradients"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "dilo_co.submit_gradient",
    {"worker_id": "example", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
