# sangha_lock

**Category**: system | **Safety**: write
**Gana**: `gana_room`

## Description

Unified resource lock management for multi-agent coordination. Actions: acquire (lock resource), release (unlock), list (show active locks).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "acquire",
        "release",
        "list"
      ],
      "description": "Action to perform"
    },
    "resource": {
      "type": "string",
      "description": "Resource to lock/unlock (for acquire/release)"
    },
    "reason": {
      "type": "string",
      "description": "Lock reason (for acquire)"
    },
    "timeout": {
      "type": "integer",
      "default": 3600,
      "description": "Lock timeout seconds (for acquire)"
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
    "action"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "sangha_lock",
    {"action": "Action to perform", "resource": "Resource to lock/unlock (for acquire/release)", "reason": "Lock reason (for acquire)", "timeout": 3600, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
