# session.consolidate

**Category**: session | **Safety**: write
**Gana**: `gana_heart`

## Description

Sleep consolidation — promote important session turns (decisions, breakthroughs, errors) to the codex galaxy as long-term semantic knowledge.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session ID to consolidate"
    },
    "min_importance": {
      "type": "number",
      "default": 0.7,
      "description": "Minimum importance threshold for promotion"
    },
    "dry_run": {
      "type": "boolean",
      "default": false,
      "description": "If true, only report what would be promoted"
    },
    "request_id": {
      "type": "string",
      "description": "Optional caller-provided request id for tracing. If omitted, a UUID is generated."
    },
    "idempotency_key": {
      "type": "string",
      "description": "Optional idempotency key. For write tools, retries with the same key will replay prior results."
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
    "session.consolidate",
    {"session_id": "Session ID to consolidate", "min_importance": 0.7, "dry_run": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
