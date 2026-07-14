# swarm.vote

**Category**: agent | **Safety**: write
**Gana**: `gana_ox`

## Description

Record a vote from an agent on a consensus topic

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "topic_id": {
      "type": "string"
    },
    "agent_id": {
      "type": "string"
    },
    "value": {
      "type": "string"
    },
    "confidence": {
      "type": "number",
      "default": 1.0
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
    "topic_id",
    "agent_id",
    "value"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "swarm.vote",
    {"topic_id": "example", "agent_id": "example", "value": "example", "confidence": 1.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
