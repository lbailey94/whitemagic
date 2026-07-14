# windsurf.full_steps

**Category**: archaeology | **Safety**: read
**Gana**: `gana_chariot`

## Description

Fetch complete step-by-step data for a single session via the language server API. Bypasses the 200K character transcript truncation. Requires Windsurf/Devin Desktop running.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "cascade_id": {
      "type": "string",
      "description": "The cascade trajectory ID to fetch steps for"
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
    "cascade_id"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "windsurf.full_steps",
    {"cascade_id": "The cascade trajectory ID to fetch steps for", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
