# dream

**Category**: system | **Safety**: write
**Gana**: `gana_abundance`

## Description

Unified Dream Cycle control — background processing during idle time (consolidation, serendipity, kaizen, oracle, decay). Actions: start, stop, status, now.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "start",
        "stop",
        "status",
        "now"
      ],
      "description": "Action to perform"
    },
    "idle_threshold": {
      "type": "number",
      "description": "Seconds of idle before dreaming starts (for start)",
      "default": 120
    },
    "cycle_interval": {
      "type": "number",
      "description": "Seconds between dream phases (for start)",
      "default": 60
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
    "dream",
    {"action": "Action to perform", "idle_threshold": 120, "cycle_interval": 60, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
