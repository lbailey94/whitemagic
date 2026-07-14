# drive.event

**Category**: introspection | **Safety**: write
**Gana**: `gana_ghost`

## Description

Feed an event into the Emotion & Drive Core to update drive levels (e.g. tool_success, novelty_detected, dharma_violation).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "event_type": {
      "type": "string",
      "description": "Event type (tool_success, tool_error, novelty_detected, dharma_violation, etc.)."
    },
    "data": {
      "type": "object",
      "description": "Optional event data. Include 'score' (0-1) to scale the effect."
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
    "event_type"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "drive.event",
    {"event_type": "Event type (tool_success, tool_error, novelty_dete", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
