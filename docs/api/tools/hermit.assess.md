# hermit.assess

**Category**: security | **Safety**: write
**Gana**: `gana_room`

## Description

Assess threat level from signals (boundary violations, coercion, abuse). May trigger automatic state transition.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "signals": {
      "type": "object",
      "description": "Threat signals dict. Keys: boundary_violations (0-1), coercion_detected (bool), abuse_score (0-1), repeated_violations (bool), unauthorized_access (0-1), emotional_manipulation (0-1).",
      "default": {}
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
    "hermit.assess",
    {"request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
