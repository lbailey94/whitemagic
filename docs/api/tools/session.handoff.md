# session.handoff

**Category**: session | **Safety**: write
**Gana**: `gana_heart`

## Description

Unified cross-device session handoff. Actions: transfer (send session to another device), accept (receive handoff), list (browse handoffs).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "transfer",
        "accept",
        "list"
      ],
      "description": "Action to perform."
    },
    "session_id": {
      "type": "string",
      "description": "Session to hand off (for transfer)."
    },
    "target_device": {
      "type": "string",
      "description": "Target hostname or 'any' (for transfer).",
      "default": "any"
    },
    "message": {
      "type": "string",
      "description": "Message for receiver (for transfer)."
    },
    "handoff_id": {
      "type": "string",
      "description": "Handoff package ID (for accept)."
    },
    "limit": {
      "type": "integer",
      "description": "Max results (for list).",
      "default": 20
    },
    "filter_status": {
      "type": "string",
      "description": "Filter by status (for list)."
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
    "session.handoff",
    {"action": "Action to perform.", "session_id": "Session to hand off (for transfer).", "target_device": "Target hostname or 'any' (for transfer).", "message": "Message for receiver (for transfer).", "handoff_id": "Handoff package ID (for accept).", "limit": 20, "filter_status": "Filter by status (for list).", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
