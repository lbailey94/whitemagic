# session.continuity

**Category**: session | **Safety**: read
**Gana**: `gana_heart`

## Description

Get cross-session continuity — recent turns from the previous session for context injection on reconnect.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "n": {
      "type": "integer",
      "default": 10,
      "description": "Number of turns from previous session"
    },
    "session_id": {
      "type": "string",
      "description": "Current session ID (to exclude from search)"
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
    "session.continuity",
    {"n": 10, "session_id": "Current session ID (to exclude from search)", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
