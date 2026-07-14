# agent.list

**Category**: agent | **Safety**: read
**Gana**: `gana_girl`

## Description

List registered agents with optional active-only and capability filters

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "only_active": {
      "type": "boolean",
      "default": false,
      "description": "Only show active agents"
    },
    "capability": {
      "type": "string",
      "description": "Filter by capability"
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
    "agent.list",
    {"only_active": false, "capability": "Filter by capability", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
