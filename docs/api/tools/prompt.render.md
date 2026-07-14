# prompt.render

**Category**: system | **Safety**: read
**Gana**: `gana_net`

## Description

Render a named prompt template with variable substitution and optional Wu Xing tone

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Template name (e.g. session_greeting, memory_synthesis)",
      "default": "session_greeting"
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
      "description": "Wu Xing element for tone selection"
    },
    "variables": {
      "type": "object",
      "description": "Key-value pairs for template variable substitution",
      "default": {}
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
    "prompt.render",
    {"name": "Template name (e.g. session_greeting, memory_synth", "wu_xing": "Wu Xing element for tone selection", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
