# sangha_chat_send

**Category**: system | **Safety**: write
**Gana**: `gana_encampment`

## Description

Send message to Sangha chat channel for multi-agent coordination

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "message": {
      "type": "string",
      "description": "Message content"
    },
    "channel": {
      "type": "string",
      "default": "general"
    },
    "sender": {
      "type": "string",
      "description": "Sender ID"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "priority": {
      "type": "string",
      "enum": [
        "low",
        "normal",
        "high",
        "urgent"
      ],
      "default": "normal"
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
    "message",
    "sender"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "sangha_chat_send",
    {"message": "Message content", "channel": "example", "sender": "Sender ID", "tags": [], "priority": "example", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
