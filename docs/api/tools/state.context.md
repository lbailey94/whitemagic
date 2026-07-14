# state.context

**Category**: session | **Safety**: write
**Gana**: `gana_heart`

## Description

Get or set context values in the current work state. Without arguments, returns all context. With key+value, sets a context entry. With just key, gets a specific entry.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "key": {
      "type": "string",
      "description": "Context key"
    },
    "value": {
      "type": "string",
      "description": "Context value (omit to get, include to set)"
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
    "state.context",
    {"key": "Context key", "value": "Context value (omit to get, include to set)", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
