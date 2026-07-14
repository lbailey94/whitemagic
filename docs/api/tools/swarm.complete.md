# swarm.complete

**Category**: agent | **Safety**: write
**Gana**: `gana_ox`

## Description

Mark a subtask as completed or failed

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "plan_id": {
      "type": "string"
    },
    "task_id": {
      "type": "string"
    },
    "result": {
      "type": "string"
    },
    "success": {
      "type": "boolean",
      "default": true
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
    "plan_id",
    "task_id"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "swarm.complete",
    {"plan_id": "example", "task_id": "example", "result": "example", "success": true, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
