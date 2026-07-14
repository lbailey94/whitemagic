# task.route_smart

**Category**: agent | **Safety**: read
**Gana**: `gana_stomach`

## Description

Determine the optimal host for a task based on current system load across local and remote machines.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "task_type": {
      "type": "string",
      "description": "Type of task (compilation, ai_inference, etc.).",
      "default": "general"
    },
    "prefer_local": {
      "type": "boolean",
      "description": "Prefer local unless overloaded.",
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
  }
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "task.route_smart",
    {"task_type": "Type of task (compilation, ai_inference, etc.).", "prefer_local": true, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
