# hermit.resolve

**Category**: security | **Safety**: write
**Gana**: `gana_room`

## Description

Resolve a mediation request — approve or deny unlock.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "approved": {
      "type": "boolean",
      "description": "Whether to approve the unlock.",
      "default": true
    },
    "resolver": {
      "type": "string",
      "description": "Who is resolving (default: system).",
      "default": "system"
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
    "hermit.resolve",
    {"approved": true, "resolver": "Who is resolving (default: system).", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
