# swarm.resolve

**Category**: agent | **Safety**: read
**Gana**: `gana_ox`

## Description

Resolve a consensus vote using majority, unanimous, first_wins, or weighted strategy

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "topic_id": {
      "type": "string"
    },
    "strategy": {
      "type": "string",
      "enum": [
        "majority",
        "unanimous",
        "first_wins",
        "weighted"
      ],
      "default": "majority"
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
    "topic_id"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "swarm.resolve",
    {"topic_id": "example", "strategy": "example", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
