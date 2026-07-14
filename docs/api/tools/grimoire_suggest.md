# grimoire_suggest

**Category**: system | **Safety**: read
**Gana**: `gana_willow`

## Description

Suggest Grimoire spells for a given task context

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "task": {
      "type": "string",
      "description": "Task description to match spells against",
      "default": "general guidance"
    },
    "emotional_state": {
      "type": "string",
      "default": "neutral"
    },
    "wu_xing": {
      "type": "string",
      "enum": [
        "wood",
        "fire",
        "earth",
        "metal",
        "water"
      ],
      "default": "earth"
    },
    "urgency": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "default": 0.5
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
  "required": []
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "grimoire_suggest",
    {"task": "Task description to match spells against", "emotional_state": "example", "wu_xing": "example", "urgency": 0.5, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
