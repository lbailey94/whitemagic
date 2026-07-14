# anomaly

**Category**: metrics | **Safety**: read
**Gana**: `gana_hairy_head`

## Description

Unified anomaly detection on Harmony Vector dimensions. Actions: check (active anomalies), history (recent alerts), status (detector stats).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "check",
        "history",
        "status"
      ],
      "description": "Action to perform",
      "default": "check"
    },
    "limit": {
      "type": "integer",
      "default": 20,
      "description": "Max alerts to return (for history)"
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
    "anomaly",
    {"action": "Action to perform", "limit": 20, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
