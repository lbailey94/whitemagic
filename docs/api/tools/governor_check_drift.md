# governor_check_drift

**Category**: governor | **Safety**: read
**Gana**: `gana_star`

## Description

Check if an action drifts from the goal

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "description": "Action to check",
      "default": "read"
    },
    "goal": {
      "type": "string",
      "description": "Goal to check against"
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
    "governor_check_drift",
    {"action": "Action to check", "goal": "Goal to check against", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
