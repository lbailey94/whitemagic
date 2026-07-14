# session.record

**Category**: session | **Safety**: write
**Gana**: `gana_heart`

## Description

Record a conversation turn (user message or AI response) as a persistent session memory with sequence number for chronological recall.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "role": {
      "type": "string",
      "enum": [
        "user",
        "ai"
      ],
      "description": "Who said this turn"
    },
    "content": {
      "type": "string",
      "description": "The message content"
    },
    "turn_type": {
      "type": "string",
      "enum": [
        "message",
        "decision",
        "breakthrough",
        "question",
        "answer",
        "code_change",
        "error",
        "summary",
        "context"
      ],
      "default": "message"
    },
    "importance": {
      "type": "number",
      "default": 0.5,
      "description": "0.0-1.0 importance score"
    },
    "emotional_valence": {
      "type": "number",
      "default": 0.0,
      "description": "-1.0 to 1.0 emotional tone"
    },
    "session_id": {
      "type": "string",
      "description": "Session ID (auto-generated if omitted)"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Additional tags"
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
    "role",
    "content"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "session.record",
    {"role": "Who said this turn", "content": "The message content", "turn_type": "example", "importance": 0.5, "emotional_valence": 0.0, "session_id": "Session ID (auto-generated if omitted)", "tags": [], "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
