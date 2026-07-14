# session.replay

**Category**: session | **Safety**: read
**Gana**: `gana_heart`

## Description

Replay session turns — full chronological, selective (important turns only), or progressive (token-budgeted compact previews).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "mode": {
      "type": "string",
      "enum": [
        "full",
        "selective",
        "progressive"
      ],
      "default": "full"
    },
    "n": {
      "type": "integer",
      "default": 50,
      "description": "Max turns (full mode)"
    },
    "turn_types": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Filter by turn type (selective mode)"
    },
    "min_importance": {
      "type": "number",
      "default": 0.7,
      "description": "Min importance (selective mode)"
    },
    "token_budget": {
      "type": "integer",
      "default": 2000,
      "description": "Token budget (progressive mode)"
    },
    "session_id": {
      "type": "string",
      "description": "Session ID"
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
    "session.replay",
    {"mode": "example", "n": 50, "turn_types": [], "min_importance": 0.7, "token_budget": 2000, "session_id": "Session ID", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
