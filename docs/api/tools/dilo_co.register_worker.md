# dilo_co.register_worker

**Category**: agent | **Safety**: write
**Gana**: `gana_ox`

## Description

Register a worker to the DiLoCo Parcae pool

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "worker_id": {
      "type": "string"
    },
    "compute_capacity": {
      "type": "number",
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
    "worker_id"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "dilo_co.register_worker",
    {"worker_id": "example", "compute_capacity": 1.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
