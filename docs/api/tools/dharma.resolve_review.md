# dharma.resolve_review

**Category**: governance | **Safety**: write
**Gana**: `gana_straddling_legs`

## Description

Resolve a human review item from the escalation pipeline. Sets the human-assigned decision and score, marking the review as resolved.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "review_id": {
      "type": "string",
      "description": "The review ID to resolve"
    },
    "decision": {
      "type": "string",
      "enum": [
        "allow",
        "warn",
        "block"
      ]
    },
    "score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
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
    "review_id",
    "decision",
    "score"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "dharma.resolve_review",
    {"review_id": "The review ID to resolve", "decision": "example", "score": 1.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
